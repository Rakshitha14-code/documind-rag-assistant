import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from src.embeddings import embed_texts, embed_query

load_dotenv()

DEFAULT_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
_CHROMA_CLIENT_INSTANCE: Optional[chromadb.PersistentClient] = None


def get_chroma_client(persist_directory: Optional[str] = None) -> chromadb.PersistentClient:
    """Returns a singleton Chroma persistent client."""
    global _CHROMA_CLIENT_INSTANCE
    target_dir = persist_directory or DEFAULT_CHROMA_DIR
    os.makedirs(target_dir, exist_ok=True)

    if _CHROMA_CLIENT_INSTANCE is None:
        _CHROMA_CLIENT_INSTANCE = chromadb.PersistentClient(
            path=target_dir,
            settings=Settings(anonymized_telemetry=False)
        )
    return _CHROMA_CLIENT_INSTANCE


def get_user_collection_name(user_id: int) -> str:
    """Names collections uniquely per user to guarantee tenant isolation."""
    return f"user_{user_id}_knowledge"


def get_or_create_user_collection(user_id: int, persist_directory: Optional[str] = None):
    """Retrieves or creates the user's isolated vector collection."""
    client = get_chroma_client(persist_directory)
    collection_name = get_user_collection_name(user_id)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def add_document_chunks(user_id: int, chunks: List[Dict[str, Any]], persist_directory: Optional[str] = None) -> int:
    """
    Embeds chunk texts and persists them with rich metadata into Chroma.
    """
    if not chunks:
        return 0

    collection = get_or_create_user_collection(user_id, persist_directory)

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Generate embeddings with local model
    embeddings = embed_texts(texts)

    # Add in batches to prevent memory spikes on large PDFs
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = i + batch_size
        collection.add(
            ids=ids[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings[i:end]
        )

    return len(ids)


def query_similar_chunks(
    user_id: int,
    query: str,
    top_k: int = 4,
    doc_ids: Optional[List[int]] = None,
    persist_directory: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves the most semantically relevant chunks for a question,
    with strict user isolation and optional document filtering.
    """
    if not query.strip():
        return []

    collection = get_or_create_user_collection(user_id, persist_directory)
    if collection.count() == 0:
        return []

    query_vector = embed_query(query)

    # Build where clause for metadata filtering if doc_ids specified
    where_filter: Optional[Dict[str, Any]] = None
    if doc_ids:
        clean_doc_ids = [int(d) for d in doc_ids]
        if len(clean_doc_ids) == 1:
            where_filter = {"doc_id": clean_doc_ids[0]}
        else:
            where_filter = {"doc_id": {"$in": clean_doc_ids}}

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, max(1, collection.count())),
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    retrieved: List[Dict[str, Any]] = []
    if results and results.get("ids") and results["ids"][0]:
        doc_texts = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        for chunk_id, text, meta, dist in zip(ids, doc_texts, metadatas, distances):
            # Cosine similarity conversion: 1 - cosine_distance
            similarity = round(1.0 - float(dist), 4) if dist is not None else 0.0
            retrieved.append({
                "id": chunk_id,
                "text": text,
                "metadata": meta,
                "distance": dist,
                "similarity": similarity,
                "filename": meta.get("filename", "Unknown"),
                "page": meta.get("page", 1),
                "doc_id": meta.get("doc_id")
            })

    # Sort descending by similarity
    retrieved.sort(key=lambda x: x["similarity"], reverse=True)
    return retrieved


def delete_document_chunks(user_id: int, doc_id: int, persist_directory: Optional[str] = None) -> bool:
    """Removes all indexed chunks belonging to a specific document from ChromaDB."""
    try:
        collection = get_or_create_user_collection(user_id, persist_directory)
        collection.delete(where={"doc_id": int(doc_id)})
        return True
    except Exception:
        return False


def count_user_chunks(user_id: int, persist_directory: Optional[str] = None) -> int:
    """Returns the total number of indexed vectors for the given user."""
    try:
        collection = get_or_create_user_collection(user_id, persist_directory)
        return collection.count()
    except Exception:
        return 0
