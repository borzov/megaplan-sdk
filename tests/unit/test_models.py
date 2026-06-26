"""Unit tests for models."""

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, Meta, Money, Pagination, SortField
from megaplan_sdk.models.deal import Deal, ProgramState
from megaplan_sdk.models.project import Project
from megaplan_sdk.models.task import Task


def test_base_entity():
    """Test BaseEntity basic fields."""
    entity = BaseEntity(contentType="Task", id=1)
    assert entity.content_type == "Task"
    assert entity.id == 1


def test_base_entity_name():
    """Test BaseEntity now captures optional name field."""
    entity = BaseEntity(contentType="Program", id=14, name="Сайт или приложение")
    assert entity.name == "Сайт или приложение"


def test_base_entity_extra_allow():
    """Test BaseEntity stores unknown API fields via extra=allow."""
    entity = BaseEntity(contentType="Employee", id=10, name="Иванов", firstName="Иван")
    assert entity.name == "Иванов"
    assert entity.model_extra.get("firstName") == "Иван"


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


def test_money_model():
    """Test Money model parses API monetary value objects."""
    money = Money(contentType="Money", currency="RUB", value=18055000)
    assert money.currency == "RUB"
    assert money.value == 18055000
    assert money.content_type == "Money"


def test_money_model_full():
    """Test Money model with all fields."""
    money = Money(
        contentType="Money",
        currency="USD",
        value=1000,
        valueInMain=90000,
        rate=90.0,
    )
    assert money.value_in_main == 90000
    assert money.rate == 90.0


def test_timestamp_mixin_time_created():
    """Test TimestampMixin uses timeCreated/timeUpdated aliases."""
    task = Task(
        id=1,
        contentType="Task",
        name="Test",
        timeCreated={"contentType": "DateTime", "value": "2025-01-01T00:00:00+00:00"},
        timeUpdated={"contentType": "DateTime", "value": "2025-06-01T00:00:00+00:00"},
    )
    assert task.time_created is not None
    assert isinstance(task.time_created, DateTime)
    assert task.time_created.value == "2025-01-01T00:00:00+00:00"
    assert task.time_updated is not None
    assert task.time_updated.value == "2025-06-01T00:00:00+00:00"


def test_timestamp_mixin_project():
    """Test Project timestamps use timeCreated/timeUpdated."""
    project = Project(
        id=1,
        contentType="Project",
        name="Test",
        timeCreated={"contentType": "DateTime", "value": "2025-03-15T12:00:00+00:00"},
    )
    assert project.time_created is not None
    assert project.time_created.value == "2025-03-15T12:00:00+00:00"
    assert project.time_updated is None


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
    """Test Deal model basic fields."""
    deal = Deal(id=1, contentType="Deal", name="Test deal")
    assert deal.id == 1
    assert deal.content_type == "Deal"
    assert deal.name == "Test deal"


def test_deal_manager_field():
    """Test Deal.manager replaces the old responsible field."""
    deal = Deal(
        id=7,
        contentType="Deal",
        name="Leader-ID 2019",
        manager={"contentType": "Employee", "id": 1000011, "name": "Урюпин Александр"},
    )
    assert deal.manager is not None
    assert deal.manager.id == 1000011
    assert deal.manager.name == "Урюпин Александр"


def test_deal_price_money_field():
    """Test Deal.price accepts Money object from API."""
    deal = Deal(
        id=7,
        contentType="Deal",
        name="Test Deal",
        price={"contentType": "Money", "currency": "RUB", "value": 18055000},
    )
    assert deal.price is not None
    assert isinstance(deal.price, Money)
    assert deal.price.currency == "RUB"
    assert deal.price.value == 18055000


def test_deal_new_fields():
    """Test Deal new fields: number, short_description, cost, debt, result."""
    deal = Deal(
        id=7,
        contentType="Deal",
        name="Leader-ID 2019",
        number="1",
        shortDescription="Процесс 1 Leader-ID...",
        result="positive",
        cost={"contentType": "Money", "currency": "RUB", "value": 5000000},
        debt={"contentType": "Money", "currency": "RUB", "value": 18055000},
    )
    assert deal.number == "1"
    assert deal.short_description == "Процесс 1 Leader-ID..."
    assert deal.result == "positive"
    assert deal.cost is not None
    assert deal.cost.value == 5000000
    assert deal.debt is not None
    assert deal.debt.value == 18055000


def test_deal_timestamps_via_time_created():
    """Test Deal timestamps use timeCreated/timeUpdated from API."""
    deal = Deal(
        id=7,
        contentType="Deal",
        name="Test",
        timeCreated={"contentType": "DateTime", "value": "2019-04-03T05:19:30+00:00"},
        timeUpdated={"contentType": "DateTime", "value": "2024-01-31T05:38:14+00:00"},
    )
    assert deal.time_created is not None
    assert deal.time_created.value == "2019-04-03T05:19:30+00:00"
    assert deal.time_updated is not None
    assert deal.time_updated.value == "2024-01-31T05:38:14+00:00"


def test_deal_extra_allow():
    """Test Deal stores unknown API fields via extra=allow."""
    deal = Deal(
        id=7,
        contentType="Deal",
        name="Test",
        unknownFutureField="some_value",
    )
    assert deal.model_extra.get("unknownFutureField") == "some_value"


def test_program_state_str_with_name():
    """Test ProgramState __str__ returns name when available."""
    state = ProgramState(id=126, contentType="ProgramState", name="Проект сдан")
    assert str(state) == "Проект сдан"


def test_program_state_str_fallback():
    """Test ProgramState __str__ falls back to State#id when name is absent."""
    state = ProgramState(id=126, contentType="ProgramState")
    assert str(state) == "State#126"


def test_employee_status_fields():
    """Test Employee status fields: isWorking, fireInProgress, canLogin (#13)."""
    from megaplan_sdk.models.employee import Employee

    e = Employee.model_validate(
        {"contentType": "Employee", "id": 1, "isWorking": True,
         "fireInProgress": False, "canLogin": True}
    )
    assert e.is_working is True
    assert e.fire_in_progress is False
    assert e.can_login is True
    assert not hasattr(Employee.model_fields, "isDropped")
