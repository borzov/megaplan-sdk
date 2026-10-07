"""Entity todos generics shared by all resources that expose /todos.

`EntityTodosMixin` needs a handful of members from the `BaseResource` it is
mixed into (`_build_path`, `_build_list_params`, `_get_list`). Those stay
defined on `BaseResource`; `_TodosHost` below is a structural `Protocol` used
only to type `self` inside this mixin's methods, mirroring the approach taken
by `HistoryMixin` in `_history.py` — so mypy strict can check attribute access
without a runtime or import-time dependency on `base.py`.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from megaplan_sdk.models.todo import Todo
from megaplan_sdk.resources._id_param import IdParamMeta

T = TypeVar("T")


class _TodosHost(Protocol):
    """Members `EntityTodosMixin` requires from the resource it is mixed into."""

    _history_entity_type: str

    def _build_path(self, *parts: str) -> str: ...

    def _build_list_params(
        self,
        filter: Any | None = None,
        limit: int | None = None,
        page_after: Any | None = None,
        page_before: Any | None = None,
        page_with: Any | None = None,
        fields: Any | None = None,
        sort_by: list[dict[str, str]] | None = None,
        only_requested_fields: bool | None = None,
        page_content_type: str | None = None,
        page: Any | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]: ...

    async def _get_list(
        self,
        path: str,
        model_class: type[T],
        params: dict[str, Any] | None = None,
    ) -> list[T]: ...


class EntityTodosMixin(metaclass=IdParamMeta):
    """Access to the todos attached to an entity (/{entity}/{id}/todos)."""

    _own_id_param_methods = ("_todos_of_entity",)

    async def _get_entity_todos(
        self: _TodosHost,
        entity_type: str,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
    ) -> list[Todo]:
        """Get todos attached to one entity.

        Args:
            entity_type: API resource type (e.g., "deal", "task", "project",
                "contractor", "employee").
            entity_id: Entity identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.

        Returns:
            Todos attached to the entity.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "todos")
        params = self._build_list_params(limit=limit, page_after=page_after)
        return await self._get_list(path, Todo, params)

    async def _todos_of_entity(
        self: _TodosHost,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
    ) -> list[Todo]:
        """Todos of this resource's own entity.

        Shared body behind ``get_todos``. A resource exposes it by overriding
        ``get_todos`` with a one-line delegation; the mixin method raises, so a
        resource that never had ``get_todos`` behaves as if it still does not.

        Args:
            entity_id: Entity identifier. Bound per resource under its own
                keyword — ``task_id``, ``deal_id``, ``project_id``,
                ``employee_id``.
            limit: Number of items per page.
            page_after: Load page starting from this entity.

        Returns:
            Todos of the entity.
        """
        return await self._get_entity_todos(self._history_entity_type, entity_id, limit, page_after)

    async def get_todos(
        self: _TodosHost,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
    ) -> list[Todo]:
        """Get todos attached to this entity.

        Only the resources that override this method actually have it. For
        every other resource the call fails as a missing attribute, because the
        method is inherited from a mixin shared by all of them.

        Raises:
            AttributeError: This resource does not expose ``get_todos``.
        """
        del entity_id, limit, page_after
        raise AttributeError(f"{type(self).__name__} has no attribute 'get_todos'")
