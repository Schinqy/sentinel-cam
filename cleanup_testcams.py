import sqlite3
conn = sqlite3.connect('detection-hub/violations.db')
conn.execute("DELETE FROM cameras WHERE id LIKE 'testcam%'")
conn.commit()
remaining = conn.execute("SELECT id,name FROM cameras").fetchall()
print("Remaining cameras:", remaining)
conn.close()
