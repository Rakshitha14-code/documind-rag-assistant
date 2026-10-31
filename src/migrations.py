import os
import sqlite3
from typing import Optional


def run_sqlite_migrations(db_path: str) -> None:
    """
    Safely applies non-destructive schema migrations and activates
    production SQLite PRAGMAs (WAL mode, foreign keys, busy timeout).
    Never erases existing data.
    """
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()

        # 1. Activate Write-Ahead Logging (WAL) for high concurrency and crash safety
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA busy_timeout = 20000;")

        # 2. Check and add updated_at column to documents if missing
        cursor.execute("PRAGMA table_info(documents);")
        columns = [row[1] for row in cursor.fetchall()]

        if "updated_at" not in columns and len(columns) > 0:
            cursor.execute("ALTER TABLE documents ADD COLUMN updated_at TIMESTAMP;")

        # 3. Check and add updated_at column to user_preferences if missing
        cursor.execute("PRAGMA table_info(user_preferences);")
        pref_cols = [row[1] for row in cursor.fetchall()]
        if "updated_at" not in pref_cols and len(pref_cols) > 0:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN updated_at TIMESTAMP;")


        conn.commit()
    except Exception as e:
        print(f"[Migration Warning] SQLite migration step notice: {e}")
    finally:
        conn.close()
