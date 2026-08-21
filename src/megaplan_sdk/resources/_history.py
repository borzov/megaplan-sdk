"""Entity journal generics shared by all resources that expose history.

`HistoryMixin` needs a handful of members from the `BaseResource` it is mixed
into (`_build_path`, `_build_list_params`, `_parse_list_response`, `_http`,
`_page_content_type`). Those stay defined on `BaseResource`; `_HistoryHost`
below is a structural `Protocol` used only to type `self` inside this mixin's
methods, so mypy strict can check attribute access without a runtime or
import-time dependency on `base.py`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Protocol

from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.history import BasedOnHistory, LinkEvent, parse_history_entry

if TYPE_CHECKING:
    from megaplan_sdk.http_client import HTTPClient


class _HistoryHost(Protocol):
    """Members `HistoryMixin` requires from the resource it is mixed into."""

    _http: HTTPClient
    _page_content_type: str | None

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

    async def _get_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    def _iterate_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 100,
        raw: bool = False,
    ) -> AsyncIterator[Any]: ...


class HistoryMixin:
    """Journal access for resources whose entity has /history in the API."""

    async def _get_entity_history(
        self: _HistoryHost,
        entity_type: str,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generic method to get history log for any entity.

        Args:
            entity_type: API resource type (e.g., "task", "project", "deal").
            entity_id: Entity identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of history entries.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "history")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )

        response = await self._http.get(path, params=params if params else None)
        return self._parse_list_response(response)

    async def _iterate_entity_history(
        self: _HistoryHost,
        entity_type: str,
        entity_id: int,
        limit: int = 100,
        raw: bool = False,
    ) -> AsyncIterator[Any]:
        """Iterate the whole journal of an entity, page by page.

        Args:
            entity_type: API resource type (e.g. "task", "deal").
            entity_id: Entity identifier.
            limit: Number of entries per page.
            raw: Yield untouched payloads instead of parsed entries.

        Yields:
            Journal entries, newest first — the server's default order for
            `GET .../history` (no `sort_by` is sent). Confirmed empirically
            against a live account's deal journal (monotonically descending
            `timeCreated` across 6 entries, 2026-08-21); not a documented API
            contract, so treat it as an observation, not a guarantee.
        """
        page_after: dict[str, Any] | None = None
        while True:
            page = await self._get_entity_history(entity_type, entity_id, limit, page_after)
            if not page:
                return
            for payload in page:
                yield payload if raw else parse_history_entry(payload)
            if len(page) < limit:
                return
            last = page[-1]
            last_id = last.get("id")
            if last_id is None:
                logger.warning("History entry without id during pagination; stopping")
                return
            page_after = {"contentType": last.get("contentType"), "id": last_id}

    async def _get_link_events(
        self: _HistoryHost,
        entity_type: str,
        entity_id: int,
        since_id: int | None = None,
        since_time: str | None = None,
        limit: int = 100,
    ) -> list[LinkEvent]:
        """Extract link/unlink events for an entity from its journal.

        The journal is the only place where a *single* link change is visible:
        the entity card exposes no list of related entities, so without this
        two states would have to be diffed (#link-tracking). Verified on the
        stand 2026-08-05: BasedOnHistory records appear on both sides of a link
        and carry ``unlink`` for removals.

        Args:
            entity_type: API resource type (e.g. "deal").
            entity_id: Entity identifier.
            since_id: Return only events with a larger BasedOnHistory id.
            since_time: Return only events created strictly after this
                ISO-8601 timestamp.
            limit: Number of journal entries per page.

        Returns:
            Link events, newest first — this method just filters the stream
            from `_iterate_entity_history`, in the order that method yields
            it (see its docstring; this description previously said "oldest
            page first", which contradicted every public facade and was
            simply wrong — confirmed newest-first empirically against a live
            account's deal journal on 2026-08-21). No `sort_by` is sent to
            the server for either call, so this is the server's default
            order, not a documented contract — do not rely on it holding
            across accounts or API versions; use `since_id`/`since_time` to
            poll incrementally instead of indexing into the result.
        """
        events: list[LinkEvent] = []
        async for entry in self._iterate_entity_history(entity_type, entity_id, limit):
            if not isinstance(entry, BasedOnHistory):
                continue
            if since_id is not None and (entry.id is None or entry.id <= since_id):
                continue
            if since_time is not None and (
                entry.time_created is None or entry.time_created.value <= since_time
            ):
                continue
            is_source = (
                entry.based_model is not None
                and entry.based_model.id == entity_id
                and entry.based_model.content_type == (self._page_content_type or "")
            )
            other = entry.generated_model if is_source else entry.based_model
            if other is None:
                continue
            events.append(
                LinkEvent(
                    id=entry.id,
                    time=entry.time_created,
                    user=entry.user,
                    unlink=entry.unlink,
                    other=other,
                    is_source=is_source,
                    description=entry.description,
                )
            )
        return events

    async def _search_entity_history(
        self: _HistoryHost,
        entity_type: str,
        entity_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generic method to search in entity history log.

        Args:
            entity_type: API resource type (e.g., "task", "project", "deal").
            entity_id: Entity identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of matching history entries.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "history", "search")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )
        params_dict: dict[str, Any] = params if params is not None else {}
        params_dict["q"] = query

        response = await self._http.get(path, params=params_dict)
        return self._parse_list_response(response)
