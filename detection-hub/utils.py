from PIL import Image
import os
import time
import random

import pytesseract
import cv2
import numpy as np

def extract_plate_text(frame_bytes):
    """
    Extracts text from the image using Tesseract OCR.
    Perfect for reading high-contrast printed stickers on toy cars.
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Pre-process for OCR: Grayscale -> Threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Run Tesseract
        # --psm 11 looks for sparse text in any order
        text = pytesseract.image_to_string(thresh, config='--psm 11').strip()
        
        # Clean up the string (remove non-alphanumeric except dash)
        clean_text = "".join(c for c in text if c.isalnum() or c == '-')
        
        if len(clean_text) >= 4:
            return clean_text.upper()
        
    except Exception as e:
        print(f"[OCR ERROR] {e}")
        
    # Fallback to mock if Tesseract fails or finds nothing
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    numbers = "0123456789"
    plate = "MOCK-" + "".join(random.choices(numbers, k=4))
    return plate

CAPTURES_DIR = "captures"

def ensure_captures_dir():
    """Ensures the captures directory exists."""
    if not os.path.exists(CAPTURES_DIR):
        os.makedirs(CAPTURES_DIR)

def save_violation_frame(frame, cam_id, v_type):
    """
    Saves a frame to disk and returns the relative path.
    Filename format: cam_id_timestamp_type.jpg
    
    Expects frame to be a numpy array (BGR) or a PIL Image.
    """
    ensure_captures_dir()
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{cam_id}_{timestamp}_{v_type}.jpg".lower()
    filepath = os.path.join(CAPTURES_DIR, filename)
    
    try:
        if isinstance(frame, bytes):
            with open(filepath, "wb") as f:
                f.write(frame)
        elif hasattr(frame, 'save'): # Already a PIL Image
            frame.save(filepath)
        else: # Likely a numpy array
            # Convert BGR to RGB for Pillow
            import numpy as np
            rgb_frame = frame[:, :, ::-1]
            img = Image.fromarray(rgb_frame)
            img.save(filepath)
        return filepath
    except Exception as e:
        print(f"[UTILS] Error saving frame: {e}")
        return None
