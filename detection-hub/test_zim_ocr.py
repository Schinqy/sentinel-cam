import sys
import os

# Make sure we can import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import extract_plate_text

def test_plate(label, expected, filepath):
    print(f"\n  [{label}]")
    print(f"  Expected: '{expected}'")
    if not os.path.exists(filepath):
        print(f"  SKIP: {filepath} not found.")
        return False

    with open(filepath, "rb") as f:
        img_bytes = f.read()

    result = extract_plate_text(img_bytes)
    print(f"  Got:      '{result}'")

    # Check if any part of expected is in result
    expected_parts = expected.replace(" ", "").lower()
    result_clean = result.replace(" ", "").replace("-", "").lower()

    if expected_parts in result_clean:
        print(f"  RESULT: [HIT] EasyOCR detected the plate!")
        return True
    else:
        # Partial match check (at least 4 consecutive chars match)
        for i in range(len(expected_parts) - 3):
            chunk = expected_parts[i:i+4]
            if chunk in result_clean:
                print(f"  RESULT: [PARTIAL HIT] Found '{chunk.upper()}' in result")
                return True
        print(f"  RESULT: [MISS] Plate not found in output")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   ZIM PLATE OCR BENCHMARK - EasyOCR Edition")
    print("="*60)

    hits = 0
    total = 3

    if test_plate("CLEAR (ideal sticker)", "ADC 4821", "zim_plate_clear.png"):
        hits += 1
    if test_plate("MEDIUM (ESP32-CAM quality)", "BFG 7703", "zim_plate_medium.png"):
        hits += 1
    if test_plate("BLURRY (motion/bad light)", "ZIM 1234", "zim_plate_blurry.png"):
        hits += 1

    print("\n" + "="*60)
    print(f"   FINAL SCORE: {hits}/{total} plates detected")
    if hits >= 2:
        print("   VERDICT: EasyOCR is GOOD ENOUGH for production.")
    elif hits == 1:
        print("   VERDICT: Partial success - works on clear plates only.")
    else:
        print("   VERDICT: EasyOCR also failing - consider manual plate entry.")
    print("="*60 + "\n")
