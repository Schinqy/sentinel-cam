import asyncio
import json
import time
import os
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from database import init_db, save_violation, get_all_violations, get_cameras, update_camera_roi
from utils import save_violation_frame, mock_extract_plate

app = FastAPI(title="SentinelCam Detection Hub")

API_KEY = "sentinel-secret-2026"

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
    return x_api_key

# Shared state
latest_frames = {}
camera_configs = {}
active_connections = set()

# AI Model (Mocked for environment stability)
class MockModel:
    def __call__(self, frame, verbose=False):
        return [type('Result', (), {'boxes': []})]

model = MockModel()

def get_placeholder_frame():
    from PIL import Image
    import io
    img = Image.new('RGB', (640, 480), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

async def fetch_camera_stream(cam_id):
    """Background worker that simulates fetching frames and performing detection."""
    print(f"[HUB] Starting fetch task for {cam_id}...")
    
    while True:
        config = camera_configs.get(cam_id)
        if not config: break
        
        await asyncio.sleep(random.randint(10, 20))
        
        timestamp_str = time.strftime("%H:%M:%S")
        v_type = "ILLEGAL_PARKING" if cam_id == "cam1" else "TRAFFIC_VIOLATION"
        confidence = round(random.uniform(0.7, 0.99), 2)
        
        dummy_frame = get_placeholder_frame()
        latest_frames[cam_id] = dummy_frame
        
        image_path = save_violation_frame(dummy_frame, cam_id, v_type)
        plate_number = mock_extract_plate(dummy_frame)
        
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
        
        await asyncio.sleep(0.1)

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
        retention_period = 30 * 24 * 60 * 60 # 30 days
        for filename in os.listdir("captures"):
            filepath = os.path.join("captures", filename)
            if os.path.getmtime(filepath) < now - retention_period:
                try:
                    os.remove(filepath)
                    print(f"[CLEANUP] Deleted {filename}")
                except: pass
        await asyncio.sleep(24 * 60 * 60) # Run once a day

@app.on_event("startup")
async def startup_event():
    await init_db()
    
    if not os.path.exists("captures"):
        os.makedirs("captures")
    app.mount("/captures", StaticFiles(directory="captures"), name="captures")

    # Start cleanup task
    asyncio.create_task(cleanup_old_captures())

    cameras = await get_cameras()
    for cam in cameras:
        cam_id = cam['id']
        camera_configs[cam_id] = cam
        latest_frames[cam_id] = None
        asyncio.create_task(fetch_camera_stream(cam_id))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/video/{cam_id}")
async def video_feed(cam_id: str):
    if cam_id not in camera_configs:
        return {"error": "Camera not found"}
    
    def generate():
        while True:
            frame = latest_frames.get(cam_id)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
