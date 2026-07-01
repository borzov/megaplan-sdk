"""Declarative expand pipeline rules.

Resources describe *what* can be expanded via ``ExpandRule`` tables declared as
class attributes; the assembly itself lives in ``BaseResource._expand_and_wrap``.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExpandRule:
    """How one expandable reference field is loaded and where the result goes.

    Attributes:
        entity_type: API entity type used to fetch the referenced entity
            (e.g. "employee").
        model: Pydantic model class the fetched entity is parsed into.
        details_field: Field on the resource's details model that receives the
            loaded entity (wrap mode). None means the loaded entity replaces
            the reference field itself on an immutable copy (replace mode).
    """

    entity_type: str
    model: type[Any]
    details_field: str | None = None
