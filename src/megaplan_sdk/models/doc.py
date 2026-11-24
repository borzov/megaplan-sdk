"""Document cards, folders and downloadable versions."""

from pydantic import Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, File


class DocContent(File):
    """File attached to a document version."""

    extension: str | None = None


class DocVersion(BaseEntity):
    """One revision of a document and its downloadable content."""

    content_type: str = Field(alias="contentType", default="DocVersion")
    content: DocContent | str | None = None
    time_created: DateTime | None = Field(alias="timeCreated", default=None)


class Doc(BaseEntity):
    """Document card with the currently available version."""

    content_type: str = Field(alias="contentType", default="Doc")
    actual_version: DocVersion | None = Field(alias="actualVersion", default=None)


class DocFolder(BaseEntity):
    """Document folder with documents and references to its child folders."""

    content_type: str = Field(alias="contentType", default="DocFolder")
    docs: list[Doc] = Field(default_factory=list)
    childs: list[BaseEntity] = Field(default_factory=list)
