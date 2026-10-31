import os
import tempfile
import pytest
from src.database import (
    init_db,
    register_user,
    authenticate_user,
    get_user_by_id,
    update_user_profile,
    update_user_password,
    verify_password
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_user_registration_and_hashing(temp_db):
    res = register_user(
        email="student@university.edu",
        password="SecurePassword123!",
        full_name="Alex Rivera",
        db_path=temp_db
    )
    assert res["success"] is True
    assert res["user"]["email"] == "student@university.edu"
    assert res["user"]["full_name"] == "Alex Rivera"

    # Verify password is NOT stored as plaintext
    user = get_user_by_id(res["user"]["id"], db_path=temp_db)
    assert user is not None
    assert "SecurePassword123!" not in str(user.values())


def test_duplicate_email_rejected(temp_db):
    res1 = register_user("alex@example.com", "Password123", "Alex", db_path=temp_db)
    assert res1["success"] is True

    # Same email with different case
    res2 = register_user("ALEX@example.com", "Password456", "Alex Clone", db_path=temp_db)
    assert res2["success"] is False
    assert "already exists" in res2["error"]


def test_password_length_validation(temp_db):
    res = register_user("short@example.com", "12345", "Shorty", db_path=temp_db)
    assert res["success"] is False
    assert "at least 8 characters" in res["error"]


def test_invalid_email_validation(temp_db):
    res = register_user("not-an-email", "Password123", "User", db_path=temp_db)
    assert res["success"] is False
    assert "valid email" in res["error"]


def test_authentication_success_and_failure(temp_db):
    register_user("jane@test.org", "MySecretKey99", "Jane Doe", db_path=temp_db)

    # Valid login
    auth_ok = authenticate_user("jane@test.org", "MySecretKey99", db_path=temp_db)
    assert auth_ok["success"] is True
    assert auth_ok["user"]["full_name"] == "Jane Doe"

    # Wrong password
    auth_bad = authenticate_user("jane@test.org", "WrongPassword", db_path=temp_db)
    assert auth_bad["success"] is False
    assert "Invalid email or password" in auth_bad["error"]

    # Non-existent user
    auth_ghost = authenticate_user("ghost@test.org", "SomePassword1", db_path=temp_db)
    assert auth_ghost["success"] is False


def test_password_update(temp_db):
    res = register_user("update@test.com", "OldPassword1", "Updater", db_path=temp_db)
    user_id = res["user"]["id"]

    # Try updating with wrong old password
    up_fail = update_user_password(user_id, "WrongOld", "BrandNewPass123", db_path=temp_db)
    assert up_fail["success"] is False

    # Update with correct old password
    up_ok = update_user_password(user_id, "OldPassword1", "BrandNewPass123", db_path=temp_db)
    assert up_ok["success"] is True

    # Login with new password
    auth = authenticate_user("update@test.com", "BrandNewPass123", db_path=temp_db)
    assert auth["success"] is True
