"""Tasks resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, overload

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.task import Task, TaskFullDetails
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.full_details import FullDetailsMixin, RelatedDataConfig
from megaplan_sdk.types import FilterType


class TasksResource(BaseResource, FullDetailsMixin):
    """Resource for working with tasks."""

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
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
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
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
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
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
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
                Warning: This parameter may return 422 ValidationError due to API limitations.
                Use FilterBuilder for reliable status filtering instead.
            q: Text search query (searches in task name and description).
                **Note:** This parameter may not work properly in Megaplan API
                (returns empty results). For text search, use FilterBuilder instead:
                ```python
                from megaplan_sdk import FilterBuilder

                # Simple text search
                filter_obj = FilterBuilder("TaskFilter").field("name").contains("договор").build()
                tasks = await client.tasks.list(filter=filter_obj)

                # Multiple conditions with different types
                filter_obj = (
                    FilterBuilder("TaskFilter")
                    .field("name").contains("договор")
                    .and_()
                    .field_number("amount").greater_than(1000)
                    .and_()
                    .field_enum("status").in_list(["active", "pending"])
                    .build()
                )
                tasks = await client.tasks.list(filter=filter_obj)

                # Nested groups
                filter_obj = (
                    FilterBuilder("TaskFilter")
                    .field("name").contains("договор")
                    .and_()
                    .group()
                        .field("status").equals("active")
                        .or_()
                        .field("priority").equals("high")
                    .end_group()
                    .build()
                )
                tasks = await client.tasks.list(filter=filter_obj)

                # Using specialized builder
                from megaplan_sdk import TaskFilterBuilder
                filter_obj = TaskFilterBuilder().field("name").contains("договор").build()
                tasks = await client.tasks.list(filter=filter_obj)
                ```
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
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

        # Convert filter ID to object format if needed
        processed_filter = filter
        if filter is not None and isinstance(filter, int | str) and not isinstance(filter, dict):
            # Convert ID to filter object format
            processed_filter = {"contentType": "TaskFilter", "id": str(filter)}

        # Use base method to build params (DRY)
        params = self._build_list_params(
            filter=processed_filter,
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            statuses=statuses,  # Extra param specific to tasks
            q=q,  # Extra param specific to tasks - text search
        )

        # 1. Fetch tasks
        tasks = await self._get_list(path, Task, params)

        # 2. If no expand, return as is
        if not expand or not tasks:
            return tasks

        # 3. Batch load related entities
        from megaplan_sdk.models.employee import Employee

        expand_config: dict[str, tuple[str, type, str]] = {
            "responsible": ("employee", Employee, ContentType.EMPLOYEE),
            "owner": ("employee", Employee, ContentType.EMPLOYEE),
        }

        expanded = await self._expand_list_entities(tasks, expand, expand_config)
        responsible_map = expanded.get("responsible", {})
        owner_map = expanded.get("owner", {})

        # 4. Build TaskFullDetails objects
        results = []
        for task in tasks:
            resp_details = None
            owner_details = None

            if task.responsible and task.responsible.id in responsible_map:
                resp_details = responsible_map[task.responsible.id]

            if task.owner and task.owner.id in owner_map:
                owner_details = owner_map[task.owner.id]

            results.append(
                TaskFullDetails(
                    task=task,
                    responsible_details=resp_details,
                    owner_details=owner_details,
                )
            )

        return results

    async def get(self, task_id: int) -> Task:
        """Get task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Task details.
        """
        return await self._get_entity("task", task_id, Task)

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
            if isinstance(processed_item.get("id"), str):
                id_str = processed_item["id"]
                # Format: "Task:1005808:dcca48101505dd86b703689a604fe3c4"
                # Extract ID between first and second colon
                parts = id_str.split(":")
                if len(parts) >= 2:
                    try:
                        # Extract numeric ID (second part)
                        numeric_id = int(parts[1])
                        processed_item["id"] = numeric_id
                    except (ValueError, IndexError):
                        # If parsing fails, keep original ID and log warning
                        from megaplan_sdk.logging_config import logger

                        logger.warning(
                            f"Could not parse tree node ID from '{id_str}', keeping original"
                        )

            processed_items.append(processed_item)

        # Parse processed items into Task models
        return [Task(**item) if isinstance(item, dict) else item for item in processed_items]

    async def iterate(
        self,
        filter: FilterType | None = None,
        statuses: list[str] | None = None,
        limit: int = 100,
    ) -> AsyncIterator[Task]:
        """Iterate over all tasks with automatic pagination.

        Args:
            filter: Task filter (ID or config).
            statuses: List of statuses to filter by.
            limit: Number of items per page.

        Yields:
            Task objects.
        """
        task: Task
        async for task in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.TASK,
            self.list,
            limit,
            filter=filter,
            statuses=statuses,
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

        Args:
            task_id: Task identifier.
            text: Comment text.
            work: Hours worked (for time tracking).
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
        extra_fields = {}
        if work is not None:
            extra_fields["workTime"] = {
                "contentType": "DateInterval",
                "seconds": int(work * 3600),
            }

        return await self._create_entity_comment(
            "task",
            task_id,
            text,
            attaches,
            **extra_fields,
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
            task_data["responsible"] = {"contentType": "Employee", "id": responsible_id}

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
            "parent": {"contentType": "Project", "id": project_id},
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
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list["Milestone"]:
        """Get milestones for a task.

        Warning: This endpoint may return 500 Internal Server Error for some tasks/projects
        due to API limitations. The error is handled gracefully and an empty list is returned.

        Args:
            task_id: Task identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of Milestone objects. Returns empty list if API returns 500 error.

        Examples:
            >>> milestones = await client.tasks.get_milestones(task_id=123)
            >>> for milestone in milestones:
            ...     print(f"{milestone.name}: {milestone.date}")
        """
        from megaplan_sdk.models.milestone import Milestone

        try:
            return await self._get_entity_related_list(
                "task",
                task_id,
                "milestones",
                limit,
                page_after,
                page_before,
                page_with,
                model_class=Milestone,
            )
        except Exception as e:
            # API may return 500 for milestones endpoint (known limitation)
            from megaplan_sdk.exceptions import ServerError
            from megaplan_sdk.logging_config import logger

            if isinstance(e, ServerError) and "500" in str(e):
                logger.warning(
                    f"Milestones endpoint returned 500 for task {task_id}. "
                    "This is a known API limitation. Returning empty list."
                )
                return []
            raise

    async def add_milestone(
        self,
        task_id: int,
        milestone_data: "Milestone | dict[str, Any]",
    ) -> "Milestone":
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
        from megaplan_sdk.models.milestone import Milestone

        # Validate and convert to dict if needed
        if isinstance(milestone_data, Milestone):
            data_dict = milestone_data.model_dump(by_alias=True, exclude_none=True)
        else:
            # Validate dict data through model
            milestone = Milestone(**milestone_data)
            data_dict = milestone.model_dump(by_alias=True, exclude_none=True)

        response = await self._add_entity_related(
            "task", task_id, "milestones", 0, "Milestone", data_override=data_dict
        )
        return Milestone(**response) if isinstance(response, dict) else response

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
            comments_limit: Limit for comments (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: comments_limit=50 returns max 50 comments.
            history_limit: Limit for history (if included).
                None = use global default (from MegaplanClient) or API default.
                Explicit value overrides global default.
                Example: history_limit=100 returns max 100 history entries.

        Returns:
            TaskFullDetails object with all requested data.

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
        """
        return await self._get_full_details_generic(
            entity_id=task_id,
            entity_getter="get",
            full_details_class=TaskFullDetails,
            config=self._full_details_config,
            main_entity_field="task",
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
        )
