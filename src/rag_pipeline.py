import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from src.vector_store import query_similar_chunks
from src.database import get_user_preferences

load_dotenv()


def format_context_prompt(chunks: List[Dict[str, Any]]) -> str:
    """Formats retrieved vector chunks into an unambiguous grounded context block."""
    if not chunks:
        return "No relevant document excerpts were retrieved."

    formatted_parts = []
    for i, c in enumerate(chunks, 1):
        filename = c.get("filename", "Unknown Document")
        page = c.get("page", 1)
        sim = c.get("similarity", 0.0)
        text = c.get("text", "").strip()
        formatted_parts.append(
            f"--- EXCERPT {i} [Document: {filename} | Page: {page} | Similarity: {sim:.0%}] ---\n{text}"
        )

    return "\n\n".join(formatted_parts)


def build_system_prompt(answer_style: str = "Balanced") -> str:
    """Builds the strict grounding system prompt respecting user answer preferences."""
    style_instruction = ""
    if answer_style == "Concise":
        style_instruction = "Be direct, concise, and prioritize high-density bullet points."
    elif answer_style == "Detailed":
        style_instruction = "Provide a thorough, comprehensive explanation with structural headings and deep conceptual context."
    else:
        style_instruction = "Provide a well-structured, clear, and balanced academic explanation."

    return f"""You are DocuMind, an academic and research document assistant for students and researchers.

STRICT GROUNDING RULES:
1. Answer the user's question using EXCLUSIVELY the provided context excerpts.
2. For EVERY claim, fact, or definition you state, include an exact inline citation in the format: [Doc: <filename>, Page: <page_number>].
3. If the provided context snippets do NOT contain sufficient information to answer the question, do not speculate or extrapolate from outside general knowledge. State explicitly:
   "Based on the provided document excerpts, there is insufficient evidence to answer this question."
4. Never invent source citations, page numbers, or authors not present in the excerpts.
5. {style_instruction}
"""


def generate_answer_with_llm(
    prompt: str,
    system_prompt: str,
    llm_provider: str = "gemini",
    api_key: Optional[str] = None,
    temperature: float = 0.2
) -> Tuple[Optional[str], Optional[str]]:
    """
    Invokes the requested LLM provider (Gemini, OpenAI, Groq) or returns an informative error.
    Returns (answer_text, error_message).
    """
    provider = (llm_provider or "gemini").lower().strip()

    # 1. Google Gemini Provider
    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return None, "NO_KEY_GEMINI"

        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt,
                generation_config={"temperature": temperature}
            )
            response = model.generate_content(prompt)
            return response.text, None
        except Exception as e:
            return None, f"Google Gemini API error: {str(e)}"

    # 2. OpenAI Provider
    elif provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return None, "NO_KEY_OPENAI"

        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content, None
        except Exception as e:
            return None, f"OpenAI API error: {str(e)}"

    # 3. Groq Provider
    elif provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            return None, "NO_KEY_GROQ"

        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content, None
        except Exception as e:
            return None, f"Groq API error: {str(e)}"

    return None, f"Unsupported LLM provider: {provider}"


def query_rag_pipeline(
    user_id: int,
    question: str,
    doc_ids: Optional[List[int]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    custom_top_k: Optional[int] = None,
    custom_provider: Optional[str] = None,
    custom_api_key: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end RAG pipeline:
    1. Semantic retrieval of user-isolated chunks
    2. Construction of strictly grounded prompt
    3. LLM synthesis or honest setup guidance
    4. Citations & metadata packaging
    """
    prefs = get_user_preferences(user_id, db_path=db_path)
    top_k = custom_top_k or prefs.get("top_k", 4)
    provider = custom_provider or prefs.get("llm_provider", "gemini")
    api_key = custom_api_key or prefs.get("api_key")
    answer_style = prefs.get("answer_style", "Balanced")
    temperature = prefs.get("temperature", 0.2)

    # 1. Retrieve similar chunks with doc filter
    retrieved_chunks = query_similar_chunks(
        user_id=user_id,
        query=question,
        top_k=top_k,
        doc_ids=doc_ids
    )

    if not retrieved_chunks:
        return {
            "answer": "No relevant document excerpts were found in your selected PDFs for this question.",
            "sources": [],
            "insufficient_evidence": True,
            "error": None
        }

    # Format context block
    context_text = format_context_prompt(retrieved_chunks)

    # Format conversation history if available
    history_str = ""
    if conversation_history:
        recent_history = conversation_history[-4:]  # Last 2 turns
        hist_lines = []
        for h in recent_history:
            role = "User" if h.get("role") == "user" else "Assistant"
            hist_lines.append(f"{role}: {h.get('content', '')}")
        history_str = "PREVIOUS CONVERSATION CONTEXT:\n" + "\n".join(hist_lines) + "\n\n"

    # User prompt
    full_prompt = f"""{history_str}CONTEXT DOCUMENT EXCERPTS:
{context_text}

USER QUESTION:
{question}

Provide an accurate, grounded answer strictly supported by the excerpts above. Include page citations."""

    system_prompt = build_system_prompt(answer_style)

    # Generate answer
    raw_answer, error = generate_answer_with_llm(
        prompt=full_prompt,
        system_prompt=system_prompt,
        llm_provider=provider,
        api_key=api_key,
        temperature=temperature
    )

    # Package sources
    sources_summary = [
        {
            "filename": c.get("filename", "Unknown"),
            "page": c.get("page", 1),
            "snippet": c.get("text", "")[:350] + ("..." if len(c.get("text", "")) > 350 else ""),
            "similarity": c.get("similarity", 0.0),
            "doc_id": c.get("doc_id")
        }
        for c in retrieved_chunks
    ]

    # Handle missing API key cleanly without fabricating
    if error and error.startswith("NO_KEY_"):
        key_name = error.replace("NO_KEY_", "")
        fallback_msg = f"""⚠️ **LLM API Key Required for AI Synthesis**

DocuMind successfully retrieved **{len(retrieved_chunks)} relevant verified excerpts** from your documents matching this question (inspect the exact pages and snippets in the source cards below).

To enable generative AI synthesis:
1. Open **Settings** or your `.env` file.
2. Add your **{key_name} API Key** (e.g. Gemini key is free at [Google AI Studio](https://aistudio.google.com/)).
3. Resubmit your question.

You can still inspect all verbatim source text, page numbers, and cosine relevance scores below!"""
        return {
            "answer": fallback_msg,
            "sources": sources_summary,
            "insufficient_evidence": False,
            "error": "API_KEY_REQUIRED"
        }

    if error:
        return {
            "answer": f"⚠️ An error occurred while generating the answer: {error}",
            "sources": sources_summary,
            "insufficient_evidence": True,
            "error": error
        }

    # Check for insufficient evidence in response
    insufficient = "insufficient evidence" in (raw_answer or "").lower()

    return {
        "answer": raw_answer or "No answer returned.",
        "sources": sources_summary,
        "insufficient_evidence": insufficient,
        "error": None
    }
