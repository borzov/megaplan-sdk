"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def base_url() -> str:
    """Base URL for Megaplan API."""
    return "https://example.megaplan.ru"


@pytest.fixture
def username() -> str:
    """Test username."""
    return "test@example.com"


@pytest.fixture
def password() -> str:
    """Test password."""
    return "test_password"


@pytest.fixture
def access_token() -> str:
    """Test access token."""
    return "test_access_token_12345"


@pytest.fixture
def auth_response(access_token: str) -> dict:
    """OAuth2 authentication response."""
    return {
        "access_token": access_token,
        "expires_in": 172800,
        "token_type": "bearer",
        "scope": None,
        "refresh_token": "test_refresh_token_67890",
    }
