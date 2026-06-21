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


# Task fields users commonly try to sort by that the Megaplan API rejects (422).
# Maps the unsupported field name to the supported replacement to suggest.
UNSUPPORTED_TASK_SORT_FIELDS: dict[str, str] = {
    "timeUpdated": "activity",
    "updatedAt": "activity",
}
