"""Employees resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource


class EmployeesResource(BaseResource):
    """Resource for working with employees."""

    _page_content_type = ContentType.EMPLOYEE

    # Replace mode: no details model — loaded entities replace the reference
    # fields on immutable copies, the public return type stays list[Employee].
    _expand_rules = {
        "department": ExpandRule("department", Department),
        "manager": ExpandRule("employee", Employee),
    }

    async def create(self, employee_data: dict[str, Any]) -> Employee:
        """Create a new employee.

        Args:
            employee_data: Employee data dictionary.
                Required: email, firstName, lastName
                Optional: phone, position, department, etc.

        Returns:
            Created employee.

        Examples:
            >>> employee_data = {
            ...     "email": "user@example.com",
            ...     "firstName": "John",
            ...     "lastName": "Doe",
            ...     "position": "Developer"
            ... }
            >>> employee = await client.employees.create(employee_data)
        """
        return await self._create_entity("employee", employee_data, Employee)

    # No server-side filtering works on /api/v3/employee: filter/q are accepted
    # (200 OK) but silently ignored (#13), while department/status are hard-
    # rejected with 422 (#26/#27). These params are intentionally absent from
    # the signature (#28); any attempt is caught below with clear guidance.
    _UNSUPPORTED_FILTER_PARAMS = ("filter", "q", "department_id", "status", "department")

    async def list(
        self,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
        **unsupported: Any,
    ) -> list[Employee]:
        """Get list of employees.

        Server-side filtering on ``/api/v3/employee`` does not work at all
        (#13/#26/#27/#28): ``filter``/``q`` are accepted with 200 OK but
        silently ignored, and ``department``/``status`` are rejected with 422.
        Passing any of them raises ``NotImplementedError`` with guidance to
        filter client-side instead.

        Args:
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["department", "manager"]).
                Supported values: "department", "manager".
                Note: When expand is provided, department and manager fields will be
                replaced with full Department/Employee objects instead of BaseEntity.
            **unsupported: Trap for dead filter params (``filter``, ``q``,
                ``department_id``, ``status``) — raises ``NotImplementedError``.

        Returns:
            List of employees (with expanded fields if requested).

        Raises:
            NotImplementedError: If any server-side filter param is provided
                (the endpoint has no working filter — raise loudly to prevent
                silent wrong results).

        Examples:
            >>> # No server filter; fetch a page and filter client-side
            >>> employees = await client.employees.list(limit=500)
            >>> working = [e for e in employees if e.is_working]
            >>> dept = [e for e in employees if getattr(e.department, "id", None) == 1000004]
            >>>
            >>> # Get employees with expanded department
            >>> employees = await client.employees.list(
            ...     limit=10, expand=["department", "manager"]
            ... )
        """
        if unsupported:
            bad = ", ".join(sorted(unsupported))
            raise NotImplementedError(
                f"Server-side filtering on /api/v3/employee is not supported "
                f"(got: {bad}). The endpoint ignores filter/q (200 OK, no effect) "
                f"and 422s on department/status. Fetch `.list(limit=500)` and "
                f"filter client-side, e.g. `[e for e in emps if e.is_working]`. "
                f"(#13/#26/#27/#28)"
            )

        path = self._build_path("api", "v3", "employee")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        employees = await self._get_list(path, Employee, params)
        return await self._expand_and_wrap(employees, expand)

    async def get(self, employee_id: int) -> Employee:
        """Get employee by ID.

        Args:
            employee_id: Employee identifier.

        Returns:
            Employee details.

        Note:
            Use get_current() for the current user; get("me") raises ValueError.
        """
        # #10: `/employee/me` exists only for DELETE → confusing 405.
        if isinstance(employee_id, str) and employee_id.lower() == "me":
            raise ValueError(
                "To get the current user, use `employees.get_current()` "
                "(calls /api/v3/currentUser)."
            )

        return await self._get_entity("employee", employee_id, Employee)

    async def update(self, employee_id: int, employee_data: dict[str, Any]) -> Employee:
        """Update employee.

        Args:
            employee_id: Employee identifier.
            employee_data: Updated employee data.

        Returns:
            Updated employee.
        """
        return await self._update_entity("employee", employee_id, employee_data, Employee)

    async def delete(self, employee_id: int) -> None:
        """Delete employee.

        Args:
            employee_id: Employee identifier.
        """
        await self._delete_entity("employee", employee_id)

    async def get_current(self) -> Employee:
        """Get current authenticated employee.

        Returns:
            Current employee details.

        Examples:
            >>> me = await client.employees.get_current()
            >>> print(f"Logged in as: {me.email}")

        Note:
            Uses /api/v3/currentUser endpoint which returns Employee or ContractorHuman.
            For ContractorHuman users, some fields may be None.
        """
        path = self._build_path("api", "v3", "currentUser")
        response = await self._http.get(path)
        return Employee(**response["data"])

    async def get_many(self, ids: list[int], use_cache: bool = True) -> dict[int, Employee]:
        """Batch-fetch employees by id (#FR-1).

        The bulk endpoint 500s on Employee links (server bug), so this falls
        back to parallel single gets. Inaccessible ids are absent.

        Args:
            ids: Employee ids to load (duplicates ignored).
            use_cache: Read/populate the entity cache (default: True).

        Returns:
            Dict mapping id -> Employee.
        """
        logger.debug("bulk endpoint 500s for Employee; using sequential gets for get_many")
        return await self._get_many_sequential("employee", ids, Employee, use_cache)

    async def iterate(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Employee]:
        """Iterate over all employees with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Employee objects.

        Examples:
            >>> async for employee in client.employees.iterate(limit=100):
            ...     print(f"{employee.first_name} {employee.last_name}")
        """
        employee: Employee
        async for employee in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.EMPLOYEE,
            self.list,
            limit,
            **kwargs,
        ):
            yield employee
