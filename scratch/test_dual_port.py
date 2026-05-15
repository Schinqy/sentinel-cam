import requests
import time

def test_dual_port():
    esp_ip = "10.212.59.40"
    
    print(f"--- DUAL-PORT DIAGNOSTIC ---")
    
    # Check API on Port 81
    print(f"[1] Checking Status API (Port 81)...")
    try:
        r = requests.get(f"http://{esp_ip}:81/status", timeout=2)
        print(f"   - Response: {r.status_code}")
        print(f"   - Data: {r.text}")
    except Exception as e:
        print(f"   - FAILED: {e}")

    # Check Stream on Port 80 (Just a quick ping)
    print(f"\n[2] Checking Stream (Port 80)...")
    try:
        r = requests.get(f"http://{esp_ip}/stream", stream=True, timeout=2)
        print(f"   - Stream Header: {r.status_code}")
        r.close()
    except Exception as e:
        print(f"   - Stream unreachable: {e}")

if __name__ == "__main__":
    test_dual_port()
