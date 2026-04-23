# SentinelCam Hardware Setup & Flashing Guide

To deploy the SentinelCam traffic enforcement nodes, you will need the following hardware and setup steps.

## 1. Required Components
- **ESP32-CAM Module**: (AI-Thinker model recommended).
- **OV2640 Camera Module**: Usually included with the ESP32-CAM.
- **FTDI USB-to-TTL Adapter**: To flash the code onto the ESP32.
- **Jumper Wires**: Female-to-Female.
- **5V/2A Power Supply**: ESP32-CAM is power-hungry during WiFi/Camera operations.

## 2. Wiring Diagram for Flashing
Connect the FTDI adapter to the ESP32-CAM as follows:

| FTDI Adapter | ESP32-CAM |
| :--- | :--- |
| GND | GND |
| 5V / 3.3V | VCC (Match voltage) |
| TX | U0R |
| RX | U0T |
| **GND** | **GPIO 0** (Must be shorted during flashing) |

> [!IMPORTANT]
> You must connect **GPIO 0 to GND** to enter specialized "Flash Mode". Remove this jumper after flashing to run the code.

## 3. Arduino IDE Configuration
1. Open `esp32-firmware/sentinel_cam_node.ino`.
2. Update the `ssid` and `password` variables with your local WiFi credentials.
3. Install the **ESP32** board library (by Espressif Systems) via the Boards Manager.
4. Select the following settings under **Tools**:
   - **Board**: "AI Thinker ESP32-CAM"
   - **Flash Mode**: QIO
   - **Flash Frequency**: 80MHz
   - **Partition Scheme**: "Huge App (3MB No OTA/1MB SPIFFS)"
   - **Upload Speed**: 115200

## 4. Booting & Streaming
1. Click **Upload** in the Arduino IDE.
2. Once the message "Hard resetting via RTS pin..." appears, **remove the GPIO 0 to GND jumper**.
3. Press the **Reset (RST)** button on the back of the ESP32-CAM.
4. Open the Serial Monitor at **115200 baud**.
5. Copy the IP address displayed (e.g., `http://192.168.1.45/stream`).

## 5. Connecting to the Hub
Update `detection-hub/main.py` with the IP address of your module in the `CAMERAS` dictionary:

```python
CAMERAS = {
    "cam1": "http://192.168.1.45/stream",
    # ...
}
```
