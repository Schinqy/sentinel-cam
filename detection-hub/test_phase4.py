import asyncio
import requests
import os
import json

# Make sure your main.py server is running!
BASE_URL = "http://127.0.0.1:8005"
API_KEY = "sentinel-secret-2026"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def test_traffic_light():
    print("\n--- 🚦 Testing Traffic Light Endpoint ---")
    data = {"status": "RED"}
    try:
        res = requests.post(f"{BASE_URL}/api/traffic-light/status", json=data, headers=HEADERS)
        if res.status_code == 200:
            print("✅ SUCCESS: Traffic light set to RED. Check your dashboard UI to see if it updated!")
        else:
            print(f"❌ FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ ERROR: Server not running? {e}")

def test_challan_generation():
    print("\n--- 📄 Testing E-Challan PDF Generation ---")
    # Mock violation data
    mock_violation = {
        "cam_id": "cam2",
        "violation": "RED_ROBOT",
        "timestamp": "14:30:00",
        "plate_number": "TEST-1234",
        "confidence": 0.98,
        "image_path": "" # No image for this test
    }
    
    try:
        res = requests.post(f"{BASE_URL}/api/generate-challan", json=mock_violation, headers=HEADERS)
        if res.status_code == 200:
            pdf_url = res.json().get("pdf_url")
            print(f"✅ SUCCESS: Challan generated! URL: {pdf_url}")
            
            # Verify the file actually exists on disk
            filename = os.path.basename(pdf_url)
            local_path = os.path.join("captures", filename)
            if os.path.exists(local_path):
                print(f"✅ VERIFIED: PDF file found at {local_path}")
            else:
                print("❌ FAILED: PDF file not found on disk.")
        else:
            print(f"❌ FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("Starting SentinelCam Hardware Simulator...")
    test_traffic_light()
    test_challan_generation()
    print("\nDone! To test Computer Vision, point the dashboard camera URL to an mp4 file instead of an ESP32 IP.")
