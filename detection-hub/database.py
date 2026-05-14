import aiosqlite
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(curr_dir, "violations.db")

def load_env_urls():
    urls = {
        "cam1": "http://192.168.1.45/stream",
        "cam2": "http://192.168.1.46/stream",
        "cam3": "http://192.168.1.47/stream"
    }
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(curr_dir)
    
    paths = [
        os.path.join(root_dir, ".env"),
        os.path.join(curr_dir, ".env"),
        ".env"
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, val = line.strip().split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key == "CAM1_URL": urls["cam1"] = val
                        elif key == "CAM2_URL": urls["cam2"] = val
                        elif key == "CAM3_URL": urls["cam3"] = val
    return urls

async def init_db():
    """Initializes the database and creates necessary tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Violations Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cam_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT,
                plate_number TEXT
            )
        """)

        # Migration: Ensure plate_number column exists if table was created in an older version
        try:
            async with db.execute("SELECT plate_number FROM violations LIMIT 1") as cursor:
                await cursor.fetchone()
        except aiosqlite.OperationalError:
            print("[DB] Migrating database: adding 'plate_number' column to 'violations' table")
            await db.execute("ALTER TABLE violations ADD COLUMN plate_number TEXT")

        
        # Cameras Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                roi_x1 REAL DEFAULT 0,
                roi_y1 REAL DEFAULT 0,
                roi_x2 REAL DEFAULT 0,
                roi_y2 REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                enforce_direction TEXT DEFAULT 'UP'
            )
        """)
        
        # Migration: Ensure enforce_direction column exists
        try:
            async with db.execute("SELECT enforce_direction FROM cameras LIMIT 1") as cursor:
                await cursor.fetchone()
        except aiosqlite.OperationalError:
            print("[DB] Migrating database: adding 'enforce_direction' column to 'cameras' table")
            await db.execute("ALTER TABLE cameras ADD COLUMN enforce_direction TEXT DEFAULT 'UP'")
        
        # Migration: Reset cameras that still have the old default full-frame ROI [0,0,1,1]
        # A user-drawn zone would never be exactly 0,0,1,1 unless they drew the full frame manually
        await db.execute(
            "UPDATE cameras SET roi_x2=0, roi_y2=0 WHERE roi_x1=0 AND roi_y1=0 AND roi_x2=1 AND roi_y2=1"
        )
        
        urls = load_env_urls()
        # Seed cameras or update URLs from .env
        async with db.execute("SELECT id, url FROM cameras") as cursor:
            existing_cams = {row[0]: row[1] for row in await cursor.fetchall()}
            
        for cid, name in [("cam1", "North Intersection"), ("cam2", "East Junction"), ("cam3", "South Crosswalk")]:
            new_url = urls.get(cid)
            if cid not in existing_cams:
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", (cid, name, new_url))
            elif existing_cams[cid] != new_url:
                print(f"[DB] Updating {cid} URL to: {new_url}")
                await db.execute("UPDATE cameras SET url=? WHERE id=?", (new_url, cid))
        
        await db.commit()

async def save_violation(cam_id, v_type, confidence, timestamp, image_path, plate_number=None):
    """Saves a violation record to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "INSERT INTO violations (cam_id, type, confidence, timestamp, image_path, plate_number) VALUES (?, ?, ?, ?, ?, ?)",
            (cam_id, v_type, confidence, timestamp, image_path, plate_number)
        ) as cursor:
            row_id = cursor.lastrowid
            await db.commit()
            return row_id

async def get_all_violations(limit=50):
    """Retrieves the latest violations from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM violations ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_cameras():
    """Retrieves all cameras."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cameras") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_camera_roi(cam_id, roi):
    """Updates the ROI for a specific camera."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cameras SET roi_x1=?, roi_y1=?, roi_x2=?, roi_y2=? WHERE id=?",
            (roi[0], roi[1], roi[2], roi[3], cam_id)
        )
        await db.commit()