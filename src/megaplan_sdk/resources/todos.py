"""Todos resource for Megaplan API — read and write access to todos ("Дела")."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.task import Task
from megaplan_sdk.models.todo import Todo
from megaplan_sdk.resources.base import BaseResource


class TodosResource(BaseResource):
    """Resource for todos ("Дела").

    Unlike tasks and deals, a todo has no ``timeUpdated`` and the API offers
    no "changed after" filter — incremental sync must go through app event
    streams instead.

    Note:
        Writes on this entity are eventually consistent on the live API: a
        write POST returns 200 with the intended state right away, but a GET
        issued immediately after can still show the previous value for a few
        seconds — worse under several rapid writes to the same todo. This is
        a server-side characteristic; the SDK does not poll to mask it.
    """

    _page_content_type = ContentType.TODO

    async def create(self, name: str, **fields: Any) -> Todo:
        """Create a todo.

        Args:
            name: Todo name.
            **fields: Any other Todo fields, in API notation (e.g.
                ``responsible``, ``category``, ``status``).

        Returns:
            The created todo.

        Note:
            ``when`` cannot be set through this method: any shape tried for
            it (``IntervalDates``/``IntervalTime``) gives a 422 on the live
            API (``'stdClass' is not assignable to 'IntervalDates|
            IntervalTime'``) — the wire format the server expects for
            scheduling on create has not been found.
        """
        payload: dict[str, Any] = {"contentType": ContentType.TODO, "name": name, **fields}
        return await self._create_entity("todo", payload, Todo)

    async def update(self, todo_id: int, todo_data: dict[str, Any]) -> Todo:
        """Update a todo.

        Args:
            todo_id: Todo identifier.
            todo_data: Updated todo fields, in API notation.

        Returns:
            Updated todo.
        """
        return await self._update_entity("todo", todo_id, todo_data, Todo)

    async def delete(self, todo_id: int) -> None:
        """Delete a todo.

        Args:
            todo_id: Todo identifier.
        """
        await self._delete_entity("todo", todo_id)

    async def finish(self, todo_id: int, status_id: int) -> Todo:
        """Finish a todo by switching it to a closed status.

        Args:
            todo_id: Todo identifier.
            status_id: Id of a ``TodoStatus`` whose ``masterType`` is one of
                "finished", "success", "fail", "finish_without_result" — see
                ``GET /api/v3/todoStatus`` for the account's actual status
                list, since ids are not stable across accounts.

        Returns:
            The updated todo.

        Note:
            There is no dedicated finish action route: ``POST
            /todo/{id}/finish`` 404s "No route found" on a live account
            (RAML's ``TodoFinishActionRequest`` type is not reachable that
            way). This method is plain sugar over :meth:`update` that only
            changes ``status`` — confirmed on a live account to actually
            persist. RAML separately documents a unified ``POST
            /todo/{id}/doAction`` route accepting a discriminated
            ``TodoFinishActionRequest`` (also carrying ``resultText``,
            ``resultAttaches``, ``notifyContractors``); that route was not
            probed for this release and is not used here.
        """
        return await self.update(
            todo_id, {"status": {"contentType": "TodoStatus", "id": str(status_id)}}
        )

    async def list(
        self,
        limit: int | None = None,
        q: str | None = None,
        filter: dict[str, Any] | None = None,
        page_after: dict[str, Any] | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
    ) -> list[Todo]:
        """Get a page of todos.

        Args:
            limit: Number of items per page.
            q: Free-text query, passed through untouched as ``q``.
            filter: Ad-hoc filter, passed through untouched.
            page_after: Load page starting from this entity.
            fields: Additional fields to request from the API.
            sort_by: Sort fields.

        Returns:
            List of todos.

        Note:
            An ad-hoc ``filter`` is passed through untouched. The server
            silently ignores unknown filter fields (200 + unfiltered result),
            so always verify a new filter by the number of rows it returns.
        """
        path = self._build_path("api", "v3", "todo")
        params = self._build_list_params(
            filter=filter,
            limit=limit,
            page_after=page_after,
            fields=fields,
            sort_by=sort_by,
            q=q,
        )
        return await self._get_list(path, Todo, params)

    async def iterate(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[Todo]:
        """Iterate over all todos with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters passed to :meth:`list`.

        Yields:
            Todo objects.
        """
        todo: Todo
        async for todo in self._iterate_generic(  # type: ignore[valid-type]
            ContentType.TODO,
            self.list,
            limit,
            **kwargs,
        ):
            yield todo

    async def get(self, todo_id: int) -> Todo:
        """Get a single todo by id.

        Args:
            todo_id: Todo identifier.

        Returns:
            The todo.
        """
        return await self._get_entity("todo", todo_id, Todo)

    async def search(self, q: str) -> list[BaseEntity]:
        """Search todos by free text.

        Args:
            q: Search query.

        Returns:
            Bare entity references matching the query (``GET /todo/search``
            returns ``BaseEntity[]``, not full ``Todo`` objects).
        """
        path = self._build_path("api", "v3", "todo", "search")
        return await self._get_list(path, BaseEntity, {"q": q})

    async def busy_days(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """Get an aggregate of busy days in a date range.

        Args:
            from_date: Range start, ``YYYY-MM-DD``.
            to_date: Range end, ``YYYY-MM-DD``.

        Returns:
            Raw payloads as returned by the server. ``GET /todo/busyDays``
            answers with ``TodosBusyDay[]``, a shape the SDK has no typed
            model for yet — parse the dicts yourself until one is added.
        """
        path = self._build_path("api", "v3", "todo", "busyDays")
        response = await self._http.get(path, params={"from": from_date, "to": to_date})
        return self._parse_list_response(response)

    async def get_comments(self, todo_id: int) -> list[Comment]:
        """Get comments for a todo.

        Args:
            todo_id: Todo identifier.

        Returns:
            List of comments.
        """
        return await self._get_entity_comments("todo", todo_id)

    async def get_linked_deals(self, todo_id: int) -> list[Deal]:
        """Get deals linked to a todo.

        Args:
            todo_id: Todo identifier.

        Returns:
            Linked deals.
        """
        return await self._get_linked_entities(todo_id, "deals", Deal)

    async def get_linked_tasks(self, todo_id: int) -> list[Task]:
        """Get tasks linked to a todo.

        Args:
            todo_id: Todo identifier.

        Returns:
            Linked tasks.

        Note:
            The subresource is named ``issues``, not ``tasks`` — a trap in
            the API surface this method hides from callers.
        """
        return await self._get_linked_entities(todo_id, "issues", Task)
