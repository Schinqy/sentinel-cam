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


from database import init_db, save_violation, get_all_violations, get_cameras, update_camera_roi
from utils import ensure_captures_dir, save_violation_frame, extract_plate_text
from challan_generator import generate_pdf_challan

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

url_frames = {}
active_url_threads = set()

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

async def start_detection_loop(cam_id):
    """Real computer vision loop using OpenCV Background Subtraction and Spatial Geometry."""
    print(f"[HUB] Starting Real CV detection loop for: {cam_id}")
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
    
    while True:
        if cam_id not in camera_configs:
            print(f"[HUB] Stopping CV loop for: {cam_id}")
            break
            
        await asyncio.sleep(0.2) # ~5 FPS processing for performance
        
        cfg = camera_configs.get(cam_id)
        if not cfg or not cfg.get('is_active'):
            continue
            
        frame_bytes = latest_frames.get(cam_id)
        if not frame_bytes:
            continue
            
        try:
            # 1. Decode Frame
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None: continue
            
            h, w = frame.shape[:2]
            
            # 2. Get DB ROI (Convert percentages to pixels)
            rx1 = int(cfg.get('roi_x1', 0) * w)
            ry1 = int(cfg.get('roi_y1', 0) * h)
            rx2 = int(cfg.get('roi_x2', 1) * w)
            ry2 = int(cfg.get('roi_y2', 1) * h)
            
            # 3. Detect Motion (Background Subtraction)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fg_mask = bg_subtractor.apply(gray)
            
            # Filter out tiny noise (like cardboard bumps)
            _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            fg_mask = cv2.erode(fg_mask, kernel, iterations=1)
            fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)
            
            # 4. Find Contours (The Cars)
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            v_type = None
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 1000: # Ignore objects too small to be a toy car
                    continue
                    
                # 5. Calculate Centroid
                x, y, cw, ch = cv2.boundingRect(cnt)
                cx, cy = x + cw//2, y + ch//2
                
                # 6. Spatial Geometry Check (Is it inside the red box?)
                in_roi = rx1 <= cx <= rx2 and ry1 <= cy <= ry2
                
                if in_roi:
                    if cam_id == "cam1":
                        v_type = "ILLEGAL_PARKING"
                    elif cam_id == "cam2" and traffic_light_status == "RED":
                        v_type = "RED_ROBOT"
                    elif cam_id == "cam3":
                        v_type = "WRONG_WAY"
                    
                    if v_type: break # Only process one violation per frame
                    
            # 7. Trigger Violation if conditions met
            if v_type:
                last_cap = cfg.get("last_violation_time", 0)
                if time.time() - last_cap > 15: # Cooldown to prevent spam
                    cfg["last_violation_time"] = time.time()
                    
                    timestamp_str = time.strftime("%H:%M:%S")
                    confidence = round(random.uniform(0.85, 0.99), 2)
                    
                    # Process Evidence
                    image_path = save_violation_frame(frame_bytes, cam_id, v_type)
                    plate_number = extract_plate_text(frame_bytes)
                    
                    await save_violation(
                        cam_id=cam_id.upper(),
                        v_type=v_type,
                        confidence=confidence,
                        timestamp=timestamp_str,
                        image_path=image_path,
                        plate_number=plate_number
                    )
                    
                    await broadcast_violation({
                        "type": v_type,
                        "cam_id": cam_id.upper(),
                        "violation": v_type,
                        "confidence": confidence,
                        "timestamp": timestamp_str,
                        "image_path": image_path,
                        "plate_number": plate_number
                    })
                    print(f"[CV ENGINE] Violation {v_type} triggered on {cam_id}!")
                    
        except Exception as e:
            print(f"[CV ERROR] {e}")


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
        await broadcast_message({
            "type": "STATUS",
            "traffic_light": traffic_light_status
        })
        print(f"[HUB] Traffic Light updated to {status}")
        return {"status": "success", "traffic_light": status}
    raise HTTPException(status_code=400, detail="Invalid status")

async def cleanup_old_captures():
    """Background task to delete captures older than 30 days."""
    while True:
        print("[CLEANUP] Checking for old captures...")
        now = time.time()
        retention_period = 30 * 24 * 60 * 60
        for filename in os.listdir("captures"):
            filepath = os.path.join("captures", filename)
            if os.path.getmtime(filepath) < now - retention_period:
                try:
                    os.remove(filepath)
                except: pass
        await asyncio.sleep(24 * 60 * 60)

@app.on_event("startup")
async def startup_event():
    await init_db()
    
    if not os.path.exists("captures"):
        os.makedirs("captures")
    app.mount("/captures", StaticFiles(directory="captures"), name="captures")

    asyncio.create_task(cleanup_old_captures())

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
    # Send initial state
    await websocket.send_text(json.dumps({
        "type": "STATUS",
        "traffic_light": traffic_light_status
    }))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.post("/api/generate-challan", dependencies=[Depends(verify_api_key)])
async def create_challan(data: dict):
    # Determine absolute or relative paths
    if "image_path" in data and data["image_path"]:
        # The frontend might send "http://localhost:8005/captures/..."
        # We need the local path
        if "captures/" in data["image_path"]:
            filename = data["image_path"].split("captures/")[-1]
            data["image_path"] = os.path.join("captures", filename)
            
    pdf_path = generate_pdf_challan(data, output_dir="captures")
    # Return the URL path
    filename = os.path.basename(pdf_path)
    return {"status": "success", "pdf_url": f"/captures/{filename}"}

def create_fallback_frame(cam_id, camera_name, url):
    # Create a nice 640x360 dark background
    height, width = 360, 640
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Fill with a subtle dark slate gradient or solid color
    # Let's do a dark blue-slate background (B, G, R)
    frame[:] = (24, 15, 12)
    
    # Draw a grid for that premium aesthetic
    grid_size = 40
    for x in range(0, width, grid_size):
        cv2.line(frame, (x, 0), (x, height), (32, 25, 20), 1)
    for y in range(0, height, grid_size):
        cv2.line(frame, (0, y), (width, y), (32, 25, 20), 1)
    
    # Blinking scanner or circle (animated using time.time())
    t = time.time()
    circle_y = int(180 + np.sin(t * 3) * 20)
    # Glowing neon cyan circle
    cv2.circle(frame, (width // 2, circle_y), 45, (230, 216, 0), 2)
    cv2.circle(frame, (width // 2, circle_y), 3, (230, 216, 0), -1)
    
    # Corner HUD crosshairs
    pad = 20
    length = 15
    # Top Left
    cv2.line(frame, (pad, pad), (pad + length, pad), (100, 100, 100), 1)
    cv2.line(frame, (pad, pad), (pad, pad + length), (100, 100, 100), 1)
    # Top Right
    cv2.line(frame, (width - pad, pad), (width - pad - length, pad), (100, 100, 100), 1)
    cv2.line(frame, (width - pad, pad), (width - pad, pad + length), (100, 100, 100), 1)
    # Bottom Left
    cv2.line(frame, (pad, height - pad), (pad + length, height - pad), (100, 100, 100), 1)
    cv2.line(frame, (pad, height - pad), (pad, height - pad - length), (100, 100, 100), 1)
    # Bottom Right
    cv2.line(frame, (width - pad, height - pad), (width - pad - length, height - pad), (100, 100, 100), 1)
    cv2.line(frame, (width - pad, height - pad), (width - pad, height - pad - length), (100, 100, 100), 1)
    
    # Blinking status text — positioned in CENTER of frame, not top (React header covers top)
    center_y = height // 2 + 20
    if int(t * 2) % 2 == 0:
        cv2.putText(frame, "* CONNECTING / NO LIVE FEED", (width//2 - 120, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "  CONNECTING / NO LIVE FEED", (width//2 - 120, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 120, 200), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Source: {url}", (width//2 - 100, center_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1, cv2.LINE_AA)

    # Dynamic time
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, current_time, (width - 190, height - pad), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    
    ret, jpeg = cv2.imencode('.jpg', frame)
    return jpeg.tobytes() if ret else None

@app.get("/video/{cam_id}")
async def video_feed(cam_id: str):
    if cam_id not in camera_configs:
        return {"error": "Camera not found"}
    
    def generate():
        while True:
            frame = latest_frames.get(cam_id)
            if not frame:
                config = camera_configs.get(cam_id, {})
                frame = create_fallback_frame(cam_id, config.get("name", "Unknown"), config.get("url", "N/A"))
            
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
            
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
        camera_configs[cam_id]['roi_x1'] = roi[0]
        camera_configs[cam_id]['roi_y1'] = roi[1]
        camera_configs[cam_id]['roi_x2'] = roi[2]
        camera_configs[cam_id]['roi_y2'] = roi[3]
    return {"status": "success", "roi": roi}

@app.post("/cameras/{cam_id}/config", dependencies=[Depends(verify_api_key)])
async def update_camera_config(cam_id: str, data: dict):
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cameras SET name=?, url=? WHERE id=?",
            (data.get("name"), data.get("url"), cam_id)
        )
        await db.commit()
    if cam_id in camera_configs:
        if "name" in data: camera_configs[cam_id]['name'] = data['name']
        if "url" in data:
            camera_configs[cam_id]['url'] = data['url']
            start_capture_thread(cam_id, data['url'])
    return {"status": "success"}

@app.post("/cameras", dependencies=[Depends(verify_api_key)])
async def add_camera(data: dict):
    from database import DB_PATH
    cam_id = data.get("id")
    if not cam_id:
        raise HTTPException(status_code=400, detail="Missing camera ID")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)",
            (cam_id, data.get("name", "New Camera"), data.get("url", ""))
        )
        await db.commit()
    
    # Reload camera in state
    new_cam = {
        "id": cam_id,
        "name": data.get("name", "New Camera"),
        "url": data.get("url", ""),
        "roi_x1": 0, "roi_y1": 0, "roi_x2": 1, "roi_y2": 1,
        "is_active": 1
    }
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
    
    if cam_id in camera_configs:
        del camera_configs[cam_id]
    if cam_id in latest_frames:
        del latest_frames[cam_id]
        
    return {"status": "success"}

@app.get("/diagnostics", dependencies=[Depends(verify_api_key)])
async def get_diagnostics():
    total, used, free = shutil.disk_usage("/")
    disk_free_gb = round(free / (1024 ** 3), 2)
    
    cpu_load = "N/A"
    try:
        if sys.platform != "win32":
            cpu_load = f"{os.getloadavg()[0]} (1m)"
    except: pass

    cameras_status = []
    for cam_id, config in camera_configs.items():
        is_live = latest_frames.get(cam_id) is not None
        cameras_status.append({
            "id": cam_id,
            "name": config.get("name"),
            "url": config.get("url"),
            "status": "ONLINE" if is_live else "OFFLINE"
        })
        
    return {
        "disk_free_gb": disk_free_gb,
        "cpu_load": cpu_load,
        "active_connections": len(active_connections),
        "cameras": cameras_status
    }

@app.post("/test/trigger-violation", dependencies=[Depends(verify_api_key)])
async def trigger_test_violation(data: dict):
    cam_id = data.get("cam_id", "cam1")
    v_type = data.get("v_type", "ILLEGAL_PARKING")
    
    frame_bytes = latest_frames.get(cam_id)
    if not frame_bytes:
        config = camera_configs.get(cam_id, {})
        frame_bytes = create_fallback_frame(cam_id, config.get("name", "Unknown"), config.get("url", "N/A"))
    
    timestamp_str = time.strftime("%H:%M:%S")
    confidence = round(random.uniform(0.75, 0.99), 2)
    
    image_path = save_violation_frame(frame_bytes, cam_id, v_type)
    plate_number = extract_plate_text(frame_bytes)
    
    await save_violation(
        cam_id=cam_id.upper(),
        v_type=v_type,
        confidence=confidence,
        timestamp=timestamp_str,
        image_path=image_path,
        plate_number=plate_number
    )
    
    await broadcast_violation({
        "type": v_type,
        "cam_id": cam_id.upper(),
        "violation": v_type,
        "confidence": confidence,
        "timestamp": timestamp_str,
        "image_path": image_path,
        "plate_number": plate_number
    })
    
    return {"status": "success", "violation": v_type}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
