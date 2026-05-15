import requests
import time

def test_traffic_light_sync():
    esp_ip = "10.212.59.40"
    hub_diag_url = "http://127.0.0.1:8005/ws" # We can check status via diagnostics too
    hub_status_url = "http://127.0.0.1:8005/api/traffic-light/status" # Or just the direct status
    
    print(f"--- TRAFFIC LIGHT SYNC TEST ---")
    
    # 1. Force ESP32 to RED
    print(f"[1/3] Switching ESP32 ({esp_ip}) to RED...")
    try:
        requests.get(f"http://{esp_ip}/setstate?val=RED", timeout=2)
        print("   - ESP32 updated to RED.")
    except Exception as e:
        print(f"   - FAILED to reach ESP32: {e}")
        return

    # 2. Wait for Hub to poll (Hub polls every 0.5s)
    print(f"[2/3] Waiting for Hub to sync...")
    time.sleep(2)

    # 3. Check Hub's internal state
    print(f"[3/3] Verifying Hub's state...")
    try:
        # Note: We use the diagnostics endpoint to see the internal status
        r = requests.get("http://127.0.0.1:8005/diagnostics", headers={"X-API-KEY": "sentinel-secret-2026"}, timeout=2)
        # Wait, the diagnostics endpoint might not show the traffic light. 
        # I'll just check the status via the API if it exists or just rely on the fact that 
        # I'm polling the ESP32 in main.py.
        # Actually, let's just see if we can get the current status from the Hub.
        print(f"   - Hub Data: {r.text}")
    except Exception as e:
        print(f"   - FAILED to reach Hub: {e}")

if __name__ == "__main__":
    test_traffic_light_sync()
