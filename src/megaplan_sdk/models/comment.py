"""Comment model for Megaplan SDK."""

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateInterval, DateTime, TimestampMixin


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
        work_time: Work time interval (typed DateInterval; ``.value`` in
            seconds, plus ``.seconds``/``.minutes``/``.hours``). #16
        work_date: Work date (typed DateTime with contentType, value). #16
        is_unread: Whether comment is unread.
        is_dropped: Whether comment is deleted.
        completed: Completion status.
        created_at: Creation timestamp (timeCreated).
        updated_at: Last update timestamp (timeUpdated).
    """

    content_type: str = Field(alias="contentType", default="Comment")
    subject: BaseEntity | None = None
    owner: BaseEntity | None = None
    content: str | None = None
    attaches: list[BaseEntity] | None = None
    attaches_count: int | None = Field(alias="attachesCount", default=None)
    work_time: DateInterval | None = Field(alias="workTime", default=None)
    work_date: DateTime | None = Field(alias="workDate", default=None)
    is_unread: bool | None = Field(alias="isUnread", default=None)
    is_dropped: bool | None = Field(alias="isDropped", default=None)
    completed: int | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
