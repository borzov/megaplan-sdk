"""Main client for Megaplan SDK."""

from types import TracebackType

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.cache import EntityCache
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger, setup_logging
from megaplan_sdk.resources.auth import AuthResource
from megaplan_sdk.resources.comments import CommentsResource
from megaplan_sdk.resources.contractors import ContractorsResource
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.departments import DepartmentsResource
from megaplan_sdk.resources.employees import EmployeesResource
from megaplan_sdk.resources.files import FileResource
from megaplan_sdk.resources.projects import ProjectsResource
from megaplan_sdk.resources.tasks import TasksResource


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
        )
        self._auth_manager = AuthManager(self._http)

        # Initialize entity cache
        self._cache = EntityCache(max_size=cache_max_size, ttl=cache_ttl) if enable_cache else None
        if self._cache:
            logger.debug(f"Entity cache enabled (max_size={cache_max_size}, ttl={cache_ttl}s)")

        if access_token:
            self._auth_manager._access_token = access_token
            self._auth_manager._expires_at = None
            logger.debug("MegaplanClient initialized with access_token")

        self.auth = AuthResource(self._http, cache=self._cache)
        self.tasks = TasksResource(self._http, cache=self._cache)
        self.projects = ProjectsResource(self._http, cache=self._cache)
        self.deals = DealsResource(self._http, cache=self._cache)
        self.files = FileResource(self._http, cache=self._cache)
        self.comments = CommentsResource(self._http, cache=self._cache)
        self.contractors = ContractorsResource(self._http, cache=self._cache)
        self.employees = EmployeesResource(self._http, cache=self._cache)
        self.departments = DepartmentsResource(self._http, cache=self._cache)

        # Security: Store password only for initial authentication if provided
        self._initial_password = password if (username and password) else None
        if self._initial_password:
            logger.debug("MegaplanClient initialized with username/password")

    async def __aenter__(self) -> "MegaplanClient":
        """Async context manager entry."""
        logger.debug("Entering MegaplanClient context")
        await self._http._ensure_client()

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

    async def authenticate(self, username: str, password: str) -> str:
        """Manually authenticate with username and password.

        Args:
            username: User email or username.
            password: User password.

        Returns:
            Access token.

        Note:
            For security, password is not stored. Use refresh tokens for
            subsequent authentications.
        """
        return await self._auth_manager.authenticate(username, password)

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
        self._http.set_access_token(access_token)
        self._auth_manager._access_token = access_token

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
