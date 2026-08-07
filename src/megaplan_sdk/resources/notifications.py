"""Notifications resource for Megaplan API (#FR-F)."""

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.notification import Notification, NotificationCounter, NotificationType
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource


class NotificationsResource(BaseResource):
    """Resource for working with notifications.

    Notifications are the only reliable source of mentions: the server sets
    ``isMention`` itself. Note the server-side filtering limits (verified on a
    live account 2026-08-07): the request entity ``GetAllNotificationsRequest``
    accepts pagination and ``isActive`` only — anything else, including a
    mention filter, is rejected with 422. ``only_mentions`` is therefore applied
    client-side; use :meth:`iterate` when you need every mention rather than
    the mentions inside one page.
    """

    _page_content_type = ContentType.NOTIFICATION

    async def list(
        self,
        limit: int | None = None,
        only_active: bool | None = None,
        only_mentions: bool = False,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
    ) -> list[Notification]:
        """Get a page of notifications.

        Args:
            limit: Number of items per page.
            only_active: Server-side filter on ``isActive``.
            only_mentions: Keep only mentions. Applied client-side (the server
                rejects a mention filter with 422), so this narrows the page
                that was fetched — it does not fetch more.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).
            fields: Additional fields to request from the API.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.

        Returns:
            List of notifications.

        Examples:
            >>> mentions = await client.notifications.list(limit=60, only_mentions=True)
            >>> for note in mentions:
            ...     print(note.entity_ref, note.sender.display_name())
        """
        path = self._build_path("api", "v3", "notification")

        extra_params: dict[str, Any] = {}
        if only_active is not None:
            extra_params["isActive"] = only_active

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
            fields=fields,
            sort_by=sort_by,
            only_requested_fields=only_requested_fields,
            **extra_params,
        )

        notifications = await self._get_list(path, Notification, params)

        if only_mentions:
            return [item for item in notifications if item.is_mention]
        return notifications

    async def iterate(
        self,
        limit: int = 100,
        only_mentions: bool = False,
        **kwargs: Any,
    ) -> AsyncIterator[Notification]:
        """Iterate over all notifications with automatic pagination.

        Args:
            limit: Number of items per page.
            only_mentions: Yield mentions only. Filtering happens after paging,
                so short filtered pages do not stop the iteration.
            **kwargs: Additional parameters passed to :meth:`list`.

        Yields:
            Notification objects.
        """
        notification: Notification
        async for notification in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.NOTIFICATION,
            self.list,
            limit,
            **kwargs,
        ):
            if only_mentions and not notification.is_mention:
                continue
            yield notification

    async def counter(self) -> NotificationCounter:
        """Get the unread notification counter.

        Returns:
            Counter with ``count`` and reported ``attributes`` (e.g. ["mention"]).
        """
        path = self._build_path("api", "v3", "notification", "counter")
        response = await self._http.get(path)
        return NotificationCounter(**response.get("data", {}))

    async def activity_types(self) -> list[NotificationType]:
        """Get available notification types.

        Returns:
            List of notification types with their string ids and descriptions.
        """
        path = self._build_path("api", "v3", "notification", "activityTypes")
        return await self._get_list(path, NotificationType)
