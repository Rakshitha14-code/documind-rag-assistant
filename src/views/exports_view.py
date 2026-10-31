import streamlit as st
from datetime import datetime

from src.auth import get_current_user
from src.database import get_user_documents
from src.report_generator import (
    generate_report_content,
    export_report_to_pdf,
    export_report_to_docx
)


def render_exports_view():
    """Renders the Report Generator & Export interface for PDF and DOCX downloads."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to generate reports.")
        return

    user_id = user["id"]
    author_name = user["full_name"]

    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">Report Generator & Exports</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Transform your lecture notes and papers into publication-ready study guides, executive summaries, and research briefs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    indexed_docs = get_user_documents(user_id, status_filter="indexed")
    if not indexed_docs:
        st.markdown(
            """
            <div class="dm-empty-state">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📄</div>
                <h3>No Indexed Documents Available</h3>
                <p>Upload and index at least one PDF to generate structured study reports.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("📤 Upload Documents", type="primary"):
            st.session_state["active_page"] = "My Documents"
            st.rerun()
        return

    doc_options = {d["id"]: f"{d['filename']} ({d['page_count']} p.)" for d in indexed_docs}

    col_config, col_preview = st.columns([1.1, 1.9])

    with col_config:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.4rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.8rem; color: #B42332;">Report Settings</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("report_config_form"):
            rep_title = st.text_input("Report Title", value="Comprehensive Document Synthesis")
            selected_docs = st.multiselect(
                "Include Documents",
                options=list(doc_options.keys()),
                format_func=lambda did: doc_options.get(did, str(did)),
                default=list(doc_options.keys())[:3]
            )
            rep_topic = st.text_input(
                "Focus Topic / Theme (optional)",
                value="",
                placeholder="e.g. Core concepts, methodology, conclusions"
            )

            submit_report = st.form_submit_button("📑 Generate Report", type="primary", use_container_width=True)

            if submit_report:
                if not selected_docs:
                    st.error("Please select at least one document.")
                else:
                    with st.spinner("Synthesizing document report..."):
                        report_data = generate_report_content(
                            user_id=user_id,
                            doc_ids=selected_docs,
                            title=rep_title,
                            focus_topic=rep_topic if rep_topic.strip() else None
                        )
                        st.session_state["active_report_data"] = report_data

    # Preview & Export Actions Column
    with col_preview:
        rep_data = st.session_state.get("active_report_data")

        if not rep_data:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px dashed #E9DED7; border-radius: 12px; padding: 3rem 1.5rem; text-align: center;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📄</div>
                    <h4 style="margin: 0 0 0.3rem 0; color: #252525;">No Report Generated Yet</h4>
                    <p style="color: #706B68; font-size: 0.88rem; max-width: 400px; margin: 0 auto;">
                        Select your documents on the left and click <strong>Generate Report</strong> to preview and export as PDF or Word document.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"### 📑 {rep_data['title']}")

            # Export download buttons
            col_dl_pdf, col_dl_docx = st.columns(2)
            clean_filename = rep_data['title'].lower().replace(" ", "_").replace(":", "")[:30]

            with col_dl_pdf:
                try:
                    pdf_bytes = export_report_to_pdf(rep_data, author_name=author_name)
                    st.download_button(
                        label="📥 Download PDF (.pdf)",
                        data=pdf_bytes,
                        file_name=f"{clean_filename}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF generation error: {e}")

            with col_dl_docx:
                try:
                    docx_bytes = export_report_to_docx(rep_data, author_name=author_name)
                    st.download_button(
                        label="📥 Download Word (.docx)",
                        data=docx_bytes,
                        file_name=f"{clean_filename}_{datetime.now().strftime('%Y%m%d')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"DOCX generation error: {e}")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            # Live preview box
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.8rem; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                """,
                unsafe_allow_html=True
            )
            st.markdown(rep_data["content_markdown"])
            st.markdown("</div>", unsafe_allow_html=True)
