import asyncio
import numpy as np
from database import init_db, save_violation, get_all_violations
from utils import save_violation_frame
import os

async def test():
    print("--- Phase 1 Test ---")
    
    # 1. Init DB
    print("[1] Initializing DB...")
    await init_db()
    if os.path.exists("violations.db"):
        print("SUCCESS: violations.db created.")
    
    # 2. Save a dummy frame
    print("[2] Saving dummy frame...")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    image_path = save_violation_frame(dummy_frame, "TEST_CAM", "TEST_TYPE")
    if image_path and os.path.exists(image_path):
        print(f"SUCCESS: Frame saved at {image_path}")
    else:
        print("FAILURE: Frame not saved.")
        return

    # 3. Save to DB
    print("[3] Saving to DB...")
    await save_violation(
        cam_id="TEST_CAM",
        v_type="TEST_TYPE",
        confidence=0.95,
        timestamp="12:00:00",
        image_path=image_path
    )
    print("SUCCESS: Record sent to save_violation.")

    # 4. Verify DB
    print("[4] Verifying DB...")
    violations = await get_all_violations()
    if len(violations) > 0 and violations[0]['cam_id'] == "TEST_CAM":
        print(f"SUCCESS: Found record in DB: {violations[0]}")
    else:
        print(f"FAILURE: Record not found in DB. Count: {len(violations)}")

if __name__ == "__main__":
    asyncio.run(test())
