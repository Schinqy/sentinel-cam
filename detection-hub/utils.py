import cv2
import os
import time

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
    
    # Save the frame
    success = cv2.imwrite(filepath, frame)
    
    if success:
        return filepath
    return None
