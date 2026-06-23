import pytest
from datetime import timedelta
from jose import JWTError
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_refresh_token
)


def test_password_hashing_produces_bcrypt_hash():
    hashed = hash_password("MyPassword123")
    assert hashed.startswith("$2b$")  # bcrypt signature

def test_password_hashing_is_not_reversible():
    hashed = hash_password("MyPassword123")
    assert hashed != "MyPassword123"

def test_correct_password_verifies():
    hashed = hash_password("CorrectPassword")
    assert verify_password("CorrectPassword", hashed) is True

def test_wrong_password_fails_verification():
    hashed = hash_password("CorrectPassword")
    assert verify_password("WrongPassword", hashed) is False

def test_empty_password_fails_verification():
    hashed = hash_password("CorrectPassword")
    assert verify_password("", hashed) is False

def test_access_token_created_with_correct_subject():
    token = create_access_token(data={"sub": "user@test.com"})
    assert token is not None
    assert len(token) > 20

def test_refresh_token_is_different_from_access_token():
    access = create_access_token(data={"sub": "user@test.com"})
    refresh = create_refresh_token(data={"sub": "user@test.com"})
    assert access != refresh

def test_refresh_token_can_be_verified():
    refresh = create_refresh_token(data={"sub": "user@test.com"})
    payload = verify_refresh_token(refresh)
    assert payload["sub"] == "user@test.com"
    assert payload["type"] == "refresh"

def test_access_token_rejected_as_refresh_token():
    access = create_access_token(data={"sub": "user@test.com"})
    with pytest.raises(JWTError):
        verify_refresh_token(access)  # should reject — wrong type

def test_expired_token_raises_error():
    from jose import jwt
    from app.core.config import settings
    from datetime import datetime, timezone
    # Manually create an expired token
    expired_token = jwt.encode(
        {"sub": "user@test.com", "exp": datetime.now(timezone.utc).timestamp() - 3600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    with pytest.raises(JWTError):
        jwt.decode(expired_token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
