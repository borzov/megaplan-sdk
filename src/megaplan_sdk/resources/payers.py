"""Typed payer CRUD and reviewed updates."""

from __future__ import annotations

import builtins
from collections.abc import AsyncIterator
from os import PathLike
from typing import Any, Literal, overload

from megaplan_sdk.models.payer import Payer, PayerCreate, PayerPatch
from megaplan_sdk.models.update import UpdatePreview
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.updates import apply_update, normalize_patch, prepare_update


class PayersResource(BaseResource):
    """Work with requisites stored on payers, not directly on contractors."""

    _page_content_type: str | None = "Payer"

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
    ) -> list[Payer]:
        """List payers without assuming server-side INN filtering.

        Args:
            limit: Items per page.
            page_after: Cursor after the prior payer.
            page_before: Cursor before the requested page.
            page_with: Payer to include in the page.
            page: Page position replacing cursor parameters.
            fields: Additional fields.
            sort_by: Sort rules.
            only_requested_fields: Return only requested fields.

        Returns:
            Typed payers; unrequested fields can be absent.
        """
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
        return await self._get_list(self._build_path("api", "v3", "payer"), Payer, params)

    async def iterate(self, limit: int = 100, **kwargs: Any) -> AsyncIterator[Payer]:
        """Iterate payer pages, forwarding additional list parameters.

        Args:
            limit: Items per page.
            **kwargs: Additional list parameters.

        Yields:
            Typed payers.
        """
        payer: Payer
        async for payer in self._iterate_generic("Payer", self.list, limit, **kwargs):
            yield payer

    async def get(self, payer_id: int) -> Payer:
        """Read one payer by ID.

        Args:
            payer_id: Payer identifier.

        Returns:
            Typed payer.
        """
        return await self._get_entity("payer", payer_id, Payer)

    async def create(self, contractor_id: int, data: dict[str, Any] | PayerCreate) -> Payer:
        """Create a payer with required type and country.

        Args:
            contractor_id: Parent contractor identifier.
            data: Editable fields; type is Legal/Natural, country has a string ID.

        Returns:
            Created payer.

        Note:
            Network/5xx errors are not replayed: creation may already have
            succeeded. Inspect the contractor's payers before trying again.
            Account-specific aliases can be updated after get() confirms them.
        """
        payload = normalize_patch(data, PayerCreate)
        payload["contentType"] = "Payer"
        if isinstance(payload.get("country"), dict):
            payload["country"].setdefault("contentType", "Country")
        path = self._build_path("api", "v3", "contractor", str(contractor_id), "payers")
        response = await self._http.post(path, json_data=payload, retry_on_error=False)
        return Payer.model_validate(response["data"])

    @overload
    async def update(
        self, payer_id: int, data: dict[str, Any] | PayerPatch, *, dry_run: Literal[False] = False
    ) -> Payer: ...

    @overload
    async def update(
        self, payer_id: int, data: dict[str, Any] | PayerPatch, *, dry_run: Literal[True]
    ) -> UpdatePreview: ...

    @overload
    async def update(
        self, payer_id: int, data: dict[str, Any] | PayerPatch, *, dry_run: bool
    ) -> Payer | UpdatePreview: ...

    async def update(
        self,
        payer_id: int,
        data: dict[str, Any] | PayerPatch,
        *,
        dry_run: bool = False,
    ) -> Payer | UpdatePreview:
        """Validate a partial patch, or prepare a review without writing.

        Args:
            payer_id: Payer identifier.
            data: Explicitly supplied editable fields.
            dry_run: Return an UpdatePreview without POST.

        Returns:
            Updated payer or the reviewable preview.

        Note:
            Use dry_run plus apply_update for conflict checking and audit.
            Direct updates are not automatically retried on network/5xx errors.
            Unset values are omitted; explicit null is sent unchanged.
            Live clearing and partial-update semantics still need a stand check.
        """
        path = self._build_path("api", "v3", "payer", str(payer_id))
        preview = await prepare_update(self._http, path, payer_id, data, PayerPatch, ("Payer",))
        if dry_run:
            return preview
        payload = {**preview.patch, "contentType": "Payer"}
        response = await self._http.post(path, json_data=payload, retry_on_error=False)
        return Payer.model_validate(response["data"])

    async def apply_update(
        self,
        preview: UpdatePreview,
        *,
        audit_path: str | PathLike[str],
        actor: str,
    ) -> Payer:
        """Apply a reviewed payer patch with conflict checking and JSONL audit.

        Args:
            preview: Preview created by this account's payer resource.
            audit_path: Audit file in an existing local directory.
            actor: Operator identity supplied by the application.

        Returns:
            Updated payer, or fresh payer if no fields changed.

        Raises:
            UpdateConflictError: State changed; no POST was sent.
            UpdateAuditError: Audit failed after POST; outcome may be unknown.
            OSError: Intent audit failed before POST.

        Note:
            The final GET and POST are not atomic; there is no server lock.
        """
        path = self._build_path("api", "v3", "payer", str(preview.entity_id))
        response = await apply_update(
            self._http,
            path,
            preview,
            PayerPatch,
            ("Payer",),
            audit_path,
            actor,
        )
        return Payer.model_validate(response["data"])

    async def delete(self, payer_id: int) -> None:
        """Delete a payer by ID.

        Args:
            payer_id: Payer identifier.

        Note:
            This calls the server deletion endpoint; it is not a preview.
        """
        await self._delete_entity("payer", payer_id)

    async def extra_fields(
        self,
        country: str | None = None,
        payer_type: Literal["Legal", "Natural"] | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """Read dynamic field descriptions, whose IDs need not be API aliases.

        Args:
            country: Country ID, such as RU.
            payer_type: Legal or Natural, supplied together with country.

        Returns:
            Raw field definitions, retaining string identifiers and settings.

        Raises:
            ValueError: Only one selector, invalid type or unsafe country path.
        """
        if (country is None) != (payer_type is None):
            raise ValueError("Pass country and payer_type together")
        parts = ["api", "v3", "payer", "extraFields"]
        if country is not None:
            if not country.isalnum() or payer_type not in ("Legal", "Natural"):
                raise ValueError("Invalid country or payer_type")
            parts.extend((country, str(payer_type)))
        response = await self._http.get(self._build_path(*parts))
        return self._parse_list_response(response)
