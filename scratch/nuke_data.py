import os
import shutil
import sqlite3

def nuke_data():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(curr_dir, "detection-hub", "violations.db")
    captures_dir = os.path.join(curr_dir, "detection-hub", "captures")
    
    print("--- SENTINEL DATA NUKE ---")
    
    # 1. Clear Database
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM violations")
            conn.commit()
            conn.close()
            print(f"[✔] Cleared violations from {db_path}")
        except Exception as e:
            print(f"[!] Error clearing DB: {e}")
    else:
        print("[?] Database file not found, skipping.")

    # 2. Clear Captures
    if os.path.exists(captures_dir):
        try:
            for filename in os.listdir(captures_dir):
                file_path = os.path.join(captures_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
            print(f"[✔] Cleared all files in {captures_dir}")
        except Exception as e:
            print(f"[!] Error clearing captures: {e}")
    else:
        print("[?] Captures directory not found, skipping.")

    print("--- NUKE COMPLETE ---")

if __name__ == "__main__":
    nuke_data()
