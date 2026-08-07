"""Notification models for Megaplan SDK (#FR-F)."""

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk._notification_links import NotificationEntityRef, parse_entity_ref
from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.common import DateTime
from megaplan_sdk.models.employee import Employee


class Notification(BaseEntity):
    """Notification entity.

    The only reliable source of "this user was mentioned": the server sets
    ``is_mention`` itself when a comment contains
    ``<megaplan:mention to="Employee/<id>">``. Matching names in comment text
    with regular expressions misses mentions the server renders as HTML.

    Attributes:
        content_type: Entity content type (always "Notification").
        type: Notification type id, e.g. "BumsTaskN_TaskNewComment".
        content: Rendered HTML text of the notification.
        time: When the notification was produced.
        is_active: Whether the notification is still active (unread/unarchived).
        is_mention: Whether this notification is a mention of the current user.
        is_history_log: Whether the record comes from the history log.
        size: Server-side rendering hint.
        sender: Employee who caused the notification.
        subject: Entity the notification is about. Polymorphic — Comment, Deal,
            Task and Todo all occur; use ``subject_comment`` for the typed
            comment, and ``entity_ref`` for the entity behind the link.
    """

    content_type: str = Field(alias="contentType", default="Notification")
    type: str | None = None
    content: str | None = None
    time: DateTime | None = None
    is_active: bool | None = Field(alias="isActive", default=None)
    is_mention: bool | None = Field(alias="isMention", default=None)
    is_history_log: bool | None = Field(alias="isHistoryLog", default=None)
    size: int | None = None
    sender: Employee | None = None
    subject: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def entity_ref(self) -> NotificationEntityRef | None:
        """Entity the notification links to, parsed out of ``content``.

        Examples:
            >>> notification.entity_ref
            NotificationEntityRef(entity_type='task', entity_id=1006256, comment_anchor=189191)
        """
        return parse_entity_ref(self.content)

    @property
    def subject_comment(self) -> Comment | None:
        """``subject`` as a typed Comment, or None when it is another entity."""
        if self.subject is None or self.subject.content_type != ContentType.COMMENT:
            return None
        return Comment.model_validate(self.subject.model_dump(by_alias=True))


class NotificationCounter(BaseModel):
    """Unread notification counter (``/notification/counter``).

    Attributes:
        content_type: Always "Counter".
        id: Counter identifier, e.g. "notifications".
        attributes: Counter attributes reported by the server, e.g. ["mention"].
        count: Number of notifications.
    """

    content_type: str = Field(alias="contentType", default="Counter")
    id: str | None = None
    attributes: list[str] | None = None
    count: int | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NotificationType(BaseModel):
    """Notification type from ``/notification/activityTypes``.

    Ids are strings ("BumsCommonN_CommentLiked"), so this is not a BaseEntity.

    Attributes:
        content_type: Always "NotificationType".
        id: String type identifier.
        name: Human-readable description.
    """

    content_type: str = Field(alias="contentType", default="NotificationType")
    id: str
    name: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
