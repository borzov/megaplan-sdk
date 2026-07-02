"""Resource for working with departments."""

from typing import Any

from megaplan_sdk.models.department import Department
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource


class DepartmentsResource(BaseResource):
    """Resource for working with departments.

    Provides methods to list and get department information.

    Examples:
        >>> async with MegaplanClient(...) as client:
        ...     # List all departments
        ...     departments = await client.departments.list()
        ...
        ...     # Get specific department
        ...     dept = await client.departments.get(department_id=1)
    """

    async def list(
        self,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
    ) -> list[Department]:
        """Get list of departments.

        Args:
            limit: Maximum number of departments to return.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).

        Returns:
            List of departments.

        Examples:
            >>> async with MegaplanClient(...) as client:
            ...     departments = await client.departments.list(limit=50)
            ...     for dept in departments:
            ...         print(f"{dept.name}")
        """
        path = self._build_path("api", "v3", "department")
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
        )
        return await self._get_list(path, Department, params)

    async def get(self, department_id: int) -> Department:
        """Get department by ID.

        Args:
            department_id: Department identifier.

        Returns:
            Department instance.

        Examples:
            >>> async with MegaplanClient(...) as client:
            ...     dept = await client.departments.get(1)
            ...     print(dept.name)
        """
        return await self._get_entity("department", department_id, Department)
