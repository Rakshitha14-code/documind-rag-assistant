import json
import streamlit as st
from typing import List, Dict, Any, Optional

from src.auth import get_current_user
from src.database import (
    get_user_documents,
    get_user_chat_sessions,
    get_chat_session,
    create_chat_session,
    rename_chat_session,
    delete_chat_session,
    get_session_messages,
    add_chat_message,
    create_note
)
from src.rag_pipeline import query_rag_pipeline


def render_chat_view():
    """Renders the Multi-PDF Chat interface with grounded citations and session management."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to chat with your documents.")
        return

    user_id = user["id"]

    # Header
    st.markdown(
        """
        <div style="margin-bottom: 1rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">Chat with Documents</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Ask questions across single or multiple PDFs. Every answer is grounded with verifiable page citations.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Check if user has indexed documents
    indexed_docs = get_user_documents(user_id, status_filter="indexed")
    if not indexed_docs:
        st.markdown(
            """
            <div class="dm-empty-state">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📚</div>
                <h3>No Indexed Documents Available</h3>
                <p>You need to upload and index at least one PDF before asking questions.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("📤 Go to My Documents to Upload PDFs", type="primary"):
            st.session_state["active_page"] = "My Documents"
            st.rerun()
        return

    # Chat Sessions Management
    sessions = get_user_chat_sessions(user_id)
    if not sessions:
        # Create initial default session
        new_sid = create_chat_session(user_id, "Research Notes & Q&A")
        st.session_state["current_chat_session_id"] = new_sid
        sessions = get_user_chat_sessions(user_id)

    curr_sid = st.session_state.get("current_chat_session_id")
    if not curr_sid or not any(s["id"] == curr_sid for s in sessions):
        curr_sid = sessions[0]["id"]
        st.session_state["current_chat_session_id"] = curr_sid

    active_session = get_chat_session(user_id, curr_sid)

    # Top Control Bar: Session Selector, New Chat, Rename, Scope Filter
    col_sess, col_btn_new, col_btn_ren, col_btn_del = st.columns([2.5, 0.8, 0.8, 0.8])

    with col_sess:
        session_titles = {s["id"]: s["title"] for s in sessions}
        selected_session_id = st.selectbox(
            "Conversation Session",
            options=list(session_titles.keys()),
            format_func=lambda sid: session_titles.get(sid, sid),
            index=list(session_titles.keys()).index(curr_sid) if curr_sid in session_titles else 0,
            key="chat_session_selector"
        )
        if selected_session_id != curr_sid:
            st.session_state["current_chat_session_id"] = selected_session_id
            st.rerun()

    with col_btn_new:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ New", help="Start a new chat conversation"):
            new_id = create_chat_session(user_id, "New Research Chat")
            st.session_state["current_chat_session_id"] = new_id
            st.rerun()

    with col_btn_ren:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        rename_toggle_key = f"toggle_rename_{curr_sid}"
        if st.button("✏️ Rename", help="Rename active chat session"):
            st.session_state[rename_toggle_key] = not st.session_state.get(rename_toggle_key, False)
            st.rerun()

    with col_btn_del:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if len(sessions) > 1:
            if st.button("🗑️ Del", help="Delete this chat session"):
                delete_chat_session(user_id, curr_sid)
                remaining = get_user_chat_sessions(user_id)
                st.session_state["current_chat_session_id"] = remaining[0]["id"] if remaining else None
                st.rerun()

    # Inline rename input
    if st.session_state.get(f"toggle_rename_{curr_sid}", False):
        col_ren_in, col_ren_ok = st.columns([3, 1])
        with col_ren_in:
            new_title_val = st.text_input("New Session Name", value=active_session["title"] if active_session else "")
        with col_ren_ok:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Save Name"):
                if new_title_val.strip():
                    rename_chat_session(user_id, curr_sid, new_title_val.strip())
                    st.session_state[f"toggle_rename_{curr_sid}"] = False
                    st.rerun()

    # Document Scope Filter
    doc_options = {d["id"]: f"{d['filename']} ({d['page_count']} pages)" for d in indexed_docs}

    with st.expander("🎯 Filter Document Scope (select specific PDFs to query)", expanded=False):
        scope_all = st.checkbox("Query all indexed documents", value=True, key="scope_all_docs")
        selected_doc_ids: Optional[List[int]] = None
        if not scope_all:
            selected_docs = st.multiselect(
                "Select target documents:",
                options=list(doc_options.keys()),
                format_func=lambda did: doc_options.get(did, str(did)),
                default=list(doc_options.keys())[:3]
            )
            selected_doc_ids = selected_docs if selected_docs else None

    # Load and display chat messages
    messages = get_session_messages(curr_sid)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if not messages:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; text-align: center; margin: 1rem 0;">
                <div style="font-size: 2rem; margin-bottom: 0.4rem;">💬</div>
                <h4 style="margin: 0 0 0.3rem 0; color: #252525;">Ask anything about your documents</h4>
                <p style="color: #706B68; font-size: 0.88rem; max-width: 500px; margin: 0 auto;">
                    DocuMind will retrieve the exact paragraphs, summarize the findings, and give you verbatim citations.
                </p>
                <div style="display: flex; gap: 8px; justify-content: center; margin-top: 1rem; flex-wrap: wrap;">
                    <span class="dm-badge dm-badge-red">What is the central hypothesis?</span>
                    <span class="dm-badge dm-badge-gray">Summarize the key findings</span>
                    <span class="dm-badge dm-badge-gray">Explain the methodology</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        sources_raw = msg.get("sources_json")

        with st.chat_message(role):
            st.markdown(content)

            # Display citations and source card for assistant messages
            if role == "assistant" and sources_raw:
                try:
                    sources = json.loads(sources_raw)
                    if sources:
                        with st.expander(f"📚 Verified Sources & Page Citations ({len(sources)})", expanded=False):
                            for s in sources:
                                fname = s.get("filename", "Document")
                                page = s.get("page", 1)
                                sim = s.get("similarity", 0.0)
                                snippet = s.get("snippet", "")
                                st.markdown(
                                    f"""
                                    <div class="dm-citation">
                                        <div class="dm-citation-meta">
                                            📄 {fname} • Page {page} • <span style="color: #287D55;">{sim:.0%} Match</span>
                                        </div>
                                        <div style="font-style: italic; color: #353535;">
                                            "{snippet}"
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                            # Quick Save to Notes Action
                            col_n1, col_n2 = st.columns([3, 1.2])
                            with col_n2:
                                note_save_key = f"save_note_{msg['id']}"
                                if st.button("💾 Save Answer to Notes", key=note_save_key, help="Add this response directly into your Saved Notes notebook"):
                                    citation_str = f"{sources[0]['filename']} (Page {sources[0]['page']})" if sources else "Chat"
                                    create_note(
                                        user_id=user_id,
                                        title=f"Note: {active_session['title']}",
                                        content=content,
                                        source_citation=citation_str,
                                        tags="Q&A"
                                    )
                                    st.success("Saved to your Notebook!")
                except Exception:
                    pass

    # Chat Input Box
    user_query = st.chat_input("Ask a question based on your indexed PDFs...")

    if user_query:
        # 1. Add user message to SQLite
        add_chat_message(session_id=curr_sid, role="user", content=user_query)

        # 2. Re-fetch history for multi-turn context
        history = [{"role": m["role"], "content": m["content"]} for m in messages]

        # 3. Query RAG pipeline
        with st.spinner("Searching document vectors & generating answer..."):
            rag_result = query_rag_pipeline(
                user_id=user_id,
                question=user_query,
                doc_ids=selected_doc_ids,
                conversation_history=history
            )

        answer_text = rag_result["answer"]
        sources_list = rag_result["sources"]
        sources_json_str = json.dumps(sources_list) if sources_list else None

        # 4. Save assistant answer to SQLite
        add_chat_message(
            session_id=curr_sid,
            role="assistant",
            content=answer_text,
            sources_json=sources_json_str
        )

        st.rerun()
