"""List-query parameter building shared by every resource.

`ListParamsMixin` needs a handful of members from the `BaseResource` it is
mixed into (`_page_content_type`, `_normalize_base_entity`). Those stay
defined on `BaseResource`; `_ListParamsHost` below is a structural `Protocol`
used only to type `self` inside this mixin's methods, so mypy strict can check
attribute access without a runtime or import-time dependency on `base.py`.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol


class _ListParamsHost(Protocol):
    """Members `ListParamsMixin` requires from the resource it is mixed into."""

    _page_content_type: str | None
    _UNSUPPORTED_LIST_FIELDS: ClassVar[dict[str, tuple[str, ...]]]
    _Q_ALLOWED_FIELDS: tuple[str, ...]
    _filter_content_type: str | None
    _default_sort: ClassVar[list[dict[str, str]]]

    def _normalize_base_entity(self, entity: dict[str, Any] | Any) -> dict[str, Any]: ...

    def _coerce_page_ref(
        self,
        value: Any,
        default_content_type: str | None = None,
    ) -> Any: ...

    def _q_to_filter(self, filter_content_type: str, q: str, q_in: list[str]) -> dict[str, Any]: ...


class ListParamsMixin:
    """Query-parameter assembly for the list endpoints every resource shares."""

    # Field names this resource's list endpoint rejects with a raw 422, mapped
    # to the fields to suggest instead. A blacklist, not an allowlist: custom
    # category fields are unknowable in advance and must pass through.
    _UNSUPPORTED_LIST_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = {}

    def _validate_list_fields(self: _ListParamsHost, fields: Any | None) -> None:
        """Reject ``fields=`` values the list endpoint answers with a raw 422.

        Args:
            fields: Value passed to ``list(fields=...)``.

        Raises:
            ValueError: If a field is known-unsupported, naming the fields to
                use instead and where the data is available.
        """
        if not fields or not isinstance(fields, list | tuple):
            return
        entity = self._page_content_type or type(self).__name__
        for field in fields:
            if not isinstance(field, str):
                continue
            suggestions = self._UNSUPPORTED_LIST_FIELDS.get(field)
            if suggestions:
                raise ValueError(
                    f"{entity} list endpoint has no field '{field}' (API returns 422). "
                    f"Did you mean: {', '.join(suggestions)}? "
                    f"Card-only data is available via get()."
                )

    def _coerce_page_ref(
        self: _ListParamsHost,
        value: Any,
        default_content_type: str | None = None,
    ) -> Any:
        """Normalize a pagination ref to the server's ``{contentType, id}`` link (#23).

        The server requires an entity link, not a bare id or a full model dump.
        Accepts an ``int`` id, a Pydantic model / object with ``id``, or a dict;
        fills in ``contentType`` from the model or the resource default when the
        caller did not supply it.

        Args:
            value: ``int`` id, entity/model, dict link, or None.
            default_content_type: Fallback contentType (resource's entity type).

        Returns:
            A clean ``{"contentType": ..., "id": int}`` dict, or the value
            unchanged if it cannot be interpreted.
        """
        if value is None:
            return None
        ct = default_content_type or self._page_content_type
        # Entity / Pydantic model with an id → clean link (NOT a full dump, which
        # carries extra fields the server rejects with 422).
        if not isinstance(value, dict | int) and hasattr(value, "id"):
            model_ct = getattr(value, "content_type", None) or getattr(value, "contentType", None)
            return {"contentType": model_ct or ct, "id": value.id}
        if isinstance(value, bool):  # guard: bool is an int subclass
            return value
        if isinstance(value, int):
            return {"contentType": ct, "id": value}
        if isinstance(value, dict):
            link = dict(value)
            if "id" in link and isinstance(link["id"], str):
                try:
                    link["id"] = int(link["id"])
                except (ValueError, TypeError):
                    pass
            if "contentType" not in link and ct:
                link["contentType"] = ct
            return link
        return value

    def _build_list_params(
        self: _ListParamsHost,
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
    ) -> dict[str, Any]:
        """Build standard list parameters for pagination and filtering.

        Args:
            filter: Filter ID or configuration.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            page: Page position; replaces the page_after/page_before/page_with
                trio. Passing both raises ValueError.
            **extra_params: Additional parameters (e.g., statuses, status, q).

        Returns:
            Dictionary with non-None parameters.
        """
        if page is not None:
            if page_after is not None or page_before is not None or page_with is not None:
                raise ValueError("Pass either page= or page_after/page_before/page_with, not both.")
            page_after, page_before, page_with = page.after, page.before, page.with_

        params: dict[str, Any] = {}

        if filter is not None:
            params["filter"] = filter
        if limit is not None:
            params["limit"] = limit
        if page_after is not None:
            params["pageAfter"] = self._coerce_page_ref(page_after, page_content_type)
        if page_before is not None:
            params["pageBefore"] = self._coerce_page_ref(page_before, page_content_type)
        if page_with is not None:
            params["pageWith"] = self._coerce_page_ref(page_with, page_content_type)
        if fields is not None:
            params["fields"] = fields
        if sort_by:
            params["sortBy"] = sort_by
        if only_requested_fields is not None:
            params["onlyRequestedFields"] = only_requested_fields

        # Add extra params (like statuses, status, q, baseOn, etc.)
        # Filter out None values to avoid sending null in JSON
        filtered_extra = {k: v for k, v in extra_params.items() if v is not None}

        # Normalize BaseEntity in extra params (e.g., baseOn)
        for key, value in filtered_extra.items():
            if key in ("baseOn", "base_on") and isinstance(value, dict):
                params[key if key == "baseOn" else "baseOn"] = self._normalize_base_entity(value)
            else:
                params[key] = value

        return params if params else {}

    _Q_ALLOWED_FIELDS = ("name", "statement")

    # Content type of the filter a free-text `q` becomes. None = this resource
    # does not opt into the shared list-query policy.
    _filter_content_type: str | None = None

    # Default sort applied when list() is called without sort_by. Empty = no
    # default; a caller passing sort_by=[] opts out explicitly.
    _default_sort: ClassVar[list[dict[str, str]]] = []

    def _apply_list_defaults(
        self: _ListParamsHost,
        filter: Any | None,
        q: str | None,
        q_in: list[str] | None,
        sort_by: list[dict[str, str]] | None,
    ) -> tuple[Any | None, str | None, list[dict[str, str]] | None]:
        """Apply the list-query policy shared by resources that opt in.

        A resource opts in by setting `_filter_content_type` (enables `q`) and
        `_default_sort` (enables the default ordering). `sort_by=[]` is an
        explicit opt-out and is preserved as-is.
        """
        if sort_by is None and self._default_sort:
            sort_by = list(self._default_sort)
        if q is not None:
            if filter is not None:
                raise ValueError("Pass either `q` or `filter`, not both.")
            filter = self._q_to_filter(self._filter_content_type, q, q_in or ["name"])
            q = None
        return filter, q, sort_by

    def _q_to_filter(
        self: _ListParamsHost, filter_content_type: str, q: str, q_in: list[str]
    ) -> dict[str, Any]:
        """Convert a free-text query into a FilterBuilder filter.

        Megaplan ignores a raw ``q`` param (it is not in the RAML), so a
        ``q=`` that the user expects to search silently returns 0 (#11).
        Only ``name`` and ``statement`` are filterable server-side; other
        text fields (``description``/``subject``/...) are silently ignored.
        Subclasses may narrow ``_Q_ALLOWED_FIELDS`` further for entities that
        don't have all of these fields (e.g. ``Todo`` has no ``statement``).

        Args:
            filter_content_type: e.g. ``"TaskFilter"`` / ``"TradeFilter"``.
            q: Search needle.
            q_in: Fields to search; subset of ``name``/``statement``.

        Returns:
            A filter dict ready for the ``filter`` query param.

        Raises:
            NotImplementedError: If ``q_in`` contains a non-filterable field.
        """
        from megaplan_sdk.filter_builder import FilterBuilder

        invalid = [f for f in q_in if f not in self._Q_ALLOWED_FIELDS]
        if invalid:
            raise NotImplementedError(
                f"Server-side text filter on {invalid} is silently ignored by "
                f"Megaplan; only {list(self._Q_ALLOWED_FIELDS)} work. (#11)"
            )
        builder = FilterBuilder(filter_content_type)
        for i, field_name in enumerate(q_in):
            if i:
                builder.or_()
            builder.field(field_name).contains(q)
        return builder.build()
