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
                roi_x2 REAL DEFAULT 1,
                roi_y2 REAL DEFAULT 1,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        urls = load_env_urls()
        # Only seed cameras on first run — never overwrite existing rows
        # so that UI config changes survive restarts
        async with db.execute("SELECT COUNT(*) FROM cameras") as cursor:
            count = await cursor.fetchone()
            if count[0] == 0:
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam1", "North Intersection", urls["cam1"]))
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam2", "East Junction", urls["cam2"]))
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam3", "South Crosswalk", urls["cam3"]))
        
        await db.commit()

async def save_violation(cam_id, v_type, confidence, timestamp, image_path, plate_number=None):
    """Saves a violation record to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO violations (cam_id, type, confidence, timestamp, image_path, plate_number) VALUES (?, ?, ?, ?, ?, ?)",
            (cam_id, v_type, confidence, timestamp, image_path, plate_number)
        )
        await db.commit()

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