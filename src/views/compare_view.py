import streamlit as st
from typing import List, Dict, Any

from src.auth import get_current_user
from src.database import get_user_documents, create_note
from src.comparison import compare_documents_on_topic


def render_compare_view():
    """Renders the Document Comparison workspace for cross-document synthesis."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to compare documents.")
        return

    user_id = user["id"]

    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">Compare Documents</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Cross-examine findings, compare methodologies, and discover agreements or contradictions across multiple PDFs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    indexed_docs = get_user_documents(user_id, status_filter="indexed")
    if len(indexed_docs) < 2:
        st.markdown(
            """
            <div class="dm-empty-state">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚖️</div>
                <h3>At Least 2 Indexed Documents Required</h3>
                <p>
                    Document comparison requires at least two uploaded and indexed PDF files.
                    Please upload another document to enable side-by-side synthesis.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("📤 Upload Documents Now", type="primary"):
            st.session_state["active_page"] = "My Documents"
            st.rerun()
        return

    doc_options = {d["id"]: f"{d['filename']} ({d['page_count']} pages)" for d in indexed_docs}

    col_select, col_topic = st.columns([1.3, 1.7])

    with col_select:
        st.markdown("<h4 style='font-size: 1.05rem; margin-bottom: 0.4rem;'>1. Select Documents (min 2)</h4>", unsafe_allow_html=True)
        selected_ids = st.multiselect(
            "Target Documents",
            options=list(doc_options.keys()),
            format_func=lambda did: doc_options.get(did, str(did)),
            default=list(doc_options.keys())[:2],
            help="Select two or more PDFs from your library to compare."
        )

    with col_topic:
        st.markdown("<h4 style='font-size: 1.05rem; margin-bottom: 0.4rem;'>2. Enter Comparison Topic</h4>", unsafe_allow_html=True)
        topic_input = st.text_input(
            "Topic or Focus Question",
            placeholder="e.g. Central hypothesis, methodology, or results",
            help="What aspect would you like to compare across these documents?"
        )

        st.caption("Quick Topic Presets:")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            if st.button("Key Findings", use_container_width=True):
                topic_input = "Key findings, conclusions, and core contributions"
        with col_p2:
            if st.button("Methodology", use_container_width=True):
                topic_input = "Research methodology, experiments, and datasets used"
        with col_p3:
            if st.button("Limitations", use_container_width=True):
                topic_input = "Limitations, potential weaknesses, and open challenges"

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if st.button("⚖️ Run Comparative Analysis", type="primary", use_container_width=True):
        if len(selected_ids) < 2:
            st.error("Please select at least 2 documents to compare.")
        elif not topic_input.strip():
            st.error("Please enter a topic to compare.")
        else:
            with st.spinner("Extracting comparative evidence & synthesizing..."):
                result = compare_documents_on_topic(
                    user_id=user_id,
                    doc_ids=selected_ids,
                    topic=topic_input
                )

                st.session_state["last_comparison_result"] = result
                st.session_state["last_comparison_topic"] = topic_input

    # Display comparison results if available
    saved_res = st.session_state.get("last_comparison_result")
    saved_topic = st.session_state.get("last_comparison_topic")

    if saved_res and saved_res.get("success"):
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(f"### 📋 Comparison Report: *\"{saved_topic}\"*")

        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.8rem; margin-bottom: 1.5rem;">
            """,
            unsafe_allow_html=True
        )

        st.markdown(saved_res["comparison_text"])

        st.markdown("</div>", unsafe_allow_html=True)

        # Evidence Cards Expander
        doc_evidence = saved_res.get("doc_evidence", {})
        with st.expander("🔍 Inspect Verbatim Evidence Excerpts by Document", expanded=False):
            for fname, data in doc_evidence.items():
                st.markdown(f"**📄 {fname}**")
                chunks = data.get("chunks", [])
                if not chunks:
                    st.caption("No relevant chunks found.")
                for c in chunks:
                    st.markdown(
                        f"""
                        <div class="dm-citation">
                            <div class="dm-citation-meta">Page {c['page']} • {c['similarity']:.0%} Match</div>
                            "{c['text']}"
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Save to Notes Action
        col_s1, col_s2 = st.columns([3, 1.2])
        with col_s2:
            if st.button("💾 Save Report to Notes", use_container_width=True):
                create_note(
                    user_id=user_id,
                    title=f"Comparison: {saved_topic}",
                    content=saved_res["comparison_text"],
                    source_citation=", ".join(doc_evidence.keys()),
                    tags="Comparison"
                )
                st.success("Saved to your Notebook!")
