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


# Task fields users commonly try to sort by that the Megaplan API rejects (422).
# Maps the unsupported field name to the supported replacement to suggest.
UNSUPPORTED_TASK_SORT_FIELDS: dict[str, str] = {
    "timeUpdated": "activity",
    "updatedAt": "activity",
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
    {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
]
