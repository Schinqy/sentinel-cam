import easyocr
import cv2
import numpy as np
import os
import time

# Initialize EasyOCR reader once at module load (avoids slow startup on every call)
# This downloads a small model (~40MB) on first run, then caches it locally.
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        print("[OCR] Initializing EasyOCR reader (first run may take a moment)...")
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[OCR] EasyOCR ready.")
    return _reader

def extract_plate_text(frame_bytes):
    """
    Extracts license plate text from an image using EasyOCR.
    Optimized for low-res ESP32-CAM feeds and paper/sticker Zim-style plates.
    """
    try:
        # Decode image
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return "NOT_DETECTED"

        # Pre-process: upscale for better model performance on small images
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Run EasyOCR
        reader = get_reader()
        results = reader.readtext(img, detail=1)

        # Filter: only keep results with decent confidence
        candidates = []
        for (bbox, text, confidence) in results:
            clean = "".join(c for c in text if c.isalnum() or c == ' ' or c == '-').strip()
            if confidence > 0.3 and len(clean) >= 3:
                candidates.append((confidence, clean.upper()))

        if candidates:
            # Return the result with the highest confidence
            candidates.sort(reverse=True)
            return candidates[0][1]

    except Exception as e:
        print(f"[OCR ERROR] {e}")

    return "NOT_DETECTED"


# ---- File saving utils (unchanged) ----
CAPTURES_DIR = "captures"

def ensure_captures_dir():
    """Ensures the captures directory exists."""
    if not os.path.exists(CAPTURES_DIR):
        os.makedirs(CAPTURES_DIR)

def save_violation_frame(frame, cam_id, v_type):
    """
    Saves a frame to disk and returns the relative path.
    Filename format: cam_id_timestamp_type.jpg
    """
    ensure_captures_dir()
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{cam_id}_{timestamp}_{v_type}.jpg".lower()
    filepath = os.path.join(CAPTURES_DIR, filename)
    
    try:
        from PIL import Image
        if isinstance(frame, bytes):
            with open(filepath, "wb") as f:
                f.write(frame)
        elif hasattr(frame, 'save'):
            frame.save(filepath)
        else:
            rgb_frame = frame[:, :, ::-1]
            img = Image.fromarray(rgb_frame)
            img.save(filepath)
        return filepath
    except Exception as e:
        print(f"[UTILS] Error saving frame: {e}")
        return None
