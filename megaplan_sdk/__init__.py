"""Megaplan Python SDK - Professional SDK for Megaplan API v3."""

from megaplan_sdk.client import MegaplanClient
from megaplan_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    MegaplanError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from megaplan_sdk.logging_config import setup_logging
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.common import DateTime
from megaplan_sdk.models.contractor import Contractor, ContractorCompany, ContractorHuman
from megaplan_sdk.models.deal import Deal, DealFullDetails
from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.project import Project, ProjectFullDetails
from megaplan_sdk.models.task import Task, TaskFullDetails

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
    "Task",
    "TaskFullDetails",
    "Project",
    "ProjectFullDetails",
    "Deal",
    "DealFullDetails",
    "Comment",
    "Contractor",
    "ContractorCompany",
    "ContractorHuman",
    "Employee",
    "Department",
    "DateTime",
    # Utils
    "setup_logging",
]

__version__ = "0.1.0"
