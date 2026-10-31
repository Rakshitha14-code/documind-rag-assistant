import io
import os
from typing import List, Dict, Any, Tuple, Optional
import pypdf

# Maximum permitted file size: 50MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def validate_pdf(file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validates PDF file integrity, magic bytes, size, and encryption status.
    Returns (is_valid, error_message).
    """
    if not filename.lower().endswith(".pdf"):
        return False, "File must have a .pdf extension."

    if len(file_bytes) == 0:
        return False, "Uploaded file is empty (0 bytes)."

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return False, f"File exceeds the 50MB limit ({len(file_bytes) / (1024*1024):.1f} MB)."

    # Check PDF magic bytes (%PDF)
    if not file_bytes.startswith(b"%PDF-"):
        return False, "Invalid PDF header. File is corrupted or not a valid PDF."

    try:
        stream = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(stream)
        if reader.is_encrypted:
            return False, "Document is password-protected or encrypted. Please remove encryption before uploading."
        if len(reader.pages) == 0:
            return False, "PDF contains 0 pages."
    except Exception as e:
        return False, f"PDF could not be parsed: {str(e)}"

    return True, None


def extract_pdf_pages(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Extracts text page-by-page preserving 1-based page indices.
    Detects scanned or empty PDFs.
    Returns (pages_list, warning_or_error_message).
    """
    stream = io.BytesIO(file_bytes)
    reader = pypdf.PdfReader(stream)
    pages: List[Dict[str, Any]] = []
    total_chars = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        clean_text = text.strip()
        total_chars += len(clean_text)
        pages.append({
            "page": page_num,
            "text": clean_text
        })

    if total_chars < 30:
        return pages, "This PDF appears to be a scanned document or image without a selectable text layer."

    return pages, None


def split_text_into_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """
    Recursive character chunking preserving sentence boundaries where possible.
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def _split(t: str, seps: List[str]) -> List[str]:
        if not seps or len(t) <= chunk_size:
            # Base case: split by character slice
            chunks = []
            start = 0
            while start < len(t):
                end = min(start + chunk_size, len(t))
                chunks.append(t[start:end].strip())
                if end == len(t):
                    break
                start += (chunk_size - chunk_overlap)
            return [c for c in chunks if c]

        sep = seps[0]
        remaining_seps = seps[1:]
        parts = t.split(sep)
        chunks = []
        current_chunk = ""

        for part in parts:
            candidate = f"{current_chunk}{sep}{part}" if current_chunk else part
            if len(candidate) <= chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(part) > chunk_size:
                    # Recursive split on inner separator
                    sub_chunks = _split(part, remaining_seps)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    raw_chunks = _split(text, separators)

    # Post-process with overlap merging if needed
    final_chunks: List[str] = []
    for c in raw_chunks:
        c_clean = c.strip()
        if len(c_clean) >= 20:  # Ignore trivial noise chunks
            final_chunks.append(c_clean)

    return final_chunks


def chunk_document_pages(pages: List[Dict[str, Any]], doc_id: int, user_id: int,
                         filename: str, chunk_size: int = 800,
                         chunk_overlap: int = 150) -> List[Dict[str, Any]]:
    """
    Chunks document pages and produces rich metadata for vector indexing.
    """
    all_chunks: List[Dict[str, Any]] = []
    global_chunk_idx = 0

    for p in pages:
        page_num = p["page"]
        page_text = p["text"]
        if not page_text:
            continue

        page_chunks = split_text_into_chunks(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for idx_in_page, chunk_text in enumerate(page_chunks):
            chunk_id = f"doc_{doc_id}_p{page_num}_c{idx_in_page}"
            all_chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": global_chunk_idx
                }
            })
            global_chunk_idx += 1

    return all_chunks
