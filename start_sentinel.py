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

    print("\n" + "="*55)
    print("   A.T.V.D - AUTOMATED TRAFFIC VIOLATION DETECTION")
    print("   Starting all system services...")
    print("="*55 + "\n")

    # 0. Cleanup existing zombies (Targeted ports 8005 and 3001)
    print("[0/3] Cleaning up existing processes...")
    try:
        # Kill whatever is on port 8005 (Hub) and 3001 (Dashboard)
        subprocess.run("for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :8005') do taskkill /F /PID %a", shell=True, capture_output=True)
        subprocess.run("for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :3001') do taskkill /F /PID %a", shell=True, capture_output=True)
    except:
        pass
    time.sleep(1)

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
    url = "http://localhost:3001"
    webbrowser.open(url)

    # 4. Main monitoring loop
    print("\n[✔] SYSTEM LIVE: Dashboard at http://localhost:3001")
    print("[!] Press CTRL+C to stop all services.\n")
    
    try:
        while True:
            # Check if processes are still alive
            hub_status = hub_proc.poll()
            dash_status = dash_proc.poll()
            
            if hub_status is not None:
                print(f"[!] Hub process died with code {hub_status}. Restarting...")
                hub_proc = subprocess.Popen([sys.executable, "main.py"], cwd=hub_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            if dash_status is not None:
                print(f"[!] Dashboard process died with code {dash_status}. Restarting...")
                dash_proc = subprocess.Popen("npm run dev", cwd=dash_dir, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n[!] Shutting down SentinelCam...")
    except Exception as e:
        print(f"\n[❌] CRITICAL ERROR: {e}")
    finally:
        # Kill processes aggressively on Windows
        try:
            subprocess.run(f"taskkill /F /T /PID {hub_proc.pid}", shell=True, capture_output=True)
            subprocess.run(f"taskkill /F /T /PID {dash_proc.pid}", shell=True, capture_output=True)
        except:
            pass
        print("[✔] Cleanup complete. Goodbye!")

if __name__ == "__main__":
    try:
        start_system()
    except Exception as e:
        print(f"FAILED TO START: {e}")
