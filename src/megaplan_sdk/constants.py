"""Constants for Megaplan SDK."""

from typing import Any


class ContentType:
    """Content type constants for Megaplan API entities."""

    TASK = "Task"
    PROJECT = "Project"
    DEAL = "Deal"
    EMPLOYEE = "Employee"
    CONTRACTOR = "Contractor"
    CONTRACTOR_COMPANY = "ContractorCompany"
    CONTRACTOR_HUMAN = "ContractorHuman"
    CONTRACTOR_CATEGORY = "ContractorCategory"
    DEPARTMENT = "Department"
    COMMENT = "Comment"
    GROUP = "Group"
    KNOWLEDGE_BASE = "KnowledgeBase"
    KNOWLEDGE_ARTICLE = "KnowledgeArticle"

    # Value types (not entities) that the API also tags with contentType
    DATE_TIME = "DateTime"
    DATE_INTERVAL = "DateInterval"
    SORT_FIELD = "SortField"


# Task fields users commonly try to sort by that the Megaplan API rejects (422).
# Maps the unsupported field name to the supported replacement to suggest.
UNSUPPORTED_TASK_SORT_FIELDS: dict[str, str] = {
    "timeUpdated": "activity",
    "updatedAt": "activity",
}

# Field names carried over from other CRM APIs (Bitrix24, amoCRM, ...) that
# Task does not have — the server answers `fields=` requests with a raw 422
# "Task have not this fields" (#32). Maps each synonym to the real Task
# fields to suggest. A blacklist is used deliberately: an allowlist derived
# from the pydantic model is wrong in both directions (the model inherits
# `timeUpdated` from TimestampMixin, which the server rejects, and omits
# legit server fields like `commentsCount`; custom category fields are
# unknowable in advance).
UNSUPPORTED_TASK_FIELDS: dict[str, tuple[str, ...]] = {
    "timeUpdated": ("statusChangeTime", "lastCommentTimeCreated", "activity"),
    "updatedAt": ("statusChangeTime", "lastCommentTimeCreated", "activity"),
    "updated_at": ("statusChangeTime", "lastCommentTimeCreated", "activity"),
    "dateUpdated": ("statusChangeTime", "lastCommentTimeCreated", "activity"),
    "createdAt": ("timeCreated",),
    "created_at": ("timeCreated",),
    "dateCreated": ("timeCreated",),
}

# Recommended `fields` set for tasks.list() so that date fields are populated.
# Megaplan list endpoints omit these unless explicitly requested, which makes
# client-side time-window filtering silently return nothing (#8).
# Only fields confirmed to exist on Task are included (no "timeUpdated" — see #7).
DEFAULT_TASK_LIST_FIELDS: tuple[str, ...] = (
    "name",
    "status",
    "timeCreated",
    "activity",
    "lastCommentTimeCreated",
    "statusChangeTime",
    "actualStart",
    "owner",
    "responsible",
    "commentsCount",
)

# Default sort for list endpoints: newest first by creation time.
# Megaplan's bare list order is an internal index (not date) — see #14.
# Matches the Megaplan UI, which always shows the freshest items on top.
# Pass sort_by=[] to a list() method to opt out of any sorting.
DEFAULT_SORT_RECENT: list[dict[str, Any]] = [
    {"contentType": ContentType.SORT_FIELD, "fieldName": "timeCreated", "desc": True}
]
