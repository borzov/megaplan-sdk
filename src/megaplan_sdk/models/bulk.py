"""Models for the batch endpoint ``POST /api/v3/bulk`` (#FR-E)."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiCall(BaseModel):
    """One call inside a batch.

    Attributes:
        content_type: Always "ApiCall".
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        url: Path after the host, e.g. "/api/v3/deal/1001/linkedDeals".
        body: Request body. Dicts and lists are serialized to the JSON string
            the server expects.
    """

    content_type: str = Field(alias="contentType", default="ApiCall")
    method: str
    url: str
    body: Any | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def to_payload(self) -> dict[str, Any]:
        """Render the call as the server's wire format."""
        payload: dict[str, Any] = {
            "contentType": "ApiCall",
            "method": self.method.upper(),
            "url": self.url,
        }
        if self.body is not None:
            payload["body"] = (
                self.body
                if isinstance(self.body, str)
                else json.dumps(self.body, ensure_ascii=False)
            )
        return payload


class BulkCallResult(BaseModel):
    """Result of one call inside a batch.

    Each call reports its own status: a 404 in one call leaves the others
    untouched, so results must be handled per element, not per batch.

    Attributes:
        status: HTTP-like status of this call.
        errors: Server errors for this call, if any.
        data: Payload the call returned.
        pagination: Pagination block, for list calls.
    """

    status: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
    data: Any | None = None
    pagination: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

    @property
    def is_success(self) -> bool:
        """Whether this call succeeded."""
        return self.status == 200

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BulkCallResult":
        """Build a result from one element of the batch response."""
        meta = payload.get("meta") or {}
        return cls(
            status=int(meta.get("status", 200)),
            errors=list(meta.get("errors") or []),
            data=payload.get("data"),
            pagination=meta.get("pagination"),
        )
