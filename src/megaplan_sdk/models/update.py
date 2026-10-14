"""Patch and preview types for reviewed profile updates."""

import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateOnly


class ContractorPatch(BaseModel):
    """Editable profile fields; unset values are never sent.

    Account-specific fields are validated against the current card by the
    resource. Deprecated requisites belong to Payer and are not writable here.
    """

    name: str | None = None
    first_name: str | None = Field(None, alias="firstName")
    middle_name: str | None = Field(None, alias="middleName")
    last_name: str | None = Field(None, alias="lastName")
    gender: str | None = None
    position: str | None = None
    company: BaseEntity | None = None
    type: BaseEntity | None = None
    responsibles: list[BaseEntity] | None = None
    contact_info: list[dict[str, Any]] | None = Field(None, alias="contactInfo")
    description: str | None = None
    birthday: DateOnly | str | None = None
    prefer_transport: str | None = Field(None, alias="preferTransport")
    advertising_way: BaseEntity | None = Field(None, alias="advertisingWay")
    activity_type: BaseEntity | None = Field(None, alias="activityType")
    status: BaseEntity | str | None = None
    partners: list[BaseEntity] | None = None
    competitors: list[BaseEntity] | None = None
    is_public: bool | None = Field(None, alias="isPublic")
    tags: list[BaseEntity | str] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


@dataclass(frozen=True)
class UpdateFieldChange:
    """One changed field, retaining the distinction between missing and null."""

    field: str
    before: Any
    after: Any
    before_exists: bool


@dataclass(frozen=True)
class UpdatePreview:
    """Reviewable update bound to an account, entity and original state.

    Payloads are stored as JSON. Accessors return fresh copies so mutating a
    displayed patch or diff cannot alter the reviewed write.
    """

    entity_type: str
    entity_id: int
    _payload_json: str = field(repr=False)

    @property
    def origin(self) -> str:
        """Account URL for which the preview was prepared."""
        return str(json.loads(self._payload_json)["origin"])

    @property
    def source(self) -> dict[str, Any]:
        """Original API card, including missing versus present fields."""
        result: dict[str, Any] = json.loads(self._payload_json)["source"]
        return result

    @property
    def patch(self) -> dict[str, Any]:
        """Validated API patch, without unset fields."""
        result: dict[str, Any] = json.loads(self._payload_json)["patch"]
        return result

    @property
    def changes(self) -> list[UpdateFieldChange]:
        """Changes to review; equality of entity references ignores extra metadata."""
        from megaplan_sdk.updates import field_changes

        return field_changes(self.source, self.patch)
