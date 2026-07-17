"""Deals resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast, overload

from megaplan_sdk.constants import DEFAULT_SORT_RECENT, ContentType
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.deal import Deal, DealFullDetails, ProgramState
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.pagination import Page
from megaplan_sdk.registry import filter_content_type_for
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.full_details import FullDetailsMixin, RelatedDataConfig
from megaplan_sdk.types import FilterType


class DealsResource(BaseResource, FullDetailsMixin):
    """Resource for working with deals."""

    _page_content_type = ContentType.DEAL
    _filter_content_type = filter_content_type_for("deal")

    _expand_rules = {
        "manager": ExpandRule("employee", Employee, details_field="manager_details"),
        "contractor": ExpandRule("contractor", Contractor, details_field="contractor_details"),
    }
    _details_model = DealFullDetails
    _main_field = "deal"

    def __init__(
        self,
        http_client,
        cache=None,
        default_comments_limit: int | None = None,
        default_history_limit: int | None = None,
    ):
        """Initialize deals resource.

        Args:
            http_client: HTTP client for making requests.
            cache: Optional entity cache.
            default_comments_limit: Default limit for comments in get_full_details().
            default_history_limit: Default limit for history in get_full_details().
        """
        super().__init__(
            http_client,
            cache=cache,
            default_comments_limit=default_comments_limit,
            default_history_limit=default_history_limit,
        )
        # Define config after __init__ to avoid circular import
        self._full_details_config = [
            RelatedDataConfig(
                "comments", "include_comments", "get_comments", limit_param="comments_limit"
            ),
            RelatedDataConfig(
                "history", "include_history", "get_history", limit_param="history_limit"
            ),
            RelatedDataConfig("status_history", "include_status_history", "get_status_history"),
            RelatedDataConfig("auditors", "include_auditors", "get_auditors"),
            RelatedDataConfig(
                "manager_details",
                "include_manager_details",
                None,
                entity_field="manager",
                entity_type="employee",
            ),
            RelatedDataConfig(
                "contractor_details",
                "include_contractor_details",
                None,
                entity_field="contractor",
                entity_type="contractor",
            ),
            RelatedDataConfig(
                "related_tasks",
                "include_related_tasks",
                None,
                custom_fetcher=self._fetch_related_tasks,
            ),
        ]

    async def _fetch_related_tasks(self, deal_id: int, **kwargs: Any) -> Any:
        """Related tasks cannot be fetched — the API has no tasks-by-deal filter.

        Verified empirically (2026-07-02): every baseOn wire format is either
        silently ignored (the endpoint returns ALL account tasks) or rejected
        with 422; the server reports Task has no deal/trade/baseOn fields, and
        the deal side exposes only tasksCount. The previous implementation
        silently returned unrelated tasks.
        """
        raise NotImplementedError(
            "Megaplan API has no working tasks-by-deal (baseOn) filter: object "
            "configs are silently ignored and string configs are rejected with "
            "422. include_related_tasks previously returned ALL account tasks. "
            "Use deal.tasksCount for the count; there is no way to list the tasks."
        )

    async def create(self, deal_data: dict[str, Any]) -> Deal:
        """Create a new deal.

        Args:
            deal_data: Deal data dictionary.

        Returns:
            Created deal.
        """
        return await self._create_entity("deal", deal_data, Deal)

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        status: ProgramState | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: None = None,
    ) -> list[Deal]: ...

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        status: ProgramState | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str],
    ) -> list[DealFullDetails]: ...

    async def list(
        self,
        filter: FilterType | None = None,
        status: ProgramState | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Deal] | list[DealFullDetails]:
        """Get list of deals.

        Args:
            filter: Trade filter (ID or config).
            status: Program state to filter by.
            q: Text search by name (converted to a server-side name filter; #11).
                Use q_in=["name", "statement"] to also match statement.
                Other fields are silently ignored by the API.
                Cannot be combined with ``filter`` — raises ValueError.
            q_in: Fields to search within when ``q`` is provided (default: ["name"]).
                Allowed values: "name", "statement".
                Other values raise NotImplementedError (silently ignored by server).
            base_on: Base entity for filtering.
                Warning: This parameter may return 422 ValidationError due to API limitations.
                Format: {"contentType": "Contractor", "id": 123} (id should be int, not string).
                BaseEntity objects are automatically normalized to ensure correct format.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to request from the API.
                Must use actual API field names: ``manager``, ``price``,
                ``timeCreated``, ``timeUpdated``, ``number``, ``cost``, ``debt``,
                ``result``, ``shortDescription``, ``stateTimeUpdated``.

                **Linked entities** (owner/responsible/manager/contractor):
                the server deduplicates repeated entities within one response,
                so ``fields=`` fills them only at the first occurrence per
                page — repeats come back as bare references without ``name``
                (#36). Use ``expand=`` when you need them fully populated.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["manager", "contractor"]).
                Supported values: "manager", "contractor".
                If provided, returns list[DealFullDetails] instead of list[Deal].

        Returns:
            List of deals (list[Deal] if expand is None, list[DealFullDetails] otherwise).

        Examples:
            >>> # Get deals without expansion
            >>> deals = await client.deals.list(limit=10)
            >>>
            >>> # Get deals with expanded manager and contractor
            >>> deals_full = await client.deals.list(
            ...     limit=10, expand=["manager", "contractor"]
            ... )
            >>> for deal_full in deals_full:
            ...     if deal_full.manager_details:
            ...         print(deal_full.manager_details.display_name())
            ...     if deal_full.contractor_details:
            ...         print(deal_full.contractor_details.display_name())
        """
        path = self._build_path("api", "v3", "deal")

        # #14: default to newest-first; sort_by=[] opts out.
        if sort_by is None:
            sort_by = list(DEFAULT_SORT_RECENT)

        # #11: raw `q` is ignored server-side; convert to a real name filter.
        if q is not None:
            if filter is not None:
                raise ValueError("Pass either `q` or `filter`, not both.")
            filter = self._q_to_filter(self._filter_content_type, q, q_in or ["name"])
            q = None

        # Convert filter ID to object format if needed
        processed_filter = filter
        if filter is not None and isinstance(filter, int | str) and not isinstance(filter, dict):
            # Convert ID to filter object format
            processed_filter = {"contentType": self._filter_content_type, "id": str(filter)}

        # Prepare deal-specific parameters
        extra_params: dict[str, Any] = {}
        if status:
            extra_params["status"] = (
                status.model_dump(by_alias=True) if hasattr(status, "model_dump") else status
            )
        if base_on:
            extra_params["baseOn"] = base_on

        # Use base method to build params (DRY)
        params = self._build_list_params(
            filter=processed_filter,
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

        deals = await self._get_list(path, Deal, params)
        self._warn_reduced_linked_fields(deals, fields, expand)
        return await self._expand_and_wrap(deals, expand)

    async def get(self, deal_id: int, fields: list[str] | None = None) -> Deal:
        """Get deal by ID.

        Args:
            deal_id: Deal identifier.
            fields: Extra fields to request (e.g. ``["commentsCount"]``).

        Returns:
            Deal details.
        """
        return await self._get_entity("deal", deal_id, Deal, fields=fields)

    async def get_many(self, ids: list[int], use_cache: bool = True) -> dict[int, Deal]:
        """Batch-fetch deals by id via the bulk endpoint (#FR-1).

        Args:
            ids: Deal ids to load (duplicates ignored).
            use_cache: Read/populate the entity cache (default: True).

        Returns:
            Dict mapping id -> Deal. Inaccessible ids are absent.
        """
        return await self._get_many_via_bulk(ContentType.DEAL, ids, Deal, use_cache)

    async def update(self, deal_id: int, deal_data: dict[str, Any]) -> Deal:
        """Update deal.

        Args:
            deal_id: Deal identifier.
            deal_data: Updated deal data.

        Returns:
            Updated deal.
        """
        return await self._update_entity("deal", deal_id, deal_data, Deal)

    async def delete(self, deal_id: int) -> None:
        """Delete deal.

        Args:
            deal_id: Deal identifier.
        """
        await self._delete_entity("deal", deal_id)

    async def apply_transition(self, deal_id: int, transition_id: int) -> Deal:
        """Apply transition to deal (change status).

        Args:
            deal_id: Deal identifier.
            transition_id: Transition identifier.

        Returns:
            Updated deal.
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "applyTransition")
        response = await self._http.post(path, json_data={"transition": transition_id})
        return Deal(**response["data"])

    async def apply_trigger(self, deal_id: int, trigger_id: int) -> Deal:
        """Apply trigger to deal.

        Args:
            deal_id: Deal identifier.
            trigger_id: Trigger identifier.

        Returns:
            Updated deal.
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "applyTrigger")
        response = await self._http.post(path, json_data={"trigger": trigger_id})
        return Deal(**response["data"])

    async def get_status_history(self, deal_id: int) -> list[dict[str, Any]]:
        """Get status change history for deal.

        Args:
            deal_id: Deal identifier.

        Returns:
            List of status history entries.
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "statusHistory")
        response = await self._http.get(path)
        data: list[dict[str, Any]] = response.get("data", [])
        return data

    async def check_exists(
        self,
        filter: FilterType | None = None,
        status: ProgramState | dict[str, Any] | None = None,
        query: str | None = None,
        deal: dict[str, Any] | None = None,
    ) -> bool:
        """Check if deal exists.

        Uses GET request with parameters in query string as per API documentation.

        Warning: This endpoint may return 500 Internal Server Error due to API limitations.
        The error is handled gracefully and False is returned.

        Args:
            filter: Trade filter (ID or config).
                If ID (int/str), will be converted to BaseEntity format.
            status: Program state to filter by (ProgramState object or dict).
            query: Search query string.
            deal: Deal object with fields to match.
                Nested BaseEntity objects (e.g., contractor) are automatically normalized.
                Format: {"name": "Deal name", "contractor": {"contentType": "Contractor", "id": 123}}

        Returns:
            True if deal exists, False otherwise (or if API returns 500 error).

        Examples:
            >>> # Check by query
            >>> exists = await client.deals.check_exists(query="Deal name")
            >>>
            >>> # Check by deal object
            >>> exists = await client.deals.check_exists(
            ...     deal={"name": "Deal name", "contractor": {"contentType": "Contractor", "id": 123}}
            ... )
            >>>
            >>> # Check by filter ID
            >>> exists = await client.deals.check_exists(filter=123)
            >>>
            >>> # Check by filter object
            >>> exists = await client.deals.check_exists(
            ...     filter={"contentType": "TradeFilter", "id": "my_filter"}
            ... )
        """
        path = self._build_path("api", "v3", "deal", "checkDealExist")
        params: dict[str, Any] = {}

        # Normalize filter parameter
        if filter is not None:
            if isinstance(filter, int | str):
                params["filter"] = {
                    "contentType": self._filter_content_type,
                    "id": int(filter) if str(filter).isdigit() else str(filter),
                }
            else:
                params["filter"] = filter

        # Normalize status parameter
        if status:
            params["status"] = (
                status.model_dump(by_alias=True) if hasattr(status, "model_dump") else status
            )

        # Add query parameter
        if query:
            params["query"] = query

        # Normalize deal parameter
        if deal:
            if hasattr(deal, "model_dump"):
                params["deal"] = deal.model_dump(by_alias=True)
            elif isinstance(deal, dict):
                normalized_deal = {
                    key: self._normalize_base_entity(value)
                    if isinstance(value, dict) and "contentType" in value
                    else value
                    for key, value in deal.items()
                }
                params["deal"] = normalized_deal
            else:
                params["deal"] = deal

        # Execute API call with error handling
        try:
            response = await self._http.get(path, params=params if params else None)
            return response.get("data", {}).get("exists", False)
        except Exception as e:
            from megaplan_sdk.exceptions import ServerError
            from megaplan_sdk.logging_config import logger

            if isinstance(e, ServerError) and "500" in str(e):
                logger.warning(
                    "check_exists endpoint returned 500. "
                    "This is a known API limitation. Returning False."
                )
                return False
            raise

    async def iterate(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Deal]:
        """Iterate over all deals with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Deal objects.
        """
        deal: Deal
        async for deal in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.DEAL,
            self.list,
            limit,
            **kwargs,
        ):
            yield deal

    async def get_comments(
        self,
        deal_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Comment]:
        """Get comments for a deal.

        Args:
            deal_id: Deal identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of comments.

        Examples:
            >>> comments = await client.deals.get_comments(deal_id=123)
        """
        return await self._get_entity_comments(
            "deal",
            deal_id,
            limit,
            page_after,
            page_before,
            page_with,
        )

    async def get_auditors(
        self,
        deal_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get auditors for a deal.

        Args:
            deal_id: Deal identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of auditors.

        Examples:
            >>> auditors = await client.deals.get_auditors(deal_id=123)
        """
        return await self._get_entity_related_list(
            "deal", deal_id, "auditors", limit, page_after, page_before, page_with
        )

    async def add_auditor(
        self,
        deal_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> Any:
        """Add auditor to the deal.

        Args:
            deal_id: Deal identifier.
            auditor_id: Auditor ID (Employee ID).
            auditor_content_type: Content type (usually "Employee").

        Returns:
            Added auditor.

        Examples:
            >>> auditor = await client.deals.add_auditor(
            ...     deal_id=123,
            ...     auditor_id=456
            ... )
        """
        return await self._add_entity_related(
            "deal", deal_id, "auditors", auditor_id, auditor_content_type
        )

    async def remove_auditor(
        self,
        deal_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Remove auditor from the deal.

        Args:
            deal_id: Deal identifier.
            auditor_id: Auditor ID.
            auditor_content_type: Content type (usually "Employee").

        Examples:
            >>> await client.deals.remove_auditor(deal_id=123, auditor_id=456)
        """
        await self._remove_entity_related(
            "deal",
            deal_id,
            "auditors",
            auditor_id,
            auditor_content_type,
            # API irregularity: /deal/{id}/auditors/{auditorId} — no contentType
            content_type_in_path=False,
        )

    async def get_history(
        self,
        deal_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get history log for a deal.

        Args:
            deal_id: Deal identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of history entries.

        Examples:
            >>> history = await client.deals.get_history(deal_id=123, limit=10)
        """
        return await self._get_entity_history(
            "deal", deal_id, limit, page_after, page_before, page_with
        )

    async def search_history(
        self,
        deal_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search in deal history log.

        Args:
            deal_id: Deal identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of matching history entries.

        Examples:
            >>> results = await client.deals.search_history(deal_id=123, query="transition")
        """
        return await self._search_entity_history(
            "deal", deal_id, query, limit, page_after, page_before, page_with
        )

    async def get_full_details(
        self,
        deal_id: int,
        include_comments: bool = False,
        include_history: bool = False,
        include_status_history: bool = False,
        include_auditors: bool = False,
        include_manager_details: bool = False,
        include_contractor_details: bool = False,
        include_related_tasks: bool = False,
        resolve_participants: bool = True,
        comments_limit: int | None = None,
        history_limit: int | None = None,
    ) -> DealFullDetails:
        """Get full deal details with related entities.

        This method fetches the deal and optionally loads related data in parallel
        for better performance.

        Args:
            deal_id: Deal identifier.
            include_comments: Load deal comments.
            include_history: Load change history.
            include_status_history: Load status change history.
            include_auditors: Load auditors list.
            include_manager_details: Load full manager (responsible Employee) details.
            include_contractor_details: Load full contractor details.
            include_related_tasks: Load tasks related to this deal.
            resolve_participants: Resolve ``auditors`` to full Employee
                objects via one cached batch (#35). On by default —
                participant lists are small (3-8 entries) and the
                related-list endpoint returns bare references otherwise.
                Pass False to keep the raw references.
            comments_limit: Limit for comments (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: comments_limit=50 returns max 50 comments.
                Requires the matching include_* flag to be True; passing a
                limit without it raises ValueError.
                Note: the API caps a single comments page (~100); requesting
                more returns at most one server page. Use client.comments.iterate
                for full pagination.
            history_limit: Limit for history (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: history_limit=100 returns max 100 history entries.
                Requires the matching include_* flag to be True; passing a
                limit without it raises ValueError.

        Returns:
            DealFullDetails object with all requested data.

        Note:
            The card is requested with ``fields=["commentsCount"]`` so
            ``details.comments_count`` is populated regardless of
            ``comments_limit`` (#34). ``len(details.comments) <
            details.comments_count`` reliably signals truncation.

        Examples:
            >>> # Get deal with comments and history
            >>> details = await client.deals.get_full_details(
            ...     deal_id=123,
            ...     include_comments=True,
            ...     include_history=True,
            ...     comments_limit=50
            ... )
            >>> print(details.deal.name)
            >>> print(len(details.comments))
        """
        details = cast(
            DealFullDetails,
            await self._get_full_details_generic(
                entity_id=deal_id,
                entity_getter="get",
                full_details_class=DealFullDetails,
                config=self._full_details_config,
                main_entity_field="deal",
                entity_getter_kwargs={"fields": ["commentsCount"]},
                include_comments=include_comments,
                include_history=include_history,
                include_status_history=include_status_history,
                include_auditors=include_auditors,
                include_manager_details=include_manager_details,
                include_contractor_details=include_contractor_details,
                include_related_tasks=include_related_tasks,
                comments_limit=comments_limit,
                history_limit=history_limit,
            ),
        )
        if resolve_participants and details.auditors:
            details.auditors = await self._resolve_employee_entities(details.auditors)
        return details

    async def get_all_participants(
        self,
        deal_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Employee]:
        """Get all participants of a deal.

        Returns complete list of participants including responsible and
        auditors in a single request.

        Note: Unlike tasks and projects, deals only return Employee participants
        (no ContractorHuman or Group).

        Args:
            deal_id: Deal identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of Employee participants.

        Examples:
            >>> participants = await client.deals.get_all_participants(deal_id=123)
            >>> for employee in participants:
            ...     print(employee.display_name())
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "allParticipants")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        return await self._get_list(path, Employee, params if params else None)
