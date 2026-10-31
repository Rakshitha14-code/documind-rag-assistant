import streamlit as st
from datetime import datetime
from src.auth import get_current_user
from src.database import get_user_dashboard_stats


def render_dashboard_view():
    """Renders the authentic, data-driven Dashboard with real metrics and quick actions."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to access your dashboard.")
        return

    user_id = user["id"]
    stats = get_user_dashboard_stats(user_id)

    # Header section with personalized greeting
    col_head, col_action = st.columns([2.5, 1])
    with col_head:
        st.markdown(
            f"""
            <div style="margin-bottom: 1.5rem;">
                <h1 style="font-size: 2rem; margin-bottom: 0.3rem; overflow-wrap: break-word; word-break: break-word;">Welcome back, {user['full_name']}</h1>
                <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                    Here is an overview of your active knowledge workspace and document intelligence.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_action:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ Upload", use_container_width=True, help="Upload new PDF documents"):
                st.session_state["active_page"] = "My Documents"
                st.rerun()
        with col_btn2:
            if st.button("💬 Ask", use_container_width=True, help="Ask questions across your PDFs"):
                st.session_state["active_page"] = "Chat with Documents"
                st.rerun()

    # Real Metrics Grid
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Documents", stats["total_docs"])
    with m2:
        st.metric("Indexed & Ready", stats["indexed_docs"])
    with m3:
        st.metric("Knowledge Chunks", stats["total_chunks"])
    with m4:
        st.metric("Questions Asked", stats["questions_asked"])

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # If user has no documents yet: show informative Getting Started Empty State
    if stats["total_docs"] == 0:
        st.markdown(
            """
            <div class="dm-empty-state">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📂</div>
                <h3>Your Document Workspace is Empty</h3>
                <p>
                    Get started by uploading your lecture notes, textbook chapters, or research papers.
                    DocuMind will chunk, vectorize, and prepare them for instant verifiable Q&A.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.8rem; margin-top: 1.2rem;">
                <h3 style="font-size: 1.2rem; margin-bottom: 1rem; color: #B42332;">🚀 3 Easy Steps to Supercharge Your Study Workflow</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.2rem;">
                    <div style="background: #FFF9F0; border: 1px solid #E9DED7; border-radius: 8px; padding: 1.2rem;">
                        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">1️⃣</div>
                        <strong style="color: #252525;">Upload Multi-Page PDFs</strong>
                        <p style="color: #706B68; font-size: 0.88rem; margin-top: 0.4rem;">
                            Head to <strong>My Documents</strong> and upload one or multiple PDF files. You can assign them to collections like Biology or Math.
                        </p>
                    </div>
                    <div style="background: #FFF9F0; border: 1px solid #E9DED7; border-radius: 8px; padding: 1.2rem;">
                        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">2️⃣</div>
                        <strong style="color: #252525;">Ask Natural Language Questions</strong>
                        <p style="color: #706B68; font-size: 0.88rem; margin-top: 0.4rem;">
                            Open <strong>Chat with Documents</strong>. Ask targeted questions and inspect exact page citations and supporting excerpts.
                        </p>
                    </div>
                    <div style="background: #FFF9F0; border: 1px solid #E9DED7; border-radius: 8px; padding: 1.2rem;">
                        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">3️⃣</div>
                        <strong style="color: #252525;">Synthesize & Export</strong>
                        <p style="color: #706B68; font-size: 0.88rem; margin-top: 0.4rem;">
                            Cross-examine multiple papers in <strong>Compare Documents</strong>, save high-yield study notes, and export professional DOCX/PDF reports.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_c1, col_c2, col_c3 = st.columns([1, 1.2, 1])
        with col_c2:
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            if st.button("📤 Upload Your First Document Now", use_container_width=True, type="primary"):
                st.session_state["active_page"] = "My Documents"
                st.rerun()

    else:
        # User has documents: show Recently Added Documents and Quick Overview
        col_recents, col_summary = st.columns([1.8, 1.2])

        with col_recents:
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                    <h3 style="font-size: 1.2rem; margin: 0;">Recently Added Documents</h3>
                </div>
                """,
                unsafe_allow_html=True
            )

            for doc in stats["recent_docs"]:
                status = doc.get("status", "processing")
                if status == "indexed":
                    badge_html = '<span class="dm-badge dm-badge-green">READY</span>'
                elif status == "failed":
                    badge_html = '<span class="dm-badge dm-badge-red">FAILED</span>'
                else:
                    badge_html = '<span class="dm-badge dm-badge-gray">PROCESSING</span>'

                coll_name = doc.get("collection_name") or "General"
                size_mb = doc["file_size"] / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB" if size_mb >= 0.1 else f"{doc['file_size'] / 1024:.1f} KB"

                st.markdown(
                    f"""
                    <div class="dm-card" style="padding: 1rem 1.2rem; margin-bottom: 0.8rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="font-size: 1.5rem;">📄</div>
                                <div>
                                    <strong style="color: #252525; font-size: 0.95rem; overflow-wrap: break-word; word-break: break-word;">{doc['filename']}</strong>
                                    <div style="color: #706B68; font-size: 0.8rem; margin-top: 2px;">
                                        {size_str} • {doc['page_count']} pages • {doc['chunk_count']} chunks • Collection: <em>{coll_name}</em>
                                    </div>
                                </div>
                            </div>
                            <div>{badge_html}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if st.button("View All Documents in Library →", use_container_width=False):
                st.session_state["active_page"] = "My Documents"
                st.rerun()

        with col_summary:
            st.markdown(
                """
                <h3 style="font-size: 1.2rem; margin-bottom: 0.8rem;">Quick Shortcuts</h3>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.3rem;">
                    <p style="color: #252525; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.4rem;">
                        📚 Knowledge Summary
                    </p>
                    <p style="color: #706B68; font-size: 0.88rem; line-height: 1.5; margin-bottom: 1rem;">
                        You have <strong>{stats['indexed_docs']}</strong> verified documents split into <strong>{stats['total_chunks']}</strong> semantic vectors ready for grounded retrieval.
                    </p>
                    <hr style="border-color: #E9DED7; margin: 1rem 0;" />
                    <p style="color: #252525; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.4rem;">
                        📝 Saved Study Notes
                    </p>
                    <p style="color: #706B68; font-size: 0.88rem; line-height: 1.5; margin-bottom: 1.2rem;">
                        You have <strong>{stats['notes_count']}</strong> saved notes in your notebook.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
            if st.button("⚖️ Compare Two or More PDFs", use_container_width=True):
                st.session_state["active_page"] = "Compare Documents"
                st.rerun()

            if st.button("📓 Open Saved Notes", use_container_width=True):
                st.session_state["active_page"] = "Saved Notes"
                st.rerun()
