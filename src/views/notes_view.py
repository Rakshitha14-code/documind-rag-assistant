import streamlit as st
from typing import Optional

from src.auth import get_current_user
from src.database import (
    get_user_notes,
    get_note_by_id,
    create_note,
    update_note,
    delete_note,
    get_user_documents
)


def render_notes_view():
    """Renders the Saved Notes & Research Notebook interface."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to view your notes.")
        return

    user_id = user["id"]

    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">Saved Notes & Research Notebook</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Capture key takeaways, save verifiable AI answers, and organize your study notes with direct document links.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_list, tab_create = st.tabs(["📓 My Notebook", "➕ Create New Note"])

    # =========================================================================
    # TAB 1: LIST & SEARCH NOTES
    # =========================================================================
    with tab_list:
        col_search, col_spacer = st.columns([2.5, 1])
        with col_search:
            search_term = st.text_input("🔍 Search notes by title, content, or tag", placeholder="Search keywords...")

        notes = get_user_notes(user_id, search=search_term if search_term.strip() else None)

        if not notes:
            st.markdown(
                """
                <div class="dm-empty-state">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📝</div>
                    <h3>No Notes Found</h3>
                    <p>
                        Your notebook is empty. You can write your own notes in the Create tab,
                        or click "Save to Notes" when asking questions in the Chat workspace.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.caption(f"Showing {len(notes)} saved note(s)")
            for note in notes:
                note_id = note["id"]
                edit_key = f"editing_note_{note_id}"
                confirm_del_key = f"confirm_del_note_{note_id}"

                # Editing Mode
                if st.session_state.get(edit_key, False):
                    st.markdown(f"#### ✏️ Edit Note: {note['title']}")
                    with st.form(f"edit_form_{note_id}"):
                        edit_title = st.text_input("Title", value=note["title"])
                        edit_content = st.text_area("Content", value=note["content"], height=180)
                        edit_tags = st.text_input("Tags (comma-separated)", value=note.get("tags") or "")

                        col_save, col_cancel = st.columns([1, 1])
                        with col_save:
                            save_btn = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                        with col_cancel:
                            cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

                        if save_btn:
                            if not edit_title.strip() or not edit_content.strip():
                                st.error("Title and content cannot be blank.")
                            else:
                                update_note(user_id, note_id, edit_title, edit_content, edit_tags)
                                st.session_state[edit_key] = False
                                st.success("Note updated!")
                                st.rerun()

                        if cancel_btn:
                            st.session_state[edit_key] = False
                            st.rerun()

                # View Mode
                else:
                    tag_str = note.get("tags") or "General"
                    citation_html = ""
                    if note.get("source_citation"):
                        citation_html = f'<span class="dm-badge dm-badge-red">📖 {note["source_citation"]}</span>'

                    st.markdown(
                        f"""
                        <div class="dm-card" style="padding: 1.4rem; margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.8rem;">
                                <div>
                                    <h3 style="margin: 0 0 4px 0; font-size: 1.2rem; color: #252525;">{note['title']}</h3>
                                    <div style="display: flex; gap: 8px; align-items: center; font-size: 0.8rem; color: #706B68;">
                                        <span>Updated: {str(note['updated_at'])[:16]}</span>
                                        <span>•</span>
                                        <span class="dm-badge dm-badge-gray">🏷️ {tag_str}</span>
                                        {citation_html}
                                    </div>
                                </div>
                            </div>
                            <div style="font-size: 0.92rem; color: #353535; line-height: 1.6; white-space: pre-wrap; margin-bottom: 1rem;">
{note['content']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    col_n1, col_n_edit, col_n_del = st.columns([4, 1, 1])
                    with col_n_edit:
                        if st.button("✏️ Edit", key=f"edit_btn_{note_id}", use_container_width=True):
                            st.session_state[edit_key] = True
                            st.rerun()

                    with col_n_del:
                        if st.session_state.get(confirm_del_key, False):
                            st.warning("Delete?")
                            col_y, col_n = st.columns(2)
                            with col_y:
                                if st.button("Yes", key=f"y_del_{note_id}"):
                                    delete_note(user_id, note_id)
                                    st.session_state[confirm_del_key] = False
                                    st.rerun()
                            with col_n:
                                if st.button("No", key=f"n_del_{note_id}"):
                                    st.session_state[confirm_del_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"del_note_{note_id}", use_container_width=True):
                                st.session_state[confirm_del_key] = True
                                st.rerun()

    # =========================================================================
    # TAB 2: CREATE NEW NOTE
    # =========================================================================
    with tab_create:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Create a Note</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 0;">
                    Draft study notes, formulas, or synthesis from your lectures and reading materials.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        user_docs = get_user_documents(user_id)
        doc_map = {"None (General Note)": None}
        for d in user_docs:
            doc_map[d["filename"]] = d["id"]

        with st.form("create_note_form"):
            note_title = st.text_input("Note Title", placeholder="e.g., Key Equations in Thermodynamics")
            note_content = st.text_area("Note Content (Markdown supported)", placeholder="Write your notes here...", height=200)

            col_link_doc, col_tags = st.columns(2)
            with col_link_doc:
                selected_doc_name = st.selectbox("Link to Document (optional)", list(doc_map.keys()))
                linked_doc_id = doc_map[selected_doc_name]
            with col_tags:
                note_tags = st.text_input("Tags", placeholder="e.g., Physics, Midterm, Lecture 4")

            source_citation = st.text_input("Source Citation / Page Reference (optional)", placeholder="e.g., Physics_101.pdf, Page 12-14")

            submit_new_note = st.form_submit_button("Save Note to Notebook", type="primary", use_container_width=True)

            if submit_new_note:
                if not note_title.strip() or not note_content.strip():
                    st.error("Please provide both a title and note content.")
                else:
                    create_note(
                        user_id=user_id,
                        title=note_title,
                        content=note_content,
                        document_id=linked_doc_id,
                        source_citation=source_citation if source_citation.strip() else None,
                        tags=note_tags if note_tags.strip() else "General"
                    )
                    st.success("Note saved successfully!")
                    st.rerun()
