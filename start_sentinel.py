import subprocess
import os
import sys
import time
import signal
import webbrowser

def start_system():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    hub_dir = os.path.join(root_dir, "detection-hub")
    dash_dir = os.path.join(root_dir, "web-dashboard")

    print("\n" + "="*50)
    print("   SENTINEL-CAM: CARDBOARD CITY COMMAND CENTER")
    print("="*50 + "\n")

    # 1. Start Detection Hub
    print("[1/3] Starting Detection Hub (Python)...")
    hub_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=hub_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # 2. Start Web Dashboard
    print("[2/3] Starting Web Dashboard (Next.js)...")
    dash_proc = subprocess.Popen(
        "npm run dev",
        cwd=dash_dir,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    print("[3/3] Waiting for services to stabilize...")
    time.sleep(5)

    # 3. Open Browser
    url = "http://localhost:3000"
    print(f"\n🚀 System is LIVE at {url}")
    webbrowser.open(url)

    print("\nKEEP THIS WINDOW OPEN TO RUN THE SYSTEM.")
    print("Close this window or press Ctrl+C to stop all services.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[!] Shutting down SentinelCam...")
        hub_proc.terminate()
        # Kill dashboard process tree (npm spawns children)
        subprocess.run(f"taskkill /F /T /PID {dash_proc.pid}", shell=True, capture_output=True)
        print("[✔] Cleanup complete. Goodbye!")

if __name__ == "__main__":
    start_system()
