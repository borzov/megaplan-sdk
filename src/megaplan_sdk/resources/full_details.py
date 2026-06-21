"""FullDetailsMixin for unified get_full_details implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

    from megaplan_sdk.resources.base import BaseResource


@dataclass
class RelatedDataConfig:
    """Configuration for related data loading in get_full_details.

    Attributes:
        field_name: Name of the field in FullDetails model (e.g., "sub_tasks").
        include_flag: Name of the include_* parameter (e.g., "include_sub_tasks").
        fetch_method: Name of the method to call for loading (e.g., "get_sub_tasks").
            If None, entity_field and entity_type must be provided for entity loading.
        entity_field: Name of the field in main entity to check (e.g., "responsible").
            Used when fetch_method is None.
        entity_type: Entity type for _get_entity_cached (e.g., "employee", "contractor").
            Used when fetch_method is None.
        limit_param: Name of the limit parameter in kwargs (e.g., "comments_limit").
        fetch_args: Additional arguments to pass to fetch_method.
        custom_fetcher: Custom async method to fetch data.
            Bound method that takes (entity_id, **kwargs) and returns coroutine.
    """

    field_name: str
    include_flag: str
    fetch_method: str | None = None
    entity_field: str | None = None
    entity_type: str | None = None
    limit_param: str | None = None
    fetch_args: dict[str, Any] | None = None
    custom_fetcher: Callable[..., Awaitable[Any]] | None = None


class FullDetailsMixin:
    """Mixin for implementing get_full_details with configurable related data loading."""

    async def _get_full_details_generic(
        self: BaseResource,
        entity_id: int,
        entity_getter: str,
        full_details_class: type[BaseModel],
        config: list[RelatedDataConfig],
        main_entity_field: str,
        **kwargs: Any,
    ) -> BaseModel:
        """Generic implementation of get_full_details.

        Args:
            entity_id: Identifier of the main entity.
            entity_getter: Name of the method to get main entity (e.g., "get").
            full_details_class: FullDetails model class to instantiate.
            config: List of RelatedDataConfig for supported related data.
            main_entity_field: Name of the field in FullDetails for main entity
                (e.g., "task", "project", "deal").
            **kwargs: Parameters from get_full_details call.

        Returns:
            Instance of full_details_class with all requested data.
        """
        # Get main entity
        getter = getattr(self, entity_getter)
        main_entity = await getter(entity_id)

        # Guard: a *_limit without its include_* flag silently does nothing (#2).
        # Reject it with a clear error instead of returning empty/stub data.
        # This guard runs BEFORE the global-defaults block so that a client-level
        # default (injected below) never triggers a false-positive error here.
        for item_config in config:
            limit_param = item_config.limit_param
            if limit_param is None:
                continue
            if kwargs.get(limit_param) is not None and not kwargs.get(item_config.include_flag):
                raise ValueError(
                    f"'{limit_param}' was provided but '{item_config.include_flag}' is False. "
                    f"Pass '{item_config.include_flag}=True' to load this data, "
                    f"or omit '{limit_param}'."
                )

        # Apply global defaults for limit parameters if not explicitly provided
        # Note: parameters are always in kwargs (even if None), so check value instead of presence
        if hasattr(self, "_default_comments_limit") and kwargs.get("comments_limit") is None:
            if self._default_comments_limit is not None:
                kwargs["comments_limit"] = self._default_comments_limit

        if hasattr(self, "_default_history_limit") and kwargs.get("history_limit") is None:
            if self._default_history_limit is not None:
                kwargs["history_limit"] = self._default_history_limit

        # Prepare parallel tasks
        tasks: dict[str, Any] = {}

        for item_config in config:
            include_value = kwargs.get(item_config.include_flag, False)
            if not include_value:
                continue

            # Handle custom fetcher
            if item_config.custom_fetcher:
                # custom_fetcher is a bound method, call it with entity_id and kwargs
                tasks[item_config.field_name] = item_config.custom_fetcher(entity_id, **kwargs)
                continue

            # Handle entity loading (responsible, owner, contractor)
            if item_config.fetch_method is None:
                if item_config.entity_field and item_config.entity_type:
                    entity_ref = getattr(main_entity, item_config.entity_field, None)
                    if entity_ref and hasattr(entity_ref, "id"):
                        # Import model class based on entity_type
                        if item_config.entity_type == "employee":
                            from megaplan_sdk.models.employee import Employee

                            model_class = Employee
                        elif item_config.entity_type == "contractor":
                            from megaplan_sdk.models.contractor import Contractor

                            model_class = Contractor
                        else:
                            continue

                        tasks[item_config.field_name] = self._get_entity_cached(
                            item_config.entity_type, entity_ref.id, model_class
                        )
                continue

            # Handle method-based loading (lists, etc.)
            fetch_method = getattr(self, item_config.fetch_method)
            fetch_kwargs: dict[str, Any] = {}

            # Add entity_id as first positional argument
            # Methods like get_sub_tasks(task_id, ...) or get_comments(deal_id, ...)
            if item_config.limit_param and item_config.limit_param in kwargs:
                fetch_kwargs["limit"] = kwargs[item_config.limit_param]

            if item_config.fetch_args:
                fetch_kwargs.update(item_config.fetch_args)

            # Call method with entity_id and kwargs
            tasks[item_config.field_name] = fetch_method(entity_id, **fetch_kwargs)

        # Execute all tasks in parallel
        task_results = await self._fetch_details_parallel(tasks)

        # Build FullDetails object
        details_kwargs: dict[str, Any] = {main_entity_field: main_entity}
        for item_config in config:
            details_kwargs[item_config.field_name] = task_results.get(item_config.field_name)

        return full_details_class(**details_kwargs)
