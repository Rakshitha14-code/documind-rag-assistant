from typing import List, Dict, Any, Optional
from src.database import get_document_by_id, get_user_preferences
from src.vector_store import query_similar_chunks
from src.rag_pipeline import generate_answer_with_llm


def compare_documents_on_topic(
    user_id: int,
    doc_ids: List[int],
    topic: str,
    custom_provider: Optional[str] = None,
    custom_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs comparative document synthesis across two or more selected PDFs on a given topic.
    Extracts evidence per document and generates a structured comparison with citations.
    """
    if len(doc_ids) < 2:
        return {
            "success": False,
            "error": "Please select at least two documents to compare."
        }

    if not topic.strip():
        return {
            "success": False,
            "error": "Please enter a topic or question to compare across the documents."
        }

    # 1. Retrieve evidence per document
    doc_evidence: Dict[str, Dict[str, Any]] = {}
    combined_context_parts = []

    for did in doc_ids:
        doc_info = get_document_by_id(user_id, did)
        fname = doc_info["filename"] if doc_info else f"Document_{did}"
        chunks = query_similar_chunks(
            user_id=user_id,
            query=topic,
            top_k=3,
            doc_ids=[did]
        )
        doc_evidence[fname] = {
            "doc_id": did,
            "filename": fname,
            "chunks": chunks
        }

        # Build context section
        excerpts_text = "\n".join([
            f"  - (Page {c['page']}): \"{c['text']}\""
            for c in chunks
        ]) if chunks else "  - No directly relevant excerpts found for this topic."
        combined_context_parts.append(f"DOCUMENT: {fname}\n{excerpts_text}")

    combined_context = "\n\n".join(combined_context_parts)

    # 2. Get user LLM preferences
    prefs = get_user_preferences(user_id)
    provider = custom_provider or prefs.get("llm_provider", "gemini")
    api_key = custom_api_key or prefs.get("api_key")
    temperature = prefs.get("temperature", 0.2)

    prompt = f"""You are DocuMind, an academic and research document comparison engine.
Compare the following documents strictly on the requested topic: "{topic}".

DOCUMENT EVIDENCE:
{combined_context}

REQUIREMENTS:
1. Ground your analysis strictly in the provided excerpts.
2. Structure your comparison with clear markdown headings:
   - ## 🔍 Executive Summary
   - ## 🤝 Key Similarities & Common Ground
   - ## ⚡ Key Differences & Contrasting Claims
   - ## ❓ Missing or Conflicting Information
   - ## 📊 Comparative Breakdown Table (Markdown table comparing specific dimensions across documents)
3. For EVERY claim or observation, include explicit inline citations: [Doc: <filename>, Page: <page>].
4. If an excerpt does not contain enough info on a point, note it as "Not addressed in provided excerpts".
"""

    system_prompt = "You are an objective academic research synthesizer. Ground all claims in provided excerpts with page citations. Never invent facts."

    raw_comparison, error = generate_answer_with_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        llm_provider=provider,
        api_key=api_key,
        temperature=temperature
    )

    if error and error.startswith("NO_KEY_"):
        fallback_markdown = f"""### 📊 Retrieved Document Evidence for: *"{topic}"*

*(LLM API key not configured. Below is the side-by-side evidence extracted from each document. To enable automated synthesis and markdown comparison table, add your API key in Settings).*

"""
        for fname, data in doc_evidence.items():
            fallback_markdown += f"#### 📄 {fname}\n"
            if data["chunks"]:
                for c in data["chunks"]:
                    fallback_markdown += f"- **Page {c['page']}** (Relevance: {c['similarity']:.0%}):\n  > \"{c['text']}\"\n\n"
            else:
                fallback_markdown += "- *No matching excerpts found for this topic.*\n\n"

        return {
            "success": True,
            "comparison_text": fallback_markdown,
            "doc_evidence": doc_evidence,
            "error": "API_KEY_REQUIRED"
        }

    if error:
        return {
            "success": False,
            "error": f"Comparison generation error: {error}",
            "doc_evidence": doc_evidence
        }

    return {
        "success": True,
        "comparison_text": raw_comparison or "No comparison generated.",
        "doc_evidence": doc_evidence,
        "error": None
    }
