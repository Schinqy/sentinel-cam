import asyncio
import json
import websockets
import requests

async def test_ws_sync():
    esp_ip = "10.212.59.40"
    ws_url = "ws://127.0.0.1:8005/ws"
    
    print("--- WEBSOCKET SYNC TEST ---")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # 1. Get initial state
            initial = await websocket.recv()
            print(f"[1] Initial Hub State: {initial}")
            
            # 2. Trigger RED on ESP32
            print(f"[2] Triggering RED on ESP32...")
            requests.get(f"http://{esp_ip}/setstate?val=RED", timeout=2)
            
            # 3. Listen for broadcast
            print(f"[3] Waiting for Hub Broadcast...")
            # We might get multiple messages, look for the STATUS one
            for _ in range(5):
                msg = await websocket.recv()
                data = json.loads(msg)
                if data.get("type") == "STATUS":
                    print(f"   🎉 SUCCESS! Hub Broadcasted: {msg}")
                    break
            
            # 4. Reset to GREEN
            requests.get(f"http://{esp_ip}/setstate?val=GREEN", timeout=2)
            print("[4] Reset ESP32 to GREEN.")

    except Exception as e:
        print(f"--- TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws_sync())
