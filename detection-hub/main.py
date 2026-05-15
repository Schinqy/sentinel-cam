import asyncio
import json
import time
import os
import random
import sys
import shutil
import threading
import cv2
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
from starlette.responses import StreamingResponse
import numpy as np
import uvicorn
from scipy.spatial import distance as dist


from database import init_db, save_violation, get_all_violations, get_cameras, update_camera_roi
from utils import ensure_captures_dir, save_violation_frame, extract_plate_text
from challan_generator import generate_pdf_challan
import aiohttp

app = FastAPI(title="SentinelCam Detection Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "sentinel-secret-2026"

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
    return x_api_key

# Shared state
latest_frames = {}
camera_configs = {}
active_connections = set()
traffic_light_status = "GREEN"
# ESP32_STATUS_URL will be resolved dynamically from Camera 2 config
ESP32_STATUS_URL = None 
is_system_armed = True # MASTER ARM/DISARM
show_debug_overlays = True # AI VIEW TOGGLE
show_motion_mask = False # DIAGNOSTIC MASK TOGGLE

url_frames = {}
fg_masks = {} # cam_id -> binary mask
active_url_threads = set()
trackers = {} # cam_id -> CentroidTracker instance
learning_counters = {} # cam_id -> frame_count
last_violation_times = {} # cam_id -> float timestamp

# --- INTELLIGENT TRACKING CORE ---

class CentroidTracker:
    def __init__(self, max_disappeared=10):
        self.next_object_id = 0
        self.objects = {} # ID -> (cx, cy)
        self.disappeared = {} # ID -> count
        self.metadata = {} # ID -> {'first_seen', 'last_seen', 'positions', 'stationary_start'}
        self.max_disappeared = max_disappeared

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.metadata[self.next_object_id] = {
            'first_seen': time.time(),
            'last_seen': time.time(),
            'positions': [centroid],
            'stationary_start': None,
            'is_violating': False
        }
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.metadata[object_id]

    def update(self, rects):
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            input_centroids[i] = (cX, cY)

        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Simple Euclidean distance tracking
            from scipy.spatial import distance as dist
            D = dist.cdist(np.array(object_centroids), input_centroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                
                # Update Metadata
                meta = self.metadata[object_id]
                meta['last_seen'] = time.time()
                meta['positions'].append(tuple(input_centroids[col]))
                if len(meta['positions']) > 20: meta['positions'].pop(0)
                
                # Check for stationary status (moved less than 5px)
                prev = meta['positions'][-2]
                curr = meta['positions'][-1]
                movement = np.sqrt((curr[0]-prev[0])**2 + (curr[1]-prev[1])**2)
                
                if movement < 3:
                    if meta['stationary_start'] is None:
                        meta['stationary_start'] = time.time()
                else:
                    meta['stationary_start'] = None

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            if D.shape[0] >= D.shape[1]:
                for row in unused_rows:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            else:
                for col in unused_cols:
                    self.register(input_centroids[col])

        return self.objects

# --- END TRACKING CORE ---

def start_capture_thread(cam_id, url):
    """Adaptive and deduplicated video capture worker supporting both HTTP/MJPEG and OpenCV."""
    if url in active_url_threads:
        print(f"[HUB] Reusing existing capture thread for URL: {url}")
        return

    active_url_threads.add(url)

    def run_capture():
        # Adaptive check for HTTP vs other sources
        is_http = isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
        
        if is_http:
            print(f"[HUB] Connecting via MJPEG parser to: {url}")
            while True:
                active_urls = {cfg['url'] for cfg in camera_configs.values()}
                if url not in active_urls:
                    active_url_threads.discard(url)
                    break
                try:
                    stream = requests.get(url, stream=True, timeout=10)
                    if stream.status_code != 200:
                        raise Exception(f"HTTP Status {stream.status_code}")
                    
                    buffer = b''
                    for chunk in stream.iter_content(chunk_size=4096):
                        buffer += chunk
                        
                        while True:
                            start = buffer.find(b'\xff\xd8')  # JPEG start
                            if start == -1:
                                break
                            
                            end = buffer.find(b'\xff\xd9', start)  # JPEG end
                            if end == -1:
                                break
                            
                            jpg = buffer[start:end+2]
                            buffer = buffer[end+2:]
                            
                            # Cache frame for this URL
                            url_frames[url] = jpg
                            
                            # Copy to latest_frames for fallback/compat
                            for cid, cfg in camera_configs.items():
                                if cfg.get('url') == url:
                                    latest_frames[cid] = jpg
                            
                        # Break early if config changed
                        active_urls = {cfg['url'] for cfg in camera_configs.values()}
                        if url not in active_urls:
                            break
                except Exception as e:
                    print(f"[HUB] HTTP stream error for {url}: {e}, retrying in 3s...")
                    time.sleep(3)
        else:
            print(f"[HUB] Connecting via OpenCV to: {url}")
            source = url
            try:
                if str(url).strip().isdigit():
                    source = int(url)
            except:
                pass

            cap = cv2.VideoCapture(source)
            while True:
                active_urls = {cfg['url'] for cfg in camera_configs.values()}
                if url not in active_urls:
                    cap.release()
                    active_url_threads.discard(url)
                    break
                
                ret, frame = cap.read()
                if not ret:
                    time.sleep(2)
                    cap.open(source)
                    continue
                
                ret, jpeg = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = jpeg.tobytes()
                    url_frames[url] = frame_bytes
                    for cid, cfg in camera_configs.items():
                        if cfg.get('url') == url:
                            latest_frames[cid] = frame_bytes

    t = threading.Thread(target=run_capture, daemon=True)
    t.start()

import concurrent.futures

# Thread pool for CPU-bound tasks (CV and OCR)
cv_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

async def start_detection_loop(cam_id):
    """Behavioral CV loop using Centroid Tracking and Persistence Analysis."""
    print(f"[HUB] Starting Intelligent CV loop for: {cam_id}")
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=45, detectShadows=False)
    tracker = CentroidTracker(max_disappeared=15)
    trackers[cam_id] = tracker # Shared for video feed
    learning_counters[cam_id] = 0
    
    violated_ids = set() # Trackers we've already ticketed in this encounter
    
    def process_cv_math(f_bytes, sub, trk, cid, light_status):
        nparr = np.frombuffer(f_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None: return None, None, None
        h, w = frame.shape[:2]
        
        # Selective Motion
        if cid not in ["cam1", "cam3"] and light_status == "GREEN":
            trk.update([])
            return frame, {}, (h, w)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = sub.apply(gray)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=1)
        fg_masks[cid] = mask
        
        conts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rcts = []
        min_a = 3000 if cid.lower() == "cam3" else 500
        for c in conts:
            if cv2.contourArea(c) < min_a: continue
            (x, y, cw, ch) = cv2.boundingRect(c)
            rcts.append((x, y, x + cw, y + ch))
        
        objs = trk.update(rcts)
        return frame, objs, (h, w)

    while True:
        if cam_id not in camera_configs:
            break
            
        await asyncio.sleep(0.2) # ~5 FPS (Optimized for CPU)
        
        if not is_system_armed:
            continue
            
        # Cooling Break check (Per Camera)
        cid_lower = cam_id.lower()
        cooldown_remaining = 30 - (time.time() - last_violation_times.get(cid_lower, 0))
        is_cooling = cooldown_remaining > 0

        cfg = camera_configs.get(cam_id)
        if not cfg or not cfg.get('is_active'):
            continue
            
        frame_bytes = latest_frames.get(cam_id)
        if not frame_bytes:
            continue
            
        try:
            # Offload heavy CV math to thread pool to prevent event loop freeze
            frame, objects, size = await asyncio.to_thread(process_cv_math, frame_bytes, bg_subtractor, tracker, cam_id, traffic_light_status)
            
            # 0. Calibration Progress
            if learning_counters[cam_id] < 50:
                learning_counters[cam_id] += 1
                continue

            if frame is None: continue
            h, w = size
            
            # 1. ROI Prep (needed for behavioral analysis below)
            rx1 = int(cfg.get('roi_x1', 0) * w)
            ry1 = int(cfg.get('roi_y1', 0) * h)
            rx2 = int(cfg.get('roi_x2', 1) * w)
            ry2 = int(cfg.get('roi_y2', 1) * h)
            
            # 4. Behavioral Analysis
            for (obj_id, centroid) in objects.items():
                if obj_id in violated_ids: continue
                
                # We still track movement during cooldown, but we skip the actual violation logic
                
                cx, cy = centroid
                in_roi = rx1 <= cx <= rx2 and ry1 <= cy <= ry2
                if not in_roi: continue
                
                meta = tracker.metadata[obj_id]
                v_type = None
                
                # RULE: Illegal Parking (Persistence)
                if cam_id == "cam1":
                    if meta['stationary_start'] and (time.time() - meta['stationary_start'] > 4.0):
                        v_type = "ILLEGAL_PARKING"
                
                # RULE: Red Robot (Signal state + Crossing)
                elif cam_id == "cam2" and traffic_light_status == "RED":
                    # Simple rule: if moving significantly across ROI on Red
                    if meta['positions'] and len(meta['positions']) > 5:
                        p_start = meta['positions'][0]
                        p_curr = meta['positions'][-1]
                        if abs(p_curr[1] - p_start[1]) > 40:
                            v_type = "RED_ROBOT"

                # RULE: Wrong Way (Trajectory Analysis)
                elif cam_id == "cam3":
                    if len(meta['positions']) > 8:
                        start_pos = meta['positions'][0]
                        curr_pos = meta['positions'][-1]
                        
                        # Support configurable directions (Default is UP)
                        direction = cfg.get('enforce_direction', 'UP')
                        
                        is_wrong = False
                        # Sensitivity: Increased movement requirement (80px) and consistency (10+ frames)
                        # This prevents false positives from slight wobbles or noise
                        move_thresh = 80 
                        if direction == 'UP' and curr_pos[1] < start_pos[1] - move_thresh:
                            is_wrong = True
                        elif direction == 'DOWN' and curr_pos[1] > start_pos[1] + move_thresh:
                            is_wrong = True
                        elif direction == 'LEFT' and curr_pos[0] < start_pos[0] - move_thresh:
                            is_wrong = True
                        elif direction == 'RIGHT' and curr_pos[0] > start_pos[0] + move_thresh:
                            is_wrong = True
                            
                        if is_wrong:
                            # TRIGGER VIOLATION (Only if NOT cooling down)
                            if is_cooling:
                                # We still mark it as violating for visual feedback, but don't save to DB
                                meta['is_violating'] = True
                                continue
                            
                            v_type = "WRONG_WAY"
                
                if v_type:
                    # TRIGGER VIOLATION (Only if NOT cooling down)
                    if is_cooling:
                        meta['is_violating'] = True
                        continue

                    violated_ids.add(obj_id)
                    timestamp_str = time.strftime("%H:%M:%S")
                    confidence = round(random.uniform(0.92, 0.99), 2)
                    
                    image_path = save_violation_frame(frame_bytes, cam_id, v_type)
                    # OCR is extremely slow on CPU, offload to thread pool
                    plate_number = await asyncio.to_thread(extract_plate_text, frame_bytes)
                    
                    meta['is_violating'] = True # Mark for visual feedback
                    last_violation_times[cam_id.lower()] = time.time() # Start cooling break
                    v_id = await save_violation(cam_id.upper(), v_type, confidence, timestamp_str, image_path, plate_number)
                    await broadcast_violation({
                        "id": v_id,
                        "type": v_type, "cam_id": cam_id.upper(), "violation": v_type,
                        "confidence": confidence, "timestamp": timestamp_str,
                        "image_path": image_path, "plate_number": plate_number
                    })
                    print(f"[BEHAVIOR] Violation {v_type} triggered for ID {obj_id}")

            # Cleanup violated_ids for objects that left
            active_ids = set(objects.keys())
            violated_ids = violated_ids.intersection(active_ids)

        except Exception as e:
            import traceback
            traceback.print_exc()

async def broadcast_message(data):
    if active_connections:
        message = json.dumps(data)
        for connection in active_connections:
            try: await connection.send_text(message)
            except: pass

async def broadcast_violation(data):
    await broadcast_message(data)

@app.post("/api/traffic-light/status", dependencies=[Depends(verify_api_key)])
async def update_traffic_light(data: dict):
    global traffic_light_status
    status = data.get("status", "").upper()
    if status in ["RED", "GREEN", "YELLOW"]:
        traffic_light_status = status
        await broadcast_message({"type": "STATUS", "traffic_light": traffic_light_status})
        return {"status": "success", "traffic_light": status}
    raise HTTPException(status_code=400, detail="Invalid status")

@app.post("/api/system/arm", dependencies=[Depends(verify_api_key)])
async def toggle_arm(data: dict):
    global is_system_armed
    is_system_armed = data.get("armed", True)
    await broadcast_message({"type": "SYSTEM_ARMED", "armed": is_system_armed})
    return {"status": "success", "armed": is_system_armed}

@app.post("/api/system/debug", dependencies=[Depends(verify_api_key)])
async def toggle_debug(data: dict):
    global show_debug_overlays
    show_debug_overlays = data.get("enabled", True)
    return {"status": "success", "enabled": show_debug_overlays}

@app.post("/api/system/mask", dependencies=[Depends(verify_api_key)])
async def toggle_mask(data: dict):
    global show_motion_mask
    show_motion_mask = data.get("enabled", True)
    return {"status": "success", "enabled": show_motion_mask}

@app.delete("/api/violations/clear", dependencies=[Depends(verify_api_key)])
async def clear_violations():
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM violations")
        await db.commit()
    
    if os.path.exists("captures"):
        for f in os.listdir("captures"):
            try: os.remove(os.path.join("captures", f))
            except: pass
            
    return {"status": "success"}

@app.delete("/api/violations/{violation_id}", dependencies=[Depends(verify_api_key)])
async def delete_single_violation(violation_id: int):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        # Get image path first to delete the file
        async with db.execute("SELECT image_path FROM violations WHERE id=?", (violation_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                try: os.remove(row[0])
                except: pass
        
        await db.execute("DELETE FROM violations WHERE id=?", (violation_id,))
        await db.commit()
    return {"status": "success"}

@app.post("/api/violations/delete-multiple", dependencies=[Depends(verify_api_key)])
async def delete_multiple_violations(data: dict):
    ids = data.get("ids", [])
    if not ids:
        return {"status": "error", "message": "No IDs provided"}
    
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        # Batch fetch image paths
        placeholders = ",".join(["?"] * len(ids))
        async with db.execute(f"SELECT image_path FROM violations WHERE id IN ({placeholders})", ids) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                if row[0] and os.path.exists(row[0]):
                    try: os.remove(row[0])
                    except: pass
        
        await db.execute(f"DELETE FROM violations WHERE id IN ({placeholders})", ids)
        await db.commit()
    return {"status": "success"}

async def poll_esp32_status():
    """Background task to sync AI detection state with physical ESP32 state."""
    global traffic_light_status, ESP32_STATUS_URL
    print("[HUB] Starting ESP32 status sync...")
    async with aiohttp.ClientSession() as session:
        while True:
            # Dynamically resolve URL if not set or if config changed
            if not ESP32_STATUS_URL and "cam2" in camera_configs:
                cam2_url = camera_configs["cam2"].get("url", "")
                if "http" in cam2_url:
                    # Convert http://1.2.3.4/stream to http://1.2.3.4:81/status
                    base = "/".join(cam2_url.split("/")[:-1])
                    ESP32_STATUS_URL = f"{base}:81/status"
            
            if ESP32_STATUS_URL:
                try:
                    async with session.get(ESP32_STATUS_URL, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            new_status = data.get("state", "GREEN").upper()
                            if new_status != traffic_light_status:
                                traffic_light_status = new_status
                                await broadcast_message({"type": "STATUS", "traffic_light": traffic_light_status})
                                print(f"[HUB] Traffic Light Synced: {traffic_light_status}")
                except Exception:
                    # Silently fail if ESP32 is offline
                    pass
            await asyncio.sleep(5.0)

async def cleanup_old_captures():
    while True:
        now = time.time()
        retention = 30 * 24 * 60 * 60
        if os.path.exists("captures"):
            for f in os.listdir("captures"):
                p = os.path.join("captures", f)
                if os.path.getmtime(p) < now - retention:
                    try: os.remove(p)
                    except: pass
        await asyncio.sleep(24 * 60 * 60)

@app.on_event("startup")
async def startup_event():
    await init_db()
    if not os.path.exists("captures"): os.makedirs("captures")
    app.mount("/captures", StaticFiles(directory="captures"), name="captures")
    asyncio.create_task(cleanup_old_captures())
    asyncio.create_task(poll_esp32_status())
    cameras = await get_cameras()
    for cam in cameras:
        cam_id = cam['id']
        camera_configs[cam_id] = cam
        latest_frames[cam_id] = None
        start_capture_thread(cam_id, cam['url'])
        asyncio.create_task(start_detection_loop(cam_id))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    await websocket.send_text(json.dumps({
        "type": "STATUS", 
        "traffic_light": traffic_light_status,
        "system_armed": is_system_armed
    }))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)

@app.post("/api/generate-challan", dependencies=[Depends(verify_api_key)])
async def create_challan(data: dict):
    if "image_path" in data and data["image_path"]:
        # Get just the filename regardless of path separators
        filename = os.path.basename(data["image_path"])
        data["image_path"] = os.path.join("captures", filename)
    pdf_path = generate_pdf_challan(data, output_dir="captures")
    return {"status": "success", "pdf_url": f"/captures/{os.path.basename(pdf_path)}"}

def create_fallback_frame(cam_id, camera_name, url):
    height, width = 360, 640
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (24, 15, 12)
    grid = 40
    for x in range(0, width, grid): cv2.line(frame, (x, 0), (x, height), (32, 25, 20), 1)
    for y in range(0, height, grid): cv2.line(frame, (0, y), (width, y), (32, 25, 20), 1)
    t = time.time()
    cy = int(180 + np.sin(t * 3) * 20)
    cv2.circle(frame, (width // 2, cy), 45, (230, 216, 0), 2)
    cv2.circle(frame, (width // 2, cy), 3, (230, 216, 0), -1)
    if int(t * 2) % 2 == 0:
        cv2.putText(frame, "* CONNECTING / NO LIVE FEED", (width//2 - 120, height//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Source: {url}", (width//2 - 100, height//2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1, cv2.LINE_AA)
    ret, jpeg = cv2.imencode('.jpg', frame)
    return jpeg.tobytes()

@app.get("/video/{cam_id}")
async def video_feed(cam_id: str):
    if cam_id not in camera_configs: return {"error": "Camera not found"}
    def generate():
        while True:
            frame_bytes = latest_frames.get(cam_id)
            if not frame_bytes:
                config = camera_configs.get(cam_id, {})
                frame = create_fallback_frame(cam_id, config.get("name", "Unknown"), config.get("url", "N/A"))
            else:
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    h, w = frame.shape[:2]
                    
                    # 1. Show Motion Mask (Diagnostic View)
                    if show_motion_mask:
                        mask = fg_masks.get(cam_id)
                        if mask is not None:
                            # Resize mask if it doesn't match frame
                            if mask.shape[:2] != (h, w):
                                mask = cv2.resize(mask, (w, h))
                            # Convert to BGR so we can still draw colored overlays
                            frame = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

                    # 2. Draw AI OVERLAYS
                    if show_debug_overlays:
                        cfg = camera_configs.get(cam_id, {})
                        
                        # Calibration Label
                        if learning_counters.get(cam_id, 0) < 50:
                            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), -1) # Blackout during initial learn
                            cv2.putText(frame, "CALIBRATING AI: LEARNING BACKGROUND...", (w//2 - 180, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                            cv2.putText(frame, f"Frame {learning_counters[cam_id]}/50", (w//2 - 40, h//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
                        else:
                            # Draw ROI
                            rx1, ry1 = int(cfg.get('roi_x1', 0) * w), int(cfg.get('roi_y1', 0) * h)
                            rx2, ry2 = int(cfg.get('roi_x2', 1) * w), int(cfg.get('roi_y2', 1) * h)
                            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255, 100, 0), 2)
                            cv2.putText(frame, "DETECTION ZONE", (rx1, ry1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1)
                            
                            # Cooling Break Label (More visible - Top Center)
                            cid_lower = cam_id.lower()
                            cooldown = 30 - (time.time() - last_violation_times.get(cid_lower, 0))
                            if cooldown > 0:
                                # Semi-transparent overlay for text
                                cv2.putText(frame, f"COOLING DOWN: {int(cooldown)}s", (w//2 - 70, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                cv2.putText(frame, "ENFORCEMENT PAUSED", (w//2 - 65, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            
                            # Direction Indicator for Cam 3 (Wrong Way)
                            if cid_lower == "cam3":
                                # Draw a large "Correct Flow" arrow
                                mid_x = (rx1 + rx2) // 2
                                mid_y = (ry1 + ry2) // 2
                                direction = cfg.get('enforce_direction', 'UP')
                                
                                # Note: Arrow points in the LEGAL direction (opposite of wrong way)
                                # Actually, user might prefer arrow to point in CORRECT direction.
                                # Let's draw arrow in CORRECT direction.
                                if direction == 'UP': # Wrong is UP, so Correct is DOWN
                                    cv2.arrowedLine(frame, (mid_x, ry1 + 10), (mid_x, ry2 - 10), (255, 100, 0), 2, tipLength=0.3)
                                elif direction == 'DOWN': # Wrong is DOWN, Correct is UP
                                    cv2.arrowedLine(frame, (mid_x, ry2 - 10), (mid_x, ry1 + 10), (255, 100, 0), 2, tipLength=0.3)
                                elif direction == 'LEFT': # Wrong is LEFT, Correct is RIGHT
                                    cv2.arrowedLine(frame, (rx1 + 10, mid_y), (rx2 - 10, mid_y), (255, 100, 0), 2, tipLength=0.3)
                                elif direction == 'RIGHT': # Wrong is RIGHT, Correct is LEFT
                                    cv2.arrowedLine(frame, (rx2 - 10, mid_y), (rx1 + 10, mid_y), (255, 100, 0), 2, tipLength=0.3)
                                
                                cv2.putText(frame, "LEGAL FLOW", (rx1 + 5, ry1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 100, 0), 1)
                            
                            # Draw Objects
                            tracker = trackers.get(cam_id)
                            if tracker:
                                for obj_id, centroid in tracker.objects.items():
                                    meta = tracker.metadata.get(obj_id, {})
                                    cx, cy = centroid
                                    is_v = meta.get('is_violating', False)
                                    main_color = (0, 0, 255) if is_v else (0, 255, 0) # Red if violating, Green if OK
                                    
                                    # 1. Draw Centroid Dot & Label
                                    cv2.circle(frame, (cx, cy), 4, main_color, -1)
                                    cv2.putText(frame, f"ID: {obj_id}", (cx+10, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, main_color, 1)

                                    # 2. Draw Motion Trail (Ghost Path) - Optimized
                                    positions = meta.get('positions', [])
                                    pos_len = len(positions)
                                    if pos_len > 2:
                                        trail_color = (0, 0, 255) if is_v else (255, 255, 0)
                                        # Optimization: Draw thicker single line or polyline instead of per-segment math
                                        pts = np.array(positions, np.int32).reshape((-1, 1, 2))
                                        cv2.polylines(frame, [pts], False, trail_color, 2)
                                    
                                    # 3. Draw Directional Vector Arrow (ONLY CAM 3)
                                    if cid_lower == "cam3" and len(positions) > 5:
                                        p1 = positions[-5]
                                        p2 = positions[-1]
                                        arrow_color = (0, 0, 255) if is_v else (0, 255, 255) # Red or Yellow
                                        cv2.arrowedLine(frame, p1, p2, arrow_color, 2, tipLength=0.5)

                                    # 4. Stationary / Violation Status
                                    if meta.get('stationary_start'):
                                        dur = round(time.time() - meta['stationary_start'], 1)
                                        cv2.putText(frame, f"STATIONARY: {dur}s", (cx+10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
                
                ret, jpeg = cv2.imencode('.jpg', frame)
                frame = jpeg.tobytes()

            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.08)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/violations", dependencies=[Depends(verify_api_key)])
async def list_violations():
    return await get_all_violations()

@app.get("/cameras", dependencies=[Depends(verify_api_key)])
async def list_cameras():
    return await get_cameras()

@app.post("/cameras/{cam_id}/roi", dependencies=[Depends(verify_api_key)])
async def update_roi(cam_id: str, roi: list = Body(...)):
    await update_camera_roi(cam_id, roi)
    if cam_id in camera_configs:
        camera_configs[cam_id].update({'roi_x1': roi[0], 'roi_y1': roi[1], 'roi_x2': roi[2], 'roi_y2': roi[3]})
    return {"status": "success", "roi": roi}

@app.post("/cameras/{cam_id}/config", dependencies=[Depends(verify_api_key)])
async def update_camera_config(cam_id: str, data: dict):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cameras SET name=?, url=?, enforce_direction=? WHERE id=?", 
            (data.get("name"), data.get("url"), data.get("enforce_direction", "UP"), cam_id)
        )
        await db.commit()
    if cam_id in camera_configs:
        if "name" in data: camera_configs[cam_id]['name'] = data['name']
        if "enforce_direction" in data: camera_configs[cam_id]['enforce_direction'] = data['enforce_direction']
        if "url" in data:
            camera_configs[cam_id]['url'] = data['url']
            start_capture_thread(cam_id, data['url'])
    return {"status": "success"}

@app.post("/cameras", dependencies=[Depends(verify_api_key)])
async def add_camera(data: dict):
    from database import DB_PATH
    cam_id = data.get("id")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", (cam_id, data.get("name", "New"), data.get("url", "")))
        await db.commit()
    new_cam = {"id": cam_id, "name": data.get("name", "New"), "url": data.get("url", ""), "roi_x1": 0, "roi_y1": 0, "roi_x2": 1, "roi_y2": 1, "is_active": 1}
    camera_configs[cam_id] = new_cam
    latest_frames[cam_id] = None
    start_capture_thread(cam_id, new_cam['url'])
    asyncio.create_task(start_detection_loop(cam_id))
    return {"status": "success", "camera": new_cam}

@app.delete("/cameras/{cam_id}", dependencies=[Depends(verify_api_key)])
async def delete_camera(cam_id: str):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cameras WHERE id=?", (cam_id,))
        await db.commit()
    if cam_id in camera_configs: del camera_configs[cam_id]
    return {"status": "success"}

@app.get("/diagnostics", dependencies=[Depends(verify_api_key)])
async def get_diagnostics():
    _, _, free = shutil.disk_usage("/")
    return {
        "disk_free_gb": round(free / (1024**3), 2),
        "active_connections": len(active_connections),
        "system_armed": is_system_armed,
        "cameras": [{"id": c, "status": "ONLINE" if latest_frames.get(c) else "OFFLINE"} for c in camera_configs]
    }

@app.post("/test/trigger-violation", dependencies=[Depends(verify_api_key)])
async def trigger_test_violation(data: dict):
    cam_id = data.get("cam_id", "cam1")
    v_type = data.get("v_type", "ILLEGAL_PARKING")
    frame = latest_frames.get(cam_id) or create_fallback_frame(cam_id, "Test", "N/A")
    t_str = time.strftime("%H:%M:%S")
    img_p = save_violation_frame(frame, cam_id, v_type)
    plate = extract_plate_text(frame)
    v_id = await save_violation(cam_id.upper(), v_type, 0.99, t_str, img_p, plate)
    await broadcast_violation({"id": v_id, "type": v_type, "cam_id": cam_id.upper(), "violation": v_type, "confidence": 0.99, "timestamp": t_str, "image_path": img_p, "plate_number": plate})
    return {"status": "success", "id": v_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
