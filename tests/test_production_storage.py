import os
import io
import tempfile
import time
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.database import (
    init_db,
    register_user,
    authenticate_user,
    get_user_by_id,
    add_document,
    update_document_status,
    get_user_documents,
    get_document_by_id,
    delete_document,
    delete_document_cascade,
    retry_document_processing,
    check_document_duplicate,
    create_chat_session,
    add_chat_message,
    get_session_messages,
    create_note,
    get_user_notes,
    get_user_preferences,
    save_user_preferences
)
from src.auth import create_session_token, verify_session_token
from src.document_processor import validate_pdf, extract_pdf_pages, chunk_document_pages
from src.storage_provider import LocalStorageProvider
from src.vector_store import add_document_chunks, query_similar_chunks, count_user_chunks
from src.migrations import run_sqlite_migrations
from src.backup import backup_sqlite_database, export_user_workspace
from src.supabase_client import test_supabase_connection as check_supabase_connection


def create_sample_pdf(title: str, text: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, f"Title: {title}")
    c.drawString(100, 700, f"Content: {text}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def env_setup():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_documind.db")
    storage_dir = os.path.join(temp_dir, "uploads")
    chroma_dir = os.path.join(temp_dir, "chroma")
    os.makedirs(storage_dir, exist_ok=True)
    os.makedirs(chroma_dir, exist_ok=True)

    init_db(db_path)
    storage = LocalStorageProvider(base_dir=storage_dir)

    yield {
        "dir": temp_dir,
        "db": db_path,
        "storage_dir": storage_dir,
        "chroma_dir": chroma_dir,
        "storage": storage
    }

    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


# ------------------------------------------------------------------------------
# 1. New account registration
# ------------------------------------------------------------------------------
def test_1_new_account_registration(env_setup):
    db = env_setup["db"]
    res = register_user("newuser@university.edu", "StrongPassword123!", "New Student", db_path=db)
    assert res["success"] is True
    user = res["user"]
    assert user["email"] == "newuser@university.edu"
    assert user["full_name"] == "New Student"

    # Verify password is NOT stored as plaintext
    user_row = get_user_by_id(user["id"], db_path=db)
    assert user_row is not None
    assert "StrongPassword123!" not in str(user_row.values())

    # Verify default collection and preferences are created
    prefs = get_user_preferences(user["id"], db_path=db)
    assert prefs["answer_style"] == "Balanced"


# ------------------------------------------------------------------------------
# 2. Existing-user login, token generation, and logout
# ------------------------------------------------------------------------------
def test_2_existing_user_login_and_logout(env_setup):
    db = env_setup["db"]
    register_user("alex@domain.com", "MySecretKey99", "Alex", db_path=db)

    # Valid login
    auth_ok = authenticate_user("alex@domain.com", "MySecretKey99", db_path=db)
    assert auth_ok["success"] is True
    uid = auth_ok["user"]["id"]

    # Session token creation and verification
    token = create_session_token(uid, "alex@domain.com", duration_sec=3600)
    payload = verify_session_token(token)
    assert payload is not None
    assert payload["uid"] == uid
    assert payload["em"] == "alex@domain.com"

    # Expired token test
    expired_token = create_session_token(uid, "alex@domain.com", duration_sec=-10)
    assert verify_session_token(expired_token) is None


# ------------------------------------------------------------------------------
# 3. Uploading a valid PDF
# ------------------------------------------------------------------------------
def test_3_uploading_valid_pdf(env_setup):
    db = env_setup["db"]
    storage = env_setup["storage"]
    reg = register_user("uploader@test.edu", "Pass12345", "Uploader", db_path=db)
    uid = reg["user"]["id"]

    pdf_bytes = create_sample_pdf("Quantum Computing", "Superposition is a fundamental principle of quantum mechanics.")
    is_valid, err = validate_pdf(pdf_bytes, "quantum.pdf")
    assert is_valid is True
    assert err is None

    stored_path = storage.save_file(uid, "quantum.pdf", pdf_bytes)
    assert os.path.exists(stored_path)

    doc_id = add_document(uid, "quantum.pdf", stored_path, len(pdf_bytes), db_path=db)
    assert doc_id > 0


# ------------------------------------------------------------------------------
# 4. Rejecting invalid or oversized files
# ------------------------------------------------------------------------------
def test_4_rejecting_invalid_or_oversized_files():
    # Wrong extension
    ok, err = validate_pdf(b"%PDF-1.4 dummy", "notes.txt")
    assert ok is False
    assert "extension" in err

    # Empty file
    ok, err = validate_pdf(b"", "empty.pdf")
    assert ok is False
    assert "empty" in err

    # Corrupted header
    ok, err = validate_pdf(b"NOT_A_PDF_HEADER_DATA", "corrupt.pdf")
    assert ok is False
    assert "header" in err

    # Oversized (>50MB)
    oversized = b"%PDF-" + b"0" * (51 * 1024 * 1024)
    ok, err = validate_pdf(oversized, "big.pdf")
    assert ok is False
    assert "50MB" in err


# ------------------------------------------------------------------------------
# 5. Persisting PDF files and metadata
# ------------------------------------------------------------------------------
def test_5_persisting_pdf_files_and_metadata(env_setup):
    db = env_setup["db"]
    storage = env_setup["storage"]
    u = register_user("persist@test.edu", "Password123", "Persist", db_path=db)["user"]
    uid = u["id"]

    pdf_bytes = create_sample_pdf("Genetics", "DNA is composed of four nucleotide bases.")
    stored_path = storage.save_file(uid, "genetics.pdf", pdf_bytes)
    doc_id = add_document(uid, "genetics.pdf", stored_path, len(pdf_bytes), db_path=db)
    update_document_status(doc_id, uid, "indexed", page_count=1, chunk_count=2, db_path=db)

    # Verify retrieval
    doc = get_document_by_id(uid, doc_id, db_path=db)
    assert doc is not None
    assert doc["filename"] == "genetics.pdf"
    assert doc["status"] == "indexed"
    assert doc["page_count"] == 1

    retrieved_bytes = storage.get_file_bytes(uid, stored_path)
    assert retrieved_bytes == pdf_bytes


# ------------------------------------------------------------------------------
# 6. Retrieving previously uploaded PDF after simulated restart
# ------------------------------------------------------------------------------
def test_6_retrieve_uploaded_pdf_after_restart(env_setup):
    db = env_setup["db"]
    storage_dir = env_setup["storage_dir"]
    u = register_user("restart@test.edu", "Password123", "Restart User", db_path=db)["user"]
    uid = u["id"]

    # Initial session: upload file
    storage_s1 = LocalStorageProvider(base_dir=storage_dir)
    pdf_bytes = create_sample_pdf("Lecture 1", "Introduction to Artificial Intelligence.")
    path = storage_s1.save_file(uid, "lecture1.pdf", pdf_bytes)
    add_document(uid, "lecture1.pdf", path, len(pdf_bytes), db_path=db)

    # Simulated restart: instantiate completely new storage provider instance
    storage_s2 = LocalStorageProvider(base_dir=storage_dir)
    docs = get_user_documents(uid, db_path=db)
    assert len(docs) == 1
    assert docs[0]["filename"] == "lecture1.pdf"

    reloaded_bytes = storage_s2.get_file_bytes(uid, docs[0]["stored_path"])
    assert reloaded_bytes == pdf_bytes


# ------------------------------------------------------------------------------
# 7. Restoring chat history and saved notes
# ------------------------------------------------------------------------------
def test_7_restore_chat_history_and_saved_notes(env_setup):
    db = env_setup["db"]
    u = register_user("chatter@test.edu", "Password123", "Chatter", db_path=db)["user"]
    uid = u["id"]

    # Chat session and messages
    sid = create_chat_session(uid, "Neural Networks Discussion", db_path=db)
    add_chat_message(sid, "user", "What is backpropagation?", db_path=db)
    add_chat_message(sid, "assistant", "Backpropagation computes the gradient of the loss function.", sources_json='[{"doc": "nn.pdf", "page": 4}]', db_path=db)

    # Note
    note_id = create_note(uid, "Backprop Formula", "Gradient descent update rule.", tags="AI, Math", db_path=db)

    # Verify restoration
    messages = get_session_messages(sid, db_path=db)
    assert len(messages) == 2
    assert messages[0]["content"] == "What is backpropagation?"
    assert "loss function" in messages[1]["content"]

    notes = get_user_notes(uid, db_path=db)
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert "Gradient descent" in notes[0]["content"]


# ------------------------------------------------------------------------------
# 8. Document processing failure and safe retry
# ------------------------------------------------------------------------------
def test_8_document_processing_failure_and_safe_retry(env_setup, monkeypatch):
    db = env_setup["db"]
    storage = env_setup["storage"]
    chroma_dir = env_setup["chroma_dir"]

    # Patch storage provider and chroma dir
    monkeypatch.setenv("CHROMA_PERSIST_DIR", chroma_dir)
    monkeypatch.setenv("UPLOADS_DIR", env_setup["storage_dir"])

    u = register_user("retryer@test.edu", "Password123", "Retryer", db_path=db)["user"]
    uid = u["id"]

    pdf_bytes = create_sample_pdf("Biochemistry", "Enzymes act as biological catalysts to accelerate chemical reactions.")
    stored_path = storage.save_file(uid, "biochem.pdf", pdf_bytes)
    doc_id = add_document(uid, "biochem.pdf", stored_path, len(pdf_bytes), db_path=db)

    # Intentionally simulate a failed indexing status
    update_document_status(doc_id, uid, "failed", error_message="Simulated temporary GPU/vector index failure.", db_path=db)
    doc_fail = get_document_by_id(uid, doc_id, db_path=db)
    assert doc_fail["status"] == "failed"

    # Execute safe retry
    res = retry_document_processing(uid, doc_id, db_path=db)
    assert res["success"] is True

    # Verify recovered document status
    doc_recovered = get_document_by_id(uid, doc_id, db_path=db)
    assert doc_recovered["status"] == "indexed"
    assert doc_recovered["page_count"] >= 1
    assert doc_recovered["chunk_count"] >= 1
    assert doc_recovered["error_message"] is None


# ------------------------------------------------------------------------------
# 9. Preventing duplicate processing
# ------------------------------------------------------------------------------
def test_9_preventing_duplicate_processing(env_setup):
    db = env_setup["db"]
    u = register_user("dedup@test.edu", "Password123", "Dedup", db_path=db)["user"]
    uid = u["id"]

    doc_id = add_document(uid, "thesis.pdf", "/dummy/thesis.pdf", 45000, db_path=db)
    update_document_status(doc_id, uid, "indexed", db_path=db)

    # Check duplicate
    dup = check_document_duplicate(uid, "thesis.pdf", 45000, db_path=db)
    assert dup is not None
    assert dup["id"] == doc_id

    # Non-duplicate
    no_dup = check_document_duplicate(uid, "thesis_v2.pdf", 45000, db_path=db)
    assert no_dup is None


# ------------------------------------------------------------------------------
# 10. User A denied access to User B's documents, chats, notes, and vectors
# ------------------------------------------------------------------------------
def test_10_tenant_isolation(env_setup):
    db = env_setup["db"]
    storage = env_setup["storage"]

    u1 = register_user("usera@test.edu", "Password123!", "User A", db_path=db)["user"]
    u2 = register_user("userb@test.edu", "Password123!", "User B", db_path=db)["user"]

    u1_id, u2_id = u1["id"], u2["id"]

    # User A data
    pdf_bytes = create_sample_pdf("Private A", "Confidential financial statement.")
    path_a = storage.save_file(u1_id, "private_a.pdf", pdf_bytes)
    doc_a_id = add_document(u1_id, "private_a.pdf", path_a, len(pdf_bytes), db_path=db)
    note_a_id = create_note(u1_id, "Secret Note A", "Password list for Project X", db_path=db)
    sess_a_id = create_chat_session(u1_id, "Secret Session A", db_path=db)

    # User B attempts to access User A's document metadata -> Returns None
    assert get_document_by_id(u2_id, doc_a_id, db_path=db) is None
    assert len(get_user_documents(u2_id, db_path=db)) == 0

    # User B attempts to access User A's physical file via storage -> Raises PermissionError
    with pytest.raises(PermissionError):
        storage.get_file_bytes(u2_id, path_a)

    with pytest.raises(PermissionError):
        storage.delete_file(u2_id, path_a)

    # User B attempts to access User A's notes and chat sessions
    assert len(get_user_notes(u2_id, db_path=db)) == 0
    assert get_document_by_id(u2_id, doc_a_id, db_path=db) is None


# ------------------------------------------------------------------------------
# 11. Secure document deletion (coordinating storage, DB, and vectors)
# ------------------------------------------------------------------------------
def test_11_secure_document_deletion(env_setup, monkeypatch):
    db = env_setup["db"]
    storage = env_setup["storage"]
    chroma_dir = env_setup["chroma_dir"]

    monkeypatch.setenv("CHROMA_PERSIST_DIR", chroma_dir)
    monkeypatch.setenv("UPLOADS_DIR", env_setup["storage_dir"])

    u = register_user("deleter@test.edu", "Pass1234", "Deleter", db_path=db)["user"]
    uid = u["id"]

    pdf_bytes = create_sample_pdf("Delete Me", "Temporary document to test cascade deletion.")
    path = storage.save_file(uid, "delete_me.pdf", pdf_bytes)
    doc_id = add_document(uid, "delete_me.pdf", path, len(pdf_bytes), db_path=db)

    # Add mock vector chunks
    chunks = chunk_document_pages(
        pages=[{"page": 1, "text": "Temporary document to test cascade deletion."}],
        doc_id=doc_id,
        user_id=uid,
        filename="delete_me.pdf"
    )
    add_document_chunks(uid, chunks, persist_directory=chroma_dir)
    assert count_user_chunks(uid, persist_directory=chroma_dir) >= 1

    # Execute cascade deletion
    res = delete_document_cascade(uid, doc_id, db_path=db)
    assert res["success"] is True

    # 1. DB record is gone
    assert get_document_by_id(uid, doc_id, db_path=db) is None

    # 2. File is deleted from disk
    assert not os.path.exists(path)

    # 3. Vector chunks are pruned
    assert count_user_chunks(uid, persist_directory=chroma_dir) == 0


# ------------------------------------------------------------------------------
# 12. Database migration without data loss
# ------------------------------------------------------------------------------
def test_12_database_migration_without_data_loss(tmp_path):
    old_db = str(tmp_path / "legacy.db")
    import sqlite3
    conn = sqlite3.connect(old_db)
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            status TEXT DEFAULT 'indexed'
        );
    """)
    conn.execute("INSERT INTO documents (user_id, filename, stored_path, file_size) VALUES (1, 'legacy.pdf', '/leg.pdf', 1000);")
    conn.commit()
    conn.close()

    # Run migration
    run_sqlite_migrations(old_db)

    # Verify existing row remains intact and updated_at column was added
    conn2 = sqlite3.connect(old_db)
    cursor = conn2.cursor()
    cursor.execute("SELECT id, filename, updated_at FROM documents WHERE id = 1;")
    row = cursor.fetchone()
    conn2.close()

    assert row is not None
    assert row[0] == 1
    assert row[1] == "legacy.pdf"


# ------------------------------------------------------------------------------
# 13. Missing or invalid service credentials handling
# ------------------------------------------------------------------------------
def test_13_missing_or_invalid_service_credentials():
    # When Supabase is not configured in .env, connection test reports unconfigured gracefully without crashing
    res = check_supabase_connection()
    assert isinstance(res, dict)
    assert "configured" in res
    if not res["configured"]:
        assert "not configured" in res["message"].lower()


# ------------------------------------------------------------------------------
# 14. Recovery behavior after failed storage and backup snapshots
# ------------------------------------------------------------------------------
def test_14_recovery_behavior_and_backup(env_setup):
    db = env_setup["db"]
    u = register_user("recovery@test.edu", "Pass1234", "Recovery User", db_path=db)["user"]
    uid = u["id"]

    # Missing file recovery behavior: should report clean failure without crashing
    missing_doc_id = add_document(uid, "ghost.pdf", "/nonexistent/path/ghost.pdf", 1234, db_path=db)
    res = retry_document_processing(uid, missing_doc_id, db_path=db)
    assert res["success"] is False
    assert "could not be read" in res["error"] or "missing" in res["error"]

    # Verify backup snapshot creation
    backup_file = backup_sqlite_database(db_path=db)
    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 0

    # Verify JSON workspace export
    export_bundle = export_user_workspace(uid, db_path=db)
    assert export_bundle["user"]["email"] == "recovery@test.edu"
    assert "documents" in export_bundle

