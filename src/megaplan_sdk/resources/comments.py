"""Comments resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.models.comment import Comment
from megaplan_sdk.resources.base import BaseResource


class CommentsResource(BaseResource):
    """Resource for working with comments."""

    async def create(
        self,
        entity_id: int,
        comment_data: dict[str, Any],
        entity_type: str = "task",
    ) -> Comment:
        """Create a new comment for an entity.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            comment_data: Comment data dictionary.
                Required: text
                Optional: work (hours), attaches (file IDs)
            entity_type: Entity type segment for the API path.
                Allowed values: ``"task"`` | ``"project"`` | ``"deal"``.
                Defaults to ``"task"``.

        Returns:
            Created comment.

        Examples:
            >>> # Create comment for task #123
            >>> comment = await client.comments.create(
            ...     entity_id=123,
            ...     comment_data={"text": "Comment text", "work": 2.5}
            ... )
            >>> # Create comment for project #55
            >>> comment = await client.comments.create(
            ...     entity_id=55,
            ...     comment_data={"text": "Project note"},
            ...     entity_type="project",
            ... )
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "comments")
        response = await self._http.post(path, json_data=comment_data)
        return Comment(**response["data"])

    async def list(
        self,
        entity_id: int,
        entity_type: str = "task",
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        expand: list[str] | None = None,
    ) -> list[Comment]:
        """Get list of comments for an entity.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            entity_type: Entity type segment for the API path.
                Allowed values: ``"task"`` | ``"project"`` | ``"deal"``.
                Defaults to ``"task"``.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            expand: Fields to expand. Supported values: ``"owner"``.
                When ``"owner"`` is included, resolves Employee comment authors
                to full Employee objects via batch parallel requests (cached).
                The API never returns populated owners, so this is the only
                resolution path.

        Returns:
            List of comments.

        Examples:
            >>> # Get all comments for task #123
            >>> comments = await client.comments.list(entity_id=123)
            >>> # Get all comments for project #55
            >>> comments = await client.comments.list(entity_id=55, entity_type="project")
            >>> # Resolve comment authors to full Employee objects
            >>> comments = await client.comments.list(entity_id=123, expand=["owner"])
            >>> print(comments[0].owner.name)  # "Иван Петров"
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "comments")

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

        comments = await self._get_list(path, Comment, params)

        if not expand or "owner" not in expand or not comments:
            return comments

        from megaplan_sdk.models.employee import Employee

        # Only Employee owners are resolvable via the employee endpoint.
        employee_owners = [
            c.owner for c in comments if c.owner is not None and c.owner.content_type == "Employee"
        ]
        owner_map = await self._load_related_entities(employee_owners, "employee", Employee)
        for comment in comments:
            if (
                comment.owner is not None
                and comment.owner.content_type == "Employee"
                and comment.owner.id in owner_map
            ):
                comment.owner = owner_map[comment.owner.id]

        return comments

    async def get(self, comment_id: int) -> Comment:
        """Get comment by ID.

        Args:
            comment_id: Comment identifier.

        Returns:
            Comment details.
        """
        path = self._build_path("api", "v3", "comment", str(comment_id))
        response = await self._http.get(path)
        return Comment(**response["data"])

    async def update(self, comment_id: int, comment_data: dict[str, Any]) -> Comment:
        """Update comment.

        Args:
            comment_id: Comment identifier.
            comment_data: Updated comment data.

        Returns:
            Updated comment.
        """
        path = self._build_path("api", "v3", "comment", str(comment_id))
        response = await self._http.post(path, json_data=comment_data)
        return Comment(**response["data"])

    async def delete(self, comment_id: int) -> None:
        """Delete comment.

        Args:
            comment_id: Comment identifier.
        """
        path = self._build_path("api", "v3", "comment", str(comment_id))
        await self._http.delete(path)

    async def iterate(
        self,
        entity_id: int,
        entity_type: str = "task",
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Comment]:
        """Iterate over all comments for an entity with automatic pagination.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            entity_type: Entity type segment for the API path.
                Allowed values: ``"task"`` | ``"project"`` | ``"deal"``.
                Defaults to ``"task"``.
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Comment objects.

        Examples:
            >>> # Iterate over all comments for task #123
            >>> async for comment in client.comments.iterate(entity_id=123):
            ...     print(comment.content)
            >>> # Iterate over all comments for project #55
            >>> async for comment in client.comments.iterate(entity_id=55, entity_type="project"):
            ...     print(comment.content)
        """
        comment: Comment
        async for comment in self._iterate_generic(  # type: ignore[valid-type]
            "Comment",
            self.list,
            limit,
            entity_id=entity_id,
            entity_type=entity_type,
            **kwargs,
        ):
            yield comment
