from __future__ import annotations

from uni_dev.security.security_filter import SecurityFilterMiddleware


class TestSecurityFilterMiddleware:
    def test_instantiation(self):
        mw = SecurityFilterMiddleware()
        assert mw is not None
        assert mw._filter is not None

    def test_filter_text(self):
        mw = SecurityFilterMiddleware()
        result = mw._filter.filter_text("Bearer sk-1234567890abcdef")
        assert "sk-1234567890abcdef" not in result
        assert "<REDACTED>" in result

    def test_filter_dict(self):
        mw = SecurityFilterMiddleware()
        data = {"token": "Bearer sk-1234567890abcdef", "name": "test"}
        result = mw._filter.filter_dict(data)
        assert "sk-1234567890abcdef" not in result["token"]
        assert "<REDACTED>" in result["token"]
        assert result["name"] == "test"
