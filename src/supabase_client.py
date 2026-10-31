import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

_SUPABASE_CLIENT_INSTANCE: Optional[Any] = None
_SUPABASE_ADMIN_CLIENT_INSTANCE: Optional[Any] = None


def is_supabase_configured() -> bool:
    """Returns True if minimum required Supabase credentials are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"))


def get_supabase_client() -> Optional[Any]:
    """
    Returns a cached Supabase client for client-side / authenticated user operations.
    Returns None if Supabase is not configured.
    """
    global _SUPABASE_CLIENT_INSTANCE
    if not is_supabase_configured():
        return None

    if _SUPABASE_CLIENT_INSTANCE is None:
        try:
            from supabase import create_client, Client
            _SUPABASE_CLIENT_INSTANCE = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            # Avoid crashing the application if Supabase fails to initialize
            print(f"[Supabase Client Warning] Could not initialize client: {e}")
            return None

    return _SUPABASE_CLIENT_INSTANCE


def get_supabase_admin_client() -> Optional[Any]:
    """
    Returns a Supabase client with the service role key for administrative tasks
    (e.g., bucket creation, storage administration).
    """
    global _SUPABASE_ADMIN_CLIENT_INSTANCE
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None

    if _SUPABASE_ADMIN_CLIENT_INSTANCE is None:
        try:
            from supabase import create_client, Client
            _SUPABASE_ADMIN_CLIENT_INSTANCE = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            print(f"[Supabase Admin Warning] Could not initialize admin client: {e}")
            return None

    return _SUPABASE_ADMIN_CLIENT_INSTANCE


def test_supabase_connection() -> Dict[str, Any]:
    """
    Tests Supabase connection and reports status of Auth, Database, and Storage.
    """
    if not is_supabase_configured():
        return {
            "configured": False,
            "message": "Supabase credentials not configured in .env. Running on local persistent storage engine."
        }

    client = get_supabase_client()
    if not client:
        return {
            "configured": True,
            "connected": False,
            "message": "Supabase configured but failed to connect."
        }

    status = {
        "configured": True,
        "connected": True,
        "auth_ready": False,
        "storage_ready": False,
        "database_ready": False,
        "details": {}
    }

    try:
        # Check storage buckets
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets] if buckets else []
        status["storage_ready"] = "documind-documents" in bucket_names
        status["details"]["buckets"] = bucket_names
    except Exception as e:
        status["details"]["storage_error"] = str(e)

    try:
        # Check table access
        res = client.table("profiles").select("id").limit(1).execute()
        status["database_ready"] = True
    except Exception as e:
        status["details"]["database_error"] = str(e)

    return status
