"""Resources for Megaplan SDK."""

from megaplan_sdk.resources.auth import AuthResource
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.projects import ProjectsResource
from megaplan_sdk.resources.tasks import TasksResource

__all__ = [
    "BaseResource",
    "AuthResource",
    "TasksResource",
    "ProjectsResource",
    "DealsResource",
]
