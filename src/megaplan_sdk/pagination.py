"""Pagination types for Megaplan list endpoints."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Page:
    """One page position for a list endpoint.

    Megaplan paginates by entity reference, not by offset. A Page names
    exactly one position — the direction is part of the value, so an
    ambiguous combination (after + before) is inexpressible:

        await client.tasks.list(page=Page(after=100))
        await client.tasks.list(page=Page(before=task))
        await client.tasks.list(page=Page(with_={"contentType": "Task", "id": 5}))

    Values accept a bare int id, an entity/model, or a {contentType, id}
    link — the same coercion as the legacy page_after/page_before/page_with
    parameters, which remain as aliases.

    Attributes:
        after: Load the page starting after this entity.
        before: Load the page strictly before this entity.
        with_: Load the page containing this entity.
    """

    after: Any | None = None
    before: Any | None = None
    with_: Any | None = None

    def __post_init__(self) -> None:
        given = sum(value is not None for value in (self.after, self.before, self.with_))
        if given != 1:
            raise ValueError("Page requires exactly one of after=, before=, with_=.")
