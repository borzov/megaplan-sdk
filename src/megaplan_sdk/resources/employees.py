"""Employees resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.resources.base import BaseResource


class EmployeesResource(BaseResource):
    """Resource for working with employees."""

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

    async def list(
        self,
        filter: Any | None = None,  # noqa: A002
        q: str | None = None,
        department_id: int | None = None,
        status: str | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Employee]:
        """Get list of employees.

        Args:
            filter: NOT SUPPORTED — raises NotImplementedError.
                The server accepts filter= with 200 OK but silently ignores it.
                Fetch `.list(limit=500)` and filter client-side. (#13)
            q: NOT SUPPORTED — raises NotImplementedError.
                Text search on /api/v3/employee is silently ignored server-side.
                Fetch `.list(limit=500)` and filter client-side. (#13)
            department_id: Filter by department ID.
            status: Filter by status (active, fired, etc.).
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["department", "manager"]).
                Supported values: "department", "manager".
                Note: When expand is provided, department and manager fields will be
                replaced with full Department/Employee objects instead of BaseEntity.

        Returns:
            List of employees (with expanded fields if requested).

        Raises:
            NotImplementedError: If `filter` or `q` is provided (server silently
                ignores them — raise loudly to prevent silent wrong results).

        Examples:
            >>> # Get all active employees
            >>> employees = await client.employees.list(status="active")
            >>>
            >>> # Get employees with expanded department
            >>> employees = await client.employees.list(
            ...     limit=10, expand=["department", "manager"]
            ... )
            >>> for employee in employees:
            ...     if employee.department and hasattr(employee.department, 'name'):
            ...         print(f"{employee.display_name()} - {employee.department.name}")
        """
        # #13: /api/v3/employee accepts filter/q with 200 OK but SILENTLY
        # ignores them (verified 2026-06-24 against ruvents.megaplan.ru) —
        # raise loudly instead of returning a wrong subset.
        if filter is not None:
            raise NotImplementedError(
                "Server-side filter on /api/v3/employee is accepted (200 OK) "
                "but silently ignored. Fetch `.list(limit=500)` and filter "
                "client-side. (#13)"
            )
        if q is not None:
            raise NotImplementedError(
                "Text search `q` on /api/v3/employee is silently ignored "
                "server-side. Fetch `.list(limit=500)` and filter "
                "client-side. (#13)"
            )

        path = self._build_path("api", "v3", "employee")

        # Prepare employee-specific parameters
        extra_params: dict[str, Any] = {}
        if department_id:
            extra_params["department"] = {
                "id": department_id,
                "contentType": ContentType.DEPARTMENT,
            }
        if status:
            extra_params["status"] = status

        # Use base method to build params (DRY)
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            **extra_params,
        )

        # 1. Fetch employees
        employees = await self._get_list(path, Employee, params)

        # 2. If no expand, return as is
        if not expand or not employees:
            return employees

        # 3. Batch load related entities
        from megaplan_sdk.models.department import Department

        expand_config: dict[str, tuple[str, type, str]] = {
            "department": ("department", Department, ContentType.DEPARTMENT),
            "manager": ("employee", Employee, ContentType.EMPLOYEE),
        }

        expanded = await self._expand_list_entities(employees, expand, expand_config)
        department_map = expanded.get("department", {})
        manager_map = expanded.get("manager", {})

        # 4. Replace BaseEntity references with full objects
        for employee in employees:
            if employee.department and employee.department.id in department_map:
                employee.department = department_map[employee.department.id]

            if employee.manager and employee.manager.id in manager_map:
                employee.manager = manager_map[employee.manager.id]

        return employees

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
            >>> async for employee in client.employees.iterate(status="active"):
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
