import requests
import time

def test_push_and_check():
    esp_ip = "10.212.59.40"
    
    print(f"--- PUSH-AND-CHECK TEST ---")
    
    # 1. Push RED
    print(f"[1] Pushing RED to {esp_ip}:81...")
    try:
        r = requests.get(f"http://{esp_ip}:81/setstate?val=RED", timeout=2)
        print(f"   - Push Response: {r.status_code} ({r.text})")
    except Exception as e:
        print(f"   - FAILED to push: {e}")
        return

    # 2. Check Status
    print(f"[2] Checking Status immediately...")
    try:
        r = requests.get(f"http://{esp_ip}:81/status", timeout=2)
        print(f"   - Status: {r.text}")
    except Exception as e:
        print(f"   - FAILED to check: {e}")

if __name__ == "__main__":
    test_push_and_check()
