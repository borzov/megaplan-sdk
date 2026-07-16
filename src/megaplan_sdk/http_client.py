"""HTTP client for Megaplan API."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from megaplan_sdk.exceptions import AuthenticationError, raise_for_status
from megaplan_sdk.logging_config import logger, sanitize_dict


class HTTPClient:
    """HTTP client with authentication, retry logic, and response validation.

    Handles:
    - Automatic access token injection
    - JSON parameters in query string
    - Retry logic with exponential backoff
    - Response validation
    - Error handling
    """

    def __init__(
        self,
        base_url: str,
        access_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        allow_http: bool = False,
        proxy: str | None = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL for Megaplan API (e.g., https://example.megaplan.ru).
            access_token: Optional access token for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for 5xx errors.
            allow_http: Allow HTTP connections (insecure, only for dev/test).
            proxy: Proxy URL for HTTP requests (e.g., http://user:pass@proxy:8080).
                Supports HTTP, HTTPS, and SOCKS5 proxies.

        Raises:
            ValueError: If base_url is not HTTPS and allow_http is False.
        """
        # Security: Validate HTTPS URL
        if not base_url.startswith("https://") and not allow_http:
            raise ValueError(
                f"Only HTTPS URLs are allowed for security. Got: {base_url}. "
                f"Use allow_http=True only for development/testing."
            )

        self.base_url = base_url.rstrip("/")
        self._access_token: str | None = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._proxy = proxy
        self._client: httpx.AsyncClient | None = None

    @property
    def access_token(self) -> str | None:
        """Access token for authentication (read-only)."""
        return self._access_token

    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            # Configure connection pooling for better performance
            limits = httpx.Limits(
                max_connections=100,  # Maximum total connections
                max_keepalive_connections=20,  # Keep 20 connections alive
                keepalive_expiry=30.0,  # Keep connections alive for 30 seconds
            )

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                limits=limits,
                follow_redirects=True,
                proxy=self._proxy,
            )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def set_access_token(self, access_token: str | None) -> None:
        """Set access token for authentication.

        Args:
            access_token: OAuth2 access token (or None to clear).
        """
        self._access_token = access_token

    def _build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        """Build URL with JSON parameters in query string.

        Megaplan API expects JSON parameters in query string format:
        /api/v3/task?{"limit":5}

        Args:
            path: API path (e.g., /api/v3/task).
            params: Query parameters as dictionary.

        Returns:
            Full URL with query string.
        """
        url = f"{self.base_url}{path}"

        if params:
            params_json = json.dumps(params, ensure_ascii=False)
            url = f"{url}?{params_json}"

        return url

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers with authentication.

        Args:
            extra_headers: Additional headers to include.

        Returns:
            Headers dictionary.
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | list[Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            path: API path.
            params: Query parameters.
            json_data: JSON body data.
            files: Files for multipart/form-data.
            headers: Additional headers.

        Returns:
            Response JSON as dictionary.

        Raises:
            MegaplanError: For various error conditions.
        """
        await self._ensure_client()
        assert self._client is not None  # For mypy: ensured by _ensure_client()

        url = self._build_url(path, params)
        request_headers = self._build_headers(headers)

        if files:
            request_headers.pop("Content-Type", None)

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Making {method} request to {path}",
                    extra={
                        "method": method,
                        "path": path,
                        "params": sanitize_dict(params) if params else None,
                        "attempt": attempt + 1,
                    },
                )

                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    files=files,
                )

                response.raise_for_status()
                response_data: dict[str, Any] = response.json()

                meta = response_data.get("meta", {})
                status = meta.get("status", response.status_code)

                if status != 200:
                    raise_for_status(status, response_data)

                logger.debug(
                    f"{method} {path} succeeded",
                    extra={"status_code": response.status_code, "attempt": attempt + 1},
                )

                return response_data

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                logger.warning(
                    f"HTTP error {status_code} on {method} {path}",
                    extra={"status_code": status_code, "attempt": attempt + 1},
                )

                # Handle 429 Rate Limit
                if status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", "60")
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        # Retry-After might be a date string, default to 60s
                        wait_time = 60

                    logger.warning(
                        f"Rate limit exceeded (429). Retry after {wait_time}s",
                        extra={"wait_time": wait_time, "attempt": attempt + 1},
                    )

                    if attempt < self.max_retries:
                        await asyncio.sleep(wait_time)
                        continue

                # Handle 5xx Server Errors
                if 500 <= status_code < 600 and attempt < self.max_retries:
                    # Check Retry-After header
                    retry_after_header = e.response.headers.get("Retry-After")
                    if retry_after_header:
                        try:
                            wait_time = int(retry_after_header)
                        except ValueError:
                            wait_time = 2**attempt
                    else:
                        wait_time = 2**attempt

                    logger.info(
                        f"Retrying after {wait_time}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={"wait_time": wait_time, "attempt": attempt + 1},
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # Parse error response
                response_data = {}
                if e.response:
                    try:
                        response_data = e.response.json()
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse error response as JSON")
                        response_data = {"meta": {"errors": [{"message": e.response.text[:200]}]}}

                raise_for_status(status_code, response_data)

            except httpx.RequestError as e:
                logger.warning(
                    f"Request error on {method} {path}: {str(e)}",
                    extra={"error_type": type(e).__name__, "attempt": attempt + 1},
                )

                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.info(
                        f"Retrying after {wait_time}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={"wait_time": wait_time, "attempt": attempt + 1},
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise RuntimeError("Unexpected error in request")

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make GET request.

        Args:
            path: API path.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response JSON as dictionary.
        """
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json_data: dict[str, Any] | list[Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make POST request.

        Args:
            path: API path.
            json_data: JSON body data.
            files: Files for multipart/form-data.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response JSON as dictionary.
        """
        return await self._request(
            "POST", path, json_data=json_data, files=files, params=params, headers=headers
        )

    async def put(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make PUT request.

        Args:
            path: API path.
            json_data: JSON body data.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response JSON as dictionary.
        """
        return await self._request("PUT", path, json_data=json_data, params=params, headers=headers)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make DELETE request.

        Args:
            path: API path.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response JSON as dictionary.
        """
        return await self._request("DELETE", path, params=params, headers=headers)

    async def open(self) -> None:
        """Open the underlying HTTP connection pool.

        Public counterpart of the async context manager entry, for callers
        managing the lifecycle manually. Pair with close().
        """
        await self._ensure_client()

    async def post_form(
        self,
        url: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make POST request with form data (OAuth token endpoints).

        Exists solely for authentication: no token injection, no Megaplan
        envelope validation. Owns the transport entirely — failures surface
        as AuthenticationError, so callers never handle httpx.

        Args:
            url: Full URL (not just path).
            data: Form data dictionary.
            headers: Optional headers.

        Returns:
            Parsed response JSON.

        Raises:
            AuthenticationError: On HTTP error status, network failure,
                or a non-JSON response body.
        """
        await self._ensure_client()
        assert self._client is not None  # For mypy: ensured by _ensure_client()
        try:
            response = await self._client.post(url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"Authentication request failed with status {e.response.status_code}"
            ) from e
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            raise AuthenticationError(f"Authentication request failed: {e}") from e

    def _binary_url(self, path: str) -> str:
        """Join an attachment path to base_url; pass absolute URLs through."""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}{path}"

    @asynccontextmanager
    async def stream_binary(self, path: str) -> AsyncIterator[httpx.Response]:
        """Stream an authorized binary resource (attachments; #FR-C).

        Args:
            path: Relative path from an ``Attache``/``File`` model (e.g.
                ``/attach/SdfFileM_File/File/1/2/x.png``) or an absolute URL.

        Yields:
            The open streaming ``httpx.Response``; iterate ``aiter_bytes()``.

        Raises:
            MegaplanError subclasses mapped from the HTTP status code.
        """
        await self._ensure_client()
        assert self._client is not None  # For mypy: ensured by _ensure_client()

        headers = self._build_headers()
        headers.pop("Content-Type", None)

        async with self._client.stream("GET", self._binary_url(path), headers=headers) as response:
            if response.status_code >= 400:
                await response.aread()
                raise_for_status(
                    response.status_code,
                    {},
                    f"Binary download failed for {path}",
                )
            yield response

    async def get_binary(self, path: str) -> bytes:
        """Download an authorized binary resource fully into memory (#FR-C).

        For large files prefer :meth:`stream_binary`.
        """
        async with self.stream_binary(path) as response:
            return await response.aread()
