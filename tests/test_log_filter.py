"""Tests for security/log_filter.py — PII/secret redaction."""

from uni_dev.security.log_filter import LogFilter


def test_filter_text_bearer_token():
    """Bearer token in Authorization header is redacted."""
    f = LogFilter()
    assert f.filter_text("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.dGVzdA") == (
        "Authorization: Bearer <REDACTED>"
    )


def test_filter_text_bearer_token_lowercase():
    """Lowercase bearer token is redacted case-insensitively."""
    f = LogFilter()
    result = f.filter_text("authorization: bearer abc123.def456")
    assert "<REDACTED>" in result
    assert "abc123" not in result


def test_filter_text_api_key_query():
    """API key in query param is redacted."""
    f = LogFilter()
    assert f.filter_text("https://api.example.com?api_key=sk-abc123&foo=bar") == (
        "https://api.example.com?api_key=<REDACTED>&foo=bar"
    )


def test_filter_text_api_key_header():
    """API key with hyphen in header is redacted."""
    f = LogFilter()
    result = f.filter_text("X-API-Key: sk-abcdef123456")
    assert "sk-abcdef" not in result
    assert "api_key=<REDACTED>" in result


def test_filter_text_password():
    """Password with colon format is redacted."""
    f = LogFilter()
    result = f.filter_text("password: hunter2")
    assert "hunter2" not in result
    assert "password=<REDACTED>" in result


def test_filter_text_password_equals():
    """Password with equals is redacted."""
    f = LogFilter()
    assert f.filter_text("password=secret123&user=admin") == (
        "password=<REDACTED>&user=admin"
    )


def test_filter_text_email():
    """Email address is redacted."""
    f = LogFilter()
    assert f.filter_text("Contact admin@example.com for support") == (
        "Contact <EMAIL> for support"
    )


def test_filter_text_email_multiple():
    """Multiple emails are all redacted."""
    f = LogFilter()
    result = f.filter_text("user1@foo.com, user2@bar.org")
    assert result == "<EMAIL>, <EMAIL>"


def test_filter_text_postgres_url():
    """PostgreSQL connection string credentials are redacted."""
    f = LogFilter()
    assert f.filter_text("DATABASE_URL=postgresql://user:pass@localhost:5432/db") == (
        "DATABASE_URL=postgresql://<CREDENTIALS>@localhost:5432/db"
    )


def test_filter_text_mongodb_url():
    """MongoDB connection string credentials are redacted."""
    f = LogFilter()
    assert f.filter_text("mongodb://admin:secret@mongo.example.com:27017") == (
        "mongodb://<CREDENTIALS>@mongo.example.com:27017"
    )


def test_filter_text_redis_url():
    """Redis connection URL is redacted."""
    f = LogFilter()
    assert f.filter_text("REDIS_URL=redis://:password123@redis.example.com:6379") == (
        "REDIS_URL=<REDACTED>"
    )


def test_filter_text_redis_url_with_colon():
    """Redis URL with colon separator is redacted."""
    f = LogFilter()
    result = f.filter_text("REDIS_URL: redis://localhost:6379")
    assert "redis://" not in result
    assert "REDIS_URL=<REDACTED>" in result


def test_filter_text_no_sensitive_data():
    """Text without sensitive data is returned unchanged."""
    f = LogFilter()
    original = "SELECT * FROM users WHERE id = 1"
    assert f.filter_text(original) == original


def test_filter_text_multiple_patterns():
    """Text with multiple sensitive patterns is fully redacted."""
    f = LogFilter()
    text = (
        "User admin@example.com uses api_key=sk-test123 "
        "with token Bearer eyJhbG.token on postgresql://user:pw@host/db"
    )
    result = f.filter_text(text)
    assert "admin@example.com" not in result
    assert "sk-test123" not in result
    assert "eyJhbG" not in result
    assert "user:pw" not in result
    assert "<EMAIL>" in result
    assert "<REDACTED>" in result
    assert "<CREDENTIALS>" in result


def test_filter_text_non_string_input():
    """Non-string input is returned unchanged."""
    f = LogFilter()
    assert f.filter_text(123) == 123
    assert f.filter_text(None) is None
    assert f.filter_text(3.14) == 3.14


def test_filter_dict_shallow():
    """Flat dict with sensitive values is filtered."""
    f = LogFilter()
    data = {
        "user": "alice@test.com",
        "key": "sk-12345",
        "id": 42,
    }
    result = f.filter_dict(data)
    assert result["user"] == "<EMAIL>"
    assert result["key"] == "sk-12345"  # no api_key pattern match
    assert result["id"] == 42


def test_filter_dict_nested():
    """Nested dicts are recursively filtered."""
    f = LogFilter()
    data = {
        "auth": {
            "header": "Authorization: Bearer token123",
            "email": "dev@example.org",
        },
        "db": {
            "url": "postgresql://admin:pass@host:5432/db",
        },
    }
    result = f.filter_dict(data)
    assert result["auth"]["header"] == "Authorization: Bearer <REDACTED>"
    assert result["auth"]["email"] == "<EMAIL>"
    assert result["db"]["url"] == "postgresql://<CREDENTIALS>@host:5432/db"


def test_filter_dict_list_values():
    """Lists within dicts are filtered."""
    f = LogFilter()
    data = {
        "recipients": ["a@b.com", "c@d.org"],
        "tokens": ["Bearer xyz", "Bearer abc"],
    }
    result = f.filter_dict(data)
    assert result["recipients"] == ["<EMAIL>", "<EMAIL>"]
    assert result["tokens"] == ["Bearer <REDACTED>", "Bearer <REDACTED>"]


def test_filter_dict_empty():
    """Empty dict is returned as-is."""
    f = LogFilter()
    assert f.filter_dict({}) == {}


def test_filter_text_code_identifiers_not_redacted():
    """UUIDs, base64 IDs, and GUIDs are NOT falsely redacted."""
    f = LogFilter()
    identifiers = [
        "550e8400-e29b-41d4-a716-446655440000",
        "test_user_id=abc123",
        "ref=550e8400e29b41d4a716446655440000",
        "SELECT id FROM users WHERE uuid='abc-def-123'",
    ]
    for ident in identifiers:
        assert f.filter_text(ident) == ident
