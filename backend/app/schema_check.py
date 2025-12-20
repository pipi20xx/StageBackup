import sqlite3
import os

# Adapt to host or container path
if os.path.exists("./data/backup_system.db"):
    DB_PATH = "./data/backup_system.db"
elif os.path.exists("/data/backup_system.db"):
    DB_PATH = "/data/backup_system.db"
else:
    DB_PATH = "backup_system.db"

def ensure_schema_updates():
    if not os.path.exists(DB_PATH):
        return

    print(f"Checking database schema at {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Check 'projects' table for 'sync_mode'
        cursor.execute("PRAGMA table_info(projects)")
        project_cols = [info[1] for info in cursor.fetchall()]
        if "sync_mode" not in project_cols:
            print("Auto-migrating: Adding 'sync_mode' to projects table.")
            cursor.execute("ALTER TABLE projects ADD COLUMN sync_mode TEXT DEFAULT 'overwrite'")
        
        # 2. Check 'history' table for 'progress' and 'remark'
        cursor.execute("PRAGMA table_info(history)")
        history_cols = [info[1] for info in cursor.fetchall()]
        if "progress" not in history_cols:
            print("Auto-migrating: Adding 'progress' to history table.")
            cursor.execute("ALTER TABLE history ADD COLUMN progress INTEGER DEFAULT 0")
        if "remark" not in history_cols:
            print("Auto-migrating: Adding 'remark' to history table.")
            cursor.execute("ALTER TABLE history ADD COLUMN remark TEXT")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Schema check failed: {e}")
