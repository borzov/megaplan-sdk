"""Unit tests for TasksResource."""

import json

import pytest

from megaplan_sdk.resources.tasks import TasksResource


async def test_create_task(megaplan_api, tasks):
    """Test creating a task."""
    megaplan_api.post("task", data={"id": 1, "contentType": "Task", "name": "Test"})

    task = await tasks.create({"name": "Test"})

    assert task.id == 1
    assert task.name == "Test"


async def test_list_tasks(megaplan_api, tasks):
    """Test listing tasks."""
    # list() adds default sortBy — megaplan_api matches any query string
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(limit=10)

    assert len(result) == 1
    assert result[0].id == 1


async def test_list_tasks_with_q(megaplan_api, tasks):
    """Test listing tasks with q parameter."""
    # list() adds default sortBy — megaplan_api matches any query string
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Test task"}])

    result = await tasks.list(limit=10, q="test")

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].name == "Test task"


async def test_get_task(megaplan_api, tasks):
    """Test getting a task by ID."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test"})

    task = await tasks.get(1)

    assert task.id == 1
    assert task.name == "Test"


async def test_update_task(megaplan_api, tasks):
    """Test updating a task."""
    megaplan_api.post("task/1", data={"id": 1, "contentType": "Task", "name": "Updated"})

    task = await tasks.update(1, {"name": "Updated"})

    assert task.name == "Updated"


async def test_delete_task(megaplan_api, tasks):
    """Test deleting a task."""
    megaplan_api.delete("task/1")

    await tasks.delete(1)


async def test_get_sub_tasks(megaplan_api, tasks):
    """Test getting subtasks."""
    megaplan_api.get("task/1/subTasks", data=[{"id": 2, "contentType": "Task", "name": "Subtask"}])

    subtasks = await tasks.get_sub_tasks(1)

    assert len(subtasks) == 1
    assert subtasks[0].id == 2


async def test_get_full_details(megaplan_api, tasks):
    """Test getting full task details with related entities."""
    # Mock main task with milestones field
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "responsible": {"id": 10, "contentType": "Employee"},
            "owner": {"id": 11, "contentType": "Employee"},
            "milestones": [
                {
                    "id": 100,
                    "contentType": "Milestone",
                    "name": "Test Milestone",
                    "type": "report",
                    "date": "2026-02-01T10:00:00Z",
                }
            ],
        },
    )

    # Mock subtasks
    megaplan_api.get(
        "task/1/subTasks", data=[{"id": 2, "contentType": "Task", "name": "Subtask 1"}]
    )

    # Mock actual subtasks
    megaplan_api.get(
        "task/1/actualSubTasks", data=[{"id": 3, "contentType": "Task", "name": "Actual Subtask"}]
    )

    # Mock comments
    megaplan_api.get(
        "task/1/comments", data=[{"id": 1, "contentType": "Comment", "text": "Test comment"}]
    )

    # Mock history
    megaplan_api.get("task/1/history", data=[{"id": 1, "action": "created"}])

    # Mock auditors
    megaplan_api.get("task/1/auditors", data=[{"id": 15, "contentType": "Employee"}])

    # Mock executors
    megaplan_api.get("task/1/executors", data=[{"id": 16, "contentType": "Employee"}])

    # Mock milestones
    megaplan_api.get("task/1/milestones", data=[{"id": 1, "name": "Milestone 1"}])

    # Mock responsible employee
    megaplan_api.get(
        "employee/10",
        data={"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
    )

    # Mock owner employee
    megaplan_api.get(
        "employee/11",
        data={"id": 11, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
    )

    full_details = await tasks.get_full_details(
        task_id=1,
        include_sub_tasks=True,
        include_actual_sub_tasks=True,
        include_comments=True,
        include_history=True,
        include_auditors=True,
        include_executors=True,
        include_milestones=True,
        include_responsible_details=True,
        include_owner_details=True,
    )

    # Check main task
    assert full_details.task.id == 1
    assert full_details.task.name == "Test Task"

    # Check related data
    assert full_details.sub_tasks is not None
    assert len(full_details.sub_tasks) == 1
    assert full_details.sub_tasks[0].name == "Subtask 1"

    assert full_details.actual_sub_tasks is not None
    assert len(full_details.actual_sub_tasks) == 1

    assert full_details.comments is not None
    assert len(full_details.comments) == 1

    assert full_details.history is not None
    assert len(full_details.history) == 1

    assert full_details.auditors is not None
    assert len(full_details.auditors) == 1

    assert full_details.executors is not None
    assert len(full_details.executors) == 1

    assert full_details.milestones is not None
    assert len(full_details.milestones) == 1

    assert full_details.responsible_details is not None
    assert full_details.responsible_details.first_name == "John"

    assert full_details.owner_details is not None
    assert full_details.owner_details.first_name == "Jane"


async def test_get_milestones(megaplan_api, tasks):
    """Test getting task milestones via get_full_details."""
    # Mock task with milestones field
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "milestones": [
                {
                    "id": 1,
                    "contentType": "Milestone",
                    "name": "Release 1.0",
                    "description": "Release milestone",
                    "type": "report",
                    "date": "2026-02-01T10:00:00Z",
                }
            ],
        },
    )

    milestones = await tasks.get_milestones(task_id=1)

    assert len(milestones) == 1
    assert milestones[0].id == 1
    assert milestones[0].name == "Release 1.0"
    assert milestones[0].type == "report"


async def test_get_milestones_500_error(megaplan_api, tasks):
    """Test handling 500 error when getting milestones via get_full_details."""

    # Mock task endpoint returning 500 error
    megaplan_api.get(
        "task/1",
        status=500,
        json={"meta": {"status": 500, "errors": ["Internal Server Error"]}},
    )

    # Should return empty list instead of raising exception
    milestones = await tasks.get_milestones(task_id=1)

    assert milestones == []


async def test_add_milestone_dict(megaplan_api, tasks):
    """Test adding milestone using dict."""
    megaplan_api.post(
        "task/1/milestones",
        data={
            "id": 1,
            "contentType": "Milestone",
            "name": "Release 1.0",
            "description": "Release milestone",
            "type": "report",
            "date": "2026-02-01T10:00:00Z",
        },
    )

    milestone = await tasks.add_milestone(
        task_id=1,
        milestone_data={
            "name": "Release 1.0",
            "description": "Release milestone",
            "type": "report",
            "date": "2026-02-01T10:00:00Z",
        },
    )

    assert milestone.id == 1
    assert milestone.name == "Release 1.0"
    assert milestone.description == "Release milestone"
    assert milestone.type == "report"


async def test_add_milestone_model(megaplan_api, tasks):
    """Test adding milestone using Milestone model."""
    from megaplan_sdk.models.milestone import Milestone

    megaplan_api.post(
        "task/1/milestones",
        data={
            "id": 2,
            "contentType": "Milestone",
            "name": "Phase 1",
            "description": "First phase milestone",
            "type": "reminder",
            "date": "2026-03-01T10:00:00Z",
        },
    )

    milestone_data = Milestone(
        name="Phase 1",
        description="First phase milestone",
        type="reminder",
        date="2026-03-01T10:00:00Z",
    )
    milestone = await tasks.add_milestone(task_id=1, milestone_data=milestone_data)

    assert milestone.id == 2
    assert milestone.name == "Phase 1"
    assert milestone.description == "First phase milestone"
    assert milestone.type == "reminder"


async def test_get_available_parents(megaplan_api, tasks):
    """Test getting available parent tasks/projects for a new task."""
    megaplan_api.get(
        "task/availableParents",
        data=[
            {"id": 1, "contentType": "Task", "name": "Parent Task 1"},
            {"id": 2, "contentType": "Project", "name": "Parent Project 1"},
            {"id": 3, "contentType": "Task", "name": "Parent Task 2"},
        ],
    )

    parents = await tasks.get_available_parents()

    assert len(parents) == 3
    # First item is Task
    assert parents[0].id == 1
    assert parents[0].name == "Parent Task 1"
    assert type(parents[0]).__name__ == "Task"
    # Second item is Project
    assert parents[1].id == 2
    assert parents[1].name == "Parent Project 1"
    assert type(parents[1]).__name__ == "Project"
    # Third item is Task
    assert parents[2].id == 3
    assert type(parents[2]).__name__ == "Task"


async def test_get_available_parents_with_limit(megaplan_api, tasks):
    """Test getting available parents with limit parameter."""
    megaplan_api.get(
        "task/availableParents?{%22limit%22:%205}",
        data=[
            {"id": 1, "contentType": "Task", "name": "Parent Task 1"},
        ],
    )

    parents = await tasks.get_available_parents(limit=5)

    assert len(parents) == 1
    assert parents[0].id == 1


async def test_get_available_parents_with_template_filter(megaplan_api, tasks):
    """Test getting available parents with isTemplate filter."""
    megaplan_api.get(
        "task/availableParents?{%22isTemplate%22:%20false}",
        data=[
            {"id": 1, "contentType": "Project", "name": "Regular Project"},
        ],
    )

    parents = await tasks.get_available_parents(is_template=False)

    assert len(parents) == 1
    assert parents[0].name == "Regular Project"


async def test_get_available_parents_for_task(megaplan_api, tasks):
    """Test getting available parents for a specific task."""
    megaplan_api.get(
        "task/123/availableParents",
        data=[
            {"id": 10, "contentType": "Project", "name": "Project A"},
            {"id": 20, "contentType": "Task", "name": "Task B"},
        ],
    )

    parents = await tasks.get_available_parents_for(123)

    assert len(parents) == 2
    assert parents[0].id == 10
    assert type(parents[0]).__name__ == "Project"
    assert parents[1].id == 20
    assert type(parents[1]).__name__ == "Task"


async def test_get_available_parents_for_task_with_params(megaplan_api, tasks):
    """Test getting available parents for task with all parameters."""
    megaplan_api.get(
        "task/456/availableParents?{%22limit%22:%2010,%20%22isTemplate%22:%20false}",
        data=[{"id": 1, "contentType": "Task", "name": "Parent"}],
    )

    parents = await tasks.get_available_parents_for(task_id=456, limit=10, is_template=False)

    assert len(parents) == 1


async def test_get_available_parents_empty_result(megaplan_api, tasks):
    """Test getting available parents when none available."""
    megaplan_api.get("task/availableParents", data=[])

    parents = await tasks.get_available_parents()

    assert len(parents) == 0
    assert parents == []


async def test_get_all_participants_employees(megaplan_api, tasks):
    """Test getting all participants with Employee responses."""
    megaplan_api.get(
        "task/123/allParticipants",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
            {"id": 2, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
        ],
    )

    participants = await tasks.get_all_participants(task_id=123)

    assert len(participants) == 2
    assert participants[0].id == 1
    assert participants[0].content_type == "Employee"
    assert participants[0].first_name == "John"
    assert participants[1].id == 2
    assert participants[1].first_name == "Jane"


async def test_get_all_participants_mixed_types(megaplan_api, tasks):
    """Test getting all participants with mixed types (Employee, ContractorHuman, Group)."""
    megaplan_api.get(
        "task/456/allParticipants",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John"},
            {"id": 2, "contentType": "ContractorHuman", "firstName": "Bob", "lastName": "Client"},
            {"id": 3, "contentType": "Group", "name": "Developers"},
        ],
    )

    participants = await tasks.get_all_participants(task_id=456)

    assert len(participants) == 3

    # Check Employee
    from megaplan_sdk.models.employee import Employee

    assert isinstance(participants[0], Employee)
    assert participants[0].first_name == "John"

    # Check ContractorHuman
    from megaplan_sdk.models.contractor import ContractorHuman

    assert isinstance(participants[1], ContractorHuman)
    assert participants[1].first_name == "Bob"

    # Check Group
    from megaplan_sdk.models.group import Group

    assert isinstance(participants[2], Group)
    assert participants[2].name == "Developers"


async def test_get_all_participants_empty(megaplan_api, tasks):
    """Test getting all participants when task has no participants."""
    megaplan_api.get("task/789/allParticipants", data=[])

    participants = await tasks.get_all_participants(task_id=789)

    assert len(participants) == 0
    assert participants == []


async def test_get_all_participants_with_pagination(megaplan_api, tasks):
    """Test getting all participants with pagination params."""
    megaplan_api.get(
        "task/123/allParticipants?{%22limit%22:%2050}",
        data=[{"id": 1, "contentType": "Employee", "firstName": "John"}],
    )

    participants = await tasks.get_all_participants(task_id=123, limit=50)

    assert len(participants) == 1


def test_task_parses_activity_and_time_fields():
    """Test that Task model parses activity and time fields from API camelCase keys."""
    from megaplan_sdk.models.task import Task

    task = Task(
        **{
            "contentType": "Task",
            "id": 1,
            "activity": "2026-06-20T10:00:00+00:00",
            "lastCommentTimeCreated": "2026-06-19T09:00:00+00:00",
            "statusChangeTime": "2026-06-18T08:00:00+00:00",
            "actualStart": "2026-06-17T07:00:00+00:00",
            "lastView": "2026-06-21T06:00:00+00:00",
        }
    )
    assert task.activity == "2026-06-20T10:00:00+00:00"
    assert task.last_comment_time_created == "2026-06-19T09:00:00+00:00"
    assert task.status_change_time == "2026-06-18T08:00:00+00:00"
    assert task.actual_start == "2026-06-17T07:00:00+00:00"
    assert task.last_view == "2026-06-21T06:00:00+00:00"


async def test_list_rejects_time_updated_sort_with_suggestion(tasks):
    """Test that sorting by timeUpdated raises ValueError with suggestion."""
    with pytest.raises(ValueError) as exc:
        await tasks.list(sort_by=[{"fieldName": "timeUpdated", "desc": "true"}])
    assert "timeUpdated" in str(exc.value)
    assert "activity" in str(exc.value)


async def test_list_rejects_updated_at_sort_with_suggestion(tasks):
    """Test that sorting by updatedAt raises ValueError with suggestion."""
    with pytest.raises(ValueError) as exc:
        await tasks.list(sort_by=[{"fieldName": "updatedAt", "desc": "true"}])
    assert "updatedAt" in str(exc.value)
    assert "activity" in str(exc.value)


def test_default_task_list_fields_exported():
    """Test that DEFAULT_TASK_LIST_FIELDS is exported from megaplan_sdk."""
    import megaplan_sdk

    fields = megaplan_sdk.DEFAULT_TASK_LIST_FIELDS
    assert isinstance(fields, tuple)
    # Confirmed-valid task fields from the bug journal #7/#8.
    for required in ("timeCreated", "activity", "lastCommentTimeCreated", "status"):
        assert required in fields
    # Must NOT include the API-rejected field (regression guard against #7).
    assert "timeUpdated" not in fields


async def test_list_allows_valid_sort_field(megaplan_api, tasks):
    """Test that a valid/custom sort field is NOT rejected by the deny-map."""
    megaplan_api.get("task", data=[])
    result = await tasks.list(sort_by=[{"fieldName": "activity", "desc": True}])
    assert result == []


async def test_list_defaults_to_timecreated_desc(megaplan_api, tasks):
    """Test that list() defaults to timeCreated DESC sorting."""
    import json
    import urllib.parse

    route = megaplan_api.get("task", data=[])
    await tasks.list(limit=5)
    query_str = route.calls.last.request.url.query.decode()
    sent = json.loads(urllib.parse.unquote(query_str))
    assert sent["sortBy"] == [
        {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
    ]


async def test_list_empty_sort_opts_out(megaplan_api, tasks):
    """Test that sort_by=[] opts out of default sorting."""
    import urllib.parse

    route = megaplan_api.get("task", data=[])
    await tasks.list(limit=5, sort_by=[])
    query_str = route.calls.last.request.url.query.decode()
    assert "sortBy" not in urllib.parse.unquote(query_str)


async def test_q_is_converted_to_name_filter(megaplan_api, tasks):
    """Test that q= is converted to a FilterBuilder name filter, never sent raw."""
    import urllib.parse

    route = megaplan_api.get("task", data=[])
    await tasks.list(q="ДВФМ", limit=5)
    query_str = route.calls.last.request.url.query.decode()
    unquoted = urllib.parse.unquote(query_str)
    assert '"q"' not in unquoted  # raw q must never be sent
    parsed = json.loads(unquoted)
    term = parsed["filter"]["config"]["termGroup"]["terms"][0]
    assert term["field"] == "name"
    assert term["comparison"] == "contains"
    assert term["value"] == "ДВФМ"


async def test_q_in_description_raises(tasks):
    """Test that q_in with unsupported field raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await tasks.list(q="x", q_in=["description"])


async def test_q_with_filter_raises(tasks):
    """Test that passing both q and filter raises ValueError."""
    with pytest.raises(ValueError):
        await tasks.list(q="x", filter="incoming")


async def test_get_many_returns_dict_by_id_and_drops_missing(megaplan_api, tasks):
    """get_many returns dict[id->Task]; ids absent from response are dropped."""
    route = megaplan_api.post(
        "bulk/getEntitiesByLinks",
        data=[
            {"contentType": "Task", "id": "1006174", "name": "A"},
            {"contentType": "Task", "id": "1006206", "name": "B"},
        ],  # note: requested 99999999 is absent
    )
    result = await tasks.get_many([1006174, 1006206, 99999999])
    assert set(result.keys()) == {1006174, 1006206}
    assert result[1006174].name == "A"
    body = json.loads(route.calls.last.request.content)
    assert isinstance(body, list)
    assert {"contentType": "Task", "id": "1006174"} in body


async def test_get_many_cache_hit_skips_bulk_post(megaplan_api, http_client):
    """When all requested ids are already cached, get_many must NOT issue a bulk POST."""
    from megaplan_sdk.cache import EntityCache

    cache = EntityCache(max_size=100, ttl=300)
    task_dict = {"contentType": "Task", "id": 1006174, "name": "Cached Task"}
    cache.set("Task", 1006174, task_dict)

    route = megaplan_api.post("bulk/getEntitiesByLinks", data=[])

    resource = TasksResource(http_client, cache=cache)
    result = await resource.get_many([1006174])

    assert 1006174 in result
    assert result[1006174].name == "Cached Task"
    assert not route.called


async def test_create_comment_encodes_work_as_value_seconds(megaplan_api, tasks):
    """#21/#22: create_comment must serialize work as DateInterval.value (seconds).

    Regression: the old helper wrote {"seconds": ...}, which the server silently
    dropped (workTime stored 0). It must match comments.create exactly:
    {"contentType": "DateInterval", "value": int(work * 3600)}.
    """
    route = megaplan_api.post("task/1/comments", data={"id": 7, "contentType": "Comment"})

    with pytest.warns(DeprecationWarning, match="comments.create"):
        await tasks.create_comment(task_id=1, text="x", work=1.0)

    body = json.loads(route.calls.last.request.content)
    assert body["content"] == "x"
    assert body["workTime"] == {"contentType": "DateInterval", "value": 3600}
    assert "seconds" not in body["workTime"]


async def test_iterate_forwards_fields_to_list(megaplan_api, tasks):
    """#24: iterate() forwards fields/sort_by/expand kwargs to list()."""
    route = megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "T",
                "timeCreated": {"contentType": "DateTime", "value": "2026-06-20T00:00:00+00:00"},
            }
        ],
    )

    collected = [t async for t in tasks.iterate(limit=5, fields=["name", "timeCreated"])]

    assert collected and collected[0].time_created is not None
    sent_url = str(route.calls.last.request.url)
    assert "timeCreated" in sent_url


async def test_list_page_after_accepts_int(megaplan_api, tasks):
    """#23: page_after=int is wrapped into {contentType, id} link automatically."""
    route = megaplan_api.get("task", data=[])
    await tasks.list(limit=5, page_after=12345)

    from urllib.parse import unquote

    decoded = unquote(str(route.calls.last.request.url)).replace(" ", "")
    assert '"pageAfter":{"contentType":"Task","id":12345}' in decoded


# --- #30: expand_comment_owners in get_full_details ---


async def test_get_full_details_expand_comment_owners_resolves_employees(megaplan_api, tasks):
    """#30: expand_comment_owners=True resolves comment Employee owners."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})
    megaplan_api.get(
        "task/1/comments",
        data=[
            {
                "id": 1,
                "contentType": "Comment",
                "content": "first",
                "owner": {"contentType": "Employee", "id": 1000037},
            },
            {
                "id": 2,
                "contentType": "Comment",
                "content": "second",
                "owner": {"contentType": "Employee", "id": 1000037},
            },
        ],
    )
    employee_route = megaplan_api.get(
        "employee/1000037",
        data={"contentType": "Employee", "id": 1000037, "name": "Иван Петров"},
    )

    details = await tasks.get_full_details(
        task_id=1, include_comments=True, expand_comment_owners=True
    )

    assert details.comments is not None
    assert details.comments[0].owner.name == "Иван Петров"
    assert details.comments[1].owner.name == "Иван Петров"
    # Batch loading: one employee request for repeated owner id
    assert employee_route.call_count == 1


async def test_get_full_details_expand_comment_owners_requires_include_comments(
    megaplan_api, tasks
):
    """#30: expand_comment_owners without include_comments raises ValueError."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})

    with pytest.raises(ValueError, match="include_comments"):
        await tasks.get_full_details(task_id=1, expand_comment_owners=True)


async def test_get_full_details_comment_owners_stay_stubs_by_default(megaplan_api, tasks):
    """#30: without the flag comment owners remain bare references (back-compat)."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
    megaplan_api.get(
        "task/1/comments",
        data=[
            {
                "id": 1,
                "contentType": "Comment",
                "content": "first",
                "owner": {"contentType": "Employee", "id": 1000037},
            }
        ],
    )

    details = await tasks.get_full_details(task_id=1, include_comments=True)

    assert details.comments is not None
    assert details.comments[0].owner.name is None
