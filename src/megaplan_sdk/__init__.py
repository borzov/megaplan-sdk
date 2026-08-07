"""Megaplan Python SDK - Professional SDK for Megaplan API v3."""

from megaplan_sdk._notification_links import NotificationEntityRef
from megaplan_sdk.client import MegaplanClient
from megaplan_sdk.constants import DEFAULT_SORT_RECENT, DEFAULT_TASK_LIST_FIELDS
from megaplan_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    MegaplanError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from megaplan_sdk.filter_builder import (
    FilterBuilder,
    ProjectFilterBuilder,
    TaskFilterBuilder,
    TradeFilterBuilder,
)
from megaplan_sdk.helpers import (
    make_contractor_entity,
    make_deal_entity,
    make_employee_entity,
    make_entity,
    make_project_entity,
    make_task_entity,
)
from megaplan_sdk.logging_config import setup_logging
from megaplan_sdk.models.auth import AuthTokenResponse
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.common import DateInterval, DateTime, Money
from megaplan_sdk.models.contractor import Contractor, ContractorCompany, ContractorHuman
from megaplan_sdk.models.deal import Deal, DealFullDetails
from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.filter import (
    BaseFilter,
    EmployeeFilter,
    FilterExport,
    ProjectFilter,
    TaskFilter,
    TradeFilter,
    UserSetting,
)
from megaplan_sdk.models.group import Group
from megaplan_sdk.models.knowledge import (
    KnowledgeArticle,
    KnowledgeBase,
    KnowledgeSectionWithArticles,
)
from megaplan_sdk.models.milestone import Milestone
from megaplan_sdk.models.notification import (
    Notification,
    NotificationCounter,
    NotificationType,
)
from megaplan_sdk.models.participant import Participant, parse_participant, parse_participants
from megaplan_sdk.models.project import Project, ProjectFullDetails
from megaplan_sdk.models.task import Task, TaskFullDetails
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.filters import FiltersResource
from megaplan_sdk.task_query import TaskQuery

__all__ = [
    # Client
    "MegaplanClient",
    # Exceptions
    "MegaplanError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    # Models
    "AuthTokenResponse",
    "Task",
    "TaskFullDetails",
    "Project",
    "ProjectFullDetails",
    "Deal",
    "DealFullDetails",
    "Comment",
    "Money",
    "Contractor",
    "ContractorCompany",
    "ContractorHuman",
    "Employee",
    "Department",
    "Group",
    "Milestone",
    "KnowledgeBase",
    "KnowledgeArticle",
    "KnowledgeSectionWithArticles",
    "Notification",
    "NotificationCounter",
    "NotificationEntityRef",
    "NotificationType",
    "Participant",
    "parse_participant",
    "parse_participants",
    "DateInterval",
    "DateTime",
    # Pagination
    "Page",
    # Task queries
    "TaskQuery",
    # Filters
    "FiltersResource",
    "BaseFilter",
    "TaskFilter",
    "TradeFilter",
    "EmployeeFilter",
    "ProjectFilter",
    "FilterExport",
    "UserSetting",
    # Utils
    "setup_logging",
    # Helpers
    "make_entity",
    "make_employee_entity",
    "make_project_entity",
    "make_task_entity",
    "make_deal_entity",
    "make_contractor_entity",
    # Filter Builder
    "FilterBuilder",
    "TaskFilterBuilder",
    "TradeFilterBuilder",
    "ProjectFilterBuilder",
    # Constants
    "DEFAULT_SORT_RECENT",
    "DEFAULT_TASK_LIST_FIELDS",
]

__version__ = "0.5.0"
