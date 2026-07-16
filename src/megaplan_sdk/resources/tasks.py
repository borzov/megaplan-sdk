"""Tasks resource for Megaplan API."""

from __future__ import annotations

import warnings
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, cast, overload

from megaplan_sdk.constants import (
    DEFAULT_SORT_RECENT,
    ContentType,
)
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.task import Task, TaskFullDetails
from megaplan_sdk.pagination import Page
from megaplan_sdk.registry import filter_content_type_for
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.full_details import FullDetailsMixin, RelatedDataConfig

# VALID_TASK_STATUSES is re-exported for backwards compatibility; the
# canonical definition and all task list validation live in task_query.py
from megaplan_sdk.task_query import (
    VALID_TASK_STATUSES,
    TaskQuery,
    validate_task_fields,
    validate_task_sort_field,
    validate_task_statuses,
)
from megaplan_sdk.types import FilterType

if TYPE_CHECKING:
    from megaplan_sdk.models.milestone import Milestone
    from megaplan_sdk.models.participant import Participant

__all__ = ["VALID_TASK_STATUSES", "TasksResource"]


class TasksResource(BaseResource, FullDetailsMixin):
    """Resource for working with tasks."""

    _page_content_type = ContentType.TASK
    _filter_content_type = filter_content_type_for("task")

    _expand_rules = {
        "responsible": ExpandRule("employee", Employee, details_field="responsible_details"),
        "owner": ExpandRule("employee", Employee, details_field="owner_details"),
    }
    _details_model = TaskFullDetails
    _main_field = "task"

    _full_details_config = [
        RelatedDataConfig("sub_tasks", "include_sub_tasks", "get_sub_tasks"),
        RelatedDataConfig("actual_sub_tasks", "include_actual_sub_tasks", "get_actual_sub_tasks"),
        RelatedDataConfig(
            "comments", "include_comments", "get_comments", limit_param="comments_limit"
        ),
        RelatedDataConfig("history", "include_history", "get_history", limit_param="history_limit"),
        RelatedDataConfig("auditors", "include_auditors", "get_auditors"),
        RelatedDataConfig("executors", "include_executors", "get_executors"),
        RelatedDataConfig("milestones", "include_milestones", "get_milestones"),
        RelatedDataConfig(
            "responsible_details",
            "include_responsible_details",
            None,
            entity_field="responsible",
            entity_type="employee",
        ),
        RelatedDataConfig(
            "owner_details",
            "include_owner_details",
            None,
            entity_field="owner",
            entity_type="employee",
        ),
    ]

    def __init__(
        self,
        http_client,
        cache=None,
        default_comments_limit: int | None = None,
        default_history_limit: int | None = None,
    ) -> None:
        """Initialize tasks resource.

        Args:
            http_client: HTTP client for making requests.
            cache: Optional entity cache.
            default_comments_limit: Default limit for comments in get_full_details().
            default_history_limit: Default limit for history in get_full_details().
        """
        super().__init__(
            http_client,
            cache=cache,
            default_comments_limit=default_comments_limit,
            default_history_limit=default_history_limit,
        )

    async def create(self, task_data: dict[str, Any], auto_fill_required: bool = True) -> Task:
        """Create a new task.

        Args:
            task_data: Task data dictionary.
            auto_fill_required: Automatically fill required fields if not provided.
                Default: True. Sets isUrgent=False and isTemplate=False if not specified.

        Returns:
            Created task.

        Examples:
            >>> # Minimal task creation (auto-fills required fields)
            >>> task = await client.tasks.create({"name": "New task"})
            >>>
            >>> # With explicit required fields
            >>> task = await client.tasks.create({
            ...     "name": "New task",
            ...     "isUrgent": True,
            ...     "isTemplate": False
            ... })
        """
        # Auto-fill required fields if not provided
        if auto_fill_required:
            if "isUrgent" not in task_data:
                task_data["isUrgent"] = False
            if "isTemplate" not in task_data:
                task_data["isTemplate"] = False

        return await self._create_entity("task", task_data, Task)

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        statuses: list[str] | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: None = None,
    ) -> list[Task]: ...

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        statuses: list[str] | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str],
    ) -> list[TaskFullDetails]: ...

    async def list(
        self,
        filter: FilterType | None = None,
        statuses: list[str] | None = None,
        q: str | None = None,
        q_in: list[str] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Task] | list[TaskFullDetails]:
        """Get list of tasks.

        Args:
            filter: Task filter (ID, string ID, or filter object with contentType and id).
                If filter is int/str, it will be converted to {"contentType": "TaskFilter", "id": filter}.
                If filter is dict, it will be used as is.
            statuses: List of statuses to filter by.
                Valid values: "created", "assigned", "accepted", "done", "completed",
                "rejected", "cancelled", "expired", "delayed", "template", "overdue".
                Invalid status values will cause 422 ValidationError.
                The array is serialized as JSON in query string: {"statuses": ["assigned", "accepted"]}
            q: Text search by name (converted to a server-side name filter; #11).
                Use q_in=["name", "statement"] to also match statement.
                Other fields are silently ignored by the API.
                Cannot be combined with ``filter`` — raises ValueError.
            q_in: Fields to search within when ``q`` is provided (default: ["name"]).
                Allowed values: "name", "statement".
                Other values raise NotImplementedError (silently ignored by server).
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to include.
                **Important:** list endpoints do NOT return date fields
                (timeCreated, activity, lastCommentTimeCreated, ...) unless
                requested here. To filter by a time window, pass:
                    from megaplan_sdk import DEFAULT_TASK_LIST_FIELDS
                    tasks = await client.tasks.list(fields=list(DEFAULT_TASK_LIST_FIELDS))
                Without this, those fields are None and time-window filters
                silently match nothing.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["responsible", "owner"]).
                Supported values: "responsible", "owner".
                If provided, returns list[TaskFullDetails] instead of list[Task].

        Returns:
            List of tasks (list[Task] if expand is None, list[TaskFullDetails] otherwise).

        Examples:
            >>> # Get tasks without expansion
            >>> tasks = await client.tasks.list(limit=10)
            >>>
            >>> # Get tasks with text search
            >>> tasks = await client.tasks.list(q="договор", limit=10)
            >>>
            >>> # Get tasks with filter by ID
            >>> tasks = await client.tasks.list(filter="incoming", limit=10)
            >>>
            >>> # Get tasks with filter object
            >>> tasks = await client.tasks.list(filter={"contentType": "TaskFilter", "id": "incoming"})
            >>>
            >>> # Get tasks with expanded responsible and owner
            >>> tasks_full = await client.tasks.list(
            ...     limit=10, expand=["responsible", "owner"]
            ... )
            >>> for task_full in tasks_full:
            ...     if task_full.responsible_details:
            ...         print(task_full.responsible_details.display_name())
        """
        path = self._build_path("api", "v3", "task")

        # #14: bare list order is not by date; default to newest-first.
        # sort_by=[] is an explicit opt-out (keeps server's native order).
        if sort_by is None:
            sort_by = list(DEFAULT_SORT_RECENT)

        # #11: raw `q` is ignored server-side; convert to a real name filter.
        if q is not None:
            if filter is not None:
                raise ValueError("Pass either `q` or `filter`, not both.")
            filter = self._q_to_filter(self._filter_content_type, q, q_in or ["name"])
            q = None

        # Validate statuses if provided
        if statuses:
            validate_task_statuses(statuses)

        # Validate sort_by against fields the API rejects with a raw 422 (#7).
        if sort_by:
            for rule in sort_by:
                field_name = rule.get("fieldName")
                if field_name is not None:
                    validate_task_sort_field(field_name)

        # Validate fields against known-unsupported synonyms (raw 422) (#32).
        if fields and isinstance(fields, list | tuple):
            validate_task_fields([f for f in fields if isinstance(f, str)])

        # Convert filter ID to object format if needed
        processed_filter = filter
        if filter is not None and isinstance(filter, int | str) and not isinstance(filter, dict):
            # Convert ID to filter object format
            processed_filter = {"contentType": self._filter_content_type, "id": str(filter)}

        # Use base method to build params (DRY)
        params = self._build_list_params(
            filter=processed_filter,
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            statuses=statuses,  # Extra param specific to tasks
        )

        tasks = await self._get_list(path, Task, params)
        return await self._expand_and_wrap(tasks, expand)

    async def list_by(self, query: TaskQuery) -> list[Task]:
        """Get list of tasks described by a :class:`TaskQuery`.

        The query is validated at construction time — invalid combinations
        (search+filter, bad statuses, unsupported sort fields, unfilterable
        search fields) never reach the wire.

        Args:
            query: Query built fluently with TaskQuery().

        Returns:
            List of tasks.

        Examples:
            >>> query = (
            ...     TaskQuery()
            ...     .statuses("assigned", "accepted")
            ...     .sort_by("timeCreated", desc=True)
            ...     .limit(50)
            ... )
            >>> tasks = await client.tasks.list_by(query)
        """
        return cast("list[Task]", await self.list(**query.as_list_kwargs()))

    async def get(self, task_id: int, fields: list[str] | None = None) -> Task:
        """Get task by ID.

        Args:
            task_id: Task identifier.
            fields: Extra fields to request (e.g. ``["commentsCount"]``).

        Returns:
            Task details.
        """
        return await self._get_entity("task", task_id, Task, fields=fields)

    async def get_many(self, ids: list[int], use_cache: bool = True) -> dict[int, Task]:
        """Batch-fetch tasks by id via the bulk endpoint (#FR-1).

        Args:
            ids: Task ids to load (duplicates ignored).
            use_cache: Read/populate the entity cache (default: True).

        Returns:
            Dict mapping id -> Task. Inaccessible ids are absent.

        Examples:
            >>> tasks = await client.tasks.get_many([1006174, 1006175])
            >>> tasks[1006174].name
        """
        return await self._get_many_via_bulk(ContentType.TASK, ids, Task, use_cache)

    async def update(self, task_id: int, task_data: dict[str, Any]) -> Task:
        """Update task.

        Args:
            task_id: Task identifier.
            task_data: Updated task data.

        Returns:
            Updated task.
        """
        return await self._update_entity("task", task_id, task_data, Task)

    async def delete(self, task_id: int) -> None:
        """Delete task.

        Args:
            task_id: Task identifier.
        """
        await self._delete_entity("task", task_id)

    async def get_sub_tasks(
        self,
        task_id: int,
        filters: list[dict[str, Any]] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task]:
        """Get subtasks of a task.

        Args:
            task_id: Task identifier.
            filters: Task result type filters.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of subtasks.
        """
        path = self._build_path("api", "v3", "task", str(task_id), "subTasks")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            filters=filters,
        )

        return await self._get_list(path, Task, params)

    async def get_actual_sub_tasks(
        self,
        task_id: int,
        filters: list[dict[str, Any]] | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task]:
        """Get actual subtasks of a task.

        Args:
            task_id: Task identifier.
            filters: Task result type filters.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of actual subtasks.
        """
        path = self._build_path("api", "v3", "task", str(task_id), "actualSubTasks")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            filters=filters,
        )

        return await self._get_list(path, Task, params)

    def _parse_tree_node_id(self, node_id: str | int) -> int | None:
        """Parse numeric ID from tree node ID string.

        API returns tree nodes with string IDs in format "Task:ID:hash" or "Project:ID:hash".
        This method extracts the numeric ID from the string format.

        Args:
            node_id: Node ID as string (e.g., "Task:1005808:dcca48101505dd86b703689a604fe3c4")
                     or integer (returned as is).

        Returns:
            Numeric ID if parsing successful, None otherwise.

        Examples:
            >>> resource._parse_tree_node_id("Task:1005808:dcca48101505dd86b703689a604fe3c4")
            1005808
            >>> resource._parse_tree_node_id(123)
            123
        """
        if isinstance(node_id, int):
            return node_id

        if not isinstance(node_id, str):
            return None

        # Format: "Task:1005808:dcca48101505dd86b703689a604fe3c4"
        # Extract ID between first and second colon
        parts = node_id.split(":")
        if len(parts) >= 2:
            try:
                # Extract numeric ID (second part)
                return int(parts[1])
            except (ValueError, IndexError):
                # If parsing fails, log warning and return None
                from megaplan_sdk.logging_config import logger

                logger.warning(
                    f"Could not parse tree node ID from '{node_id}', expected format 'Type:ID:hash'"
                )
                return None

        return None

    async def tree_level(
        self,
        filter: FilterType | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task]:
        """Get filtered list of projects or tasks at current tree level.

        Note: API returns tasks with string IDs in format "Task:ID:hash" or "Project:ID:hash".
        This method extracts the numeric ID from the string format.

        Args:
            filter: Task filter (ID or config).
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of tasks/projects at current tree level.

        Examples:
            >>> tasks = await client.tasks.tree_level(limit=10)
        """
        path = self._build_path("api", "v3", "task", "treeLevel")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            filter=filter,
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        # Get raw response to process string IDs
        response = await self._http.get(path, params=params if params else None)
        data: list[dict[str, Any]] = response.get("data", [])

        # Process items: extract numeric ID from string format "Task:ID:hash" or "Project:ID:hash"
        processed_items: list[dict[str, Any]] = []
        for item in data:
            processed_item = item.copy()
            # If id is a string in format "Type:ID:hash", extract the numeric ID
            item_id = processed_item.get("id")
            if item_id is not None:
                parsed_id = self._parse_tree_node_id(item_id)
                if parsed_id is not None:
                    processed_item["id"] = parsed_id

            processed_items.append(processed_item)

        # Parse processed items into Task models
        return [Task(**item) if isinstance(item, dict) else item for item in processed_items]

    async def iterate(
        self,
        filter: FilterType | None = None,
        statuses: list[str] | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Task]:
        """Iterate over all tasks with automatic pagination.

        Forwards every extra keyword (``fields``, ``sort_by``, ``expand``,
        ``q``, ``q_in``, ...) straight to :meth:`list` (#24). Without this,
        iterated tasks came back without date fields (e.g. ``time_created``
        was ``None``), which broke "walk all tasks from the last N days".

        Args:
            filter: Task filter (ID or config).
            statuses: List of statuses to filter by.
            limit: Number of items per page.
            **kwargs: Additional parameters passed through to ``list()``
                (e.g. ``fields=[...]``, ``sort_by=[...]``, ``expand=[...]``).

        Yields:
            Task objects.

        Examples:
            >>> async for task in client.tasks.iterate(
            ...     limit=100, fields=["name", "timeCreated"]
            ... ):
            ...     print(task.time_created)
        """
        task: Task
        async for task in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.TASK,
            self.list,
            limit,
            filter=filter,
            statuses=statuses,
            **kwargs,
        ):
            yield task

    async def get_comments(
        self,
        task_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Comment]:
        """Get comments for a task.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of comments.

        Examples:
            >>> comments = await client.tasks.get_comments(task_id=123)
        """
        return await self._get_entity_comments(
            "task",
            task_id,
            limit,
            page_after,
            page_before,
            page_with,
        )

    async def create_comment(
        self,
        task_id: int,
        text: str,
        work: float | None = None,
        attaches: list[dict[str, Any]] | None = None,
    ) -> Comment:
        """Create a comment for a task.

        Thin wrapper over :meth:`CommentsResource.create` (#21/#22): both
        encode ``work`` identically as ``workTime.value`` (seconds). Prefer
        ``client.comments.create(entity_id=..., content=...)`` directly; this
        helper is kept for backwards compatibility.

        Args:
            task_id: Task identifier.
            text: Comment text (maps to the API ``content`` field).
            work: Hours worked (time tracking). ``work=2.5`` ⇒ 2 h 30 min.
                Serialized as ``{"contentType": "DateInterval",
                "value": int(work * 3600)}``; the server quantizes to minutes.
            attaches: List of file attachments.

        Returns:
            Created comment.

        Examples:
            >>> comment = await client.tasks.create_comment(
            ...     task_id=123,
            ...     text="Work completed",
            ...     work=2.5
            ... )
        """
        warnings.warn(
            "tasks.create_comment() is deprecated and will be removed in 0.5.0; "
            'use client.comments.create(entity_id=..., content=..., entity_type="task").',
            DeprecationWarning,
            stacklevel=2,
        )
        from megaplan_sdk.resources.comments import CommentsResource

        comments = CommentsResource(self._http, cache=self._cache)
        return await comments.create(
            entity_id=task_id,
            content=text,
            entity_type="task",
            work=work,
            attaches=attaches,
        )

    async def create_simple(
        self,
        name: str,
        responsible_id: int | None = None,
        subject: str | None = None,
        employees_resource: Any | None = None,
    ) -> Task:
        """Create a task with minimal required parameters.

        Automatically fills required fields (isUrgent, isTemplate) and optionally
        determines responsible from current user if not provided.

        Args:
            name: Task name (required).
            responsible_id: Responsible employee ID. If None and employees_resource
                is provided, uses current user.
            subject: Task description/subject.
            employees_resource: EmployeesResource instance for auto-detecting current user.
                If provided and responsible_id is None, will use current user as responsible.

        Returns:
            Created task.

        Examples:
            >>> # Simple task with current user as responsible
            >>> task = await client.tasks.create_simple(
            ...     "New task",
            ...     employees_resource=client.employees
            ... )
            >>>
            >>> # Simple task with specific responsible
            >>> task = await client.tasks.create_simple(
            ...     "New task",
            ...     responsible_id=123
            ... )
        """
        task_data: dict[str, Any] = {
            "name": name,
            "isUrgent": False,
            "isTemplate": False,
        }

        if subject:
            task_data["subject"] = subject

        # Auto-determine responsible from current user if not provided
        if responsible_id is None and employees_resource:
            try:
                current_user = await employees_resource.get_current()
                responsible_id = current_user.id
            except Exception:
                # If we can't get current user, skip responsible
                # API will return error if required
                pass

        if responsible_id:
            task_data["responsible"] = {"contentType": ContentType.EMPLOYEE, "id": responsible_id}

        return await self.create(task_data, auto_fill_required=False)

    async def create_in_project(
        self,
        name: str,
        project_id: int,
        responsible_id: int | None = None,
        subject: str | None = None,
        employees_resource: Any | None = None,
    ) -> Task:
        """Create a task inside a project.

        Automatically sets parent relationship to project and updates task after creation
        to establish the link (as required by Megaplan API).

        Args:
            name: Task name (required).
            project_id: Project ID to create task in.
            responsible_id: Responsible employee ID. If None and employees_resource
                is provided, uses current user.
            subject: Task description/subject.
            employees_resource: EmployeesResource instance for auto-detecting current user.
                If provided and responsible_id is None, will use current user as responsible.

        Returns:
            Created task (linked to project).

        Examples:
            >>> # Create task in project with current user as responsible
            >>> task = await client.tasks.create_in_project(
            ...     "Task in project",
            ...     project_id=456,
            ...     employees_resource=client.employees
            ... )
            >>>
            >>> # Create task in project with specific responsible
            >>> task = await client.tasks.create_in_project(
            ...     "Task in project",
            ...     project_id=456,
            ...     responsible_id=123
            ... )
        """
        # Create task first
        task = await self.create_simple(
            name=name,
            responsible_id=responsible_id,
            subject=subject,
            employees_resource=employees_resource,
        )

        # Update task to set parent relationship (required by API)
        # Note: parent must be set via update, not create
        update_data = {
            "parent": {"contentType": ContentType.PROJECT, "id": project_id},
        }
        task = await self.update(task.id, update_data)

        return task

    async def get_auditors(
        self,
        task_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get auditors for a task.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of auditors (Employees).

        Examples:
            >>> auditors = await client.tasks.get_auditors(task_id=123)
        """
        return await self._get_entity_related_list(
            "task", task_id, "auditors", limit, page_after, page_before, page_with
        )

    async def add_auditor(
        self,
        task_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> Any:
        """Add auditor to the task.

        Args:
            task_id: Task identifier.
            auditor_id: Auditor ID (usually Employee ID).
            auditor_content_type: Content type (usually "Employee").

        Returns:
            Added auditor.

        Examples:
            >>> auditor = await client.tasks.add_auditor(
            ...     task_id=123,
            ...     auditor_id=456
            ... )
        """
        return await self._add_entity_related(
            "task", task_id, "auditors", auditor_id, auditor_content_type
        )

    async def remove_auditor(
        self,
        task_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Remove auditor from the task.

        Args:
            task_id: Task identifier.
            auditor_id: Auditor ID.
            auditor_content_type: Content type (usually "Employee").

        Examples:
            >>> await client.tasks.remove_auditor(task_id=123, auditor_id=456)
        """
        await self._remove_entity_related(
            "task", task_id, "auditors", auditor_id, auditor_content_type
        )

    async def get_executors(
        self,
        task_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get executors (co-performers) for a task.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of executors (Employees).

        Examples:
            >>> executors = await client.tasks.get_executors(task_id=123)
        """
        return await self._get_entity_related_list(
            "task", task_id, "executors", limit, page_after, page_before, page_with
        )

    async def add_executor(
        self,
        task_id: int,
        executor_id: int,
        executor_content_type: str = ContentType.EMPLOYEE,
    ) -> Any:
        """Add executor (co-performer) to the task.

        Args:
            task_id: Task identifier.
            executor_id: Executor ID (usually Employee ID).
            executor_content_type: Content type (usually "Employee").

        Returns:
            Added executor.

        Examples:
            >>> executor = await client.tasks.add_executor(
            ...     task_id=123,
            ...     executor_id=456
            ... )
        """
        return await self._add_entity_related(
            "task", task_id, "executors", executor_id, executor_content_type
        )

    async def remove_executor(
        self,
        task_id: int,
        executor_id: int,
        executor_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Remove executor from the task.

        Args:
            task_id: Task identifier.
            executor_id: Executor ID.
            executor_content_type: Content type (usually "Employee").

        Examples:
            >>> await client.tasks.remove_executor(task_id=123, executor_id=456)
        """
        await self._remove_entity_related(
            "task", task_id, "executors", executor_id, executor_content_type
        )

    async def get_milestones(
        self,
        task_id: int,
    ) -> list[Milestone]:
        """Get milestones for a task.

        Note: Direct endpoint /task/{id}/milestones returns 500 error.
        This method uses /task/{id} with fields parameter to get milestones.

        Args:
            task_id: Task identifier.

        Returns:
            List of Milestone objects.

        Examples:
            >>> milestones = await client.tasks.get_milestones(task_id=123)
            >>> for milestone in milestones:
            ...     print(f"{milestone.name}: {milestone.date}")
        """
        return await self._get_milestones_generic("task", task_id)

    async def add_milestone(
        self,
        task_id: int,
        milestone_data: Milestone | dict[str, Any],
    ) -> Milestone:
        """Add milestone to the task.

        Args:
            task_id: Task identifier.
            milestone_data: Milestone data as Milestone object or dict.
                Required fields: description, type, date.
                Type must be one of: "report", "reminder", "note".
                Date can be ISO 8601 string, DateTime object, or dict.

        Returns:
            Created Milestone object.

        Examples:
            >>> # Using dict
            >>> milestone = await client.tasks.add_milestone(
            ...     task_id=123,
            ...     milestone_data={
            ...         "name": "Release 1.0",
            ...         "description": "Release milestone",
            ...         "type": "report",
            ...         "date": "2026-02-01T10:00:00Z"
            ...     }
            ... )
            >>>
            >>> # Using Milestone model
            >>> from megaplan_sdk.models.milestone import Milestone
            >>> milestone = await client.tasks.add_milestone(
            ...     task_id=123,
            ...     milestone_data=Milestone(
            ...         name="Release 1.0",
            ...         description="Release milestone",
            ...         type="report",
            ...         date="2026-02-01T10:00:00Z"
            ...     )
            ... )
        """
        return await self._add_milestone_generic("task", task_id, milestone_data)

    async def get_history(
        self,
        task_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get history log for a task.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of history entries.

        Examples:
            >>> history = await client.tasks.get_history(task_id=123, limit=10)
        """
        return await self._get_entity_history(
            "task", task_id, limit, page_after, page_before, page_with
        )

    async def search_history(
        self,
        task_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search in task history log.

        Args:
            task_id: Task identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of matching history entries.

        Examples:
            >>> results = await client.tasks.search_history(task_id=123, query="status")
        """
        return await self._search_entity_history(
            "task", task_id, query, limit, page_after, page_before, page_with
        )

    async def get_full_details(
        self,
        task_id: int,
        include_sub_tasks: bool = False,
        include_actual_sub_tasks: bool = False,
        include_comments: bool = False,
        include_history: bool = False,
        include_auditors: bool = False,
        include_executors: bool = False,
        include_milestones: bool = False,
        include_responsible_details: bool = False,
        include_owner_details: bool = False,
        expand_comment_owners: bool = False,
        resolve_participants: bool = True,
        comments_limit: int | None = None,
        history_limit: int | None = None,
    ) -> TaskFullDetails:
        """Get full task details with related entities.

        This method fetches the task and optionally loads related data in parallel
        for better performance.

        Args:
            task_id: Task identifier.
            include_sub_tasks: Load subtasks.
            include_actual_sub_tasks: Load actual subtasks.
            include_comments: Load task comments.
            include_history: Load change history.
            include_auditors: Load auditors list.
            include_executors: Load executors/co-performers list.
            include_milestones: Load milestones list.
            include_responsible_details: Load full responsible (Employee) details.
            include_owner_details: Load full owner (Employee) details.
            expand_comment_owners: Resolve comment authors to full Employee
                objects via one batch of parallel cached requests (#30).
                The API never populates comment owners, so without this flag
                ``details.comments[n].owner`` is a bare ``{contentType, id}``
                reference. Requires ``include_comments=True``; passing it
                without the flag raises ValueError. Off by default so that
                text-only consumers don't pay for the extra batch.
            resolve_participants: Resolve ``auditors`` and ``executors`` to
                full Employee objects via one cached batch (#35). On by
                default — participant lists are small (3-8 entries) and the
                related-list endpoint returns bare references otherwise.
                Pass False to keep the raw references.
            comments_limit: Limit for comments (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: comments_limit=50 returns max 50 comments.
                Requires the matching include_* flag to be True; passing a
                limit without it raises ValueError.
                Note: the API caps a single comments page (~100); requesting
                more returns at most one server page. Use client.comments.iterate
                for full pagination.
            history_limit: Limit for history (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: history_limit=100 returns max 100 history entries.
                Requires the matching include_* flag to be True; passing a
                limit without it raises ValueError.

        Returns:
            TaskFullDetails object with all requested data.

        Note:
            The card is requested with ``fields=["commentsCount"]`` so
            ``details.comments_count`` is populated regardless of
            ``comments_limit`` (#34). ``len(details.comments) <
            details.comments_count`` reliably signals truncation.

        Examples:
            >>> # Get task with subtasks and comments
            >>> details = await client.tasks.get_full_details(
            ...     task_id=123,
            ...     include_sub_tasks=True,
            ...     include_comments=True,
            ...     include_responsible_details=True
            ... )
            >>> print(details.task.name)
            >>> print(details.responsible_details.first_name)
            >>>
            >>> # Comments with resolved authors
            >>> details = await client.tasks.get_full_details(
            ...     task_id=123,
            ...     include_comments=True,
            ...     expand_comment_owners=True,
            ... )
            >>> print(details.comments[0].owner.name)  # "Иван Петров"
        """
        if expand_comment_owners and not include_comments:
            raise ValueError(
                "'expand_comment_owners' was provided but 'include_comments' is False. "
                "Pass 'include_comments=True' to load comments first, "
                "or omit 'expand_comment_owners'."
            )
        details = cast(
            TaskFullDetails,
            await self._get_full_details_generic(
                entity_id=task_id,
                entity_getter="get",
                full_details_class=TaskFullDetails,
                config=self._full_details_config,
                main_entity_field="task",
                entity_getter_kwargs={"fields": ["commentsCount"]},
                include_sub_tasks=include_sub_tasks,
                include_actual_sub_tasks=include_actual_sub_tasks,
                include_comments=include_comments,
                include_history=include_history,
                include_auditors=include_auditors,
                include_executors=include_executors,
                include_milestones=include_milestones,
                include_responsible_details=include_responsible_details,
                include_owner_details=include_owner_details,
                comments_limit=comments_limit,
                history_limit=history_limit,
            ),
        )
        if expand_comment_owners and details.comments:
            await self._resolve_comment_owners(details.comments)
        if resolve_participants:
            if details.auditors:
                details.auditors = await self._resolve_employee_entities(details.auditors)
            if details.executors:
                details.executors = await self._resolve_employee_entities(details.executors)
        return details

    async def get_available_parents(
        self,
        is_template: bool | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task | Any]:
        """Get available parent tasks/projects for a new task.

        Returns list of tasks and projects that can be set as parent
        for a new task being created.

        Args:
            is_template: Filter by template status.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of Task or Project instances that can be parents.

        Examples:
            >>> # Get all available parents
            >>> parents = await client.tasks.get_available_parents(limit=10)
            >>> for parent in parents:
            ...     print(f"{type(parent).__name__}: {parent.name}")
            >>>
            >>> # Get only non-template parents
            >>> parents = await client.tasks.get_available_parents(is_template=False)
        """
        path = self._build_path("api", "v3", "task", "availableParents")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            isTemplate=is_template,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        return self._parse_mixed_task_project_response(data)

    async def get_available_parents_for(
        self,
        task_id: int,
        is_template: bool | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task | Any]:
        """Get available parent tasks/projects for an existing task.

        Returns list of tasks and projects that can be set as parent
        for the specified task.

        Args:
            task_id: Task identifier.
            is_template: Filter by template status.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of Task or Project instances that can be parents.

        Examples:
            >>> # Get available parents for task #123
            >>> parents = await client.tasks.get_available_parents_for(123)
            >>> for parent in parents:
            ...     print(f"{type(parent).__name__}: {parent.name}")
        """
        path = self._build_path("api", "v3", "task", str(task_id), "availableParents")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            isTemplate=is_template,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        return self._parse_mixed_task_project_response(data)

    async def get_all_participants(
        self,
        task_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Participant]:
        """Get all participants of a task.

        Returns complete list of participants including responsible, executors,
        auditors, and owner in a single request.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of participants (Employee, ContractorHuman, or Group).

        Examples:
            >>> participants = await client.tasks.get_all_participants(task_id=123)
            >>> for p in participants:
            ...     if hasattr(p, 'display_name'):
            ...         print(p.display_name())
        """
        from megaplan_sdk.models.participant import parse_participants

        path = self._build_path("api", "v3", "task", str(task_id), "allParticipants")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        return parse_participants(data)
