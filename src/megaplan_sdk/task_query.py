"""TaskQuery: a task list query validated at construction time.

Every rule ``tasks.list()`` enforces at call time (mutually exclusive
search/filter, valid statuses, sortable fields, filterable search fields)
fires here the moment the query is built — invalid queries never reach
the wire.
"""

from typing import Any

from megaplan_sdk.constants import (
    DEFAULT_SORT_RECENT,
    DEFAULT_TASK_LIST_FIELDS,
    UNSUPPORTED_TASK_FIELDS,
    UNSUPPORTED_TASK_SORT_FIELDS,
)
from megaplan_sdk.pagination import Page

# Valid task statuses according to RAML documentation
VALID_TASK_STATUSES = {
    "created",
    "assigned",
    "accepted",
    "done",
    "completed",
    "rejected",
    "cancelled",
    "expired",
    "delayed",
    "template",
    "overdue",
}

# Only these fields are filterable server-side for text search (#11)
SEARCHABLE_TASK_FIELDS = ("name", "statement")


def validate_task_statuses(statuses: list[str]) -> None:
    """Reject status values the API answers with a raw 422.

    Args:
        statuses: Status names to validate.

    Raises:
        ValueError: If any status is not a valid task status.
    """
    invalid = [s for s in statuses if s not in VALID_TASK_STATUSES]
    if invalid:
        raise ValueError(
            f"Invalid task status values: {invalid}. Valid values: {sorted(VALID_TASK_STATUSES)}"
        )


def validate_task_sort_field(field_name: str) -> None:
    """Reject sort fields the API answers with a raw 422 (#7).

    Args:
        field_name: Sort field name to validate.

    Raises:
        ValueError: If the field is unsupported, with the supported replacement.
    """
    if field_name in UNSUPPORTED_TASK_SORT_FIELDS:
        suggestion = UNSUPPORTED_TASK_SORT_FIELDS[field_name]
        raise ValueError(
            f"Task cannot be sorted by '{field_name}' (API returns 422). "
            f"Use '{suggestion}' instead — e.g. "
            f'sort_by=[{{"fieldName": "{suggestion}", "desc": True}}].'
        )


def validate_task_fields(fields: list[str]) -> None:
    """Reject ``fields`` values the API answers with a raw 422 (#32).

    Only known foreign-API synonyms are rejected (blacklist); unknown and
    custom category fields pass through — the pydantic model cannot serve
    as an allowlist (see ``UNSUPPORTED_TASK_FIELDS`` in constants).

    Args:
        fields: Field names requested via the ``fields`` parameter.

    Raises:
        ValueError: If a field is a known-unsupported synonym, with the
            real Task fields to use instead.
    """
    for field in fields:
        suggestions = UNSUPPORTED_TASK_FIELDS.get(field)
        if suggestions:
            raise ValueError(
                f"Task has no field '{field}' (API returns 422). "
                f"Did you mean: {', '.join(suggestions)}? "
                f"Commonly requested fields: {', '.join(DEFAULT_TASK_LIST_FIELDS)}."
            )


def validate_task_search_fields(fields: list[str]) -> None:
    """Reject search fields the server silently ignores (#11).

    Args:
        fields: Field names to search in.

    Raises:
        NotImplementedError: If any field is not filterable server-side.
    """
    invalid = [f for f in fields if f not in SEARCHABLE_TASK_FIELDS]
    if invalid:
        raise NotImplementedError(
            f"Server-side text filter on {invalid} is silently ignored by "
            f"Megaplan; only {list(SEARCHABLE_TASK_FIELDS)} work. (#11)"
        )


class TaskQuery:
    """Fluent, eagerly validated query for ``tasks.list_by()``.

    Examples:
        >>> query = (
        ...     TaskQuery()
        ...     .search("договор")
        ...     .statuses("assigned", "accepted")
        ...     .sort_by("timeCreated", desc=True)
        ...     .with_time_fields()
        ...     .limit(50)
        ... )
        >>> tasks = await client.tasks.list_by(query)

    Rules enforced at construction:
        - ``search()`` and ``filter()`` are mutually exclusive
        - statuses are checked against the valid set
        - sort fields the API rejects raise with the supported replacement
        - search fields the server silently ignores raise NotImplementedError
    """

    def __init__(self) -> None:
        self._q: str | None = None
        self._q_in: list[str] | None = None
        self._filter: Any | None = None
        self._statuses: list[str] | None = None
        self._sort_by: list[dict[str, Any]] | None = None
        self._fields: list[str] | None = None
        self._limit: int | None = None
        self._page: Page | None = None
        self._only_requested_fields: bool | None = None

    def search(self, q: str, in_: list[str] | None = None) -> "TaskQuery":
        """Full-text search by name (and optionally statement).

        Args:
            q: Search needle.
            in_: Fields to search in; subset of ``name``/``statement``.

        Raises:
            ValueError: If a filter is already set.
            NotImplementedError: If ``in_`` contains a non-filterable field.
        """
        if self._filter is not None:
            raise ValueError("Pass either search() or filter(), not both.")
        fields = in_ or ["name"]
        validate_task_search_fields(fields)
        self._q = q
        self._q_in = fields
        return self

    def filter(self, filter_ref: Any) -> "TaskQuery":
        """Use a saved filter (id, string id, or {contentType, id} link).

        Raises:
            ValueError: If a search is already set.
        """
        if self._q is not None:
            raise ValueError("Pass either search() or filter(), not both.")
        self._filter = filter_ref
        return self

    def statuses(self, *statuses: str) -> "TaskQuery":
        """Filter by task statuses (validated against the valid set)."""
        validate_task_statuses(list(statuses))
        self._statuses = list(statuses)
        return self

    def sort_by(self, field_name: str, desc: bool = False) -> "TaskQuery":
        """Sort by a field (validated against API-rejected fields)."""
        validate_task_sort_field(field_name)
        rule = {"contentType": "SortField", "fieldName": field_name, "desc": desc}
        self._sort_by = [*(self._sort_by or []), rule]
        return self

    def unsorted(self) -> "TaskQuery":
        """Opt out of the default newest-first sort (server's native order)."""
        self._sort_by = []
        return self

    def with_time_fields(self) -> "TaskQuery":
        """Request the date fields list endpoints omit by default (#8)."""
        existing = self._fields or []
        self._fields = existing + [f for f in DEFAULT_TASK_LIST_FIELDS if f not in existing]
        return self

    def fields(self, *fields: str) -> "TaskQuery":
        """Request additional fields (validated against API-rejected synonyms)."""
        validate_task_fields(list(fields))
        self._fields = [*(self._fields or []), *fields]
        return self

    def limit(self, limit: int) -> "TaskQuery":
        """Number of items per page."""
        self._limit = limit
        return self

    def page(self, page: Page) -> "TaskQuery":
        """Page position (see :class:`Page`)."""
        self._page = page
        return self

    def only_requested_fields(self, value: bool = True) -> "TaskQuery":
        """Return only the requested fields."""
        self._only_requested_fields = value
        return self

    def as_list_kwargs(self) -> dict[str, Any]:
        """Materialize the query as ``tasks.list()`` keyword arguments."""
        kwargs: dict[str, Any] = {}
        if self._q is not None:
            kwargs["q"] = self._q
            kwargs["q_in"] = self._q_in
        if self._filter is not None:
            kwargs["filter"] = self._filter
        if self._statuses is not None:
            kwargs["statuses"] = self._statuses
        if self._sort_by is not None:
            kwargs["sort_by"] = self._sort_by
        else:
            kwargs["sort_by"] = list(DEFAULT_SORT_RECENT)
        if self._fields is not None:
            kwargs["fields"] = self._fields
        if self._limit is not None:
            kwargs["limit"] = self._limit
        if self._page is not None:
            kwargs["page"] = self._page
        if self._only_requested_fields is not None:
            kwargs["only_requested_fields"] = self._only_requested_fields
        return kwargs
