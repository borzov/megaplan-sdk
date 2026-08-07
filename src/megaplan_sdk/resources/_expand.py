"""Declarative expand pipeline rules.

Resources describe *what* can be expanded via ``ExpandRule`` tables declared as
class attributes; the assembly itself lives in ``BaseResource._expand_references``.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExpandRule:
    """How one expandable reference field is loaded.

    The loaded entity replaces the reference field itself on an immutable copy
    of the listed entity, so expanding never changes the entity's type.

    Attributes:
        entity_type: API entity type used to fetch the referenced entity
            (e.g. "employee").
        model: Pydantic model class the fetched entity is parsed into.
    """

    entity_type: str
    model: type[Any]
