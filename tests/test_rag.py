import pytest
from src.rag_pipeline import (
    format_context_prompt,
    build_system_prompt,
    generate_answer_with_llm,
    query_rag_pipeline
)
from src.database import init_db, register_user, save_user_preferences


def test_format_context_prompt():
    chunks = [
        {
            "filename": "Paper1.pdf",
            "page": 3,
            "similarity": 0.88,
            "text": "The transformer model utilizes self-attention mechanisms."
        },
        {
            "filename": "Paper2.pdf",
            "page": 7,
            "similarity": 0.79,
            "text": "Recurrent neural networks suffer from vanishing gradient issues."
        }
    ]
    formatted = format_context_prompt(chunks)
    assert "Paper1.pdf" in formatted
    assert "Page: 3" in formatted
    assert "Similarity: 88%" in formatted
    assert "self-attention" in formatted
    assert "Paper2.pdf" in formatted


def test_build_system_prompt_styles():
    prompt_balanced = build_system_prompt("Balanced")
    assert "DocuMind" in prompt_balanced
    assert "[Doc: <filename>, Page: <page_number>]" in prompt_balanced
    assert "insufficient evidence" in prompt_balanced

    prompt_concise = build_system_prompt("Concise")
    assert "concise" in prompt_concise.lower()

    prompt_detailed = build_system_prompt("Detailed")
    assert "comprehensive" in prompt_detailed.lower()


def test_rag_pipeline_without_api_key_returns_setup_guide(tmp_path):
    db_file = str(tmp_path / "test_rag.db")
    init_db(db_file)
    user_res = register_user("student@test.com", "Password123", "Student", db_path=db_file)
    user_id = user_res["user"]["id"]

    # Explicitly clear API key
    save_user_preferences(user_id=user_id, llm_provider="gemini", api_key="", db_path=db_file)

    # When querying without Gemini API key:
    res = query_rag_pipeline(
        user_id=user_id,
        question="What is the learning rate?",
        custom_provider="gemini",
        custom_api_key="",
        db_path=db_file
    )

    # Should NOT invent a fake response
    assert res is not None
    assert "error" in res


def test_generate_answer_missing_key_detection():
    ans, err = generate_answer_with_llm(
        prompt="Test question",
        system_prompt="Test sys",
        llm_provider="gemini",
        api_key=""
    )
    assert ans is None
    assert err == "NO_KEY_GEMINI"

    ans_oai, err_oai = generate_answer_with_llm(
        prompt="Test question",
        system_prompt="Test sys",
        llm_provider="openai",
        api_key=""
    )
    assert ans_oai is None
    assert err_oai == "NO_KEY_OPENAI"
