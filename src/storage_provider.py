import os
import re
import uuid
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

from src.supabase_client import get_supabase_client, is_supabase_configured

load_dotenv()

DEFAULT_LOCAL_UPLOADS = os.getenv("UPLOADS_DIR", os.path.join("data", "uploads"))
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_STORAGE_BUCKET", "documind-documents")


def sanitize_filename(filename: str) -> str:
    """Removes potentially dangerous characters and path traversal sequences from filenames."""
    basename = os.path.basename(filename)
    clean = re.sub(r"[^\w\.\-\s]", "_", basename)
    return clean.strip() or "document.pdf"


class StorageProvider(ABC):
    """Abstract base class for persistent document object storage."""

    @abstractmethod
    def save_file(self, user_id: int, filename: str, file_bytes: bytes) -> str:
        """Persists file bytes and returns the stored storage reference/path."""
        pass

    @abstractmethod
    def get_file_bytes(self, user_id: int, stored_path: str) -> Optional[bytes]:
        """Retrieves raw file bytes, strictly verifying user ownership."""
        pass

    @abstractmethod
    def get_file_url(self, user_id: int, stored_path: str, expires_in: int = 900) -> Optional[str]:
        """Generates a secure, temporary signed URL for viewing/downloading the file."""
        pass

    @abstractmethod
    def delete_file(self, user_id: int, stored_path: str) -> bool:
        """Permanently deletes the stored file, strictly verifying user ownership."""
        pass

    @abstractmethod
    def is_cloud_storage(self) -> bool:
        """Returns True if files are stored in managed cloud object storage."""
        pass


class SupabaseStorageProvider(StorageProvider):
    """
    Production-ready storage provider utilizing private Supabase Storage buckets.
    Enforces strict user folder partitioning and provides time-limited signed URLs.
    """

    def __init__(self, bucket_name: str = SUPABASE_BUCKET_NAME):
        self.bucket_name = bucket_name

    def _get_client(self):
        client = get_supabase_client()
        if not client:
            raise RuntimeError("Supabase client is not available. Please verify SUPABASE_URL and SUPABASE_KEY.")
        return client

    def _build_storage_path(self, user_id: int, filename: str) -> str:
        safe_name = sanitize_filename(filename)
        unique_prefix = uuid.uuid4().hex[:8]
        return f"user_{user_id}/{unique_prefix}_{safe_name}"

    def _verify_user_isolation(self, user_id: int, stored_path: str) -> str:
        """Guarantees that a user can only ever access paths within their user_{user_id} directory."""
        clean_path = stored_path.replace("\\", "/").strip()
        expected_prefix = f"user_{user_id}/"
        if not clean_path.startswith(expected_prefix) and f"/{expected_prefix}" not in clean_path:
            raise PermissionError(f"Access denied: User {user_id} is not authorized to access '{stored_path}'.")
        # Extract relative path inside bucket
        if f"/{expected_prefix}" in clean_path:
            idx = clean_path.find(expected_prefix)
            clean_path = clean_path[idx:]
        return clean_path

    def save_file(self, user_id: int, filename: str, file_bytes: bytes) -> str:
        client = self._get_client()
        storage_path = self._build_storage_path(user_id, filename)

        try:
            client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": "application/pdf", "upsert": "false"}
            )
            return storage_path
        except Exception as e:
            # Handle existing file or bucket errors
            raise IOError(f"Failed to upload PDF to Supabase Storage: {str(e)}")

    def get_file_bytes(self, user_id: int, stored_path: str) -> Optional[bytes]:
        client = self._get_client()
        clean_path = self._verify_user_isolation(user_id, stored_path)
        try:
            data = client.storage.from_(self.bucket_name).download(clean_path)
            return data
        except Exception as e:
            print(f"[Supabase Storage Error] Download failed for '{clean_path}': {e}")
            return None

    def get_file_url(self, user_id: int, stored_path: str, expires_in: int = 900) -> Optional[str]:
        client = self._get_client()
        clean_path = self._verify_user_isolation(user_id, stored_path)
        try:
            res = client.storage.from_(self.bucket_name).create_signed_url(clean_path, expires_in)
            if isinstance(res, dict) and "signedURL" in res:
                return res["signedURL"]
            elif hasattr(res, "signed_url"):
                return res.signed_url
            return str(res)
        except Exception as e:
            print(f"[Supabase Storage Error] Signed URL creation failed for '{clean_path}': {e}")
            return None

    def delete_file(self, user_id: int, stored_path: str) -> bool:
        client = self._get_client()
        clean_path = self._verify_user_isolation(user_id, stored_path)
        try:
            client.storage.from_(self.bucket_name).remove([clean_path])
            return True
        except Exception as e:
            print(f"[Supabase Storage Error] Delete failed for '{clean_path}': {e}")
            return False

    def is_cloud_storage(self) -> bool:
        return True


class LocalStorageProvider(StorageProvider):
    """
    Persistent local filesystem storage provider for offline, local, or single-node deployments.
    Guarantees strict tenant isolation by path checking.
    """

    def __init__(self, base_dir: Optional[str] = None):
        target = base_dir or os.getenv("UPLOADS_DIR", DEFAULT_LOCAL_UPLOADS)
        self.base_dir = os.path.abspath(target)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_user_dir(self, user_id: int) -> str:
        target_base = os.getenv("UPLOADS_DIR", self.base_dir)
        user_dir = os.path.abspath(os.path.join(target_base, f"user_{user_id}"))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _verify_user_isolation(self, user_id: int, stored_path: str) -> str:
        abs_path = os.path.abspath(stored_path)
        norm_path = os.path.normcase(abs_path)
        norm_user_dir = os.path.normcase(self._get_user_dir(user_id))

        # Disallow accessing another user's folder
        for part in norm_path.replace("\\", "/").split("/"):
            if part.startswith("user_") and part != f"user_{user_id}":
                raise PermissionError(f"Access denied: Path '{stored_path}' is outside user {user_id}'s directory.")

        if not norm_path.startswith(norm_user_dir) and f"user_{user_id}" not in norm_path:
            raise PermissionError(f"Access denied: Path '{stored_path}' is outside user {user_id}'s directory.")
        return abs_path


    def save_file(self, user_id: int, filename: str, file_bytes: bytes) -> str:
        user_dir = self._get_user_dir(user_id)
        safe_name = sanitize_filename(filename)
        target_path = os.path.join(user_dir, safe_name)

        # Avoid accidental clobbering by appending unique token if name already exists
        if os.path.exists(target_path):
            base, ext = os.path.splitext(safe_name)
            target_path = os.path.join(user_dir, f"{base}_{uuid.uuid4().hex[:6]}{ext}")

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        return target_path

    def get_file_bytes(self, user_id: int, stored_path: str) -> Optional[bytes]:
        abs_path = self._verify_user_isolation(user_id, stored_path)
        if not os.path.exists(abs_path):
            return None
        try:
            with open(abs_path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"[Local Storage Error] Read failed for '{stored_path}': {e}")
            return None

    def get_file_url(self, user_id: int, stored_path: str, expires_in: int = 900) -> Optional[str]:
        # For local storage, returns the validated local filesystem path
        return self._verify_user_isolation(user_id, stored_path)

    def delete_file(self, user_id: int, stored_path: str) -> bool:
        abs_path = self._verify_user_isolation(user_id, stored_path)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
                return True
            return False
        except Exception as e:
            print(f"[Local Storage Error] Delete failed for '{stored_path}': {e}")
            return False

    def is_cloud_storage(self) -> bool:
        return False


def get_storage_provider() -> StorageProvider:
    """
    Factory function returning the active StorageProvider.
    Uses SupabaseStorageProvider if credentials are set and mode is not forced to 'local',
    otherwise returns the resilient LocalStorageProvider.
    """
    mode = os.getenv("DOCUMIND_STORAGE_MODE", "auto").lower()
    if mode != "local" and is_supabase_configured():
        return SupabaseStorageProvider()
    return LocalStorageProvider()
