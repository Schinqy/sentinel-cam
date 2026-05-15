import requests
import time

def test_diagnostics():
    esp_ip = "10.212.59.40"
    hub_url = "http://127.0.0.1:8005/diagnostics"
    
    print(f"[TEST] 1. Checking ESP32 Status API at {esp_ip}...")
    try:
        r = requests.get(f"http://{esp_ip}/status", timeout=2)
        print(f"   - Response: {r.status_code}")
        print(f"   - Data: {r.text}")
    except Exception as e:
        print(f"   - FAILED to reach ESP32: {e}")

    print(f"\n[TEST] 2. Checking Detection Hub API at {hub_url}...")
    try:
        r = requests.get(hub_url, headers={"X-API-KEY": "sentinel-secret-2026"}, timeout=2)
        print(f"   - Response: {r.status_code}")
        print(f"   - Data: {r.text}")
    except Exception as e:
        print(f"   - FAILED to reach Hub: {e}")

if __name__ == "__main__":
    test_diagnostics()
