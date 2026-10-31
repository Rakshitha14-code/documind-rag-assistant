import streamlit as st
from dotenv import load_dotenv

from src.database import init_db, get_user_dashboard_stats
from src.auth import init_session_state, is_authenticated, get_current_user, logout
from src.styles import apply_custom_theme
from src.views.login_view import render_login_page
from src.views.dashboard_view import render_dashboard_view
from src.views.documents_view import render_documents_view
from src.views.chat_view import render_chat_view
from src.views.compare_view import render_compare_view
from src.views.notes_view import render_notes_view
from src.views.exports_view import render_exports_view
from src.views.settings_view import render_settings_view

load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="DocuMind — Personal Document Workspace",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database Schema & Session State
init_db()
init_session_state()

# Inject Adobe-Inspired Design System CSS
apply_custom_theme()


def main():
    # --------------------------------------------------------------------------
    # AUTHENTICATION ROUTING
    # --------------------------------------------------------------------------
    if not is_authenticated():
        render_login_page()
        return

    # User is logged in
    user = get_current_user()
    user_id = user["id"]

    # --------------------------------------------------------------------------
    # SIDEBAR NAVIGATION
    # --------------------------------------------------------------------------
    with st.sidebar:
        # Branded Header
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; padding: 0.35rem 0 0.75rem 0;">
                <div style="background: #B42332; border-radius: 8px; width: 36px; height: 36px; min-width: 36px; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #FFF;">
                    📚
                </div>
                <div>
                    <div style="font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 700; color: #B42332; letter-spacing: -0.02em; line-height: 1.1;">
                        DocuMind
                    </div>
                    <div style="font-size: 0.72rem; color: #706B68; letter-spacing: 0.04em; text-transform: uppercase; font-weight: 500;">
                        Document Intelligence
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # User Profile Pill
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 0.65rem; display: flex; align-items: center; gap: 10px;">
                <div style="background: #F7E8E5; color: #B42332; border-radius: 50%; width: 32px; height: 32px; min-width: 32px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem;">
                    {user['full_name'][0].upper() if user.get('full_name') else 'U'}
                </div>
                <div style="overflow: hidden;">
                    <div style="font-weight: 600; font-size: 0.85rem; color: #252525; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {user['full_name']}
                    </div>
                    <div style="font-size: 0.75rem; color: #706B68; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {user['email']}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        nav_options = [
            "Dashboard",
            "My Documents",
            "Chat with Documents",
            "Compare Documents",
            "Saved Notes",
            "Exports & Reports",
            "Settings"
        ]

        active_page = st.session_state.get("active_page", "Dashboard")
        if active_page not in nav_options:
            active_page = "Dashboard"

        selected_page = st.radio(
            "Workspace Navigation",
            nav_options,
            index=nav_options.index(active_page),
            label_visibility="collapsed"
        )
        st.session_state["active_page"] = selected_page

        st.markdown("<hr style='border-color: #E9DED7; margin: 0.8rem 0 0.7rem 0;' />", unsafe_allow_html=True)

        # Live Real Storage Metric in Sidebar
        try:
            stats = get_user_dashboard_stats(user_id)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E9DED7; border-radius: 8px; padding: 0.75rem 0.85rem; font-size: 0.78rem; color: #706B68; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span>Indexed Documents:</span>
                        <strong style="color: #252525;">{stats['indexed_docs']}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span>Vector Chunks:</span>
                        <strong style="color: #252525;">{stats['total_chunks']}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Questions Asked:</span>
                        <strong style="color: #252525;">{stats['questions_asked']}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception:
            pass

        # Logout Button
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            logout()
            st.rerun()

    # --------------------------------------------------------------------------
    # ACTIVE VIEW RENDERING
    # --------------------------------------------------------------------------
    curr_view = st.session_state.get("active_page", "Dashboard")

    if curr_view == "Dashboard":
        render_dashboard_view()
    elif curr_view == "My Documents":
        render_documents_view()
    elif curr_view == "Chat with Documents":
        render_chat_view()
    elif curr_view == "Compare Documents":
        render_compare_view()
    elif curr_view == "Saved Notes":
        render_notes_view()
    elif curr_view == "Exports & Reports":
        render_exports_view()
    elif curr_view == "Settings":
        render_settings_view()


if __name__ == "__main__":
    main()