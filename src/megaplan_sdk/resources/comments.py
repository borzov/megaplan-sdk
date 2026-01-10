"""Comments resource for Megaplan API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.models.comment import Comment
from megaplan_sdk.resources.base import BaseResource


class CommentsResource(BaseResource):
    """Resource for working with comments."""

    async def create(self, entity_id: int, comment_data: dict[str, Any]) -> Comment:
        """Create a new comment for an entity.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            comment_data: Comment data dictionary.
                Required: text
                Optional: work (hours), attaches (file IDs)

        Returns:
            Created comment.

        Examples:
            >>> # Create comment for task #123
            >>> comment = await client.comments.create(
            ...     entity_id=123,
            ...     comment_data={"text": "Comment text", "work": 2.5}
            ... )
        """
        path = self._build_path("api", "v3", "todo", str(entity_id), "comments")
        response = await self._http.post(path, json_data=comment_data)
        return Comment(**response["data"])

    async def list(
        self,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Comment]:
        """Get list of comments for an entity.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of comments.

        Examples:
            >>> # Get all comments for task #123
            >>> comments = await client.comments.list(entity_id=123)
        """
        path = self._build_path("api", "v3", "todo", str(entity_id), "comments")

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

        return await self._get_list(path, Comment, params)

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
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Comment]:
        """Iterate over all comments for an entity with automatic pagination.

        Args:
            entity_id: Parent entity ID (task, project, deal, etc.).
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            Comment objects.

        Examples:
            >>> # Iterate over all comments for task #123
            >>> async for comment in client.comments.iterate(entity_id=123):
            ...     print(comment.content)
        """
        comment: Comment
        async for comment in self._iterate_generic(  # type: ignore[valid-type]
            "Comment",
            self.list,
            limit,
            entity_id=entity_id,
            **kwargs,
        ):
            yield comment
