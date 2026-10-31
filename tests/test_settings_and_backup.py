import os
import tempfile
import sqlite3
import pytest
from src.database import (
    init_db,
    register_user,
    add_document,
    create_chat_session,
    add_chat_message,
    create_note,
    create_collection
)
from src.backup import export_user_workspace, backup_sqlite_database, get_disaster_recovery_plan


@pytest.fixture
def test_workspace():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_workspace.db")
    init_db(db_path)

    user_res = register_user("testuser@research.edu", "Password123!", "Test User", db_path=db_path)
    uid = user_res["user"]["id"]

    # Add sample collection, document, chat, and note
    coll_id = create_collection(uid, "Quantum Physics", "Lecture notes on quantum mechanics", db_path=db_path)
    add_document(uid, "Quantum_Paper.pdf", "/sample/path/quantum.pdf", 2048, collection_id=coll_id, db_path=db_path)
    sid = create_chat_session(uid, "Quantum Entanglement", db_path=db_path)
    add_chat_message(sid, "user", "What is entanglement?", db_path=db_path)
    add_chat_message(sid, "assistant", "Entanglement is a physical phenomenon...", db_path=db_path)
    create_note(uid, "Bell's Theorem", "Local hidden variables theorem", source_citation="Quantum_Paper.pdf", tags="Physics", db_path=db_path)

    yield {"dir": temp_dir, "db": db_path, "uid": uid}

    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def test_export_user_workspace(test_workspace):
    uid = test_workspace["uid"]
    db = test_workspace["db"]

    bundle = export_user_workspace(uid, db_path=db)
    assert bundle["version"] == "1.0"
    assert bundle["user"]["email"] == "testuser@research.edu"
    assert len(bundle["collections"]) >= 1
    assert any(c["name"] == "Quantum Physics" for c in bundle["collections"])
    assert len(bundle["documents"]) == 1
    assert bundle["documents"][0]["filename"] == "Quantum_Paper.pdf"
    assert len(bundle["chat_history"]) == 1
    assert bundle["chat_history"][0]["session"]["title"] == "Quantum Entanglement"
    assert len(bundle["chat_history"][0]["messages"]) == 2
    assert len(bundle["notes"]) == 1
    assert bundle["notes"][0]["title"] == "Bell's Theorem"


def test_backup_sqlite_database(test_workspace):
    db = test_workspace["db"]
    backup_file = backup_sqlite_database(db_path=db)

    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 0

    # Verify backup is a valid SQLite database with the same data
    conn = sqlite3.connect(backup_file)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    conn.close()

    assert user_count >= 1
    assert doc_count >= 1


def test_disaster_recovery_plan():
    plan = get_disaster_recovery_plan()
    assert "mode" in plan
    assert "database_backup" in plan
    assert "recovery_procedure" in plan
