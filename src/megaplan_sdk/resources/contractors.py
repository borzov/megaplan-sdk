"""Contractors resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.history import LinkEvent, parse_history_entry
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource


class ContractorsResource(BaseResource):
    """Resource for working with contractors.

    Note:
        Contractor comments are not supported by Megaplan API (returns 500 error).
        Use action history or other entities for tracking contractor-related notes.

    Note:
        There is no ``get_todos()`` here, unlike deals/tasks/projects/employees.
        The route exists in RAML and is accepted by the server (not a 404),
        but confirmed on a live account (task 12b): ``GET
        /contractor/{id}/todos`` answers 500 ``There is no model class for
        bums\\crm\\api\\v03\\Entity\\Contractor`` — a server-side bug in
        instantiating the polymorphic ``Contractor`` type for this endpoint,
        not something the SDK can work around.

    Note:
        ``get_history()``/``iterate_history()``/``get_link_events()`` hit the
        **same** server-side polymorphism bug as ``get_todos()`` above:
        confirmed on the 0.6.1 stand gate (2026-08-21), ``GET
        /contractor/{id}/history`` also 500s with the identical ``There is no
        model class for bums\\crm\\api\\v03\\Entity\\Contractor`` error on
        this account. Unlike ``get_todos()``, these three methods are kept
        (not removed) pending a maintainer decision — do not assume they work
        on any given account; a caller should be prepared to catch
        ``ServerError`` here specifically, and this may need revisiting
        (removal, or a documented "known-broken" status) in a future release.
    """

    _page_content_type = ContentType.CONTRACTOR

    async def create(self, contractor_data: dict[str, Any]) -> Contractor:
        """Create a new contractor.

        Args:
            contractor_data: Contractor data dictionary.
                contentType: "ContractorCompany" or "ContractorHuman"
                Required fields vary by type.

        Returns:
            Created contractor.

        Examples:
            >>> # Create company
            >>> company_data = {
            ...     "contentType": "ContractorCompany",
            ...     "name": "Company Name",
            ...     "inn": "1234567890",
            ... }
            >>> contractor = await client.contractors.create(company_data)
        """
        path = self._build_path("api", "v3", "contractor")
        response = await self._http.post(path, json_data=contractor_data)
        data = response["data"]
        return self._parse_contractor_response(data)

    async def list(
        self,
        q: str | None = None,
        category_id: int | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Contractor]:
        """Get list of contractors.

        Warning: Pagination via page_after/page_before/page_with may not work properly
        for contractors due to API limitations. If you encounter 422 errors with pagination,
        use limit parameter and manual iteration instead.

        Note: BaseEntity objects in pagination parameters are automatically normalized
        to ensure correct format (id as int, contentType as string).

        Args:
            q: Search query (name, email, phone, INN).
            category_id: Filter by category ID.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
                Note: May not work due to API limitations.
            page_before: Load page strictly before this entity.
                Note: May not work due to API limitations.
            page_with: Load page containing this entity.
                Note: May not work due to API limitations.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of contractors.

        Examples:
            >>> # Search contractors by name
            >>> contractors = await client.contractors.list(q="Company")
            >>>
            >>> # Get contractors with limit (pagination may not work)
            >>> contractors = await client.contractors.list(limit=50)
        """
        path = self._build_path("api", "v3", "contractor")

        # Prepare contractor-specific parameters
        extra_params: dict[str, Any] = {}
        if q:
            extra_params["q"] = q
        if category_id:
            extra_params["category"] = {
                "id": category_id,
                "contentType": ContentType.CONTRACTOR_CATEGORY,
            }

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
            **extra_params,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        result: list[Contractor] = []
        for item in data:
            if isinstance(item, dict):
                result.append(self._parse_contractor_response(item))
            else:
                result.append(item)
        return result

    async def get(self, contractor_id: int) -> Contractor:
        """Get contractor by ID.

        Args:
            contractor_id: Contractor identifier.

        Returns:
            Contractor details.
        """
        path = self._build_path("api", "v3", "contractor", str(contractor_id))
        response = await self._http.get(path)
        return self._parse_contractor_response(response["data"])

    async def update(self, contractor_id: int, contractor_data: dict[str, Any]) -> Contractor:
        """Update contractor.

        Args:
            contractor_id: Contractor identifier.
            contractor_data: Updated contractor data.

        Returns:
            Updated contractor.
        """
        path = self._build_path("api", "v3", "contractor", str(contractor_id))
        response = await self._http.post(path, json_data=contractor_data)
        return self._parse_contractor_response(response["data"])

    async def iterate(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Contractor]:
        """Iterate over all contractors with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Contractor objects.

        Examples:
            >>> async for contractor in client.contractors.iterate():
            ...     print(contractor.name)
        """
        contractor: Contractor
        async for contractor in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.CONTRACTOR,
            self.list,
            limit,
            **kwargs,
        ):
            yield contractor

    async def get_deals(
        self,
        contractor_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Deal]:
        """Get deals associated with contractor.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of deals.

        Examples:
            >>> deals = await client.contractors.get_deals(contractor_id=123)
            >>> for deal in deals:
            ...     print(f"{deal.id}: {deal.name}")
        """
        path = self._build_path("api", "v3", "contractor", str(contractor_id), "deals")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        return await self._get_list(path, Deal, params)

    async def get_history(
        self,
        contractor_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> list[Any]:
        """Get the journal of a contractor.

        The stream is mixed: ``Changeset`` (field changes), ``BasedOnHistory``
        (link/unlink), comments, trigger logs. Known types are parsed; unknown
        ones are returned as raw dicts, so a new server-side type never breaks
        the call.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            raw: Return untouched payloads (pre-0.6.1 behaviour).

        Returns:
            Journal entries, newest first.

        Examples:
            >>> history = await client.contractors.get_history(contractor_id=123, limit=10)
        """
        entries = await self._get_entity_history(
            "contractor", contractor_id, limit, page_after, page_before, page_with
        )
        if raw:
            return list(entries)
        return [parse_history_entry(entry) for entry in entries]

    async def iterate_history(
        self,
        contractor_id: int,
        limit: int = 100,
        raw: bool = False,
    ) -> AsyncIterator[Any]:
        """Iterate the contractor's journal with automatic pagination.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of entries per page.
            raw: Yield untouched payloads instead of parsed entries.

        Yields:
            Journal entries, newest first.
        """
        async for entry in self._iterate_entity_history("contractor", contractor_id, limit, raw):
            yield entry

    async def get_link_events(
        self,
        contractor_id: int,
        since_id: int | None = None,
        since_time: str | None = None,
        limit: int = 100,
    ) -> list[LinkEvent]:
        """Get link/unlink events for a contractor.

        Megaplan has no webhook for linking (the app event streams only carry
        on_after_create/update/drop) and the contractor card exposes no list
        of related entities — only counters. The journal does record every
        link change, so this is the way to learn *which* link appeared or
        disappeared without diffing two states of the contractor.

        Args:
            contractor_id: Contractor identifier.
            since_id: Return only events newer than this event id — store the
                largest id seen to poll incrementally.
            since_time: Return only events created strictly after this
                ISO-8601 timestamp.
            limit: Number of journal entries fetched per page.

        Returns:
            Link events, newest first.

        Examples:
            >>> events = await client.contractors.get_link_events(contractor_id=66, since_id=1096)
            >>> for event in events:
            ...     verb = "отвязал" if event.unlink else "привязал"
            ...     print(verb, event.other.content_type, event.other.id)
        """
        return await self._get_link_events("contractor", contractor_id, since_id, since_time, limit)
