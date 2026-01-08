"""Unit tests for exceptions."""

import pytest

from megaplan_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    MegaplanError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    raise_for_status,
)


def test_megaplan_error():
    """Test base MegaplanError."""
    error = MegaplanError("Test error", status_code=400)
    assert str(error) == "Test error (HTTP 400)"
    assert error.status_code == 400
    assert error.message == "Test error"


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError("Auth failed")
    assert error.status_code == 401
    assert "Auth failed" in str(error)


def test_authorization_error():
    """Test AuthorizationError."""
    error = AuthorizationError("Forbidden")
    assert error.status_code == 403


def test_not_found_error():
    """Test NotFoundError."""
    error = NotFoundError("Not found")
    assert error.status_code == 404


def test_validation_error():
    """Test ValidationError."""
    errors = [{"field": "name", "message": "Required"}]
    error = ValidationError("Validation failed", errors=errors)
    assert error.status_code == 422
    assert error.errors == errors


def test_rate_limit_error():
    """Test RateLimitError."""
    error = RateLimitError("Rate limit")
    assert error.status_code == 429


def test_server_error():
    """Test ServerError."""
    error = ServerError("Server error", status_code=500)
    assert error.status_code == 500


def test_raise_for_status_401():
    """Test raise_for_status for 401."""
    response = {"meta": {"status": 401, "errors": []}}
    with pytest.raises(AuthenticationError):
        raise_for_status(401, response)


def test_raise_for_status_403():
    """Test raise_for_status for 403."""
    response = {"meta": {"status": 403, "errors": []}}
    with pytest.raises(AuthorizationError):
        raise_for_status(403, response)


def test_raise_for_status_404():
    """Test raise_for_status for 404."""
    response = {"meta": {"status": 404, "errors": []}}
    with pytest.raises(NotFoundError):
        raise_for_status(404, response)


def test_raise_for_status_422():
    """Test raise_for_status for 422."""
    response = {"meta": {"status": 422, "errors": [{"message": "Invalid"}]}}
    with pytest.raises(ValidationError) as exc_info:
        raise_for_status(422, response)
    assert exc_info.value.errors == [{"message": "Invalid"}]


def test_raise_for_status_429():
    """Test raise_for_status for 429."""
    response = {"meta": {"status": 429, "errors": []}}
    with pytest.raises(RateLimitError):
        raise_for_status(429, response)


def test_raise_for_status_500():
    """Test raise_for_status for 500."""
    response = {"meta": {"status": 500, "errors": []}}
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(500, response)
    assert exc_info.value.status_code == 500
