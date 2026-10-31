import os
import json
import sqlite3
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.database import (
    get_user_by_id,
    get_user_documents,
    get_user_collections,
    get_user_chat_sessions,
    get_session_messages,
    get_user_notes,
    get_user_preferences,
    get_db_path,
    get_connection
)
from src.supabase_client import is_supabase_configured



def export_user_workspace(user_id: int, export_file_path: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Exports the authenticated user's complete knowledge workspace
    (documents metadata, collections, chat sessions with messages, notes, preferences)
    into a structured JSON payload for portability and disaster recovery.
    Never exports password hashes or sensitive master keys.
    """
    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        raise ValueError(f"User {user_id} does not exist.")

    # 1. Collections
    collections = get_user_collections(user_id, db_path=db_path)

    # 2. Documents metadata
    documents = get_user_documents(user_id, db_path=db_path)

    # 3. Chat sessions and their full message history
    sessions = get_user_chat_sessions(user_id, db_path=db_path)
    chat_history = []
    for s in sessions:
        msgs = get_session_messages(s["id"], db_path=db_path)
        chat_history.append({
            "session": s,
            "messages": msgs
        })

    # 4. Notes
    notes = get_user_notes(user_id, db_path=db_path)

    # 5. Preferences (sanitize API keys)
    prefs = get_user_preferences(user_id, db_path=db_path)
    safe_prefs = {k: v for k, v in prefs.items() if k != "api_key"}

    bundle = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {

            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "created_at": str(user.get("created_at", ""))
        },
        "collections": collections,
        "documents": documents,
        "chat_history": chat_history,
        "notes": notes,
        "preferences": safe_prefs
    }

    if export_file_path:
        os.makedirs(os.path.dirname(os.path.abspath(export_file_path)), exist_ok=True)
        with open(export_file_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, default=str)

    return bundle


def backup_sqlite_database(db_path: Optional[str] = None, backup_dir: Optional[str] = None) -> str:
    """
    Performs an online, non-blocking snapshot backup of the SQLite database
    using sqlite3.backup API. Guarantees transactional consistency while
    the application continues running.
    """
    source_path = get_db_path(db_path)
    target_dir = backup_dir or os.path.join(os.path.dirname(source_path), "backups")
    os.makedirs(target_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"documind_backup_{timestamp}.db"
    dest_path = os.path.join(target_dir, backup_filename)

    source_conn = get_connection(source_path)
    dest_conn = sqlite3.connect(dest_path)

    try:
        with dest_conn:
            source_conn.backup(dest_conn, pages=100)
        return dest_path
    finally:
        dest_conn.close()
        source_conn.close()


def get_disaster_recovery_plan() -> Dict[str, Any]:
    """Returns documentation and verification metrics for the active backup plan."""
    supabase_active = is_supabase_configured()

    if supabase_active:
        return {
            "mode": "Supabase Managed Cloud",
            "database_backup": "Supabase automatically performs daily logical backups (stored offsite for 7 days on Free/Pro tiers, up to 30 days on Team/Enterprise). Point-In-Time Recovery (PITR) is available on Pro+ tiers.",
            "storage_backup": "Supabase Storage files are redundantly replicated across AWS S3 multi-AZ physical infrastructure.",
            "recovery_procedure": "In the event of an outage or accidental data loss, restore the database snapshot from the Supabase Project Dashboard -> Database -> Backups, or replay SQL migration scripts.",
            "export_available": True
        }
    else:
        return {
            "mode": "Local SQLite Engine",
            "database_backup": "Online SQLite snapshots via backup_sqlite_database(). Preserved in data/backups/ directory with Write-Ahead Logging (WAL) consistency.",
            "storage_backup": "Local PDF storage directory in data/uploads/ can be archived or synced to persistent external block storage / volume mounts.",
            "recovery_procedure": "Copy the latest documind_backup_*.db back to data/documind.db.",
            "export_available": True
        }
