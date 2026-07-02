"""Filters resource for Megaplan API."""

from __future__ import annotations

from typing import Any, TypeVar

from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.filter import (
    BaseFilter,
    FilterExport,
    NewFilterSettingsRequest,
    UserSetting,
)
from megaplan_sdk.pagination import Page
from megaplan_sdk.registry import filter_path_for
from megaplan_sdk.resources.base import BaseResource

T = TypeVar("T", bound=BaseFilter)


class FiltersResource(BaseResource):
    """Resource for managing filters.

    Provides methods to create, read, update, and delete filters for various entity types.
    """

    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normalize entity type to API format.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").

        Returns:
            Normalized entity type for API path (e.g., "taskFilter", "tradeFilter").
        """
        return filter_path_for(entity_type)

    async def list(
        self,
        entity_type: str,
        filters: list[str] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[BaseFilter]:
        """Get list of filters for entity type.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filters: List of filter IDs to include.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of filters.

        Examples:
            >>> # Get all task filters
            >>> filters = await client.filters.list("task")
            >>>
            >>> # Get specific filters
            >>> filters = await client.filters.list("task", filters=["123", "456"])
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type)

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

        if filters:
            if params is None:
                params = {}
            params["filters"] = filters

        return await self._get_list(path, BaseFilter, params)

    async def get(
        self,
        entity_type: str,
        filter_id: int | str,
    ) -> BaseFilter:
        """Get filter by ID.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).

        Returns:
            Filter instance.

        Examples:
            >>> filter = await client.filters.get("task", filter_id=123)
            >>> filter = await client.filters.get("task", filter_id="my_filter")
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id))
        response = await self._http.get(path)
        return BaseFilter(**response["data"])

    async def create(
        self,
        entity_type: str,
        filter_id: int | str,
        filter_data: dict[str, Any],
    ) -> BaseFilter:
        """Create or update filter.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).
            filter_data: Filter data dictionary (name, config, etc.).

        Returns:
            Created or updated filter.

        Examples:
            >>> filter = await client.filters.create(
            ...     "task",
            ...     "my_filter",
            ...     {"name": "Active tasks", "config": {"status": "in_progress"}}
            ... )
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id))
        response = await self._http.post(path, json_data=filter_data)
        return BaseFilter(**response["data"])

    async def update(
        self,
        entity_type: str,
        filter_id: int | str,
        filter_data: dict[str, Any],
    ) -> BaseFilter:
        """Update filter.

        This is an alias for create() since API uses POST for both create and update.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).
            filter_data: Filter data dictionary.

        Returns:
            Updated filter.

        Examples:
            >>> filter = await client.filters.update(
            ...     "task",
            ...     123,
            ...     {"name": "Updated filter name"}
            ... )
        """
        return await self.create(entity_type, filter_id, filter_data)

    async def delete(
        self,
        entity_type: str,
        filter_id: int | str,
    ) -> None:
        """Delete filter.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).

        Examples:
            >>> await client.filters.delete("task", filter_id=123)
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id))
        await self._http.delete(path)

    async def leave(
        self,
        entity_type: str,
        filter_id: int | str,
    ) -> None:
        """Leave filter (stop following it).

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).

        Examples:
            >>> await client.filters.leave("task", filter_id=123)
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id), "leave")
        await self._http.post(path)

    async def get_settings(
        self,
        entity_type: str,
        filter_id: int | str,
    ) -> UserSetting:
        """Get filter settings.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).

        Returns:
            User filter settings.

        Examples:
            >>> settings = await client.filters.get_settings("task", filter_id=123)
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id), "newFilterSettings")
        response = await self._http.get(path)
        data = response.get("data")
        if data is None:
            return UserSetting()
        return UserSetting(**data) if isinstance(data, dict) else UserSetting()

    async def set_settings(
        self,
        entity_type: str,
        filter_id: int | str,
        settings: dict[str, Any],
    ) -> UserSetting:
        """Set filter settings.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter_id: Filter identifier (can be int or string).
            settings: Settings data dictionary.

        Returns:
            Updated user filter settings.

        Examples:
            >>> settings = await client.filters.set_settings(
            ...     "task",
            ...     filter_id=123,
            ...     settings={"someSetting": "value"}
            ... )
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, str(filter_id), "newFilterSettings")
        request = NewFilterSettingsRequest(**settings)
        response = await self._http.post(path, json_data=request.model_dump(by_alias=True))
        return UserSetting(**response["data"])

    async def export(
        self,
        entity_type: str,
        filter: dict[str, Any] | int | str,
        query: str | None = None,
        fields: list[str] | None = None,
    ) -> FilterExport:
        """Export data by filter.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            filter: Filter configuration (dict), filter ID (int), or filter ID string.
            query: Search query.
            fields: List of fields to include in export.

        Returns:
            FilterExport with file entity (if export completed) or None (if queued).

        Examples:
            >>> # Export using filter ID
            >>> result = await client.filters.export("task", filter=123)
            >>>
            >>> # Export using filter config
            >>> result = await client.filters.export(
            ...     "task",
            ...     filter={"status": "in_progress"},
            ...     fields=["name", "status"]
            ... )
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, "export")

        params: dict[str, Any] = {}
        if isinstance(filter, dict):
            params["filter"] = filter
        else:
            # If filter is ID, pass as integer (API accepts filter ID directly)
            filter_id = int(filter) if isinstance(filter, str) else filter
            params["filter"] = filter_id

        if query:
            params["query"] = query
        if fields:
            params["fields"] = fields

        response = await self._http.get(path, params=params if params else None)
        data = response.get("data", {})
        return FilterExport(**data) if data else FilterExport(file=None)

    async def get_available_responsibles(
        self,
        entity_type: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Employee | Contractor]:
        """Get available responsibles for filter.

        Returns list of employees and contractors with general director role.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of employees and contractors.

        Examples:
            >>> responsibles = await client.filters.get_available_responsibles("task")
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, "availableResponsibles")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        result: list[Employee | Contractor] = []
        for item in data:
            if isinstance(item, dict):
                content_type = item.get("contentType", "")
                if content_type == "Employee":
                    result.append(Employee(**item))
                elif content_type in ("ContractorCompany", "ContractorHuman"):
                    result.append(Contractor(**item))
                else:
                    # Fallback to BaseEntity if unknown type
                    result.append(Contractor(**item))
            else:
                result.append(item)

        return result

    async def get_formula_variables(
        self,
        entity_type: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[str]:
        """Get formula variables for filter.

        Returns list of allowed variables for formula-based filtering.

        Args:
            entity_type: Entity type (e.g., "task", "deal", "employee").
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of variable names (strings).

        Examples:
            >>> variables = await client.filters.get_formula_variables("task")
        """
        normalized_type = self._normalize_entity_type(entity_type)
        path = self._build_path("api", "v3", normalized_type, "formula", "variables")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)
        return [str(item) for item in data if item is not None]
