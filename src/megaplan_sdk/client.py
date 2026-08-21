"""Main client for Megaplan SDK."""

from types import TracebackType
from typing import Any

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.cache import EntityCache
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger, setup_logging
from megaplan_sdk.models.auth import AuthTokenResponse
from megaplan_sdk.models.bulk import BulkCallResult
from megaplan_sdk.resources.attachments import AttachmentsResource
from megaplan_sdk.resources.auth import AuthResource
from megaplan_sdk.resources.comments import CommentsResource
from megaplan_sdk.resources.contractors import ContractorsResource
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.departments import DepartmentsResource
from megaplan_sdk.resources.employees import EmployeesResource
from megaplan_sdk.resources.filters import FiltersResource
from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource
from megaplan_sdk.resources.knowledge_base import KnowledgeBaseResource
from megaplan_sdk.resources.notifications import NotificationsResource
from megaplan_sdk.resources.projects import ProjectsResource
from megaplan_sdk.resources.tasks import TasksResource
from megaplan_sdk.resources.todos import TodosResource


class MegaplanClient:
    """Main client for Megaplan API.

    Coordinates all resources and handles authentication.
    """

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        allow_http: bool = False,
        log_level: str = "WARNING",
        enable_cache: bool = True,
        cache_ttl: int = 300,
        cache_max_size: int = 1000,
        default_comments_limit: int | None = None,
        default_history_limit: int | None = None,
        proxy: str | None = None,
    ) -> None:
        """Initialize Megaplan client.

        Args:
            base_url: Base URL for Megaplan API (e.g., https://example.megaplan.ru).
            username: Username for authentication (optional if access_token provided).
            password: Password for authentication (optional if access_token provided).
                Note: Password is NOT stored in memory for security reasons.
            access_token: Pre-obtained access token (optional).
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for 5xx errors.
            allow_http: Allow HTTP connections (insecure, only for dev/test).
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            enable_cache: Enable entity caching (default: True).
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes).
            cache_max_size: Maximum number of cached entities (default: 1000).
            default_comments_limit: Default limit for comments in get_full_details().
                None = use Megaplan API default (no explicit limit).
                This value is used only if comments_limit is not specified in method call.
            default_history_limit: Default limit for history in get_full_details().
                None = use Megaplan API default (no explicit limit).
                This value is used only if history_limit is not specified in method call.
            proxy: Proxy URL for HTTP requests (e.g., http://user:pass@proxy:8080).
                Supports HTTP, HTTPS, and SOCKS5 proxies.

        Security Note:
            For production use, it's recommended to use refresh tokens or pre-obtained
            access_token instead of username/password authentication.
        """
        # Setup logging
        setup_logging(log_level)
        logger.info(f"Initializing MegaplanClient for {base_url}")

        self.base_url = base_url
        self.username = username
        # Security: Do NOT store password in plain text
        self._http = HTTPClient(
            base_url,
            access_token=access_token,
            timeout=timeout,
            max_retries=max_retries,
            allow_http=allow_http,
            proxy=proxy,
        )
        self._auth_manager = AuthManager(self._http)

        # Initialize entity cache
        self._cache = EntityCache(max_size=cache_max_size, ttl=cache_ttl) if enable_cache else None
        if self._cache:
            logger.debug(f"Entity cache enabled (max_size={cache_max_size}, ttl={cache_ttl}s)")

        if access_token:
            self._auth_manager.restore_token(access_token)
            logger.debug("MegaplanClient initialized with access_token")

        self.auth = AuthResource(self._http, cache=self._cache)
        self.tasks = TasksResource(
            self._http,
            cache=self._cache,
            default_comments_limit=default_comments_limit,
            default_history_limit=default_history_limit,
        )
        self.projects = ProjectsResource(
            self._http,
            cache=self._cache,
            default_comments_limit=default_comments_limit,
            default_history_limit=default_history_limit,
        )
        self.deals = DealsResource(
            self._http,
            cache=self._cache,
            default_comments_limit=default_comments_limit,
            default_history_limit=default_history_limit,
        )
        self.comments = CommentsResource(self._http, cache=self._cache)
        self.contractors = ContractorsResource(self._http, cache=self._cache)
        self.employees = EmployeesResource(self._http, cache=self._cache)
        self.departments = DepartmentsResource(self._http, cache=self._cache)
        self.filters = FiltersResource(self._http, cache=self._cache)
        self.attachments = AttachmentsResource(self._http, cache=self._cache)
        self.notifications = NotificationsResource(self._http, cache=self._cache)
        self.todos = TodosResource(self._http, cache=self._cache)
        self.knowledge_article = KnowledgeArticleResource(self._http, cache=self._cache)
        self.knowledge_base = KnowledgeBaseResource(
            self._http, cache=self._cache, article_resource=self.knowledge_article
        )

        # Security: Store password only for initial authentication if provided
        self._initial_password = password if (username and password) else None
        if self._initial_password:
            logger.debug("MegaplanClient initialized with username/password")

    async def __aenter__(self) -> "MegaplanClient":
        """Async context manager entry."""
        logger.debug("Entering MegaplanClient context")
        await self._http.open()

        # Perform initial authentication if credentials provided
        if self._initial_password and self.username:
            await self._auth_manager.authenticate(self.username, self._initial_password)
            # Clear password from memory after first use
            self._initial_password = None

        logger.debug("MegaplanClient context ready")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def authenticate(self, username: str, password: str) -> AuthTokenResponse:
        """Manually authenticate with username and password.

        Args:
            username: User email or username.
            password: User password.

        Returns:
            Full token response. Persist ``.refresh_token`` — the server
            rotates it on every refresh and the returned one is the only
            guaranteed-valid token (FR-A).

        Note:
            For security, password is not stored. Use refresh tokens for
            subsequent authentications.
        """
        return await self._auth_manager.authenticate(username, password)

    async def raw(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any]:
        """Call an API endpoint that has no dedicated resource yet.

        Keeps token refresh, retries and ``meta.errors`` handling — the reason
        to use this instead of a second HTTP client alongside the SDK. ``query``
        is encoded into Megaplan's query literal (``?{"limit": 60}``); do not
        build that literal yourself.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            path: Full API path, e.g. ``/api/v3/notification``.
            query: Query parameters, encoded as the Megaplan JSON literal.
            json: Request body for POST/PUT/PATCH.

        Returns:
            Parsed response body including ``meta`` and ``data``.

        Examples:
            >>> body = await client.raw("GET", "/api/v3/notification", query={"limit": 60})
            >>> notifications = body["data"]
        """
        return await self._http._request(method.upper(), path, params=query, json_data=json)

    async def bulk(self, calls: list[Any]) -> list[BulkCallResult]:
        """Send several API calls in one HTTP request (``POST /api/v3/bulk``).

        Use it when the same call has to be made for many entities — links of N
        deals, cards of N tasks — instead of a loop of N requests. Results keep
        the order of ``calls``; each one carries its own status, so handle them
        per element, not per batch.

        Args:
            calls: ApiCall models or dicts with method/url[/body].

        Returns:
            One result per call, in the same order.

        Examples:
            >>> results = await client.bulk(
            ...     [{"method": "GET", "url": f"/api/v3/deal/{i}/linkedDeals"} for i in (86, 219)]
            ... )
            >>> [r.status for r in results]
            [200, 200]
        """
        return await self.deals._bulk_calls(calls)

    async def close(self) -> None:
        """Close client and cleanup resources."""
        logger.debug("Closing MegaplanClient")
        await self._http.close()
        logger.debug("MegaplanClient closed")

    def set_access_token(self, access_token: str) -> None:
        """Set access token manually.

        Args:
            access_token: OAuth2 access token.
        """
        self._auth_manager.restore_token(access_token)

    def clear_cache(self) -> None:
        """Clear all cached entities.

        Examples:
            >>> async with MegaplanClient(...) as client:
            ...     await client.tasks.list()  # Caches employees
            ...     client.clear_cache()  # Clear all cache
        """
        if self._cache:
            self._cache.clear()
            logger.debug("Entity cache cleared")

    def clear_cache_type(self, content_type: str) -> None:
        """Clear cache for specific entity type.

        Args:
            content_type: Entity type to clear (e.g., "Employee", "Contractor").

        Examples:
            >>> async with MegaplanClient(...) as client:
            ...     await client.employees.list()  # Caches employees
            ...     client.clear_cache_type("Employee")  # Clear only employees
        """
        if self._cache:
            self._cache.clear_type(content_type)
            logger.debug(f"Entity cache cleared for type: {content_type}")
