import streamlit as st
from src.auth import login, signup


def render_login_page():
    """Renders a clean, centered modern SaaS login and signup experience."""
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    # Specific CSS overrides for the centered login layout
    st.markdown(
        """<style>
        /* Center container and constrain width to 440-460px specifically on login view */
        .main .block-container:has(div[data-testid="stVerticalBlockBorderWrapper"]),
        [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][style*="display: none"]) .main .block-container {
            max-width: 460px !important;
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            margin: 0 auto !important;
        }

        /* Hide sidebar and toggle collapse control on login page */
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Login Card Container Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E9DED7 !important;
            border-radius: 16px !important;
            padding: 2.25rem 2rem 1.85rem 2rem !important;
            box-shadow: 0 10px 25px -5px rgba(37, 37, 37, 0.05), 0 8px 10px -6px rgba(37, 37, 37, 0.03) !important;
        }

        /* Form styling */
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
        }

        /* Input labels */
        .stTextInput label p {
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: #252525 !important;
            margin-bottom: 0.25rem !important;
        }

        /* Checkbox text */
        .stCheckbox label span {
            font-size: 0.85rem !important;
            color: #706B68 !important;
        }

        /* Primary action button */
        button[kind="primary"], .stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button {
            background-color: #B42332 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            font-family: 'Outfit', sans-serif !important;
            transition: all 0.2s ease !important;
        }

        button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #961B28 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(180, 35, 50, 0.25) !important;
        }

        /* Secondary toggle button */
        button[kind="secondary"], .stButton > button[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: #252525 !important;
            border: 1px solid #E9DED7 !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }

        button[kind="secondary"]:hover, .stButton > button[kind="secondary"]:hover {
            border-color: #B42332 !important;
            color: #B42332 !important;
            background-color: #F7E8E5 !important;
        }
        </style>""",
        unsafe_allow_html=True
    )

    auth_mode = st.session_state.get("auth_mode", "login")

    with st.container(border=True):
        if auth_mode == "login":
            # Header: Logo, Title, Welcome Back, Subtitle
            st.markdown(
                """<div style="text-align: center; margin-bottom: 1.5rem;">
<div style="display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: #B42332; border-radius: 10px; color: #FFFFFF; font-size: 22px; margin-bottom: 0.65rem; box-shadow: 0 4px 12px rgba(180, 35, 50, 0.25);">📚</div>
<div style="font-family: 'Outfit', sans-serif; font-size: 1.45rem; font-weight: 700; color: #252525; letter-spacing: -0.02em; line-height: 1.2;">DocuMind</div>
<h1 style="font-family: 'Outfit', sans-serif; font-size: 1.45rem; font-weight: 600; color: #252525; margin-top: 0.85rem; margin-bottom: 0.25rem; letter-spacing: -0.01em;">Welcome back</h1>
<p style="color: #706B68; font-size: 0.88rem; line-height: 1.45; margin: 0 auto; max-width: 320px;">Sign in to access your personal document workspace.</p>
</div>""",
                unsafe_allow_html=True
            )

            # Login Form
            with st.form("login_form", border=False):
                login_email = st.text_input(
                    "Email Address",
                    placeholder="student@university.edu",
                    key="login_email_input"
                )
                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password_input"
                )

                st.checkbox(
                    "Keep me signed in on this browser",
                    value=True,
                    key="login_remember_me"
                )

                submit_login = st.form_submit_button(
                    "Sign In",
                    use_container_width=True,
                    type="primary"
                )

                if submit_login:
                    if not login_email or not login_password:
                        st.error("Please enter both email and password.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            auth_result = login(login_email, login_password)
                            if auth_result.get("success"):
                                st.success("Authentication successful! Loading workspace...")
                                st.rerun()
                            else:
                                st.error(auth_result.get("error", "Invalid credentials."))

            # Create Account option for new users
            st.markdown(
                """<div style="text-align: center; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid #E9DED7; font-size: 0.88rem; color: #706B68; margin-bottom: 0.75rem;">Don't have an account?</div>""",
                unsafe_allow_html=True
            )
            if st.button("Create Account", key="switch_to_signup", use_container_width=True, type="secondary"):
                st.session_state["auth_mode"] = "signup"
                st.rerun()

        else:
            # Header for Signup mode
            st.markdown(
                """<div style="text-align: center; margin-bottom: 1.5rem;">
<div style="display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: #B42332; border-radius: 10px; color: #FFFFFF; font-size: 22px; margin-bottom: 0.65rem; box-shadow: 0 4px 12px rgba(180, 35, 50, 0.25);">📚</div>
<div style="font-family: 'Outfit', sans-serif; font-size: 1.45rem; font-weight: 700; color: #252525; letter-spacing: -0.02em; line-height: 1.2;">DocuMind</div>
<h1 style="font-family: 'Outfit', sans-serif; font-size: 1.45rem; font-weight: 600; color: #252525; margin-top: 0.85rem; margin-bottom: 0.25rem; letter-spacing: -0.01em;">Create Account</h1>
<p style="color: #706B68; font-size: 0.88rem; line-height: 1.45; margin: 0 auto; max-width: 320px;">Sign up to access your personal document workspace.</p>
</div>""",
                unsafe_allow_html=True
            )

            # Signup Form
            with st.form("signup_form", border=False):
                reg_name = st.text_input(
                    "Full Name",
                    placeholder="Alex Rivera",
                    key="reg_name_input"
                )
                reg_email = st.text_input(
                    "Email Address",
                    placeholder="alex.rivera@university.edu",
                    key="reg_email_input"
                )
                reg_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="At least 8 characters",
                    help="Must be at least 8 characters long",
                    key="reg_password_input"
                )
                reg_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter password",
                    key="reg_confirm_input"
                )

                submit_signup = st.form_submit_button(
                    "Create Account",
                    use_container_width=True,
                    type="primary"
                )

                if submit_signup:
                    with st.spinner("Creating your secure account..."):
                        reg_res = signup(
                            email=reg_email,
                            password=reg_password,
                            confirm_password=reg_confirm,
                            full_name=reg_name
                        )
                        if reg_res.get("success"):
                            st.success("Account created successfully! Signing in...")
                            login(reg_email, reg_password)
                            st.session_state["auth_mode"] = "login"
                            st.rerun()
                        else:
                            st.error(reg_res.get("error", "Registration could not be completed."))

            # Sign In option for existing users
            st.markdown(
                """<div style="text-align: center; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid #E9DED7; font-size: 0.88rem; color: #706B68; margin-bottom: 0.75rem;">Already have an account?</div>""",
                unsafe_allow_html=True
            )
            if st.button("Sign In to Existing Account", key="switch_to_login", use_container_width=True, type="secondary"):
                st.session_state["auth_mode"] = "login"
                st.rerun()
