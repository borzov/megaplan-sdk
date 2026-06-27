"""Projects resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, overload

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.project import Project, ProjectFullDetails
from megaplan_sdk.models.task import Task
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.full_details import FullDetailsMixin, RelatedDataConfig
from megaplan_sdk.types import FilterType

if TYPE_CHECKING:
    from megaplan_sdk.models.milestone import Milestone
    from megaplan_sdk.models.participant import Participant


class ProjectsResource(BaseResource, FullDetailsMixin):
    """Resource for working with projects."""

    _page_content_type = ContentType.PROJECT

    _full_details_config = [
        RelatedDataConfig("deals", "include_deals", "get_deals"),
        RelatedDataConfig("issues", "include_issues", "get_issues"),
        RelatedDataConfig("actual_issues", "include_actual_issues", "get_actual_issues"),
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
        """Initialize projects resource.

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

    async def create(
        self, project_data: dict[str, Any], auto_fill_required: bool = True
    ) -> Project:
        """Create a new project.

        Args:
            project_data: Project data dictionary.
            auto_fill_required: Automatically fill required fields if not provided.
                Default: True. Sets isTemplate=False if not specified.

        Returns:
            Created project.

        Examples:
            >>> # Minimal project creation (auto-fills required fields)
            >>> project = await client.projects.create({"name": "New project"})
            >>>
            >>> # With explicit required fields
            >>> project = await client.projects.create({
            ...     "name": "New project",
            ...     "isTemplate": False
            ... })
        """
        # Auto-fill required fields if not provided
        if auto_fill_required:
            if "isTemplate" not in project_data:
                project_data["isTemplate"] = False

        return await self._create_entity("project", project_data, Project)

    async def create_simple(
        self,
        name: str,
        owner_id: int | None = None,
        responsible_id: int | None = None,
        description: str | None = None,
        employees_resource: Any | None = None,
    ) -> Project:
        """Create a project with minimal required parameters.

        Automatically fills required fields (isTemplate) and optionally
        determines owner/responsible from current user if not provided.

        Args:
            name: Project name (required).
            owner_id: Owner employee ID. If None and employees_resource
                is provided, uses current user.
            responsible_id: Responsible employee ID. If None and employees_resource
                is provided, uses current user.
            description: Project description.
            employees_resource: EmployeesResource instance for auto-detecting current user.
                If provided and owner_id/responsible_id are None, will use current user.

        Returns:
            Created project.

        Examples:
            >>> # Simple project with current user as owner/responsible
            >>> project = await client.projects.create_simple(
            ...     "New project",
            ...     employees_resource=client.employees
            ... )
            >>>
            >>> # Simple project with specific owner
            >>> project = await client.projects.create_simple(
            ...     "New project",
            ...     owner_id=123,
            ...     responsible_id=123
            ... )
        """
        project_data: dict[str, Any] = {
            "name": name,
            "isTemplate": False,
        }

        if description:
            project_data["description"] = description

        # Auto-determine owner/responsible from current user if not provided
        if employees_resource and (owner_id is None or responsible_id is None):
            try:
                current_user = await employees_resource.get_current()
                if owner_id is None:
                    owner_id = current_user.id
                if responsible_id is None:
                    responsible_id = current_user.id
            except Exception:
                # If we can't get current user, skip owner/responsible
                # API will return error if required
                pass

        if owner_id:
            project_data["owner"] = {"contentType": "Employee", "id": owner_id}
        if responsible_id:
            project_data["responsible"] = {"contentType": "Employee", "id": responsible_id}

        return await self.create(project_data, auto_fill_required=False)

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: None = None,
    ) -> list[Project]: ...

    @overload
    async def list(
        self,
        *,
        filter: FilterType | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str],
    ) -> list[ProjectFullDetails]: ...

    async def list(
        self,
        filter: FilterType | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Project] | list[ProjectFullDetails]:
        """Get list of projects.

        Args:
            filter: Project filter (``ProjectFilterBuilder`` result or filter config dict).
                Use ``ProjectFilterBuilder`` for fluent filter construction:

                .. code-block:: python

                    from megaplan_sdk import ProjectFilterBuilder

                    f = ProjectFilterBuilder().field_date("timeCreated").greater_than("2025-01-01").build()
                    projects = await client.projects.list(filter=f)

            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: List of fields to expand (e.g., ["responsible", "owner"]).
                Supported values: "responsible", "owner".
                If provided, returns list[ProjectFullDetails] instead of list[Project].

        Returns:
            List of projects (list[Project] if expand is None, list[ProjectFullDetails] otherwise).

        Examples:
            >>> # Get projects without expansion
            >>> projects = await client.projects.list(limit=10)
            >>>
            >>> # Get projects with filter
            >>> from megaplan_sdk import ProjectFilterBuilder
            >>> f = ProjectFilterBuilder().field("name").contains("SDK").build()
            >>> projects = await client.projects.list(filter=f)
            >>>
            >>> # Get projects with expanded responsible and owner
            >>> projects_full = await client.projects.list(
            ...     limit=10, expand=["responsible", "owner"]
            ... )
            >>> for project_full in projects_full:
            ...     if project_full.responsible_details:
            ...         print(project_full.responsible_details.display_name())
        """
        path = self._build_path("api", "v3", "project")

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

        # 1. Fetch projects
        projects = await self._get_list(path, Project, params)

        # 2. If no expand, return as is
        if not expand or not projects:
            return projects

        # 3. Batch load related entities
        from megaplan_sdk.models.employee import Employee

        expand_config: dict[str, tuple[str, type, str]] = {
            "responsible": ("employee", Employee, ContentType.EMPLOYEE),
            "owner": ("employee", Employee, ContentType.EMPLOYEE),
        }

        expanded = await self._expand_list_entities(projects, expand, expand_config)
        responsible_map = expanded.get("responsible", {})
        owner_map = expanded.get("owner", {})

        # 4. Build ProjectFullDetails objects
        results = []
        for project in projects:
            resp_details = None
            owner_details = None

            if project.responsible and project.responsible.id in responsible_map:
                resp_details = responsible_map[project.responsible.id]

            if project.owner and project.owner.id in owner_map:
                owner_details = owner_map[project.owner.id]

            results.append(
                ProjectFullDetails(
                    project=project,
                    responsible_details=resp_details,
                    owner_details=owner_details,
                )
            )

        return results

    async def get(self, project_id: int) -> Project:
        """Get project by ID.

        Args:
            project_id: Project identifier.

        Returns:
            Project details.
        """
        return await self._get_entity("project", project_id, Project)

    async def update(self, project_id: int, project_data: dict[str, Any]) -> Project:
        """Update project.

        Args:
            project_id: Project identifier.
            project_data: Updated project data.

        Returns:
            Updated project.
        """
        return await self._update_entity("project", project_id, project_data, Project)

    async def delete(self, project_id: int) -> None:
        """Delete project.

        Args:
            project_id: Project identifier.
        """
        await self._delete_entity("project", project_id)

    async def get_deals(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Deal]:
        """Get deals associated with project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of deals.
        """
        path = self._build_path("api", "v3", "project", str(project_id), "deals")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        return await self._get_list(path, Deal, params)

    async def get_issues(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task]:
        """Get tasks (issues) associated with project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of tasks.
        """
        path = self._build_path("api", "v3", "project", str(project_id), "issues")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        return await self._get_list(path, Task, params)

    async def get_actual_issues(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Task]:
        """Get actual tasks (issues) associated with project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of actual tasks.
        """
        path = self._build_path("api", "v3", "project", str(project_id), "actualIssues")

        # Use base method to build params (DRY)
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
        )

        return await self._get_list(path, Task, params)

    async def iterate(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Project]:
        """Iterate over all projects with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Project objects.
        """
        project: Project
        async for project in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.PROJECT,
            self.list,
            limit,
            **kwargs,
        ):
            yield project

    async def get_comments(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Comment]:
        """Get comments for a project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of comments.

        Examples:
            >>> comments = await client.projects.get_comments(project_id=123)
        """
        return await self._get_entity_comments(
            "project",
            project_id,
            limit,
            page_after,
            page_before,
            page_with,
        )

    async def create_comment(
        self,
        project_id: int,
        text: str,
        attaches: list[dict[str, Any]] | None = None,
    ) -> Comment:
        """Create a comment for a project.

        Args:
            project_id: Project identifier.
            text: Comment text.
            attaches: List of file attachments.

        Returns:
            Created comment.

        Examples:
            >>> comment = await client.projects.create_comment(
            ...     project_id=123,
            ...     text="Project update"
            ... )
        """
        return await self._create_entity_comment(
            "project",
            project_id,
            text,
            attaches,
        )

    async def get_auditors(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get auditors for a project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of auditors (Employees).

        Examples:
            >>> auditors = await client.projects.get_auditors(project_id=123)
        """
        return await self._get_entity_related_list(
            "project", project_id, "auditors", limit, page_after, page_before, page_with
        )

    async def add_auditor(
        self,
        project_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> Any:
        """Add auditor to the project.

        Args:
            project_id: Project identifier.
            auditor_id: Auditor ID (usually Employee ID).
            auditor_content_type: Content type (usually "Employee").

        Returns:
            Added auditor.

        Examples:
            >>> auditor = await client.projects.add_auditor(
            ...     project_id=123,
            ...     auditor_id=456
            ... )
        """
        return await self._add_entity_related(
            "project", project_id, "auditors", auditor_id, auditor_content_type
        )

    async def remove_auditor(
        self,
        project_id: int,
        auditor_id: int,
        auditor_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Remove auditor from the project.

        Args:
            project_id: Project identifier.
            auditor_id: Auditor ID.
            auditor_content_type: Content type (usually "Employee").

        Examples:
            >>> await client.projects.remove_auditor(project_id=123, auditor_id=456)
        """
        await self._remove_entity_related(
            "project", project_id, "auditors", auditor_id, auditor_content_type
        )

    async def get_executors(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Get executors (co-performers) for a project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of executors (Employees).

        Examples:
            >>> executors = await client.projects.get_executors(project_id=123)
        """
        return await self._get_entity_related_list(
            "project", project_id, "executors", limit, page_after, page_before, page_with
        )

    async def add_executor(
        self,
        project_id: int,
        executor_id: int,
        executor_content_type: str = ContentType.EMPLOYEE,
    ) -> Any:
        """Add executor (co-performer) to the project.

        Args:
            project_id: Project identifier.
            executor_id: Executor ID (usually Employee ID).
            executor_content_type: Content type (usually "Employee").

        Returns:
            Added executor.

        Examples:
            >>> executor = await client.projects.add_executor(
            ...     project_id=123,
            ...     executor_id=456
            ... )
        """
        return await self._add_entity_related(
            "project", project_id, "executors", executor_id, executor_content_type
        )

    async def remove_executor(
        self,
        project_id: int,
        executor_id: int,
        executor_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Remove executor from the project.

        Args:
            project_id: Project identifier.
            executor_id: Executor ID.
            executor_content_type: Content type (usually "Employee").

        Examples:
            >>> await client.projects.remove_executor(project_id=123, executor_id=456)
        """
        await self._remove_entity_related(
            "project", project_id, "executors", executor_id, executor_content_type
        )

    async def get_milestones(
        self,
        project_id: int,
    ) -> list[Milestone]:
        """Get milestones for a project.

        Note: Direct endpoint /project/{id}/milestones returns 500 error.
        This method uses /project/{id} with fields parameter to get milestones.

        Args:
            project_id: Project identifier.

        Returns:
            List of Milestone objects.

        Examples:
            >>> milestones = await client.projects.get_milestones(project_id=123)
            >>> for milestone in milestones:
            ...     print(f"{milestone.name}: {milestone.date}")
        """
        return await self._get_milestones_generic("project", project_id)

    async def add_milestone(
        self,
        project_id: int,
        milestone_data: Milestone | dict[str, Any],
    ) -> Milestone:
        """Add milestone to the project.

        Args:
            project_id: Project identifier.
            milestone_data: Milestone data as Milestone object or dict.
                Required fields: description, type, date.
                Type must be one of: "report", "reminder", "note".
                Date can be ISO 8601 string, DateTime object, or dict.

        Returns:
            Created Milestone object.

        Examples:
            >>> # Using dict
            >>> milestone = await client.projects.add_milestone(
            ...     project_id=123,
            ...     milestone_data={
            ...         "name": "Phase 1",
            ...         "description": "First phase milestone",
            ...         "type": "report",
            ...         "date": "2026-03-15T10:00:00Z"
            ...     }
            ... )
            >>>
            >>> # Using Milestone model
            >>> from megaplan_sdk.models.milestone import Milestone
            >>> milestone = await client.projects.add_milestone(
            ...     project_id=123,
            ...     milestone_data=Milestone(
            ...         name="Phase 1",
            ...         description="First phase milestone",
            ...         type="report",
            ...         date="2026-03-15T10:00:00Z"
            ...     )
            ... )
        """
        return await self._add_milestone_generic("project", project_id, milestone_data)

    async def get_history(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get history log for a project.

        Args:
            project_id: Project identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of history entries.

        Examples:
            >>> history = await client.projects.get_history(project_id=123, limit=10)
        """
        return await self._get_entity_history(
            "project", project_id, limit, page_after, page_before, page_with
        )

    async def search_history(
        self,
        project_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search in project history log.

        Args:
            project_id: Project identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of matching history entries.

        Examples:
            >>> results = await client.projects.search_history(project_id=123, query="milestone")
        """
        return await self._search_entity_history(
            "project", project_id, query, limit, page_after, page_before, page_with
        )

    async def get_full_details(
        self,
        project_id: int,
        include_deals: bool = False,
        include_issues: bool = False,
        include_actual_issues: bool = False,
        include_comments: bool = False,
        include_history: bool = False,
        include_auditors: bool = False,
        include_executors: bool = False,
        include_milestones: bool = False,
        include_responsible_details: bool = False,
        include_owner_details: bool = False,
        comments_limit: int | None = None,
        history_limit: int | None = None,
    ) -> ProjectFullDetails:
        """Get full project details with related entities.

        This method fetches the project and optionally loads related data in parallel
        for better performance.

        Args:
            project_id: Project identifier.
            include_deals: Load associated deals.
            include_issues: Load tasks/issues.
            include_actual_issues: Load actual tasks/issues.
            include_comments: Load project comments.
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
            ProjectFullDetails object with all requested data.

        Examples:
            >>> # Get project with deals and tasks
            >>> details = await client.projects.get_full_details(
            ...     project_id=123,
            ...     include_deals=True,
            ...     include_issues=True,
            ...     include_responsible_details=True
            ... )
            >>> print(details.project.name)
            >>> print(len(details.deals))
        """
        return await self._get_full_details_generic(
            entity_id=project_id,
            entity_getter="get",
            full_details_class=ProjectFullDetails,
            config=self._full_details_config,
            main_entity_field="project",
            include_deals=include_deals,
            include_issues=include_issues,
            include_actual_issues=include_actual_issues,
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
    ) -> list[Project]:
        """Get available parent projects for a new project.

        Returns list of projects that can be set as parent
        for a new project being created.

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
            List of Project instances that can be parents.

        Examples:
            >>> # Get all available parent projects
            >>> parents = await client.projects.get_available_parents(limit=10)
            >>> for parent in parents:
            ...     print(f"Project: {parent.name}")
            >>>
            >>> # Get only non-template parents
            >>> parents = await client.projects.get_available_parents(is_template=False)
        """
        path = self._build_path("api", "v3", "project", "availableParents")

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

        return await self._get_list(path, Project, params if params else None)

    async def get_available_parents_for(
        self,
        project_id: int,
        is_template: bool | None = None,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Project]:
        """Get available parent projects for an existing project.

        Returns list of projects that can be set as parent
        for the specified project.

        Args:
            project_id: Project identifier.
            is_template: Filter by template status.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of Project instances that can be parents.

        Examples:
            >>> # Get available parents for project #123
            >>> parents = await client.projects.get_available_parents_for(123)
            >>> for parent in parents:
            ...     print(f"Project: {parent.name}")
        """
        path = self._build_path("api", "v3", "project", str(project_id), "availableParents")

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

        return await self._get_list(path, Project, params if params else None)

    async def get_all_participants(
        self,
        project_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Participant]:
        """Get all participants of a project.

        Returns complete list of participants including responsible, executors,
        auditors, and owner in a single request.

        Args:
            project_id: Project identifier.
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
            >>> participants = await client.projects.get_all_participants(project_id=123)
            >>> for p in participants:
            ...     if hasattr(p, 'display_name'):
            ...         print(p.display_name())
        """
        from megaplan_sdk.models.participant import parse_participants

        path = self._build_path("api", "v3", "project", str(project_id), "allParticipants")

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
