"""Contractors resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.history import LinkEvent, parse_history_entry
from megaplan_sdk.models.todo import Todo
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource

# GET .../contractor/{id}/history and .../contractor/{id}/todos 500 server-side
# ("There is no model class for bums\crm\api\v03\Entity\Contractor") — the
# server cannot instantiate the abstract polymorphic Contractor type on these
# two routes. Confirmed on the live stand 2026-08-21: the concrete subtype
# route works (200, real data) for both subtypes:
#   GET /contractorCompany/{id}/history | /todos  -> 200
#   GET /contractorHuman/{id}/history   | /todos  -> 200
#   GET /contractor/{id}/history        | /todos  -> 500 (same entity, both subtypes)
# So the fix is picking the right path segment, not avoiding the routes.
_SUBTYPE_SEGMENTS: dict[str, str] = {
    "ContractorCompany": "contractorCompany",
    "ContractorHuman": "contractorHuman",
}


class ContractorsResource(BaseResource):
    """Resource for working with contractors.

    Note:
        Contractor comments are not supported by Megaplan API (returns 500 error).
        Use action history or other entities for tracking contractor-related notes.

    Note:
        ``get_todos()``, ``get_history()``, ``iterate_history()`` and
        ``get_link_events()`` all read/write a concrete subtype route
        (``contractorCompany``/``contractorHuman``), not the abstract
        ``contractor`` path — ``GET /contractor/{id}/history`` and
        ``/contractor/{id}/todos`` 500 server-side (``There is no model class
        for bums\\crm\\api\\v03\\Entity\\Contractor``; confirmed on a live
        account, tasks 12b and the 0.6.1 stand gate) because the server
        cannot instantiate the abstract polymorphic ``Contractor`` type on
        those two routes specifically. The concrete subtype route works
        (confirmed live 2026-08-21, both ``ContractorCompany`` and
        ``ContractorHuman``). Each of these four methods accepts an optional
        ``content_type`` — pass ``"ContractorCompany"``/``"ContractorHuman"``
        when you already know it (e.g. from a prior ``list()``/``get()``
        call, since ``Contractor.content_type`` carries it) to skip an extra
        lookup; otherwise the method calls ``get()`` once first to resolve it,
        at the cost of one extra request.
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

    async def _resolve_subtype(
        self, contractor_id: int, content_type: str | None
    ) -> tuple[str, str]:
        """Resolve the concrete path segment + contentType for one contractor.

        See the module-level comment above `_SUBTYPE_SEGMENTS` for why this
        exists: `GET /contractor/{id}/history|todos` 500s, the subtype route
        doesn't. Pass `content_type` when already known to skip the extra
        `get()` round trip this does otherwise.

        Raises:
            ValueError: `content_type` (given or resolved) is neither
                "ContractorCompany" nor "ContractorHuman".
        """
        if content_type is None:
            contractor = await self.get(contractor_id)
            content_type = contractor.content_type
        segment = _SUBTYPE_SEGMENTS.get(content_type)
        if segment is None:
            raise ValueError(
                f"Unknown contractor contentType {content_type!r} for contractor "
                f"#{contractor_id}; expected 'ContractorCompany' or 'ContractorHuman'"
            )
        return segment, content_type

    async def get_todos(
        self,
        contractor_id: int,
        limit: int | None = None,
        content_type: str | None = None,
    ) -> list[Todo]:
        """Get todos attached to this contractor.

        Unlike `deals`/`tasks`/`projects`/`employees`, this goes through the
        concrete subtype route (`contractorCompany`/`contractorHuman`), not
        `contractor` — see the class docstring. Confirmed live 2026-08-21 on
        both subtypes.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of items per page.
            content_type: "ContractorCompany" or "ContractorHuman" if already
                known (e.g. from a prior `list()`/`get()`), to skip an extra
                lookup. Resolved via `get()` otherwise.

        Returns:
            Todos of the contractor.
        """
        segment, _ = await self._resolve_subtype(contractor_id, content_type)
        return await self._get_entity_todos(segment, contractor_id, limit)

    async def get_history(
        self,
        contractor_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        raw: bool = False,
        content_type: str | None = None,
    ) -> list[Any]:
        """Get the journal of a contractor.

        The stream is mixed: ``Changeset`` (field changes), ``BasedOnHistory``
        (link/unlink), comments, trigger logs. Known types are parsed; unknown
        ones are returned as raw dicts, so a new server-side type never breaks
        the call. Goes through the concrete subtype route — see the class
        docstring.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            raw: Return untouched payloads (pre-0.6.1 behaviour).
            content_type: "ContractorCompany" or "ContractorHuman" if already
                known, to skip an extra `get()` lookup.

        Returns:
            Journal entries, newest first.

        Examples:
            >>> history = await client.contractors.get_history(contractor_id=123, limit=10)
        """
        segment, _ = await self._resolve_subtype(contractor_id, content_type)
        entries = await self._get_entity_history(
            segment, contractor_id, limit, page_after, page_before, page_with
        )
        if raw:
            return list(entries)
        return [parse_history_entry(entry) for entry in entries]

    async def search_history(
        self,
        contractor_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        content_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search in contractor history log.

        Routed through the concrete subtype: the abstract ``/contractor/{id}``
        path returns 500 for history and todos, while
        ``/contractorCompany``/``/contractorHuman`` work (see the class
        docstring).

        Args:
            contractor_id: Contractor identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            content_type: "ContractorCompany" or "ContractorHuman" if already
                known; saves one lookup request.

        Returns:
            List of matching history entries.

        Raises:
            ValueError: The resolved contentType is neither known subtype.
        """
        segment, _ = await self._resolve_subtype(contractor_id, content_type)
        return await self._search_entity_history(
            segment, contractor_id, query, limit, page_after, page_before, page_with
        )

    async def iterate_history(
        self,
        contractor_id: int,
        limit: int = 100,
        raw: bool = False,
        content_type: str | None = None,
    ) -> AsyncIterator[Any]:
        """Iterate the contractor's journal with automatic pagination.

        Goes through the concrete subtype route — see the class docstring.

        Args:
            contractor_id: Contractor identifier.
            limit: Number of entries per page.
            raw: Yield untouched payloads instead of parsed entries.
            content_type: "ContractorCompany" or "ContractorHuman" if already
                known, to skip an extra `get()` lookup.

        Yields:
            Journal entries, newest first.
        """
        segment, _ = await self._resolve_subtype(contractor_id, content_type)
        async for entry in self._iterate_entity_history(segment, contractor_id, limit, raw):
            yield entry

    async def get_link_events(
        self,
        contractor_id: int,
        since_id: int | None = None,
        since_time: str | None = None,
        limit: int = 100,
        content_type: str | None = None,
    ) -> list[LinkEvent]:
        """Get link/unlink events for a contractor.

        Megaplan has no webhook for linking (the app event streams only carry
        on_after_create/update/drop) and the contractor card exposes no list
        of related entities — only counters. The journal does record every
        link change, so this is the way to learn *which* link appeared or
        disappeared without diffing two states of the contractor. Goes
        through the concrete subtype route — see the class docstring.

        Args:
            contractor_id: Contractor identifier.
            since_id: Return only events newer than this event id — store the
                largest id seen to poll incrementally.
            since_time: Return only events created strictly after this
                ISO-8601 timestamp.
            limit: Number of journal entries fetched per page.
            content_type: "ContractorCompany" or "ContractorHuman" if already
                known, to skip an extra `get()` lookup.

        Returns:
            Link events, newest first.

        Examples:
            >>> events = await client.contractors.get_link_events(contractor_id=66, since_id=1096)
            >>> for event in events:
            ...     verb = "отвязал" if event.unlink else "привязал"
            ...     print(verb, event.other.content_type, event.other.id)
        """
        segment, resolved_content_type = await self._resolve_subtype(contractor_id, content_type)
        return await self._get_link_events(
            segment,
            contractor_id,
            since_id,
            since_time,
            limit,
            entity_content_type=resolved_content_type,
        )
