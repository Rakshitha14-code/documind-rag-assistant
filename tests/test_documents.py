import os
import io
import tempfile
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.database import init_db, register_user, add_document, get_user_documents, delete_document
from src.document_processor import validate_pdf, extract_pdf_pages, split_text_into_chunks, chunk_document_pages
from src.vector_store import (
    add_document_chunks,
    query_similar_chunks,
    delete_document_chunks,
    count_user_chunks
)


def create_sample_pdf_bytes(title: str, body_text: str, num_pages: int = 2) -> bytes:
    """Creates a valid multi-page PDF in memory with ReportLab."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    for p in range(num_pages):
        c.drawString(100, 750, f"{title} - Page {p + 1}")
        c.drawString(100, 720, f"Section {p + 1}: {body_text}")
        c.drawString(100, 700, f"Page specific fact for page {p + 1}: The mitochondria is the powerhouse of the cell.")
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def temp_dirs():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_chroma:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(db_path)
        yield {"chroma": tmp_chroma, "db": db_path}
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_pdf_validation_valid_and_invalid():
    pdf_bytes = create_sample_pdf_bytes("Physics 101", "Thermodynamics lecture notes.", num_pages=1)

    # Valid PDF
    is_valid, err = validate_pdf(pdf_bytes, "physics_101.pdf")
    assert is_valid is True
    assert err is None

    # Invalid extension
    is_valid, err = validate_pdf(pdf_bytes, "physics_101.txt")
    assert is_valid is False
    assert "extension" in err

    # Empty bytes
    is_valid, err = validate_pdf(b"", "empty.pdf")
    assert is_valid is False

    # Corrupt header
    is_valid, err = validate_pdf(b"NOT_A_PDF_FILE_HEADER", "corrupt.pdf")
    assert is_valid is False
    assert "Invalid PDF header" in err


def test_pdf_text_extraction_and_pages():
    pdf_bytes = create_sample_pdf_bytes("Bio 200", "Cellular biology and photosynthesis.", num_pages=3)
    pages, warn = extract_pdf_pages(pdf_bytes)
    assert len(pages) == 3
    assert warn is None
    assert pages[0]["page"] == 1
    assert "Bio 200 - Page 1" in pages[0]["text"]
    assert pages[2]["page"] == 3
    assert "Bio 200 - Page 3" in pages[2]["text"]


def test_scanned_pdf_detection():
    # PDF with blank/no text pages
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.showPage()
    c.save()
    pages, warn = extract_pdf_pages(buffer.getvalue())
    assert warn is not None
    assert "scanned" in warn.lower()


def test_chunking_preserves_metadata():
    pages = [
        {"page": 1, "text": "Neural networks learn representations from high dimensional data. " * 10},
        {"page": 2, "text": "Convolutional layers specialize in spatial feature extraction. " * 10}
    ]
    chunks = chunk_document_pages(pages, doc_id=42, user_id=1, filename="DeepLearning.pdf", chunk_size=250, chunk_overlap=50)
    assert len(chunks) > 1
    assert chunks[0]["metadata"]["doc_id"] == 42
    assert chunks[0]["metadata"]["user_id"] == 1
    assert chunks[0]["metadata"]["filename"] == "DeepLearning.pdf"
    assert chunks[0]["metadata"]["page"] in [1, 2]
    assert chunks[0]["id"].startswith("doc_42_p")


def test_vector_indexing_retrieval_and_filtering(temp_dirs):
    chroma_dir = temp_dirs["chroma"]
    user_id = 101

    # Create chunks for Document 1 (Biology)
    chunks_doc1 = [
        {
            "id": "doc_1_p1_c0",
            "text": "Photosynthesis occurs inside chloroplasts where light energy converts water into oxygen.",
            "metadata": {"doc_id": 1, "user_id": user_id, "filename": "Bio_Photosynthesis.pdf", "page": 1, "chunk_index": 0}
        }
    ]
    # Create chunks for Document 2 (Calculus)
    chunks_doc2 = [
        {
            "id": "doc_2_p1_c0",
            "text": "The derivative represents the instantaneous rate of change of a mathematical function.",
            "metadata": {"doc_id": 2, "user_id": user_id, "filename": "Math_Calculus.pdf", "page": 1, "chunk_index": 0}
        }
    ]

    added1 = add_document_chunks(user_id, chunks_doc1, persist_directory=chroma_dir)
    added2 = add_document_chunks(user_id, chunks_doc2, persist_directory=chroma_dir)
    assert added1 == 1
    assert added2 == 1
    assert count_user_chunks(user_id, persist_directory=chroma_dir) == 2

    # Query without filter: ask about chloroplasts
    results = query_similar_chunks(user_id, "Where does photosynthesis take place?", top_k=2, persist_directory=chroma_dir)
    assert len(results) > 0
    assert results[0]["filename"] == "Bio_Photosynthesis.pdf"
    assert "chloroplasts" in results[0]["text"]
    assert results[0]["page"] == 1

    # Query with document filter: restrict only to Math doc_id=2
    filtered_results = query_similar_chunks(
        user_id,
        "What is instantaneous rate of change?",
        top_k=2,
        doc_ids=[2],
        persist_directory=chroma_dir
    )
    assert len(filtered_results) > 0
    for r in filtered_results:
        assert r["doc_id"] == 2
        assert r["filename"] == "Math_Calculus.pdf"


def test_document_deletion_vector_pruning(temp_dirs):
    chroma_dir = temp_dirs["chroma"]
    user_id = 202

    chunks = [
        {
            "id": f"doc_5_p1_c{i}",
            "text": f"Machine learning chunk content number {i}",
            "metadata": {"doc_id": 5, "user_id": user_id, "filename": "ML.pdf", "page": 1, "chunk_index": i}
        }
        for i in range(3)
    ]
    add_document_chunks(user_id, chunks, persist_directory=chroma_dir)
    assert count_user_chunks(user_id, persist_directory=chroma_dir) == 3

    # Delete doc_id=5
    del_ok = delete_document_chunks(user_id, doc_id=5, persist_directory=chroma_dir)
    assert del_ok is True
    assert count_user_chunks(user_id, persist_directory=chroma_dir) == 0
