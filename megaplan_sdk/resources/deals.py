"""Deals resource for Megaplan API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, overload

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.deal import Deal, DealFullDetails, ProgramState
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.full_details import FullDetailsMixin, RelatedDataConfig
from megaplan_sdk.types import FilterType


class DealsResource(BaseResource, FullDetailsMixin):
    """Resource for working with deals."""

    def __init__(self, http_client, cache=None):
        """Initialize deals resource."""
        super().__init__(http_client, cache)
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
                "responsible_details",
                "include_responsible_details",
                None,
                entity_field="responsible",
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
        """Custom fetcher for related tasks."""
        from megaplan_sdk.resources.tasks import TasksResource

        tasks_resource = TasksResource(self._http, cache=self._cache)
        filter_config = json.dumps(
            {"baseOn": {"contentType": ContentType.DEAL, "id": deal_id}}
        )
        return tasks_resource.list(filter=filter_config)

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
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
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
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
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
        base_on: dict[str, Any] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Deal] | list[DealFullDetails]:
        """Get list of deals.

        Args:
            filter: Trade filter (ID or config).
            status: Program state to filter by.
            q: Search query.
            base_on: Base entity for filtering.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["responsible", "contractor"]).
                Supported values: "responsible", "contractor".
                If provided, returns list[DealFullDetails] instead of list[Deal].

        Returns:
            List of deals (list[Deal] if expand is None, list[DealFullDetails] otherwise).

        Examples:
            >>> # Get deals without expansion
            >>> deals = await client.deals.list(limit=10)
            >>>
            >>> # Get deals with expanded responsible and contractor
            >>> deals_full = await client.deals.list(
            ...     limit=10, expand=["responsible", "contractor"]
            ... )
            >>> for deal_full in deals_full:
            ...     if deal_full.responsible_details:
            ...         print(deal_full.responsible_details.display_name())
            ...     if deal_full.contractor_details:
            ...         print(deal_full.contractor_details.display_name())
        """
        path = self._build_path("api", "v3", "deal")

        # Prepare deal-specific parameters
        extra_params: dict[str, Any] = {}
        if status:
            extra_params["status"] = (
                status.model_dump(by_alias=True) if hasattr(status, "model_dump") else status
            )
        if q:
            extra_params["q"] = q
        if base_on:
            extra_params["baseOn"] = base_on

        # Use base method to build params (DRY)
        params = self._build_list_params(
            filter=filter,
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            **extra_params,
        )

        # 1. Fetch deals
        deals = await self._get_list(path, Deal, params)

        # 2. If no expand, return as is
        if not expand or not deals:
            return deals

        # 3. Batch load related entities
        from megaplan_sdk.models.contractor import Contractor
        from megaplan_sdk.models.employee import Employee

        expand_config: dict[str, tuple[str, type, str]] = {
            "responsible": ("employee", Employee, ContentType.EMPLOYEE),
            "contractor": ("contractor", Contractor, ContentType.CONTRACTOR),
        }

        expanded = await self._expand_list_entities(deals, expand, expand_config)
        responsible_map = expanded.get("responsible", {})
        contractor_map = expanded.get("contractor", {})

        # 4. Build DealFullDetails objects
        results = []
        for deal in deals:
            resp_details = None
            contr_details = None

            if deal.responsible and deal.responsible.id in responsible_map:
                resp_details = responsible_map[deal.responsible.id]

            if deal.contractor and deal.contractor.id in contractor_map:
                contr_details = contractor_map[deal.contractor.id]

            results.append(
                DealFullDetails(
                    deal=deal,
                    responsible_details=resp_details,
                    contractor_details=contr_details,
                )
            )

        return results

    async def get(self, deal_id: int) -> Deal:
        """Get deal by ID.

        Args:
            deal_id: Deal identifier.

        Returns:
            Deal details.
        """
        return await self._get_entity("deal", deal_id, Deal)

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

    async def check_exists(self, deal_params: dict[str, Any]) -> bool:
        """Check if deal exists.

        Args:
            deal_params: Parameters to check.

        Returns:
            True if deal exists, False otherwise.
        """
        path = self._build_path("api", "v3", "deal", "checkDealExist")
        response = await self._http.post(path, json_data=deal_params)
        data: dict[str, Any] = response.get("data", {})
        exists: bool = data.get("exists", False)
        return exists

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

    async def create_comment(
        self,
        deal_id: int,
        text: str,
        attaches: list[dict[str, Any]] | None = None,
    ) -> Comment:
        """Create a comment for a deal.

        Args:
            deal_id: Deal identifier.
            text: Comment text.
            attaches: List of file attachments.

        Returns:
            Created comment.

        Examples:
            >>> comment = await client.deals.create_comment(
            ...     deal_id=123,
            ...     text="Deal update"
            ... )
        """
        return await self._create_entity_comment(
            "deal",
            deal_id,
            text,
            attaches,
        )

    async def get_auditors(
        self,
        deal_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
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
        path = self._build_path("api", "v3", "deal", str(deal_id), "auditors")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )

        response = await self._http.get(path, params=params if params else None)
        data: list[dict[str, Any]] = response.get("data", [])
        return data

    async def add_auditor(
        self,
        deal_id: int,
        auditor_id: int,
    ) -> dict[str, Any]:
        """Add auditor to the deal.

        Args:
            deal_id: Deal identifier.
            auditor_id: Auditor ID (Employee ID).

        Returns:
            Added auditor.

        Examples:
            >>> auditor = await client.deals.add_auditor(
            ...     deal_id=123,
            ...     auditor_id=456
            ... )
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "auditors")
        response = await self._http.post(path, json_data={"id": auditor_id})
        result: dict[str, Any] = response.get("data", {})
        return result

    async def remove_auditor(
        self,
        deal_id: int,
        auditor_id: int,
    ) -> None:
        """Remove auditor from the deal.

        Args:
            deal_id: Deal identifier.
            auditor_id: Auditor ID.

        Examples:
            >>> await client.deals.remove_auditor(deal_id=123, auditor_id=456)
        """
        path = self._build_path("api", "v3", "deal", str(deal_id), "auditors", str(auditor_id))
        await self._http.delete(path)

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
        include_responsible_details: bool = False,
        include_contractor_details: bool = False,
        include_related_tasks: bool = False,
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
            include_responsible_details: Load full responsible (Employee) details.
            include_contractor_details: Load full contractor details.
            include_related_tasks: Load tasks related to this deal.
            comments_limit: Limit for comments (if included).
            history_limit: Limit for history (if included).

        Returns:
            DealFullDetails object with all requested data.

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
        return await self._get_full_details_generic(
            entity_id=deal_id,
            entity_getter="get",
            full_details_class=DealFullDetails,
            config=self._full_details_config,
            main_entity_field="deal",
            include_comments=include_comments,
            include_history=include_history,
            include_status_history=include_status_history,
            include_auditors=include_auditors,
            include_responsible_details=include_responsible_details,
            include_contractor_details=include_contractor_details,
            include_related_tasks=include_related_tasks,
            comments_limit=comments_limit,
            history_limit=history_limit,
        )
