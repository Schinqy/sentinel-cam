import asyncio
import cv2
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse
from ultralytics import YOLO

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
    Background worker that fetches frames from an ESP32-CAM MJPEG stream.
    """
    print(f"[HUB] Starting fetch for {cam_id} at {url}...")
    cap = cv2.VideoCapture(url)
    
    while True:
        ret, frame = cap.read()
        if ret:
            # ROI Processing & Detection Logic would go here
            # For now, just store the latest frame
            _, buffer = cv2.imencode('.jpg', frame)
            latest_frames[cam_id] = buffer.tobytes()
            
            # Simulate a violation event (e.g. every 100 frames)
            if time.time() % 10 < 0.1: # Dummy condition
                await broadcast_violation({
                    "type": "VIOLATION",
                    "cam_id": cam_id,
                    "violation": "ILLEGAL_PARKING",
                    "timestamp": time.strftime("%H:%M:%S")
                })
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
