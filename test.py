import cv2

url = "http://10.35.14.40/stream"
print(f"Trying to open: {url}")

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
print(f"Opened: {cap.isOpened()}")

ret, frame = cap.read()
print(f"Read success: {ret}")
if ret:
    print(f"Frame shape: {frame.shape}")
else:
    print("FAILED - OpenCV cannot read this stream")

cap.release()