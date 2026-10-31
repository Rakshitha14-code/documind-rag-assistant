"""
DocuMind Root RAG Pipeline forwarder.
Re-exports the core RAG pipeline implementation from src.rag_pipeline.
"""
from src.rag_pipeline import (
    format_context_prompt,
    build_system_prompt,
    generate_answer_with_llm,
    query_rag_pipeline,
)

__all__ = [
    "format_context_prompt",
    "build_system_prompt",
    "generate_answer_with_llm",
    "query_rag_pipeline",
]
