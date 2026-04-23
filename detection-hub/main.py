import asyncio
import cv2
import json
import time
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse
from ultralytics import YOLO

from database import init_db, save_violation, get_all_violations
from utils import save_violation_frame

app = FastAPI(title="SentinelCam Detection Hub")

# Configuration
CAMERAS = {
    "cam1": "http://192.168.1.45/stream",
    "cam2": "http://192.168.1.46/stream",
    "cam3": "http://192.168.1.47/stream",
}

# Shared state
latest_frames = {id: None for id in CAMERAS}
active_connections = set()

# AI Model Initialization (Placeholder)
model = YOLO("yolov8n.pt") # Small model for scale objects

async def fetch_camera_stream(cam_id, url):
    """
    Background worker that fetches frames from an ESP32-CAM MJPEG stream,
    performs object detection, and checks for violations.
    """
    print(f"[HUB] Starting fetch for {cam_id} at {url}...")
    
    # Define ROI for each camera (normalized coordinates [x1, y1, x2, y2])
    # Example: Cam 1 concentrates on the lower center area for "parking"
    ROIs = {
        "cam1": [0.2, 0.5, 0.8, 0.9],
        "cam2": [0.1, 0.1, 0.9, 0.4],
        "cam3": [0.3, 0.3, 0.7, 0.7]
    }
    roi = ROIs.get(cam_id, [0, 0, 1, 1])

    cap = cv2.VideoCapture(url)
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            # Run inference every 5th frame to save CPU
            if frame_count % 5 == 0:
                results = model(frame, verbose=False)[0]
                
                violations_detected = []
                for box in results.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    # Class 2 is 'car' in COCO
                    if cls == 2 and conf > 0.5:
                        # Get bounding box center
                        x1, y1, x2, y2 = box.xyxyn[0]
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        
                        # Check if within ROI
                        if roi[0] < cx < roi[2] and roi[1] < cy < roi[3]:
                            violations_detected.append({
                                "type": "ILLEGAL_PARKING" if cam_id == "cam1" else "TRAFFIC_VIOLATION",
                                "confidence": conf
                            })

                if violations_detected:
                    v = violations_detected[0]
                    timestamp_str = time.strftime("%H:%M:%S")
                    
                    # 1. Save frame as evidence
                    image_path = save_violation_frame(frame, cam_id, v["type"])
                    
                    # 2. Save to Database
                    await save_violation(
                        cam_id=cam_id.upper(),
                        v_type=v["type"],
                        confidence=v["confidence"],
                        timestamp=timestamp_str,
                        image_path=image_path
                    )

                    # 3. Broadcast to Dashboard
                    await broadcast_violation({
                        "type": v["type"],
                        "cam_id": cam_id.upper(),
                        "violation": v["type"],
                        "confidence": v["confidence"],
                        "timestamp": timestamp_str,
                        "image_path": image_path
                    })

            # Store the latest frame for the dashboard stream
            _, buffer = cv2.imencode('.jpg', frame)
            latest_frames[cam_id] = buffer.tobytes()
        else:
            print(f"[HUB] Reconnecting to {cam_id}...")
            cap = cv2.VideoCapture(url)
            await asyncio.sleep(2)
        
        await asyncio.sleep(0.01) # Yield control

async def broadcast_violation(data):
    """
    Sends violation events to all connected web dashboards via WebSockets.
    """
    if active_connections:
        message = json.dumps(data)
        for connection in active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

@app.on_event("startup")
async def startup_event():
    # Initialize DB
    await init_db()
    
    # Mount static files for captures
    if not os.path.exists("captures"):
        os.makedirs("captures")
    app.mount("/captures", StaticFiles(directory="captures"), name="captures")

    # Start tasks for each camera
    for cam_id, url in CAMERAS.items():
        asyncio.create_task(fetch_camera_stream(cam_id, url))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)

def generate_frames(cam_id):
    """
    Generates a stream of MJPEG frames for the web dashboard.
    """
    while True:
        frame = latest_frames.get(cam_id)
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.05)

@app.get("/video/{cam_id}")
async def video_feed(cam_id: str):
    if cam_id not in CAMERAS:
        return {"error": "Camera not found"}
    return StreamingResponse(generate_frames(cam_id), 
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/violations")
async def list_violations():
    """Returns the list of stored violations."""
    return await get_all_violations()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
