import os
import json
from datetime import datetime
import streamlit as st
from src.auth import get_current_user, logout
from src.database import (
    get_user_by_id,
    update_user_profile,
    update_user_password,
    get_user_preferences,
    save_user_preferences
)
from src.supabase_client import test_supabase_connection, is_supabase_configured
from src.backup import export_user_workspace, backup_sqlite_database, get_disaster_recovery_plan
from src.storage_provider import get_storage_provider


def render_settings_view():
    """Renders the User Settings, Profile Management, and AI Preferences view."""
    user = get_current_user()
    if not user:
        st.warning("Please sign in to view settings.")
        return

    user_id = user["id"]
    current_user_data = get_user_by_id(user_id) or user
    prefs = get_user_preferences(user_id)

    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <h1 style="font-size: 1.9rem; margin-bottom: 0.2rem;">Account & Workspace Settings</h1>
            <p style="color: #706B68; font-size: 0.95rem; margin-bottom: 0;">
                Manage your profile, configure LLM providers, and fine-tune answering preferences.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_prefs, tab_profile, tab_security, tab_storage = st.tabs([
        "⚙️ AI & Retrieval Preferences",
        "👤 Profile Details",
        "🔒 Security & Password",
        "💾 Storage & Backups"
    ])

    # =========================================================================
    # TAB 1: AI & RETRIEVAL PREFERENCES
    # =========================================================================
    with tab_prefs:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">AI Model & Grounding Preferences</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 0;">
                    Configure which LLM provider synthesizes your answers and control the depth of retrieved citations.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("ai_prefs_form"):
            col_p1, col_p2 = st.columns(2)

            with col_p1:
                provider_options = ["gemini", "openai", "groq"]
                current_provider = prefs.get("llm_provider", "gemini").lower()
                prov_idx = provider_options.index(current_provider) if current_provider in provider_options else 0

                selected_provider = st.selectbox(
                    "LLM Provider",
                    provider_options,
                    index=prov_idx,
                    format_func=lambda x: {
                        "gemini": "Google Gemini (gemini-1.5-flash)",
                        "openai": "OpenAI (gpt-4o-mini)",
                        "groq": "Groq (llama-3.1-8b-instant)"
                    }.get(x, x),
                    help="Choose the backend model used for answer generation."
                )

                answer_style_options = ["Balanced", "Concise", "Detailed"]
                curr_style = prefs.get("answer_style", "Balanced")
                style_idx = answer_style_options.index(curr_style) if curr_style in answer_style_options else 0

                selected_style = st.selectbox(
                    "Answer Style",
                    answer_style_options,
                    index=style_idx,
                    help="Balanced: clear explanations. Concise: high-density bullet points. Detailed: thorough academic breakdowns."
                )

            with col_p2:
                top_k_options = [2, 3, 4, 5, 6, 8, 10]
                curr_k = prefs.get("top_k", 4)
                k_idx = top_k_options.index(curr_k) if curr_k in top_k_options else 2

                selected_top_k = st.selectbox(
                    "Retrieved Evidence Chunks (Top-K)",
                    top_k_options,
                    index=k_idx,
                    help="Number of most relevant excerpts retrieved from the vector store for each question."
                )

                temperature = st.slider(
                    "Generation Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(prefs.get("temperature", 0.2)),
                    step=0.05,
                    help="Lower values (0.0 - 0.2) ensure strictly factual, deterministic answers."
                )

            current_key = prefs.get("api_key") or ""
            masked_key_placeholder = f"Current: ••••••••{current_key[-4:]}" if len(current_key) > 4 else "Enter your API key"

            api_key_input = st.text_input(
                f"{selected_provider.upper()} API Key (Optional override)",
                type="password",
                placeholder=masked_key_placeholder,
                help="Leave empty to use the system environment variable from .env"
            )

            save_prefs_btn = st.form_submit_button("Save AI Preferences", type="primary", use_container_width=True)

            if save_prefs_btn:
                new_key = api_key_input.strip() if api_key_input.strip() else current_key
                save_user_preferences(
                    user_id=user_id,
                    answer_style=selected_style,
                    top_k=selected_top_k,
                    llm_provider=selected_provider,
                    api_key=new_key if new_key else None,
                    temperature=temperature
                )
                st.success("Preferences saved successfully!")
                st.rerun()

    # =========================================================================
    # TAB 2: PROFILE DETAILS
    # =========================================================================
    with tab_profile:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Personal Information</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 0;">
                    Update your account details and view registration information.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_acc_info, col_spacer = st.columns([2, 1])
        with col_acc_info:
            st.markdown(
                f"""
                <div class="dm-card" style="padding: 1.2rem; margin-bottom: 1.2rem;">
                    <div style="font-size: 0.88rem; color: #706B68;">
                        <p style="margin-bottom: 6px;"><strong>Account ID:</strong> #{current_user_data['id']}</p>
                        <p style="margin-bottom: 6px;"><strong>Member Since:</strong> {str(current_user_data['created_at'])[:10]}</p>
                        <p style="margin-bottom: 0;"><strong>Last Login:</strong> {str(current_user_data.get('last_login') or 'Active')[:16]}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            with st.form("update_profile_form"):
                new_name = st.text_input("Full Name", value=current_user_data["full_name"])
                new_email = st.text_input("Email Address", value=current_user_data["email"])

                submit_profile = st.form_submit_button("Update Profile", type="primary", use_container_width=True)

                if submit_profile:
                    if not new_name.strip() or not new_email.strip():
                        st.error("Name and email cannot be empty.")
                    else:
                        res = update_user_profile(user_id, new_name, new_email)
                        if res.get("success"):
                            st.session_state["current_user"]["full_name"] = new_name.strip()
                            st.session_state["current_user"]["email"] = new_email.strip().lower()
                            st.success("Profile updated successfully!")
                            st.rerun()
                        else:
                            st.error(res.get("error", "Update failed."))

    # =========================================================================
    # TAB 3: SECURITY & PASSWORD
    # =========================================================================
    with tab_security:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Password & Session Security</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 0;">
                    Update your password or securely end your active session on this device.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_pw, col_logout = st.columns([1.5, 1.2])

        with col_pw:
            with st.form("change_password_form"):
                st.markdown("<h4>Change Password</h4>", unsafe_allow_html=True)
                old_pw = st.text_input("Current Password", type="password")
                new_pw = st.text_input("New Password", type="password", help="Minimum 8 characters")
                confirm_pw = st.text_input("Confirm New Password", type="password")

                change_pw_btn = st.form_submit_button("Update Password", type="primary", use_container_width=True)

                if change_pw_btn:
                    if not old_pw or not new_pw:
                        st.error("Please fill out all password fields.")
                    elif new_pw != confirm_pw:
                        st.error("New passwords do not match.")
                    elif len(new_pw) < 8:
                        st.error("New password must be at least 8 characters.")
                    else:
                        pw_res = update_user_password(user_id, old_pw, new_pw)
                        if pw_res.get("success"):
                            st.success("Password changed successfully!")
                        else:
                            st.error(pw_res.get("error", "Could not update password."))

        with col_logout:
            st.markdown(
                """
                <div class="dm-card" style="padding: 1.5rem;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #B42332;">Sign Out</h4>
                    <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 1.2rem;">
                        Ending your session will clear all cached session tokens from this browser. Your documents and notes will remain securely stored in your SQLite database and vector index.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🚪 Log Out of DocuMind", type="secondary", use_container_width=True):
                logout()
                st.rerun()

    # =========================================================================
    # TAB 4: STORAGE ARCHITECTURE & WORKSPACE BACKUPS
    # =========================================================================
    with tab_storage:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.3rem;">Storage Architecture & Workspace Backups</h3>
                <p style="color: #706B68; font-size: 0.88rem; margin-bottom: 0;">
                    Monitor active database and object storage backends, download complete workspace snapshots, and verify data persistence.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_st1, col_st2 = st.columns([1.5, 1.2])

        with col_st1:
            st.markdown("<h4 style='font-size: 1.05rem; margin-bottom: 0.6rem;'>Active Storage Engine</h4>", unsafe_allow_html=True)
            storage_prov = get_storage_provider()
            is_cloud = storage_prov.is_cloud_storage()
            supabase_status = test_supabase_connection()

            if is_cloud:
                st.markdown(
                    """
                    <div class="dm-card" style="padding: 1.2rem; margin-bottom: 1rem; border-left: 4px solid #287D55;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <strong style="color: #287D55;">☁️ Supabase Cloud Storage (Active)</strong>
                            <span class="dm-badge dm-badge-green">CONNECTED</span>
                        </div>
                        <p style="font-size: 0.85rem; color: #706B68; margin-bottom: 0;">
                            PDF documents are saved in private Supabase Storage buckets with strict Row Level Security.
                            Metadata and chat logs are managed in PostgreSQL.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div class="dm-card" style="padding: 1.2rem; margin-bottom: 1rem; border-left: 4px solid #B42332;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <strong style="color: #B42332;">🗄️ Local Persistent Engine (Active)</strong>
                            <span class="dm-badge dm-badge-gray">STANDALONE / OFFLINE</span>
                        </div>
                        <p style="font-size: 0.85rem; color: #706B68; margin-bottom: 0;">
                            Running with persistent SQLite (WAL-enabled), local user uploads directory, and persistent ChromaDB vector storage.
                            Data persists across restarts, logouts, and sessions.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Details list
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 8px; padding: 1rem; font-size: 0.85rem; color: #706B68;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span>Relational Database:</span>
                        <strong style="color: #252525;">{'Managed PostgreSQL (Supabase)' if is_cloud else 'SQLite3 (data/documind.db)'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span>PDF File Storage:</span>
                        <strong style="color: #252525;">{'Supabase Private S3 Bucket' if is_cloud else 'Local Disk (data/uploads/)'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span>Vector Embeddings:</span>
                        <strong style="color: #252525;">ChromaDB Persistent Store (chroma_db/)</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Tenant Isolation:</span>
                        <strong style="color: #287D55;">Enforced per User ID (#{user_id})</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_st2:
            st.markdown("<h4 style='font-size: 1.05rem; margin-bottom: 0.6rem;'>Disaster Recovery & Snapshots</h4>", unsafe_allow_html=True)
            plan = get_disaster_recovery_plan()

            st.markdown(
                f"""
                <div class="dm-card" style="padding: 1.2rem; margin-bottom: 1rem;">
                    <div style="font-size: 0.85rem; color: #706B68; line-height: 1.5;">
                        <p style="margin-bottom: 6px;"><strong>Backup Mode:</strong> {plan['mode']}</p>
                        <p style="margin-bottom: 6px;"><strong>Database:</strong> {plan['database_backup'][:120]}...</p>
                        <p style="margin-bottom: 0;"><strong>Storage:</strong> {plan['storage_backup'][:120]}...</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Export Workspace Button
            try:
                export_data = export_user_workspace(user_id)
                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    label="📦 Export Workspace Snapshot (.json)",
                    data=json_str,
                    file_name=f"documind_workspace_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    type="primary",
                    use_container_width=True,
                    help="Downloads all your collections, document metadata, chat history, and notes as a portable JSON archive."
                )
            except Exception as e:
                st.error(f"Export error: {e}")

            if not is_cloud:
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("📸 Create DB Snapshot Now", use_container_width=True, help="Creates a consistent SQLite online backup in data/backups/"):
                    try:
                        backup_path = backup_sqlite_database()
                        st.success(f"Snapshot created: `{os.path.basename(backup_path)}`")
                    except Exception as be:
                        st.error(f"Backup failed: {be}")
