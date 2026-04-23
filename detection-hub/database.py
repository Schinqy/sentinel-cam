import aiosqlite
import os

DB_PATH = "violations.db"

async def init_db():
    """Initializes the database and creates the violations table if it doesn't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cam_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT
            )
        """)
        await db.commit()

async def save_violation(cam_id, v_type, confidence, timestamp, image_path):
    """Saves a violation record to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO violations (cam_id, type, confidence, timestamp, image_path) VALUES (?, ?, ?, ?, ?)",
            (cam_id, v_type, confidence, timestamp, image_path)
        )
        await db.commit()

async def get_all_violations(limit=50):
    """Retrieves the latest violations from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM violations ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
