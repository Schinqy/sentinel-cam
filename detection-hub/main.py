import asyncio
import json
import time
import os
import random
import sys
import shutil
import threading
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
from starlette.responses import StreamingResponse
import numpy as np


from database import init_db, save_violation, get_all_violations, get_cameras, update_camera_roi
from utils import save_violation_frame, mock_extract_plate

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

def start_capture_thread(cam_id, url):
    """Real OpenCV video capture worker."""
    def run_capture():
        print(f"[HUB] Connecting to real stream for {cam_id} using URL: {url}")
        
        # Check if URL is an integer (e.g., "0" or "1" for local webcams)
        source = url
        try:
            if str(url).strip().isdigit():
                source = int(url)
        except:
            pass

        cap = cv2.VideoCapture(source)
        while True:
            if cam_id not in camera_configs or camera_configs[cam_id]['url'] != url:
                cap.release()
                break
            
            ret, frame = cap.read()
            if not ret:
                time.sleep(2)
                cap.open(source)
                continue
            
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                latest_frames[cam_id] = jpeg.tobytes()
                
    t = threading.Thread(target=run_capture, daemon=True)
    t.start()


async def process_violations(cam_id):
    """Background task to simulate periodic traffic events for active camera streams."""
    while True:
        await asyncio.sleep(random.randint(15, 30))
        frame_bytes = latest_frames.get(cam_id)
        if frame_bytes:
            timestamp_str = time.strftime("%H:%M:%S")
            v_type = "ILLEGAL_PARKING" if cam_id == "cam1" else "TRAFFIC_VIOLATION"
            confidence = round(random.uniform(0.7, 0.99), 2)
            
            image_path = save_violation_frame(frame_bytes, cam_id, v_type)
            plate_number = mock_extract_plate(frame_bytes)
            
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

async def broadcast_violation(data):
    if active_connections:
        message = json.dumps(data)
        for connection in active_connections:
            try: await connection.send_text(message)
            except: pass

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
        asyncio.create_task(process_violations(cam_id))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

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
    
    # Draw blinking amber text or "SENTINEL-CAM"
    # Blinks every second
    if int(t * 2) % 2 == 0:
        cv2.putText(frame, "* CONNECTING / NO LIVE FEED", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "  CONNECTING / NO LIVE FEED", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 200), 1, cv2.LINE_AA)

    # Put camera metadata
    cv2.putText(frame, f"NODE: {cam_id.upper()}", (30, height - pad - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.putText(frame, f"NAME: {camera_name}", (30, height - pad - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.putText(frame, f"SOURCE: {url}", (30, height - pad), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1, cv2.LINE_AA)

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
async def update_roi(cam_id: str, roi: list):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
