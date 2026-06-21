"""Constants for Megaplan SDK."""


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
