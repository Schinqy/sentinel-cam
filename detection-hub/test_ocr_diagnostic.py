import cv2
import pytesseract
import numpy as np
import os
from utils import extract_plate_text

# 1. Setup Tesseract Path (Matches utils.py)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def run_diagnostic():
    print("\n" + "="*50)
    print("   SENTINEL-CAM OCR DIAGNOSTIC TOOL")
    print("="*50 + "\n")

    # Test 1: Check Tesseract Installation
    print("[1/3] Checking Tesseract installation...")
    if os.path.exists(pytesseract.pytesseract.tesseract_cmd):
        print("[OK] Tesseract found at expected path.")
    else:
        print("[FAIL] ERROR: Tesseract NOT FOUND at C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        print("  Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")
        return

    # Test 2: Perfect Plate Test
    print("\n[2/3] Testing with high-contrast 'Perfect Plate'...")
    test_plate_path = "test_plate.png"
    if os.path.exists(test_plate_path):
        with open(test_plate_path, "rb") as f:
            img_bytes = f.read()
        
        result = extract_plate_text(img_bytes)
        print(f"Result: {result}")
        if "SNTNL" in result or "2026" in result:
            print("[OK] Perfect Plate Recognition SUCCESSFUL.")
        else:
            print("[WARN] Recognition failed on perfect image. Logic adjustment needed.")
    else:
        print("[SKIP] test_plate.png not found.")

    # Test 3: Real Capture Test
    print("\n[3/3] Testing with a real system capture...")
    captures = [f for f in os.listdir("captures") if f.endswith(".jpg")]
    if captures:
        sample_img = os.path.join("captures", captures[-1])
        print(f"Reading: {sample_img}")
        with open(sample_img, "rb") as f:
            img_bytes = f.read()
        
        result = extract_plate_text(img_bytes)
        print(f"Result: {result}")
        if result != "NOT_DETECTED":
            print("[OK] Real Capture Recognition SUCCESSFUL.")
        else:
            print("[WARN] No text detected in real capture. (Common with motion blur or distance)")
    else:
        print("[SKIP] No images found in 'captures' folder.")

    print("\n" + "="*50)
    print("   DIAGNOSTIC COMPLETE")
    print("="*50)

if __name__ == "__main__":
    run_diagnostic()
