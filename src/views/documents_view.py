import os
import streamlit as st
from typing import List, Dict, Any
from src.auth import get_current_user
from src.database import (
    get_user_documents,
    get_user_collections,
    create_collection,
    delete_collection,
    add_document,
    update_document_status,
    delete_document,
    delete_document_cascade,
    retry_document_processing,
    check_document_duplicate
)
from src.document_processor import validate_pdf, extract_pdf_pages, chunk_document_pages
from src.vector_store import add_document_chunks, delete_document_chunks
from src.storage_provider import get_storage_provider

UPLOADS_BASE_DIR = os.getenv("UPLOADS_DIR", os.path.join("data", "uploads"))



def render_documents_view():
    """Renders the comprehensive Document Manager for uploading, organizing, and pruning PDFs."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to manage your documents.")
        return

    user_id = user["id"]

    # Header
    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">My Document Library</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Upload, categorize, inspect, and index multi-page PDF documents for verifiable AI answering.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_browse, tab_upload, tab_collections = st.tabs([
        "📚 Browse & Manage",
        "📤 Upload & Index PDFs",
        "🏷️ Collections"
    ])

    # =========================================================================
    # TAB 1: BROWSE & MANAGE DOCUMENTS
    # =========================================================================
    with tab_browse:
        collections = get_user_collections(user_id)
        collection_options = {"All Collections": None}
        for c in collections:
            collection_options[c["name"]] = c["id"]

        # Filter bar
        col_f1, col_f2, col_f3 = st.columns([2, 1.2, 1.2])
        with col_f1:
            search_query = st.text_input("🔍 Search documents by filename", placeholder="Type filename...")
        with col_f2:
            selected_coll_label = st.selectbox("Filter Collection", list(collection_options.keys()))
            filter_coll_id = collection_options[selected_coll_label]
        with col_f3:
            status_choice = st.selectbox("Status", ["All Statuses", "Ready (indexed)", "Processing", "Failed"])
            filter_status = None
            if "Ready" in status_choice:
                filter_status = "indexed"
            elif "Processing" in status_choice:
                filter_status = "processing"
            elif "Failed" in status_choice:
                filter_status = "failed"

        docs = get_user_documents(
            user_id=user_id,
            collection_id=filter_coll_id,
            search=search_query if search_query.strip() else None,
            status_filter=filter_status
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if not docs:
            st.markdown(
                """
                <div class="dm-empty-state">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📄</div>
                    <h3>No Documents Found</h3>
                    <p>There are no uploaded documents matching your filter criteria. Switch to the Upload tab to add PDFs.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.caption(f"Showing {len(docs)} document(s)")
            for doc in docs:
                status = doc.get("status", "processing")
                if status == "indexed":
                    status_badge = '<span class="dm-badge dm-badge-green">READY</span>'
                elif status == "failed":
                    status_badge = '<span class="dm-badge dm-badge-red">FAILED</span>'
                else:
                    status_badge = '<span class="dm-badge dm-badge-gray">PROCESSING</span>'

                size_kb = doc["file_size"] / 1024
                size_str = f"{size_kb / 1024:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
                coll_label = doc.get("collection_name") or "General"

                with st.container():
                    st.markdown(
                        f"""
                        <div class="dm-card" style="padding: 1.2rem; margin-bottom: 0.9rem;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div style="display: flex; gap: 12px; align-items: flex-start;">
                                    <div style="font-size: 2rem; line-height: 1;">📄</div>
                                    <div>
                                        <h4 style="margin: 0 0 4px 0; font-size: 1.05rem; color: #252525;">{doc['filename']}</h4>
                                        <div style="font-size: 0.82rem; color: #706B68; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
                                            <span><strong>Size:</strong> {size_str}</span>
                                            <span>•</span>
                                            <span><strong>Pages:</strong> {doc['page_count']}</span>
                                            <span>•</span>
                                            <span><strong>Chunks:</strong> {doc['chunk_count']}</span>
                                            <span>•</span>
                                            <span><strong>Collection:</strong> <span class="dm-badge dm-badge-gray">{coll_label}</span></span>
                                            <span>•</span>
                                            <span><strong>Uploaded:</strong> {str(doc['uploaded_at'])[:16]}</span>
                                        </div>
                                    </div>
                                </div>
                                <div>{status_badge}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Actions row
                    col_act_left, col_act_retry, col_act_dl, col_act_del = st.columns([2.5, 1.2, 1.2, 1.1])

                    with col_act_retry:
                        if doc.get("status") == "failed":
                            if st.button("🔄 Retry", key=f"retry_{doc['id']}", help="Re-extract and re-index this failed document from persistent storage"):
                                with st.spinner(f"Retrying indexing for '{doc['filename']}'..."):
                                    retry_res = retry_document_processing(user_id, doc["id"])
                                    if retry_res.get("success"):
                                        st.success("Successfully indexed!")
                                        st.rerun()
                                    else:
                                        st.error(f"Retry failed: {retry_res.get('error')}")

                    with col_act_dl:
                        storage = get_storage_provider()
                        file_bytes = None
                        try:
                            if doc.get("stored_path"):
                                file_bytes = storage.get_file_bytes(user_id, doc["stored_path"])
                        except Exception:
                            file_bytes = None
                        if file_bytes:
                            st.download_button(
                                label="⬇️ PDF",
                                data=file_bytes,
                                file_name=doc["filename"],
                                mime="application/pdf",
                                key=f"dl_{doc['id']}",
                                help="Download original verified PDF"
                            )

                    with col_act_del:
                        del_key = f"del_btn_{doc['id']}"
                        confirm_key = f"confirm_del_{doc['id']}"

                        if st.session_state.get(confirm_key, False):
                            st.warning("Delete?")
                            col_c_yes, col_c_no = st.columns(2)
                            with col_c_yes:
                                if st.button("Yes", key=f"yes_{doc['id']}", type="primary"):
                                    del_res = delete_document_cascade(user_id, doc["id"])
                                    st.session_state[confirm_key] = False
                                    if del_res.get("success"):
                                        st.success(f"Deleted '{doc['filename']}'.")
                                    else:
                                        st.error(f"Delete failed: {del_res.get('error')}")
                                    st.rerun()
                            with col_c_no:
                                if st.button("No", key=f"no_{doc['id']}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=del_key, help="Safely delete document, file storage, and vector chunks"):
                                st.session_state[confirm_key] = True
                                st.rerun()

                    if doc.get("error_message"):
                        st.error(f"Processing note: {doc['error_message']}")

    # =========================================================================
    # TAB 2: UPLOAD & INDEX
    # =========================================================================
    with tab_upload:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Upload New Documents</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 1rem;">
                    Select one or more PDF files. Each page will be verified, extracted, chunked, and embedded into your private vector store.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        collections = get_user_collections(user_id)
        coll_dict = {c["name"]: c["id"] for c in collections}
        if not coll_dict:
            coll_dict["General"] = None

        col_up_c1, col_up_c2 = st.columns([1.5, 1])
        with col_up_c1:
            chosen_coll_name = st.selectbox("Assign to Collection", list(coll_dict.keys()), key="upload_coll_select")
            target_coll_id = coll_dict.get(chosen_coll_name)

        with col_up_c2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            advanced_chunking = st.checkbox("⚙️ Custom Chunking Settings", value=False)

        chunk_size = 800
        chunk_overlap = 150
        if advanced_chunking:
            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                chunk_size = st.slider("Chunk Size (characters)", min_value=300, max_value=1500, value=800, step=50)
            with col_ch2:
                chunk_overlap = st.slider("Chunk Overlap (characters)", min_value=50, max_value=400, value=150, step=25)

        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help="Supports standard PDF lecture notes, textbook chapters, and research papers up to 50MB."
        )

        if uploaded_files:
            st.info(f"📂 {len(uploaded_files)} file(s) selected for processing.")

            if st.button("🚀 Process & Index Documents", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                total_files = len(uploaded_files)
                user_storage_dir = os.path.join(UPLOADS_BASE_DIR, f"user_{user_id}")
                os.makedirs(user_storage_dir, exist_ok=True)

                for idx, file in enumerate(uploaded_files):
                    file_name = file.name
                    file_bytes = file.getvalue()
                    file_size = len(file_bytes)

                    status_text.markdown(f"**Processing {idx+1}/{total_files}:** `{file_name}`...")

                    # 1. Duplicate check
                    duplicate = check_document_duplicate(user_id, file_name, file_size)
                    if duplicate:
                        st.warning(f"⚠️ '{file_name}' has already been indexed in collection '{duplicate.get('collection_name') or 'General'}'. Skipping duplicate indexing.")
                        progress_bar.progress((idx + 1) / total_files)
                        continue

                    # 2. PDF Validation
                    is_valid, val_err = validate_pdf(file_bytes, file_name)
                    if not is_valid:
                        st.error(f"❌ Failed to process '{file_name}': {val_err}")
                        # Record failed document in DB
                        doc_id = add_document(user_id, file_name, "", file_size, collection_id=target_coll_id)
                        update_document_status(doc_id, user_id, "failed", error_message=val_err)
                        progress_bar.progress((idx + 1) / total_files)
                        continue

                    # 3. Save physical file to persistent storage (Supabase or Local)
                    storage = get_storage_provider()
                    try:
                        saved_path = storage.save_file(user_id, file_name, file_bytes)
                    except Exception as upload_err:
                        err_msg = f"Storage save failed: {str(upload_err)}"
                        st.error(f"❌ '{file_name}': {err_msg}")
                        doc_id = add_document(user_id, file_name, "", file_size, collection_id=target_coll_id)
                        update_document_status(doc_id, user_id, "failed", error_message=err_msg)
                        progress_bar.progress((idx + 1) / total_files)
                        continue

                    # 4. Insert DB record
                    doc_id = add_document(user_id, file_name, saved_path, file_size, collection_id=target_coll_id)


                    # 5. Extract pages
                    pages, page_warning = extract_pdf_pages(file_bytes)
                    page_count = len(pages)

                    if page_warning:
                        st.warning(f"⚠️ '{file_name}': {page_warning}")
                        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=page_warning)
                        progress_bar.progress((idx + 1) / total_files)
                        continue

                    # 6. Chunk text
                    chunks = chunk_document_pages(
                        pages=pages,
                        doc_id=doc_id,
                        user_id=user_id,
                        filename=file_name,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )

                    if not chunks:
                        warn_msg = "No extractable text chunks could be formed from this document."
                        st.warning(f"⚠️ '{file_name}': {warn_msg}")
                        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=warn_msg)
                        progress_bar.progress((idx + 1) / total_files)
                        continue

                    # 7. Embed & Index into ChromaDB
                    try:
                        indexed_count = add_document_chunks(user_id, chunks)
                        update_document_status(
                            doc_id=doc_id,
                            user_id=user_id,
                            status="indexed",
                            page_count=page_count,
                            chunk_count=indexed_count
                        )
                        st.success(f"✅ Successfully indexed **{file_name}** ({page_count} pages, {indexed_count} vector chunks).")
                    except Exception as e:
                        err_msg = f"Vector indexing failed: {str(e)}"
                        st.error(f"❌ '{file_name}': {err_msg}")
                        update_document_status(doc_id, user_id, "failed", page_count=page_count, error_message=err_msg)

                    progress_bar.progress((idx + 1) / total_files)

                status_text.markdown("✨ **Batch processing complete!**")
                st.session_state["active_page"] = "My Documents"

    # =========================================================================
    # TAB 3: COLLECTIONS MANAGER
    # =========================================================================
    with tab_collections:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Workspace Collections</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 1rem;">
                    Organize your documents by course, project, or topic (e.g., "Computer Vision", "Neuroscience", "Midterm Prep").
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_new_coll, col_list_coll = st.columns([1.2, 1.8])

        with col_new_coll:
            st.markdown("<h4>Create Collection</h4>", unsafe_allow_html=True)
            with st.form("new_collection_form"):
                new_coll_name = st.text_input("Collection Name", placeholder="e.g., Biology 101")
                new_coll_desc = st.text_area("Description (optional)", placeholder="Brief summary of topic...")
                submit_coll = st.form_submit_button("Add Collection", type="primary", use_container_width=True)

                if submit_coll:
                    if not new_coll_name.strip():
                        st.error("Please enter a collection name.")
                    else:
                        create_collection(user_id, new_coll_name, new_coll_desc)
                        st.success(f"Collection '{new_coll_name}' created!")
                        st.rerun()

        with col_list_coll:
            st.markdown("<h4>Active Collections</h4>", unsafe_allow_html=True)
            colls = get_user_collections(user_id)
            if not colls:
                st.info("No collections created yet.")
            else:
                for c in colls:
                    with st.container():
                        st.markdown(
                            f"""
                            <div class="dm-card" style="padding: 1rem; margin-bottom: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <strong style="font-size: 1rem; color: #252525;">{c['name']}</strong>
                                        <div style="color: #706B68; font-size: 0.82rem; margin-top: 2px;">
                                            {c['document_count']} document(s) • {c.get('description') or 'No description'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        if c["name"] != "General":
                            if st.button("Delete Collection", key=f"del_c_{c['id']}", help="Removes collection category (documents remain in General)"):
                                delete_collection(user_id, c["id"])
                                st.rerun()
