import os
import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any
import streamlit as st

from src.database import authenticate_user, register_user, get_user_by_id
from src.supabase_client import get_supabase_client, is_supabase_configured

SESSION_USER_KEY = "current_user"
SESSION_LOGGED_IN_KEY = "is_logged_in"
AUTH_SECRET_KEY = os.getenv("SECRET_KEY", "documind-production-secret-key-salt-9821").encode("utf-8")
DEFAULT_SESSION_DURATION_SEC = 7 * 24 * 3600  # 7 days


# ==============================================================================
# CRYPTOGRAPHIC SESSION TOKEN CREATION & VERIFICATION
# ==============================================================================

def create_session_token(user_id: int, email: str, duration_sec: int = DEFAULT_SESSION_DURATION_SEC) -> str:
    """Generates a cryptographically signed HMAC-SHA256 session token with expiration."""
    exp = int(time.time()) + duration_sec
    payload = {
        "uid": user_id,
        "em": email.strip().lower(),
        "exp": exp
    }
    payload_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

    signature = hmac.new(AUTH_SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies token signature and checks expiration.
    Returns payload dictionary if valid and non-expired; otherwise None.
    """
    if not token or "." not in token:
        return None

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts

        # Re-compute signature and compare in constant time
        expected_sig = hmac.new(AUTH_SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        # Decode payload
        # Pad base64 if needed
        padding = "=" * (4 - (len(payload_b64) % 4)) if len(payload_b64) % 4 != 0 else ""
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        if time.time() > payload.get("exp", 0):
            return None

        return payload
    except Exception:
        return None


# ==============================================================================
# SESSION STATE & LIFECYCLE MANAGEMENT
# ==============================================================================

def init_session_state() -> None:
    """
    Ensures authentication keys exist in session_state,
    and automatically restores returning authenticated sessions from query parameters.
    """
    if SESSION_LOGGED_IN_KEY not in st.session_state:
        st.session_state[SESSION_LOGGED_IN_KEY] = False
    if SESSION_USER_KEY not in st.session_state:
        st.session_state[SESSION_USER_KEY] = None
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "Dashboard"
    if "current_chat_session_id" not in st.session_state:
        st.session_state["current_chat_session_id"] = None

    # Automatic Session Restoration across browser restarts / tab reopens
    if not st.session_state.get(SESSION_LOGGED_IN_KEY) or not st.session_state.get(SESSION_USER_KEY):
        query_token = st.query_params.get("session_token")
        if query_token:
            payload = verify_session_token(query_token)
            if payload:
                user = get_user_by_id(payload["uid"])
                if user and user["email"].strip().lower() == payload["em"]:
                    # Safely restore session
                    st.session_state[SESSION_LOGGED_IN_KEY] = True
                    st.session_state[SESSION_USER_KEY] = user
                    return
            # If token is invalid or expired, clear it
            try:
                del st.query_params["session_token"]
            except Exception:
                pass


def is_authenticated() -> bool:
    """Returns True if user is currently logged in with a valid session."""
    init_session_state()
    return bool(st.session_state.get(SESSION_LOGGED_IN_KEY, False) and st.session_state.get(SESSION_USER_KEY))


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the authenticated user dict or None."""
    init_session_state()
    if is_authenticated():
        return st.session_state.get(SESSION_USER_KEY)
    return None


def get_current_user_id() -> Optional[int]:
    """Convenience getter for current user's integer ID."""
    user = get_current_user()
    return user["id"] if user else None


def login(email: str, password: str) -> Dict[str, Any]:
    """Attempts user authentication and establishes a persistent session."""
    init_session_state()

    # 1. Check Supabase Auth if configured
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            if client:
                res = client.auth.sign_in_with_password({"email": email.strip().lower(), "password": password})
                if res and res.user:
                    # Sync or find user in local db
                    local_auth = authenticate_user(email, password)
                    if local_auth.get("success"):
                        user_data = local_auth["user"]
                    else:
                        user_data = {
                            "id": 1,
                            "email": email.strip().lower(),
                            "full_name": res.user.user_metadata.get("full_name") or email.split("@")[0]
                        }
                    st.session_state[SESSION_LOGGED_IN_KEY] = True
                    st.session_state[SESSION_USER_KEY] = user_data
                    st.session_state["active_page"] = "Dashboard"

                    token = create_session_token(user_data["id"], user_data["email"])
                    st.query_params["session_token"] = token
                    return {"success": True, "user": user_data}
        except Exception as e:
            # Fall back to database auth if Supabase Auth call fails or is bypassed
            pass

    # 2. Database authentication (PostgreSQL or local SQLite)
    res = authenticate_user(email, password)
    if res.get("success"):
        st.session_state[SESSION_LOGGED_IN_KEY] = True
        st.session_state[SESSION_USER_KEY] = res["user"]
        st.session_state["active_page"] = "Dashboard"

        # Generate persistent session token for browser session restoration
        token = create_session_token(res["user"]["id"], res["user"]["email"])
        st.query_params["session_token"] = token
        return {"success": True, "user": res["user"]}

    return {"success": False, "error": res.get("error", "Authentication failed.")}


def signup(email: str, password: str, confirm_password: str, full_name: str) -> Dict[str, Any]:
    """Validates inputs and registers a new account."""
    if not full_name.strip():
        return {"success": False, "error": "Please enter your full name."}
    if not email.strip():
        return {"success": False, "error": "Please enter your email address."}
    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters long."}
    if password != confirm_password:
        return {"success": False, "error": "Passwords do not match."}

    # If Supabase is configured, create Supabase user
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            if client:
                client.auth.sign_up({
                    "email": email.strip().lower(),
                    "password": password,
                    "options": {"data": {"full_name": full_name.strip()}}
                })
        except Exception as e:
            print(f"[Supabase Auth Notice] Remote signup notice: {e}")

    # Register in database
    res = register_user(email=email, password=password, full_name=full_name)
    return res


def logout() -> None:
    """Securely clears authentication session and revokes the persistent browser session token."""
    init_session_state()

    # Clear Supabase session if active
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            if client:
                client.auth.sign_out()
        except Exception:
            pass

    st.session_state[SESSION_LOGGED_IN_KEY] = False
    st.session_state[SESSION_USER_KEY] = None
    st.session_state["current_chat_session_id"] = None
    st.session_state["active_page"] = "Dashboard"

    # Remove query param token
    try:
        if "session_token" in st.query_params:
            del st.query_params["session_token"]
    except Exception:
        pass


def require_auth() -> bool:
    """Guard function: if user is not authenticated, stops page execution and displays login."""
    if not is_authenticated():
        st.warning("⚠️ You must be logged in to view this page.")
        st.stop()
        return False
    return True
