import pytest
from app.core.token_blacklist import add_to_blacklist, is_blacklisted


def test_add_to_blacklist(db):
    from datetime import datetime, timedelta, timezone
    
    jti = "test-jti-123"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    add_to_blacklist(jti, expires_at)
    
    assert is_blacklisted(jti) is True


def test_is_blacklisted_not_found():
    assert is_blacklisted("nonexistent-jti") is False
