"""Custom exceptions for Megaplan SDK."""

from typing import Any


class MegaplanError(Exception):
    """Base exception for all Megaplan SDK errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code if available.
        errors: List of error details from API response.
        response: Full API response if available.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize MegaplanError.

        Args:
            message: Error message.
            status_code: HTTP status code.
            errors: List of error details.
            response: Full API response.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        self.response = response

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.status_code:
            return f"{self.message} (HTTP {self.status_code})"
        return self.message


class AuthenticationError(MegaplanError):
    """Raised when authentication fails (401).

    Typically occurs when credentials are invalid or token has expired.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AuthenticationError."""
        super().__init__(message, status_code=401, errors=errors, response=response)


class AuthorizationError(MegaplanError):
    """Raised when authorization fails (403).

    Occurs when user doesn't have permission to access the resource.
    """

    def __init__(
        self,
        message: str = "Authorization failed",
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AuthorizationError."""
        super().__init__(message, status_code=403, errors=errors, response=response)


class NotFoundError(MegaplanError):
    """Raised when resource is not found (404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize NotFoundError."""
        super().__init__(message, status_code=404, errors=errors, response=response)


class ValidationError(MegaplanError):
    """Raised when request validation fails (422).

    Contains detailed validation errors from API.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ValidationError."""
        super().__init__(message, status_code=422, errors=errors, response=response)


class RateLimitError(MegaplanError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize RateLimitError."""
        super().__init__(message, status_code=429, errors=errors, response=response)


class ServerError(MegaplanError):
    """Raised when server returns 5xx error."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        errors: list[dict[str, Any]] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ServerError."""
        super().__init__(message, status_code=status_code, errors=errors, response=response)


def raise_for_status(
    status_code: int,
    response: dict[str, Any],
    default_message: str = "Request failed",
) -> None:
    """Raise appropriate exception based on HTTP status code.

    Args:
        status_code: HTTP status code.
        response: API response dictionary.
        default_message: Default error message.

    Raises:
        AuthenticationError: For 401 status.
        AuthorizationError: For 403 status.
        NotFoundError: For 404 status.
        ValidationError: For 422 status.
        RateLimitError: For 429 status.
        ServerError: For 5xx status.
        MegaplanError: For other error status codes.
    """
    meta = response.get("meta", {})
    errors = meta.get("errors", [])
    error_message = default_message

    if errors and isinstance(errors, list) and len(errors) > 0:
        first_error = errors[0]
        if isinstance(first_error, dict) and "message" in first_error:
            error_message = first_error["message"]

    if status_code == 401:
        raise AuthenticationError(error_message, errors=errors, response=response)
    elif status_code == 403:
        raise AuthorizationError(error_message, errors=errors, response=response)
    elif status_code == 404:
        raise NotFoundError(error_message, errors=errors, response=response)
    elif status_code == 422:
        raise ValidationError(error_message, errors=errors, response=response)
    elif status_code == 429:
        raise RateLimitError(error_message, errors=errors, response=response)
    elif 500 <= status_code < 600:
        raise ServerError(error_message, status_code=status_code, errors=errors, response=response)
    else:
        raise MegaplanError(
            error_message,
            status_code=status_code,
            errors=errors,
            response=response,
        )
