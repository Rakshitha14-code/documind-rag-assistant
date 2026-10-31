import os
import tempfile
import pytest

from src.database import (
    init_db,
    register_user,
    add_document,
    get_user_documents,
    get_document_by_id,
    delete_document,
    create_chat_session,
    get_user_chat_sessions,
    get_chat_session,
    add_chat_message,
    get_session_messages,
    create_note,
    get_user_notes,
    get_note_by_id,
    delete_note
)
from src.vector_store import (
    add_document_chunks,
    query_similar_chunks,
    count_user_chunks
)


@pytest.fixture
def multi_user_setup():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as chroma_dir:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(db_path)

        user1 = register_user("user1@univ.edu", "Password123", "User One", db_path=db_path)["user"]
        user2 = register_user("user2@univ.edu", "Password123", "User Two", db_path=db_path)["user"]

        yield {
            "db": db_path,
            "chroma": chroma_dir,
            "user1": user1,
            "user2": user2
        }

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_document_tenant_isolation(multi_user_setup):
    db = multi_user_setup["db"]
    u1_id = multi_user_setup["user1"]["id"]
    u2_id = multi_user_setup["user2"]["id"]

    # User 1 uploads a secret document
    doc1_id = add_document(u1_id, "Secret_Exam_U1.pdf", "/path/u1.pdf", 1024, db_path=db)

    # User 1 can see it
    u1_docs = get_user_documents(u1_id, db_path=db)
    assert len(u1_docs) == 1
    assert u1_docs[0]["filename"] == "Secret_Exam_U1.pdf"

    # User 2 CANNOT see User 1's document in list
    u2_docs = get_user_documents(u2_id, db_path=db)
    assert len(u2_docs) == 0

    # User 2 CANNOT fetch User 1's document directly by ID
    u2_get = get_document_by_id(u2_id, doc1_id, db_path=db)
    assert u2_get is None

    # User 2 CANNOT delete User 1's document
    del_res = delete_document(u2_id, doc1_id, db_path=db)
    assert del_res is None
    # Verify doc still exists for User 1
    assert get_document_by_id(u1_id, doc1_id, db_path=db) is not None


def test_chat_session_tenant_isolation(multi_user_setup):
    db = multi_user_setup["db"]
    u1_id = multi_user_setup["user1"]["id"]
    u2_id = multi_user_setup["user2"]["id"]

    sess1_id = create_chat_session(u1_id, "User 1 Research", db_path=db)
    add_chat_message(sess1_id, "user", "What is quantum computing?", db_path=db)

    # User 1 sees session
    assert len(get_user_chat_sessions(u1_id, db_path=db)) == 1

    # User 2 does NOT see session
    assert len(get_user_chat_sessions(u2_id, db_path=db)) == 0

    # User 2 cannot access session details
    assert get_chat_session(u2_id, sess1_id, db_path=db) is None


def test_saved_notes_tenant_isolation(multi_user_setup):
    db = multi_user_setup["db"]
    u1_id = multi_user_setup["user1"]["id"]
    u2_id = multi_user_setup["user2"]["id"]

    note1_id = create_note(u1_id, "U1 Note", "Confidential formula", db_path=db)

    # User 1 has 1 note
    assert len(get_user_notes(u1_id, db_path=db)) == 1

    # User 2 has 0 notes
    assert len(get_user_notes(u2_id, db_path=db)) == 0

    # User 2 cannot view or delete User 1's note
    assert get_note_by_id(u2_id, note1_id, db_path=db) is None
    del_note = delete_note(u2_id, note1_id, db_path=db)
    assert del_note is False


def test_vector_store_tenant_isolation(multi_user_setup):
    chroma_dir = multi_user_setup["chroma"]
    u1_id = multi_user_setup["user1"]["id"]
    u2_id = multi_user_setup["user2"]["id"]

    # User 1 adds confidential vectors
    chunks_u1 = [
        {
            "id": "u1_doc_1",
            "text": "The proprietary formula for Project Alpha is XYZ-9000.",
            "metadata": {"doc_id": 1, "user_id": u1_id, "filename": "Confidential.pdf", "page": 1, "chunk_index": 0}
        }
    ]
    add_document_chunks(u1_id, chunks_u1, persist_directory=chroma_dir)

    assert count_user_chunks(u1_id, persist_directory=chroma_dir) == 1
    assert count_user_chunks(u2_id, persist_directory=chroma_dir) == 0

    # User 2 queries for the secret term
    u2_results = query_similar_chunks(
        user_id=u2_id,
        query="What is the proprietary formula for Project Alpha?",
        top_k=3,
        persist_directory=chroma_dir
    )
    # User 2 MUST get 0 results
    assert len(u2_results) == 0

    # User 1 queries and gets their result
    u1_results = query_similar_chunks(
        user_id=u1_id,
        query="What is the proprietary formula for Project Alpha?",
        top_k=3,
        persist_directory=chroma_dir
    )
    assert len(u1_results) == 1
    assert "XYZ-9000" in u1_results[0]["text"]
