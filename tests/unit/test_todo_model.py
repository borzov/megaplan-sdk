"""Tests for the Todo ("Дела") model (task 4 of the 0.6.1 release)."""

from megaplan_sdk.models.todo import Todo, TodoCategory, TodoStatus

ALL_DAY = {
    "contentType": "Todo",
    "id": "501",
    "name": "Созвон",
    "when": {
        "contentType": "IntervalDates",
        "from": {"contentType": "DateOnly", "year": 2026, "month": 8, "day": 21},
        "to": {"contentType": "DateOnly", "year": 2026, "month": 8, "day": 21},
    },
    "status": {
        "contentType": "TodoStatus",
        "id": "3",
        "name": "Выполнено",
        "masterType": "success",
    },
    "isDropped": False,
}

TIMED = {
    "contentType": "Todo",
    "id": "502",
    "name": "Встреча",
    "when": {
        "contentType": "IntervalTime",
        "from": {"contentType": "DateTime", "value": "2026-08-21T10:00:00+00:00"},
        "to": {"contentType": "DateTime", "value": "2026-08-21T11:00:00+00:00"},
    },
    "status": {
        "contentType": "TodoStatus",
        "id": "1",
        "name": "Запланировано",
        "masterType": "scheduled",
    },
}

# Real GET /api/v3/todo/{id} response, anonymized (task-1-report.md fixture).
# `when` is null on the primary entity; the IntervalTime example lives in the
# nested `coincidentTodos` entry. `rights` carries a non-numeric id
# ("Todo/5815") and both `rights`/`coincidentTodos` must stay out of the
# model so they fall through to `model_extra` instead of breaking parsing.
STAND_RESPONSE = {
    "contentType": "Todo",
    "id": "5819",
    "name": "[SDK-TEST] fixture probe",
    "status": {
        "contentType": "TodoStatus",
        "id": "1",
        "name": "Запланировано",
        "masterType": "scheduled",
    },
    "when": None,
    "place": None,
    "responsible": None,
    "userCreated": {"contentType": "Employee", "id": "1000003", "name": "REDACTED"},
    "isNeedResult": False,
    "resultComment": None,
    "timeFinished": None,
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-21T10:47:51+00:00"},
    "linksCount": 0,
    "relationLinks": [],
    "relationLinksCount": 0,
    "coincidentTodos": [
        {
            "contentType": "Todo",
            "id": "5815",
            "name": "Запустить процедуру согласования договора",
            "status": {"contentType": "TodoStatus", "id": "1"},
            "when": {
                "contentType": "IntervalTime",
                "from": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
                "to": {"contentType": "DateTime", "value": "2026-08-21T15:00:00+00:00"},
            },
            "place": None,
            "responsible": {"contentType": "Employee", "id": "1000008", "name": "REDACTED"},
            "timeFinished": None,
            "description": "",
            "category": {
                "contentType": "TodoCategory",
                "id": "6",
                "name": "Дело",
                "masterType": "todo",
                "color": "#000000",
                "bgColor": "#cccccc",
                "activeBgColor": "#555555",
            },
            "rights": {"contentType": "TodoRights", "id": "Todo/5815", "read": True},
            "unreadCommentsCount": 0,
            "isFavorite": False,
            "conferenceIsStarted": False,
            "conferenceSettings": {"contentType": "ConferenceSettings", "type": "conference"},
        }
    ],
    "coincidentTodosCount": 1,
    "interactionsCounters": [],
    "description": "",
    "busyParticipants": [],
    "busyParticipantsCount": 0,
    "category": {"contentType": "TodoCategory", "id": "6"},
    "isTemplate": False,
    "isDropped": False,
    "isOverdue": False,
    "schedule": None,
    "attaches": [],
    "attachesCount": 0,
    "rights": {
        "contentType": "TodoRights",
        "id": "Todo/5819",
        "read": True,
        "edit": True,
        "remove": True,
        "finish": True,
        "cancel": True,
        "renew": False,
        "give": False,
        "take": True,
        "acceptInvite": False,
        "rejectInvite": False,
    },
    "reminders": [
        {
            "contentType": "Reminder",
            "transport": "email",
            "isActive": True,
            "timeBefore": {"contentType": "DateInterval", "value": 3600},
            "recipient": {"contentType": "Employee", "id": "1000003", "name": "REDACTED"},
        }
    ],
    "remindersCount": 1,
    "participants": [],
    "participantsCount": 0,
    "unreadCommentsCount": 0,
    "relations": [],
    "relationsCount": 0,
    "contactInfoCount": 0,
    "comments": [],
    "commentsCount": 0,
    "attachesCountInComments": 0,
    "unreadAnswer": False,
    "subscribed": True,
    "isFavorite": False,
    "allFilesCount": 0,
    "attachesInfo": {
        "contentType": "AttachesInfo",
        "imageFiles": [],
        "imageFilesCount": 0,
        "audioFiles": [],
        "audioFilesCount": 0,
        "otherFiles": [],
        "otherFilesCount": 0,
    },
    "conferenceIsStarted": False,
    "conferenceSettings": {"contentType": "ConferenceSettings", "type": "conference"},
    "hiddenCommentsCount": 0,
}


def test_parses_all_day_interval():
    todo = Todo(**ALL_DAY)
    assert todo.when is not None
    assert todo.when.is_all_day is True
    assert todo.when.start_date.day == 21


def test_parses_timed_interval():
    todo = Todo(**TIMED)
    assert todo.when is not None
    assert todo.when.is_all_day is False
    assert todo.when.start_datetime.value.startswith("2026-08-21T10:00")


def test_is_finished_uses_master_type_not_time_finished():
    """A todo can be finished without a result — time_finished may be absent."""
    assert Todo(**ALL_DAY).is_finished() is True
    assert Todo(**TIMED).is_finished() is False


def test_unknown_fields_are_preserved():
    todo = Todo(**{**TIMED, "someNewServerField": 42})
    assert todo.model_extra["someNewServerField"] == 42


def test_when_can_be_none():
    """The stand confirms `when` defaults to null on creation without it."""
    todo = Todo(**{**TIMED, "when": None})
    assert todo.when is None


def test_is_dropped_defaults_when_absent():
    """The stand response for some todos omits `isDropped` entirely."""
    payload = dict(TIMED)
    todo = Todo(**payload)
    assert todo.is_dropped is False


def test_truncated_status_without_master_type_does_not_crash_is_finished():
    """Nested todos (e.g. inside coincidentTodos) carry a status stripped down
    to contentType/id — no name, no masterType."""
    todo = Todo(**{**TIMED, "status": {"contentType": "TodoStatus", "id": "1"}})
    assert todo.status is not None
    assert todo.status.master_type is None
    assert todo.is_finished() is False


def test_end_date_and_end_datetime_symmetry():
    all_day = Todo(**ALL_DAY)
    assert all_day.when.end_date.day == 21
    assert all_day.when.end_datetime is None

    timed = Todo(**TIMED)
    assert timed.when.end_datetime.value.startswith("2026-08-21T11:00")
    assert timed.when.end_date is None


def test_display_name_and_str():
    named = Todo(**TIMED)
    assert named.display_name() == "Встреча"
    assert str(named) == "Встреча"

    unnamed = Todo(**{**TIMED, "name": None})
    assert unnamed.display_name() == "Todo#502"
    assert str(unnamed) == "Todo#502"


def test_parses_full_stand_response_without_crashing():
    """rights (non-numeric id "Todo/5819") and coincidentTodos (nested Todo
    list) are not declared fields — they must land in model_extra instead of
    breaking parsing."""
    todo = Todo(**STAND_RESPONSE)
    assert todo.id == 5819
    assert todo.when is None
    assert todo.is_dropped is False
    assert todo.is_finished() is False
    assert "rights" in todo.model_extra
    assert "coincidentTodos" in todo.model_extra


def test_todo_constructs_without_explicit_content_type():
    """`content_type` must default like every other top-level model (Task,
    Deal, Notification, File, DateOnly, DateTime) — a bare `Todo(id=1)` must
    not raise ValidationError."""
    todo = Todo(id=1, name="x")
    assert todo.content_type == "Todo"


def test_todo_status_and_category_construct_without_explicit_content_type():
    status = TodoStatus(id=1)
    assert status.content_type == "TodoStatus"

    category = TodoCategory(id=1)
    assert category.content_type == "TodoCategory"


def test_when_without_content_type_infers_timed_shape_from_bounds():
    """A `when` object missing `contentType` must not fail the whole Todo —
    the shape is inferred from the bounds' own keys instead (#fix-round-2)."""
    todo = Todo(
        **{
            **TIMED,
            "when": {
                "from": {"value": "2026-08-21T10:00:00+00:00"},
                "to": {"value": "2026-08-21T11:00:00+00:00"},
            },
        }
    )
    assert todo.when is not None
    assert todo.when.is_all_day is False
    assert todo.when.start_datetime is not None
    assert todo.when.start_datetime.value == "2026-08-21T10:00:00+00:00"


def test_when_without_content_type_infers_all_day_shape_from_bounds():
    """Same inference, DateOnly-shaped bounds (year/month/day, no contentType)."""
    todo = Todo(
        **{
            **TIMED,
            "when": {
                "from": {"year": 2026, "month": 8, "day": 21},
                "to": {"year": 2026, "month": 8, "day": 21},
            },
        }
    )
    assert todo.when is not None
    assert todo.when.is_all_day is True
    assert todo.when.start_date is not None
    assert todo.when.start_date.day == 21


def test_when_with_unrecognizable_bounds_returns_none_without_raising():
    """Empty or unrecognizable bounds degrade to None, never an exception."""
    empty = Todo(**{**TIMED, "when": {"from": {}, "to": {}}})
    assert empty.when is not None
    assert empty.when.is_all_day is False
    assert empty.when.start_date is None
    assert empty.when.start_datetime is None
    assert empty.when.end_date is None
    assert empty.when.end_datetime is None

    garbage = Todo(**{**TIMED, "when": {"from": {"foo": "bar"}, "to": {"foo": "bar"}}})
    assert garbage.when is not None
    assert garbage.when.is_all_day is False
    assert garbage.when.start_date is None
    assert garbage.when.start_datetime is None
    assert garbage.when.end_date is None
    assert garbage.when.end_datetime is None
