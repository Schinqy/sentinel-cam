# 🚨 SentinelCam: Cardboard City Edition

A professional-grade traffic enforcement prototype designed for miniature cardboard cities and toy car simulations.

## 🚀 Quick Start (One-Click)

To start the entire system (Detection Hub + Web Dashboard):

1. Open a terminal in the project root.
2. Run:
   ```bash
   python start_sentinel.py
   ```
3. Your browser will automatically open to `http://localhost:3001`.

## 🛠 Features
- **Live AI Feeds**: Monitor multiple "intersections" on your cardboard setup.
- **ALPR**: Automatic License Plate Recognition for your toy cars.
- **Evidence Vault**: Historical logs with high-resolution snapshots of "violations."
- **Scale Calibration**: Tuned for 1:24 scale simulations.

## 📁 Project Structure
- `/detection-hub`: FastAPI backend handling computer vision and database logic.
- `/web-dashboard`: Next.js frontend with futuristic "Command Center" UI.
- `/esp32-firmware`: (Optional) Firmware for remote camera nodes.

## 🧹 Maintenance
The system automatically cleans up evidence older than 30 days to save space on your "Command Center" computer.
