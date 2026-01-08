"""Unit tests for models."""

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import Meta, Pagination, SortField
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.project import Project
from megaplan_sdk.models.task import Task


def test_base_entity():
    """Test BaseEntity."""
    entity = BaseEntity(contentType="Task", id=1)
    assert entity.content_type == "Task"
    assert entity.id == 1


def test_meta():
    """Test Meta model."""
    meta = Meta(status=200, errors=[], pagination=None)
    assert meta.status == 200
    assert meta.errors == []


def test_pagination():
    """Test Pagination model."""
    pagination = Pagination(count=100, limit=50)
    assert pagination.count == 100
    assert pagination.limit == 50


def test_sort_field():
    """Test SortField model."""
    sort = SortField(field="name", direction="asc")
    assert sort.field == "name"
    assert sort.direction == "asc"


def test_task():
    """Test Task model."""
    task = Task(id=1, contentType="Task", name="Test task")
    assert task.id == 1
    assert task.content_type == "Task"
    assert task.name == "Test task"


def test_project():
    """Test Project model."""
    project = Project(id=1, contentType="Project", name="Test project")
    assert project.id == 1
    assert project.content_type == "Project"
    assert project.name == "Test project"


def test_deal():
    """Test Deal model."""
    deal = Deal(id=1, contentType="Deal", name="Test deal")
    assert deal.id == 1
    assert deal.content_type == "Deal"
    assert deal.name == "Test deal"
