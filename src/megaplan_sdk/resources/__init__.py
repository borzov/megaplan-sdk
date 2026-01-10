"""Resources for Megaplan SDK."""

from megaplan_sdk.resources.auth import AuthResource
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.comments import CommentsResource
from megaplan_sdk.resources.contractors import ContractorsResource
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.departments import DepartmentsResource
from megaplan_sdk.resources.employees import EmployeesResource
from megaplan_sdk.resources.filters import FiltersResource
from megaplan_sdk.resources.projects import ProjectsResource
from megaplan_sdk.resources.tasks import TasksResource

__all__ = [
    "BaseResource",
    "AuthResource",
    "TasksResource",
    "ProjectsResource",
    "DealsResource",
    "CommentsResource",
    "ContractorsResource",
    "EmployeesResource",
    "DepartmentsResource",
    "FiltersResource",
]
