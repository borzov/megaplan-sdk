"""Comment model for Megaplan SDK."""

from typing import Any

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import TimestampMixin


class Comment(BaseEntity, TimestampMixin):
    """Comment entity.

    Attributes:
        id: Comment identifier.
        content_type: Entity content type (always "Comment").
        subject: Parent entity (task, project, deal, etc.).
        owner: Comment author (Employee, ContractorCompany, or ContractorHuman).
        content: Comment text content.
        attaches: List of attached files.
        attaches_count: Number of attachments.
        work_time: Work time interval (DateInterval entity with contentType, value).
        work_date: Work date (DateTime entity with contentType, value, timestamp).
        is_unread: Whether comment is unread.
        is_dropped: Whether comment is deleted.
        completed: Completion status.
        created_at: Creation timestamp (timeCreated).
        updated_at: Last update timestamp (timeUpdated).

        Legacy fields for compatibility:
        author: Alias for owner.
        text: Alias for content.
    """

    content_type: str = Field(alias="contentType", default="Comment")
    subject: BaseEntity | None = None
    owner: BaseEntity | None = None  # Employee, ContractorCompany, or ContractorHuman
    content: str | None = None  # Comment text
    attaches: list[BaseEntity] | None = None
    attaches_count: int | None = Field(alias="attachesCount", default=None)
    work_time: dict[str, Any] | None = Field(
        alias="workTime", default=None
    )  # DateInterval (contentType, value)
    work_date: dict[str, Any] | None = Field(
        alias="workDate", default=None
    )  # DateTime (contentType, value, timestamp)
    is_unread: bool | None = Field(alias="isUnread", default=None)
    is_dropped: bool | None = Field(alias="isDropped", default=None)
    completed: int | None = None

    # Legacy aliases for compatibility
    @property
    def author(self) -> BaseEntity | None:
        """Alias for owner field."""
        return self.owner

    @property
    def text(self) -> str | None:
        """Alias for content field."""
        return self.content

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
