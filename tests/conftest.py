"""Pytest configuration and fixtures."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.comments import CommentsResource
from megaplan_sdk.resources.contractors import ContractorsResource
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.departments import DepartmentsResource
from megaplan_sdk.resources.employees import EmployeesResource
from megaplan_sdk.resources.filters import FiltersResource
from megaplan_sdk.resources.knowledge_base import KnowledgeBaseResource
from megaplan_sdk.resources.projects import ProjectsResource
from megaplan_sdk.resources.tasks import TasksResource


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


class MegaplanAPIMock:
    """Adapter over respx that speaks the Megaplan API envelope.

    Tests describe endpoint behavior in domain terms — path relative to
    /api/v3 plus the ``data`` payload — without repeating the base URL,
    the ``{"meta": ..., "data": ...}`` envelope, or transport details:

        megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
        route = megaplan_api.get("employee/10", data={...})
        assert route.call_count == 1

    Pass ``json=`` to override the whole body (envelope included) and
    ``status=`` for error responses.
    """

    def __init__(self, router: respx.MockRouter, base_url: str) -> None:
        self.router = router
        self.base_url = base_url

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/api/v3/{path.lstrip('/')}"

    def _mock(
        self,
        method: str,
        path: str,
        data: Any,
        status: int,
        json: Any,
        headers: dict[str, str] | None,
    ) -> respx.Route:
        if json is None:
            json = {"meta": {"status": status}}
            if data is not None:
                json["data"] = data
        return self.router.request(method, self._url(path)).mock(
            return_value=Response(status, json=json, headers=headers)
        )

    def get(
        self,
        path: str,
        data: Any = None,
        *,
        status: int = 200,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> respx.Route:
        """Mock a GET endpoint returning ``data`` inside the Megaplan envelope."""
        return self._mock("GET", path, data, status, json, headers)

    def post(
        self,
        path: str,
        data: Any = None,
        *,
        status: int = 200,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> respx.Route:
        """Mock a POST endpoint returning ``data`` inside the Megaplan envelope."""
        return self._mock("POST", path, data, status, json, headers)

    def delete(
        self,
        path: str,
        data: Any = None,
        *,
        status: int = 200,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> respx.Route:
        """Mock a DELETE endpoint returning ``data`` inside the Megaplan envelope."""
        return self._mock("DELETE", path, data, status, json, headers)


@pytest.fixture
def megaplan_api(base_url: str) -> Iterator[MegaplanAPIMock]:
    """Megaplan API mock: routes with the meta/data envelope built in."""
    with respx.mock(assert_all_called=False) as router:
        yield MegaplanAPIMock(router, base_url)


@pytest.fixture
async def http_client(
    megaplan_api: MegaplanAPIMock, access_token: str
) -> AsyncIterator[HTTPClient]:
    """Authenticated HTTPClient wired to the megaplan_api mock."""
    async with HTTPClient(megaplan_api.base_url, access_token=access_token) as client:
        yield client


@pytest.fixture
def tasks(http_client: HTTPClient) -> TasksResource:
    """Tasks resource over the mocked API."""
    return TasksResource(http_client)


@pytest.fixture
def projects(http_client: HTTPClient) -> ProjectsResource:
    """Projects resource over the mocked API."""
    return ProjectsResource(http_client)


@pytest.fixture
def deals(http_client: HTTPClient) -> DealsResource:
    """Deals resource over the mocked API."""
    return DealsResource(http_client)


@pytest.fixture
def employees(http_client: HTTPClient) -> EmployeesResource:
    """Employees resource over the mocked API."""
    return EmployeesResource(http_client)


@pytest.fixture
def contractors(http_client: HTTPClient) -> ContractorsResource:
    """Contractors resource over the mocked API."""
    return ContractorsResource(http_client)


@pytest.fixture
def departments(http_client: HTTPClient) -> DepartmentsResource:
    """Departments resource over the mocked API."""
    return DepartmentsResource(http_client)


@pytest.fixture
def comments(http_client: HTTPClient) -> CommentsResource:
    """Comments resource over the mocked API."""
    return CommentsResource(http_client)


@pytest.fixture
def filters(http_client: HTTPClient) -> FiltersResource:
    """Filters resource over the mocked API."""
    return FiltersResource(http_client)


@pytest.fixture
def knowledge_base(http_client: HTTPClient) -> KnowledgeBaseResource:
    """Knowledge base resource over the mocked API."""
    return KnowledgeBaseResource(http_client)
