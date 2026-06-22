"""Knowledge Base models for Megaplan SDK."""

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime


class KnowledgeBase(BaseEntity):
    """Knowledge Base section.

    The list endpoint returns a trimmed object (no ``content`` /
    ``last_updated`` / ``is_dropped``); ``knowledge_base.get(id)`` returns
    the full object including the HTML ``content``.
    """

    content_type: str = Field(alias="contentType", default="KnowledgeBase")
    content: str | None = None  # HTML, present only in the full get() response
    access_role: str | None = Field(alias="accessRole", default=None)
    last_updated: DateTime | None = Field(alias="lastUpdated", default=None)
    last_update_by: BaseEntity | None = Field(alias="lastUpdateBy", default=None)
    order_pos: int | None = Field(alias="orderPos", default=None)
    expanded: bool | None = None
    is_dropped: bool | None = Field(alias="isDropped", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class KnowledgeArticle(BaseEntity):
    """Knowledge Base article.

    NOTE: ``parent`` is ALWAYS null in the Megaplan API — use ``base`` (the
    parent section reference) to determine which section the article belongs to.
    """

    content_type: str = Field(alias="contentType", default="KnowledgeArticle")
    content: str | None = None  # HTML body
    parent: BaseEntity | None = None  # always null in API; use `base`
    base: KnowledgeBase | None = None  # the real parent-section link
    access_role: str | None = Field(alias="accessRole", default=None)
    last_updated: DateTime | None = Field(alias="lastUpdated", default=None)
    last_update_by: BaseEntity | None = Field(alias="lastUpdateBy", default=None)
    order_pos: int | None = Field(alias="orderPos", default=None)
    expanded: bool | None = None
    is_dropped: bool | None = Field(alias="isDropped", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class KnowledgeSectionWithArticles(BaseModel):
    """Composite returned by the experimental ``get_with_articles`` helper."""

    section: KnowledgeBase
    articles: list[KnowledgeArticle]

    model_config = ConfigDict(populate_by_name=True, extra="allow")
