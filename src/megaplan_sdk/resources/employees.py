"""Employees resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.exceptions import MegaplanError
from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.todo import Todo
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource


class EmployeesResource(BaseResource):
    """Resource for working with employees."""

    _page_content_type = ContentType.EMPLOYEE
    _history_entity_type = "employee"
    _history_id_param = "employee_id"

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
        *,
        include_dismissed: bool = False,
        fields_strict: bool = False,
        **unsupported: Any,
    ) -> list[Employee]:
        """Get list of employees.

        The default directory lists current staff. With include_dismissed=True
        the SDK walks the account's all and not_working directories, in that order.
        Use page_after for continuation or iterate() for a full traversal.

        Args:
            include_dismissed: Include former staff using the named employee filters.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields_strict: Require fields confirmed on this list route.
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
                (arbitrary filter configurations and free-text search are unsupported).

        Examples:
            >>> # Scan all pages and filter client-side
            >>> employees = [e async for e in client.employees.iterate(limit=100)]
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
                f"Unsupported employee filters: {bad}. Use include_dismissed=True for "
                "the combined staff directory, or filter the result of iterate() locally."
            )

        path = self._build_path("api", "v3", "employee")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            list_route="employee",
            fields_strict=fields_strict,
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        if include_dismissed:
            page_limit = 100 if limit is None else limit
            rows: list[Employee] = []
            async for employee in self._iterate_staff(params or {}, expand):
                rows.append(employee)
                if len(rows) == page_limit:
                    break
            return rows

        employees = await self._get_list(path, Employee, params)
        return await self._expand_references(employees, expand)

    async def _iterate_staff(
        self, params: dict[str, Any], expand: list[str] | None
    ) -> AsyncIterator[Employee]:
        """Walk both directories once, applying a public cursor to the combined order."""
        params = dict(params)
        if any(params.get(k) for k in ("pageBefore", "pageWith", "sortBy")):
            raise ValueError("include_dismissed supports page_after in directory order")
        after = params.pop("pageAfter", None)
        if after is not None and (
            not isinstance(after, dict)
            or after.get("contentType") != "Employee"
            or not isinstance(after.get("id"), int)
        ):
            raise ValueError("page_after must identify an Employee")
        waiting_for = after["id"] if after else None
        size = min(100, params.get("limit", 100))
        if size < 1:
            raise ValueError("limit must be positive")
        size = 100 if after else size
        params["limit"] = size

        # Some installations silently ignore an unknown saved filter. Check the
        # catalogue before yielding even one row of the combined result.
        path = self._build_path("api", "v3", "employeeFilter")
        filters: dict[str, Any] = {"limit": 100}
        available: set[str] = set()
        filter_cursors: set[str] = set()
        while not {"all", "not_working"}.issubset(available):
            entries = self._parse_list_response(await self._http.get(path, params=filters))
            available.update(str(r["id"]) for r in entries)
            if len(entries) < 100:
                break
            last = str(entries[-1]["id"])
            if last in filter_cursors:
                raise MegaplanError("Repeated employeeFilter pagination cursor")
            filter_cursors.add(last)
            filters["pageAfter"] = {"contentType": "EmployeeFilter", "id": last}
        if not {"all", "not_working"}.issubset(available):
            raise NotImplementedError("Employee directories all and not_working are required")

        seen: set[int] = set()
        for group in ("all", "not_working"):
            query = {**params, "filter": {"contentType": "EmployeeFilter", "id": group}}
            cursors: set[int] = set()
            while True:
                rows = await self._get_list(
                    self._build_path("api", "v3", "employee"), Employee, query
                )
                visible = []
                for employee in rows:
                    if employee.id in seen:
                        continue
                    seen.add(employee.id)
                    if waiting_for is not None:
                        if employee.id == waiting_for:
                            waiting_for = None
                        continue
                    visible.append(employee)
                for employee in await self._expand_references(visible, expand):
                    yield employee
                if len(rows) < size:
                    break
                last_id = rows[-1].id
                if last_id in cursors:
                    raise MegaplanError("Repeated employee directory cursor")
                cursors.add(last_id)
                query["pageAfter"] = {"contentType": "Employee", "id": last_id}
        if waiting_for is not None:
            raise ValueError("page_after employee is absent from both directories")

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
        *,
        include_dismissed: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[Employee]:
        """Iterate over all employees with automatic pagination.

        Args:
            limit: Number of items per page.
            include_dismissed: Walk both current and former employees.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Employee objects.

        Examples:
            >>> async for employee in client.employees.iterate(limit=100):
            ...     print(f"{employee.first_name} {employee.last_name}")
        """
        if include_dismissed:
            expand = kwargs.pop("expand", None)
            allowed = {
                "fields_strict",
                "fields",
                "page",
                "page_after",
                "page_before",
                "page_with",
                "sort_by",
                "only_requested_fields",
            }
            unknown = kwargs.keys() - allowed
            if unknown:
                raise NotImplementedError(
                    f"Unsupported employee filters: {', '.join(sorted(unknown))}"
                )
            params = self._build_list_params(list_route="employee", limit=limit, **kwargs)
            async for employee in self._iterate_staff(params or {}, expand):
                yield employee
            return
        employee: Employee
        async for employee in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.EMPLOYEE,
            self.list,
            limit,
            **kwargs,
        ):
            yield employee

    async def get_todos(
        self,
        employee_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
    ) -> list[Todo]:
        """Get todos attached to this employee. See ``EntityTodosMixin._todos_of_entity``."""
        return await self._todos_of_entity(employee_id, limit, page_after)
