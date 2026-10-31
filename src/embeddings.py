import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
_EMBEDDING_MODEL_INSTANCE: Optional[SentenceTransformer] = None


def get_embedding_model(model_name: Optional[str] = None) -> SentenceTransformer:
    """
    Returns a cached local SentenceTransformer embedding model.
    Runs 100% offline on local CPU/device.
    """
    global _EMBEDDING_MODEL_INSTANCE
    name = model_name or DEFAULT_MODEL_NAME

    if _EMBEDDING_MODEL_INSTANCE is None:
        # Load local model
        _EMBEDDING_MODEL_INSTANCE = SentenceTransformer(name)

    return _EMBEDDING_MODEL_INSTANCE


def embed_texts(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """Generates embedding vectors for a batch of strings."""
    if not texts:
        return []
    model = get_embedding_model(model_name)
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(query: str, model_name: Optional[str] = None) -> List[float]:
    """Generates embedding vector for a single query string."""
    model = get_embedding_model(model_name)
    embedding = model.encode(query, show_progress_bar=False, normalize_embeddings=True)
    return embedding.tolist()
