import aiosqlite
import os

DB_PATH = "violations.db"

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
        
        # Seed initial cameras if empty
        async with db.execute("SELECT COUNT(*) FROM cameras") as cursor:
            count = await cursor.fetchone()
            if count[0] == 0:
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam1", "North Intersection", "http://192.168.1.45/stream"))
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam2", "East Junction", "http://192.168.1.46/stream"))
                await db.execute("INSERT INTO cameras (id, name, url) VALUES (?, ?, ?)", ("cam3", "South Crosswalk", "http://192.168.1.47/stream"))
        
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
