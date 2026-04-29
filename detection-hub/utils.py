from PIL import Image
import os
import time
import random

def mock_extract_plate(frame):
    """
    Simulates ALPR (License Plate Recognition).
    In a real scenario, this would use EasyOCR or a specialized model.
    """
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    numbers = "0123456789"
    plate = "".join(random.choices(letters, k=3)) + "-" + "".join(random.choices(numbers, k=4))
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
