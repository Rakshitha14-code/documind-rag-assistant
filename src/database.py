import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import bcrypt
from dotenv import load_dotenv

from src.migrations import run_sqlite_migrations

load_dotenv()

DEFAULT_DB_PATH = os.getenv("DOCUMIND_DB_PATH", os.path.join("data", "documind.db"))


def get_db_path(custom_path: Optional[str] = None) -> str:
    path = custom_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 20000;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes SQLite database schema with required tables and indexes, then executes safe migrations."""
    target_path = get_db_path(db_path)
    conn = get_connection(target_path)

    try:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    collection_id INTEGER,
                    filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    page_count INTEGER DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'processing',
                    error_message TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS saved_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    document_id INTEGER,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_citation TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    answer_style TEXT DEFAULT 'Balanced',
                    top_k INTEGER DEFAULT 4,
                    llm_provider TEXT DEFAULT 'gemini',
                    api_key TEXT,
                    temperature REAL DEFAULT 0.2,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                -- Indexes for fast queries
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_saved_notes_user ON saved_notes(user_id);
            """)
    finally:
        conn.close()

    # Apply safe migrations and activate WAL mode
    run_sqlite_migrations(target_path)



# ==============================================================================
# USER & AUTHENTICATION OPERATIONS
# ==============================================================================

def hash_password(password: str) -> str:
    """Hashes a password with bcrypt using a salted hash."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies a plaintext password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def register_user(email: str, password: str, full_name: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Registers a new user, enforcing clean emails and uniqueness."""
    email_clean = email.strip().lower()
    full_name_clean = full_name.strip()

    if not email_clean or "@" not in email_clean or "." not in email_clean.split("@")[-1]:
        return {"success": False, "error": "Please provide a valid email address."}

    if not full_name_clean:
        return {"success": False, "error": "Full name is required."}

    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters long."}

    hashed = hash_password(password)
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
                (email_clean, hashed, full_name_clean)
            )
            user_id = cursor.lastrowid
            # Initialize default preferences
            cursor.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id) VALUES (?)",
                (user_id,)
            )
            # Create a default collection
            cursor.execute(
                "INSERT INTO collections (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, "General", "Default document workspace")
            )
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "email": email_clean,
                    "full_name": full_name_clean
                }
            }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "An account with this email address already exists."}
    except Exception as e:
        return {"success": False, "error": f"Registration failed: {str(e)}"}
    finally:
        conn.close()


def authenticate_user(email: str, password: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Validates login credentials and updates last_login."""
    email_clean = email.strip().lower()
    if not email_clean or not password:
        return {"success": False, "error": "Email and password are required."}

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, full_name, created_at FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()

        if not row or not verify_password(password, row["password_hash"]):
            return {"success": False, "error": "Invalid email or password."}

        # Update last login timestamp
        with conn:
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],)
            )

        return {
            "success": True,
            "user": {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "created_at": row["created_at"]
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Authentication error: {str(e)}"}
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, created_at, last_login FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_profile(user_id: int, full_name: str, email: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                (full_name.strip(), email.strip().lower(), user_id)
            )
        return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email address already in use."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def update_user_password(user_id: int, old_password: str, new_password: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    if len(new_password) < 8:
        return {"success": False, "error": "New password must be at least 8 characters long."}

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not verify_password(old_password, row["password_hash"]):
            return {"success": False, "error": "Current password is incorrect."}

        new_hash = hash_password(new_password)
        with conn:
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ==============================================================================
# COLLECTION OPERATIONS
# ==============================================================================

def create_collection(user_id: int, name: str, description: str = "", db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO collections (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, name.strip(), description.strip())
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_user_collections(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.name, c.description, c.created_at,
                   COUNT(d.id) AS document_count
            FROM collections c
            LEFT JOIN documents d ON d.collection_id = c.id AND d.user_id = c.user_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.name ASC
            """,
            (user_id,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def delete_collection(user_id: int, collection_id: int, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            # Documents in this collection will have collection_id set to NULL due to SET NULL fk
            cursor = conn.cursor()
            cursor.execute("DELETE FROM collections WHERE id = ? AND user_id = ?", (collection_id, user_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


# ==============================================================================
# DOCUMENT OPERATIONS
# ==============================================================================

def add_document(user_id: int, filename: str, stored_path: str, file_size: int,
                 collection_id: Optional[int] = None, db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO documents (user_id, collection_id, filename, stored_path, file_size, status)
                VALUES (?, ?, ?, ?, ?, 'processing')
                """,
                (user_id, collection_id, filename, stored_path, file_size)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def update_document_status(doc_id: int, user_id: int, status: str,
                           page_count: Optional[int] = None,
                           chunk_count: Optional[int] = None,
                           error_message: Optional[str] = None,
                           clear_error: bool = False,
                           db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            updates = ["status = ?"]
            params: List[Any] = [status]

            if page_count is not None:
                updates.append("page_count = ?")
                params.append(page_count)
            if chunk_count is not None:
                updates.append("chunk_count = ?")
                params.append(chunk_count)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            elif clear_error or status == "indexed":
                updates.append("error_message = NULL")

            params.extend([doc_id, user_id])
            query = f"UPDATE documents SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_user_documents(user_id: int, collection_id: Optional[int] = None,
                       search: Optional[str] = None,
                       status_filter: Optional[str] = None,
                       db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT d.id, d.user_id, d.collection_id, d.filename, d.stored_path,
                   d.file_size, d.page_count, d.chunk_count, d.status, d.error_message,
                   d.uploaded_at, c.name AS collection_name
            FROM documents d
            LEFT JOIN collections c ON d.collection_id = c.id
            WHERE d.user_id = ?
        """
        params: List[Any] = [user_id]

        if collection_id is not None:
            query += " AND d.collection_id = ?"
            params.append(collection_id)

        if search:
            query += " AND d.filename LIKE ?"
            params.append(f"%{search.strip()}%")

        if status_filter:
            query += " AND d.status = ?"
            params.append(status_filter)

        query += " ORDER BY d.uploaded_at DESC"
        cursor.execute(query, tuple(params))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_document_by_id(user_id: int, doc_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.*, c.name AS collection_name
            FROM documents d
            LEFT JOIN collections c ON d.collection_id = c.id
            WHERE d.id = ? AND d.user_id = ?
            """,
            (doc_id, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_document(user_id: int, doc_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Deletes document metadata and returns deleted doc info so file & vectors can be pruned."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        doc = cursor.fetchone()
        if not doc:
            return None
        doc_dict = dict(doc)
        with conn:
            cursor.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        return doc_dict
    finally:
        conn.close()


def check_document_duplicate(user_id: int, filename: str, file_size: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Checks if identical document (same name & file size) has already been indexed for this user."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM documents WHERE user_id = ? AND filename = ? AND file_size = ? AND status = 'indexed'",
            (user_id, filename, file_size)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_document_cascade(user_id: int, doc_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely coordinates cascading deletion of a document across:
    1. Vector store (ChromaDB chunks)
    2. Persistent storage (Supabase bucket or local filesystem)
    3. SQLite/PostgreSQL document metadata record
    Guarantees strict tenant authorization before performing any deletion.
    """
    from src.storage_provider import get_storage_provider
    from src.vector_store import delete_document_chunks

    doc = get_document_by_id(user_id, doc_id, db_path)
    if not doc:
        return {"success": False, "error": "Document not found or access denied."}

    # 1. Prune vectors from Chroma
    try:
        delete_document_chunks(user_id, doc_id)
    except Exception as e:
        print(f"[Warning] Failed to prune vectors for doc {doc_id}: {e}")

    # 2. Prune physical file from persistent storage
    try:
        storage = get_storage_provider()
        if doc.get("stored_path"):
            storage.delete_file(user_id, doc["stored_path"])
    except Exception as e:
        print(f"[Warning] Failed to delete stored file for doc {doc_id}: {e}")

    # 3. Delete metadata record from database
    deleted_doc = delete_document(user_id, doc_id, db_path)
    if not deleted_doc:
        return {"success": False, "error": "Failed to remove document database record."}

    return {"success": True, "document": doc}


def retry_document_processing(user_id: int, doc_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely re-attempts indexing for a failed or stuck document.
    Reads the preserved original PDF from persistent storage,
    re-extracts pages, re-chunks, embeds, and indexes into ChromaDB.
    """
    from src.storage_provider import get_storage_provider
    from src.document_processor import validate_pdf, extract_pdf_pages, chunk_document_pages
    from src.vector_store import delete_document_chunks, add_document_chunks

    doc = get_document_by_id(user_id, doc_id, db_path)
    if not doc:
        return {"success": False, "error": "Document not found or access denied."}

    # Mark as processing
    update_document_status(doc_id, user_id, "processing", error_message=None, db_path=db_path)

    # 1. Retrieve stored file bytes
    storage = get_storage_provider()
    stored_path = doc.get("stored_path")
    if not stored_path:
        err = "Stored file path is missing. Please re-upload the document."
        update_document_status(doc_id, user_id, "failed", error_message=err, db_path=db_path)
        return {"success": False, "error": err}

    try:
        file_bytes = storage.get_file_bytes(user_id, stored_path)
    except Exception as e:
        err = f"Stored PDF file could not be read: {str(e)}"
        update_document_status(doc_id, user_id, "failed", error_message=err, db_path=db_path)
        return {"success": False, "error": err}

    if not file_bytes:
        err = "Stored PDF file could not be read from storage."
        update_document_status(doc_id, user_id, "failed", error_message=err, db_path=db_path)
        return {"success": False, "error": err}

    # 2. Validate PDF
    is_valid, val_err = validate_pdf(file_bytes, doc["filename"])
    if not is_valid:
        update_document_status(doc_id, user_id, "failed", error_message=val_err, db_path=db_path)
        return {"success": False, "error": val_err}

    # 3. Extract pages
    pages, page_warning = extract_pdf_pages(file_bytes)
    page_count = len(pages)
    if page_warning:
        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=page_warning, db_path=db_path)
        return {"success": False, "error": page_warning}

    # 4. Remove any prior partial chunks to guarantee idempotency and avoid duplicates
    delete_document_chunks(user_id, doc_id)

    # 5. Chunk text
    chunks = chunk_document_pages(
        pages=pages,
        doc_id=doc_id,
        user_id=user_id,
        filename=doc["filename"],
        chunk_size=800,
        chunk_overlap=150
    )
    if not chunks:
        err = "No extractable text chunks could be formed from this document."
        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=err, db_path=db_path)
        return {"success": False, "error": err}

    # 6. Embed and Index into vector store
    try:
        indexed_count = add_document_chunks(user_id, chunks)
        update_document_status(
            doc_id=doc_id,
            user_id=user_id,
            status="indexed",
            page_count=page_count,
            chunk_count=indexed_count,
            error_message=None,
            db_path=db_path
        )
        return {"success": True, "page_count": page_count, "chunk_count": indexed_count}
    except Exception as e:
        err = f"Vector indexing failed: {str(e)}"
        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=err, db_path=db_path)
        return {"success": False, "error": err}



# ==============================================================================
# CHAT SESSIONS & MESSAGES
# ==============================================================================

def create_chat_session(user_id: int, title: Optional[str] = None, session_id: Optional[str] = None, db_path: Optional[str] = None) -> str:
    sid = session_id or str(uuid.uuid4())
    sess_title = title.strip() if title else f"Conversation {datetime.now().strftime('%b %d, %H:%M')}"
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, title) VALUES (?, ?, ?)",
                (sid, user_id, sess_title)
            )
        return sid
    finally:
        conn.close()


def get_user_chat_sessions(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """,
            (user_id,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_chat_session(user_id: int, session_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def rename_chat_session(user_id: int, session_id: str, new_title: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (new_title.strip(), session_id, user_id)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_chat_session(user_id: int, session_id: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


def add_chat_message(session_id: str, role: str, content: str, sources_json: Optional[str] = None, db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_messages (session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
                (session_id, role, content, sources_json)
            )
            msg_id = cursor.lastrowid
            cursor.execute("UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
            return msg_id
    finally:
        conn.close()


def get_session_messages(session_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_id, role, content, sources_json, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# ==============================================================================
# SAVED NOTES
# ==============================================================================

def create_note(user_id: int, title: str, content: str, document_id: Optional[int] = None,
                source_citation: Optional[str] = None, tags: Optional[str] = None,
                db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO saved_notes (user_id, document_id, title, content, source_citation, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, document_id, title.strip(), content.strip(), source_citation, tags)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_user_notes(user_id: int, search: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT n.*, d.filename AS document_name
            FROM saved_notes n
            LEFT JOIN documents d ON n.document_id = d.id
            WHERE n.user_id = ?
        """
        params: List[Any] = [user_id]
        if search:
            query += " AND (n.title LIKE ? OR n.content LIKE ? OR n.tags LIKE ?)"
            s_term = f"%{search.strip()}%"
            params.extend([s_term, s_term, s_term])

        query += " ORDER BY n.updated_at DESC"
        cursor.execute(query, tuple(params))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_note_by_id(user_id: int, note_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT n.*, d.filename AS document_name
            FROM saved_notes n
            LEFT JOIN documents d ON n.document_id = d.id
            WHERE n.id = ? AND n.user_id = ?
            """,
            (note_id, user_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_note(user_id: int, note_id: int, title: str, content: str,
                tags: Optional[str] = None, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE saved_notes
                SET title = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (title.strip(), content.strip(), tags, note_id, user_id)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_note(user_id: int, note_id: int, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_notes WHERE id = ? AND user_id = ?", (note_id, user_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


# ==============================================================================
# USER PREFERENCES
# ==============================================================================

def get_user_preferences(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        # Default prefs if not found
        return {
            "user_id": user_id,
            "answer_style": "Balanced",
            "top_k": 4,
            "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
            "api_key": None,
            "temperature": 0.2
        }
    finally:
        conn.close()


def save_user_preferences(user_id: int, answer_style: str = "Balanced", top_k: int = 4,
                          llm_provider: str = "gemini", api_key: Optional[str] = None,
                          temperature: float = 0.2, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, answer_style, top_k, llm_provider, api_key, temperature)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    answer_style = excluded.answer_style,
                    top_k = excluded.top_k,
                    llm_provider = excluded.llm_provider,
                    api_key = COALESCE(excluded.api_key, user_preferences.api_key),
                    temperature = excluded.temperature
                """,
                (user_id, answer_style, top_k, llm_provider, api_key, temperature)
            )
            return True
    finally:
        conn.close()


# ==============================================================================
# DASHBOARD STATS
# ==============================================================================

def get_user_dashboard_stats(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves real stored metrics for the authenticated user's dashboard."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Total docs uploaded
        cursor.execute("SELECT COUNT(*) AS total FROM documents WHERE user_id = ?", (user_id,))
        total_docs = cursor.fetchone()["total"]

        # Total indexed docs
        cursor.execute("SELECT COUNT(*) AS indexed_total, COALESCE(SUM(chunk_count), 0) AS total_chunks FROM documents WHERE user_id = ? AND status = 'indexed'", (user_id,))
        indexed_row = cursor.fetchone()
        indexed_docs = indexed_row["indexed_total"]
        total_chunks = indexed_row["total_chunks"]

        # Questions asked (user role messages)
        cursor.execute(
            """
            SELECT COUNT(m.id) AS questions
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            WHERE s.user_id = ? AND m.role = 'user'
            """,
            (user_id,)
        )
        questions_asked = cursor.fetchone()["questions"]

        # Saved notes count
        cursor.execute("SELECT COUNT(*) AS notes_total FROM saved_notes WHERE user_id = ?", (user_id,))
        notes_count = cursor.fetchone()["notes_total"]

        # Recently accessed / uploaded documents
        cursor.execute(
            """
            SELECT d.id, d.filename, d.file_size, d.page_count, d.chunk_count, d.status, d.uploaded_at, c.name AS collection_name
            FROM documents d
            LEFT JOIN collections c ON d.collection_id = c.id
            WHERE d.user_id = ?
            ORDER BY d.uploaded_at DESC
            LIMIT 5
            """,
            (user_id,)
        )
        recent_docs = [dict(r) for r in cursor.fetchall()]

        return {
            "total_docs": total_docs,
            "indexed_docs": indexed_docs,
            "total_chunks": total_chunks,
            "questions_asked": questions_asked,
            "notes_count": notes_count,
            "recent_docs": recent_docs
        }
    finally:
        conn.close()
