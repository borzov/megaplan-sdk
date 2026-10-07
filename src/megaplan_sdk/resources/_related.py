"""Related-list and participant resolution shared by all resources.

`RelatedMixin` needs a handful of members from the `BaseResource` it is mixed
into (`_build_path`, `_build_list_params`, `_parse_list_response`,
`_parse_single_response`, `_load_related_entities`, `_http`). Those stay
defined on `BaseResource`; `_RelatedHost` below is a structural `Protocol` used
only to type `self` inside this mixin's methods, so mypy strict can check
attribute access without a runtime or import-time dependency on `base.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from megaplan_sdk.constants import ContentType

if TYPE_CHECKING:
    from megaplan_sdk.http_client import HTTPClient

T = TypeVar("T")


class _RelatedHost(Protocol):
    """Members `RelatedMixin` requires from the resource it is mixed into."""

    _http: HTTPClient

    def _build_path(self, *parts: str) -> str: ...

    def _build_list_params(
        self,
        filter: Any | None = None,
        limit: int | None = None,
        page_after: Any | None = None,
        page_before: Any | None = None,
        page_with: Any | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        page_content_type: str | None = None,
        page: Any | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]: ...

    def _parse_list_response(self, response: dict[str, Any]) -> list[Any]: ...

    def _parse_single_response(self, response: dict[str, Any]) -> dict[str, Any]: ...

    async def _load_related_entities(
        self,
        entities: list[Any],
        entity_type: str,
        model_class: type[T],
    ) -> dict[int, T]: ...


class RelatedMixin:
    """Related lists (auditors, executors, milestones) and participant loading."""

    async def _resolve_comment_owners(self: _RelatedHost, comments: list[Any]) -> None:
        """Resolve Employee comment owners to full Employee objects in place.

        Batch-loads unique owners via ``_load_related_entities`` (cache-first).
        Only Employee owners are resolvable via the employee endpoint; other
        owner types (Contractor*) are left as bare references (#30).
        """
        from megaplan_sdk.models.employee import Employee

        employee_owners = [
            c.owner for c in comments if c.owner is not None and c.owner.content_type == "Employee"
        ]
        if not employee_owners:
            return
        owner_map = await self._load_related_entities(employee_owners, "employee", Employee)
        for comment in comments:
            if (
                comment.owner is not None
                and comment.owner.content_type == "Employee"
                and comment.owner.id in owner_map
            ):
                comment.owner = owner_map[comment.owner.id]

    async def _resolve_employee_entities(self: _RelatedHost, items: list[Any]) -> list[Any]:
        """Resolve bare Employee references in a mixed list to full Employees.

        Related-list endpoints (auditors, executors) return bare
        ``{contentType, id}`` dicts. Batch-load the Employee ones via
        ``_load_related_entities`` (cache-first); leave everything else
        (Group, Contractor*) untouched (#35).
        """
        from megaplan_sdk.models.base import BaseEntity
        from megaplan_sdk.models.employee import Employee

        def _employee_id(item: Any) -> int | None:
            if isinstance(item, dict):
                if item.get("contentType") == ContentType.EMPLOYEE and "id" in item:
                    return int(item["id"])
                return None
            if getattr(item, "content_type", None) == ContentType.EMPLOYEE:
                return getattr(item, "id", None)
            return None

        refs = [
            BaseEntity(**{"contentType": ContentType.EMPLOYEE, "id": employee_id})
            for item in items
            if (employee_id := _employee_id(item)) is not None
        ]
        if not refs:
            return items

        loaded = await self._load_related_entities(refs, "employee", Employee)
        return [
            loaded.get(employee_id, item)
            if (employee_id := _employee_id(item)) is not None
            else item
            for item in items
        ]

    async def _get_entity_related_list(
        self: _RelatedHost,
        entity_type: str,
        entity_id: int,
        related_type: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        model_class: type[T] | None = None,
    ) -> list[Any] | list[T]:
        """Generic method to get related list (auditors, executors, milestones).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            model_class: Optional Pydantic model class for parsing items.
                If provided, returns list[model_class], otherwise returns list[dict].

        Returns:
            List of related entities (parsed if model_class provided, otherwise raw dicts).
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), related_type)

        # Build params - always include limit for milestones to avoid 500 errors
        if related_type == "milestones" and limit is None:
            # Default limit for milestones to avoid API 500 errors
            params = self._build_list_params(limit=100)
        else:
            params = self._build_list_params(
                limit=limit,
                page_after=page_after,
                page_before=page_before,
                page_with=page_with,
            )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        if model_class:
            return [model_class(**item) if isinstance(item, dict) else item for item in data]
        return data

    async def _add_entity_related(
        self: _RelatedHost,
        entity_type: str,
        entity_id: int,
        related_type: str,
        related_id: int,
        related_content_type: str = ContentType.EMPLOYEE,
        data_override: dict[str, Any] | None = None,
    ) -> Any:
        """Generic method to add related entity (auditor, executor, milestone).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            related_id: Related entity ID.
            related_content_type: Content type of related entity (usually "Employee").
            data_override: Optional data override (for milestones with custom data).

        Returns:
            Added related entity.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), related_type)

        if data_override:
            related_data = data_override
        else:
            related_data = {"id": related_id, "contentType": related_content_type}

        response = await self._http.post(path, json_data=related_data)
        return self._parse_single_response(response)

    async def _remove_entity_related(
        self: _RelatedHost,
        entity_type: str,
        entity_id: int,
        related_type: str,
        related_id: int,
        related_content_type: str = ContentType.EMPLOYEE,
        content_type_in_path: bool = True,
    ) -> None:
        """Generic method to remove related entity (auditor, executor, milestone).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            related_id: Related entity ID.
            related_content_type: Content type of related entity (usually "Employee").
            content_type_in_path: API irregularity: tasks/projects DELETE via
                .../{contentType}/{id}, deals via .../{id} (RAML + verified
                on the stand 2026-07-02 — the contentType path 404s for deals).
        """
        path_parts = [
            "api",
            "v3",
            entity_type,
            str(entity_id),
            related_type,
        ]
        if content_type_in_path:
            path_parts.append(related_content_type)
        path_parts.append(str(related_id))
        path = self._build_path(*path_parts)
        await self._http.delete(path)
