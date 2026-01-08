"""Deal models for Megaplan SDK."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, TimestampMixin


class TradeFilter(BaseModel):
    """Trade filter configuration for deals.

    Can be used as filter ID (integer) or filter configuration (dict).
    """

    id: int | None = None
    config: dict[str, Any] | None = None


class ProgramState(BaseModel):
    """Program state model.

    Represents a state in a deal program.
    """

    id: int
    content_type: str = Field(alias="contentType", default="ProgramState")
    name: str | None = None
    program: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def __str__(self) -> str:
        """Return state name for display.

        Returns:
            State name or fallback ID representation.

        Examples:
            >>> state = ProgramState(id=1, name="In Progress")
            >>> str(state)
            'In Progress'
        """
        return self.name or f"State#{self.id}"


class Deal(TimestampMixin):
    """Deal model.

    Represents a deal in Megaplan with all its properties.
    """

    id: int
    content_type: str = Field(alias="contentType", default="Deal")
    name: str | None = None
    program: BaseEntity | None = None
    state: ProgramState | None = None
    contractor: BaseEntity | None = None
    responsible: BaseEntity | None = None
    sum_base: float | None = Field(alias="sumBase", default=None)
    currency: BaseEntity | None = None
    deadline: str | DateTime | dict[str, Any] | None = None  # Can be DateOnly, DateTime, or string
    description: str | None = None
    tags: list[BaseEntity] | None = None
    attaches: list[BaseEntity] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DealFullDetails(BaseModel):
    """Full deal details with all related entities.

    Attributes:
        deal: Main deal entity.
        comments: List of comments (if requested).
        history: Change history entries (if requested).
        status_history: Status change history (if requested).
        auditors: List of auditors (if requested).
        responsible_details: Full responsible employee details (if requested).
        contractor_details: Full contractor details (if requested).
        related_tasks: Tasks related to this deal (if requested).
    """

    deal: Deal
    comments: list[Any] | None = None
    history: list[dict[str, Any]] | None = None
    status_history: list[dict[str, Any]] | None = None
    auditors: list[dict[str, Any]] | None = None
    responsible_details: Any | None = None
    contractor_details: Any | None = None
    related_tasks: list[Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
