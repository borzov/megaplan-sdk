"""Contractors resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.resources.base import BaseResource


class ContractorsResource(BaseResource):
    """Resource for working with contractors.

    Note:
        Contractor comments are not supported by Megaplan API (returns 500 error).
        Use action history or other entities for tracking contractor-related notes.
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
