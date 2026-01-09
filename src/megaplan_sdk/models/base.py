"""Base models for Megaplan SDK."""

from pydantic import BaseModel, ConfigDict, Field


class BaseEntity(BaseModel):
    """Base entity with contentType and id.

    All Megaplan entities have contentType and id fields.
    Link entities (for references) only contain these two fields.
    """

    content_type: str = Field(alias="contentType")
    id: int

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
