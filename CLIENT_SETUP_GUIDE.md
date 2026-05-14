# 🚨 SentinelCam: Client Setup Guide & Blueprint

Welcome to the **SentinelCam (A.T.V.D)** setup guide. This document provides a step-by-step blueprint for deploying the Automated Traffic Violation Detection system on your local PC.

---

## 🏗 System Architecture
SentinelCam consists of three primary layers:
1.  **Detection Hub (Backend)**: A Python-based engine powered by FastAPI and YOLOv8 for real-time AI object detection and ALPR (Automatic License Plate Recognition).
2.  **Web Dashboard (Frontend)**: A modern Next.js interface for monitoring live feeds, managing violations, and calibrating camera zones.
    - **History Management**: View violation logs, review evidence images, and use the new **Individual/Bulk Deletion** tools to manage your database.
3.  **Camera Nodes (Edge)**: ESP32-CAM modules or standard USB/IP cameras that provide the video streams.

---

## 💻 1. Minimum System Requirements
To ensure smooth AI processing (YOLOv8) and 60FPS dashboard rendering:
- **OS**: Windows 10/11 (64-bit)
- **CPU**: Intel i5 / AMD Ryzen 5 or higher
- **RAM**: 8GB (16GB recommended)
- **GPU**: Not required (runs on CPU), but an NVIDIA GPU will significantly boost performance.
- **Storage**: 500MB for software + additional space for violation snapshots.

---

## 🛠 2. Software Prerequisites
Before running the system, install the following tools:

1.  **Python 3.10+**: [Download here](https://www.python.org/downloads/)
    - *Important*: Check "Add Python to PATH" during installation.
2.  **Node.js (v18+)**: [Download here](https://nodejs.org/)
3.  **Git**: [Download here](https://git-scm.com/)
4. **EasyOCR Engine**: The system now uses EasyOCR for high-accuracy license plate recognition.
   - Run `pip install easyocr` (Automated by `start_sentinel.py`).
   - The first run will automatically download the required AI models (~40MB).

---

## 🚀 3. Quick Start (Windows)
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/Schinqy/sentinel-cam.git
   cd sentinel-cam
   ```

2. **Install Everything**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Install Dashboard dependencies
   cd web-dashboard
   npm install
   cd ..
   ```

3. **Configure**:
   Open the `.env` file in the root folder and update the `CAM_URL` fields with your camera IPs.

4. **Launch**:
   ```bash
   python start_sentinel.py
   ```

```env
# URL for ESP32-CAM or IP Camera
CAM1_URL=http://192.168.1.45/stream 

# Use '0' for local USB Webcams
CAM2_URL=0 

# Leave empty or set to None if not used
CAM3_URL=None 
```

---

## 🚦 5. Running the System
We have provided a "One-Click" starter script. 

1.  Navigate back to the root folder: `cd ..`
2.  Run the starter script:
    ```bash
    python start_sentinel.py
    ```

**What happens next?**
- Two console windows will open (one for the AI Hub, one for the Dashboard).
- Your browser will automatically open to `http://localhost:3001`.

---

## 📸 6. Camera Setup
- **ESP32-CAM**: If using our custom firmware, follow the `hardware_setup.md` guide to flash your nodes.
- **USB Webcams**: Simply plug them in and set the URL to `0`, `1`, etc., in the `.env` file.
- **Zone Calibration**: Once the dashboard is open, use the **"Calibrate ROI"** tool to draw detection zones (e.g., stop lines or speed traps).

---

## ❓ Troubleshooting
- **Error: Tesseract not found**: Ensure Tesseract is installed at `C:\Program Files\Tesseract-OCR`.
- **Camera Feed is Black**: Check if the camera URL is correct and reachable in your browser.
- **Slow Detection**: If the UI lags, ensure you don't have other heavy apps running. The system is optimizing YOLOv8 for your CPU on the first run.

---

*© 2024 SentinelCam Intelligence Systems*
