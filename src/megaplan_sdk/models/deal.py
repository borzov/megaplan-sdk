"""Deal models for Megaplan SDK."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, MainEntityProxyMixin, Money, TimestampMixin


class TradeFilter(BaseModel):
    """Trade filter configuration for deals.

    Can be used as filter ID (integer) or filter configuration (dict).
    """

    id: int | None = None
    config: dict[str, Any] | None = None


class ProgramState(BaseModel):
    """Program state model.

    Represents a state in a deal program.

    Note:
        The ``name`` field may be absent in list endpoint responses.
        In that case ``str(state)`` falls back to ``"State#<id>"``.
        Use ``client.deals.get(deal_id)`` to retrieve the full state object
        with the name populated.
    """

    id: int
    content_type: str = Field(alias="contentType", default="ProgramState")
    name: str | None = None
    program: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

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

    Note:
        The list endpoint (``GET /api/v3/deal``) returns a subset of fields
        compared to the single-entity endpoint (``GET /api/v3/deal/{id}``).
        Fields like ``description``, ``deadline``, ``invoices``, and custom
        category fields are only available via ``client.deals.get(deal_id)``.

        When using the ``fields`` parameter in ``list()``, use the actual
        API field names: ``manager``, ``price``, ``timeCreated``, etc.

        Unknown API fields are preserved in ``model_extra`` (``extra="allow"``).
    """

    id: int
    content_type: str = Field(alias="contentType", default="Deal")
    name: str | None = None
    number: str | None = None
    short_description: str | None = Field(None, alias="shortDescription")
    description: str | None = None

    manager: BaseEntity | None = None
    program: BaseEntity | None = None
    state: ProgramState | None = None
    contractor: BaseEntity | None = None
    currency: BaseEntity | None = None

    price: Money | None = None
    cost: Money | None = None
    debt: Money | None = None

    result: str | None = None
    state_time_updated: str | DateTime | None = Field(None, alias="stateTimeUpdated")
    deadline: str | DateTime | dict[str, Any] | None = None
    tags: list[BaseEntity] | None = None
    attaches: list[BaseEntity] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DealFullDetails(MainEntityProxyMixin, BaseModel):
    """Full deal details with all related entities.

    Attribute access falls through to the wrapped ``deal`` (#25): both
    ``details.deal.manager`` and ``details.manager`` resolve identically.

    ``manager``/``contractor`` prefer the loaded ``*_details`` when expand
    populated them, falling back to the raw wire reference otherwise (#25).

    Attributes:
        deal: Main deal entity.
        comments: List of comments (if requested).
        history: Change history entries (if requested).
        status_history: Status change history (if requested).
        auditors: List of auditors (if requested).
        manager_details: Full manager (responsible) employee details (if requested).
        contractor_details: Full contractor details (if requested).
        related_tasks: Tasks related to this deal (if requested).
    """

    _main_field: ClassVar[str] = "deal"

    deal: Deal
    comments: list[Any] | None = None
    history: list[dict[str, Any]] | None = None
    status_history: list[dict[str, Any]] | None = None
    auditors: list[dict[str, Any]] | None = None
    manager_details: Any | None = None
    contractor_details: Any | None = None
    related_tasks: list[Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def manager(self) -> Any:
        """Loaded manager (``manager_details``) or the raw ``deal.manager`` reference."""
        return self.manager_details if self.manager_details is not None else self.deal.manager

    @property
    def contractor(self) -> Any:
        """Loaded contractor (``contractor_details``) or the raw reference."""
        return (
            self.contractor_details if self.contractor_details is not None else self.deal.contractor
        )
