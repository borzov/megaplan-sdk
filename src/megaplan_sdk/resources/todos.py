"""Todos resource for Megaplan API — read and write access to todos ("Дела")."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.comment import Comment
from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.history import LinkEvent, parse_history_entry
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

    Note:
        Three ``doAction`` requests are investigated, not forgotten:
        ``accept_invitation``/``reject_invitation`` — route accepts the body
        but a live probe got 403 "No act_accept_invite/act_reject_invite
        rights" (the probing account can't be an invited participant on its
        own todo); needs a probe from an account that actually holds a
        pending invitation. ``delete_repeatable`` — needs a repeating todo,
        but every ``when`` shape tried on create 422s; needs the accepted
        wire format for ``when``. ``give`` — no request type exists for it in
        the API (``possibleActions`` lists ``act_give``, but there is no
        ``TodoGiveActionRequest`` in the schema).
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

    async def _do_action(self, todo_id: int, body: dict[str, Any]) -> Todo:
        """Send ``POST /todo/{id}/doAction`` and parse the resulting todo.

        The shared action route used by :meth:`finish`, :meth:`renew` and
        :meth:`take` (and the same convention Tasks and Projects use). Each
        caller builds its own discriminated ``Todo*ActionRequest`` body.

        Args:
            todo_id: Todo identifier.
            body: Action request body, including its ``contentType``.

        Returns:
            The todo after the action was applied.
        """
        path = self._build_path("api", "v3", "todo", str(todo_id), "doAction")
        response = await self._http.post(path, json_data=body)
        return Todo(**self._parse_single_response(response))

    async def finish(
        self,
        todo_id: int,
        status_id: int | None = None,
        result_text: str | None = None,
        result_attaches: list[dict[str, Any]] | None = None,
        notify_contractors: bool | None = None,
    ) -> Todo:
        """Finish a todo via the shared ``doAction`` route.

        Confirmed on a live account: the request returns 200 and switches
        the todo's status. ``result_text`` does **not** end up in a
        ``Todo.resultText`` field — there is none — the server instead posts
        it as a regular ``Comment`` on the todo (``"<p>{result_text}</p>"``).

        Args:
            todo_id: Todo identifier.
            status_id: Id of a ``TodoStatus`` to switch to. A ``masterType``
                of "finished", "success", "fail" or "finish_without_result"
                closes the todo — see ``GET /api/v3/todoStatus`` for the
                account's actual status list, since ids are not stable
                across accounts. Optional; omit to let the server pick the
                default finished status.
            result_text: Result note. Ends up as a ``Comment`` on the todo,
                not a field on it (see above).
            result_attaches: File references (``{contentType, id}``) to
                attach to the result.
            notify_contractors: Whether to notify contractors about the
                result.

        Returns:
            The finished todo.
        """
        body: dict[str, Any] = {"contentType": "TodoFinishActionRequest"}
        if status_id is not None:
            body["status"] = {"contentType": "TodoStatus", "id": str(status_id)}
        if result_text is not None:
            body["resultText"] = result_text
        if result_attaches is not None:
            body["resultAttaches"] = result_attaches
        if notify_contractors is not None:
            body["notifyContractors"] = notify_contractors
        return await self._do_action(todo_id, body)

    async def renew(self, todo_id: int) -> Todo:
        """Revert a finished todo back to "scheduled" via ``doAction``.

        Confirmed on a live account: works when the todo is currently
        finished (status returns to "scheduled"). Calling it on a todo that
        is not finished 403s with "No act_renew rights for model {id}" —
        that is server-side state gating, not an SDK error.

        Args:
            todo_id: Todo identifier.

        Returns:
            The renewed todo.
        """
        return await self._do_action(todo_id, {"contentType": "TodoRenewActionRequest"})

    async def take(self, todo_id: int) -> Todo:
        """Take a todo — assign the current user as ``responsible``.

        Confirmed on a live account: the request returns 200 and sets
        ``responsible`` to the current user.

        Args:
            todo_id: Todo identifier.

        Returns:
            The todo with ``responsible`` set to the current user.
        """
        return await self._do_action(todo_id, {"contentType": "TodoTakeActionRequest"})

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

    async def get_history(
        self,
        todo_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> list[Any]:
        """Get the journal of a todo.

        The stream is mixed: ``Changeset`` (field changes), ``BasedOnHistory``
        (link/unlink), comments, trigger logs. Known types are parsed; unknown
        ones are returned as raw dicts, so a new server-side type never breaks
        the call.

        Args:
            todo_id: Todo identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            raw: Return untouched payloads (pre-0.6.1 behaviour).

        Returns:
            Journal entries, newest first.

        Examples:
            >>> history = await client.todos.get_history(todo_id=88, limit=10)
        """
        entries = await self._get_entity_history(
            "todo", todo_id, limit, page_after, page_before, page_with
        )
        if raw:
            return list(entries)
        return [parse_history_entry(entry) for entry in entries]

    async def iterate_history(
        self,
        todo_id: int,
        limit: int = 100,
        raw: bool = False,
    ) -> AsyncIterator[Any]:
        """Iterate the todo's journal with automatic pagination.

        Args:
            todo_id: Todo identifier.
            limit: Number of entries per page.
            raw: Yield untouched payloads instead of parsed entries.

        Yields:
            Journal entries, newest first.
        """
        async for entry in self._iterate_entity_history("todo", todo_id, limit, raw):
            yield entry

    async def get_link_events(
        self,
        todo_id: int,
        since_id: int | None = None,
        since_time: str | None = None,
        limit: int = 100,
    ) -> list[LinkEvent]:
        """Get link/unlink events for a todo.

        Args:
            todo_id: Todo identifier.
            since_id: Return only events newer than this event id — store the
                largest id seen to poll incrementally.
            since_time: Return only events created strictly after this
                ISO-8601 timestamp.
            limit: Number of journal entries fetched per page.

        Returns:
            Link events, newest first.

        Examples:
            >>> events = await client.todos.get_link_events(todo_id=88)
        """
        return await self._get_link_events("todo", todo_id, since_id, since_time, limit)
