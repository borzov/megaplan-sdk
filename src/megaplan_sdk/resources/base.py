"""Base resource class for Megaplan API resources."""

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from megaplan_sdk.constants import ContentType
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger
from megaplan_sdk.registry import content_type_for
from megaplan_sdk.resources._expand import ExpandRule

if TYPE_CHECKING:
    from megaplan_sdk.cache import EntityCache
    from megaplan_sdk.models.comment import Comment
    from megaplan_sdk.models.contractor import Contractor

T = TypeVar("T")


class BaseResource:
    """Base class for all API resources.

    Provides common functionality for making API requests.
    """

    def __init__(
        self,
        http_client: HTTPClient,
        cache: "EntityCache | None" = None,
        default_comments_limit: int | None = None,
        default_history_limit: int | None = None,
    ) -> None:
        """Initialize base resource.

        Args:
            http_client: HTTP client for making requests.
            cache: Optional entity cache for caching related entities.
            default_comments_limit: Default limit for comments in get_full_details().
                None = use API default (no explicit limit).
            default_history_limit: Default limit for history in get_full_details().
                None = use API default (no explicit limit).
        """
        self._http = http_client
        self._cache = cache
        self._default_comments_limit = default_comments_limit
        self._default_history_limit = default_history_limit

    # Default contentType for pagination refs (page_after/before/with). Resource
    # subclasses override this so a bare int id can be wrapped into the entity
    # link {contentType, id} the server requires (#23). None = unknown.
    _page_content_type: str | None = None

    # Declarative expand pipeline (see _expand.py). Subclasses fill
    # _expand_rules with field name -> ExpandRule. Wrap-mode resources also
    # declare _details_model (the *FullDetails container) and _main_field (the
    # container attribute holding the wrapped entity); without _details_model
    # the engine runs in replace mode: loaded entities replace the reference
    # fields on immutable copies.
    _expand_rules: ClassVar[dict[str, ExpandRule]] = {}
    _details_model: ClassVar[type[Any] | None] = None
    _main_field: ClassVar[str | None] = None

    def _build_path(self, *parts: str) -> str:
        """Build API path from parts.

        Args:
            *parts: Path parts.

        Returns:
            Combined path.
        """
        return "/" + "/".join(str(part).strip("/") for part in parts if part)

    def _prepare_params(self, **kwargs: Any) -> dict[str, Any] | None:
        """Prepare query parameters, removing None values.

        Args:
            **kwargs: Parameters to include.

        Returns:
            Dictionary with non-None parameters.
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        return params if params else None

    def _normalize_base_entity(self, entity: dict[str, Any] | Any) -> dict[str, Any]:
        """Normalize BaseEntity to ensure correct format.

        Ensures BaseEntity objects have contentType and id in correct format.
        Converts Pydantic models to dicts and ensures id is int (not string).

        Args:
            entity: BaseEntity as dict, Pydantic model, or other object.

        Returns:
            Normalized BaseEntity as dict.
        """
        # Handle dict - normalize id field
        if isinstance(entity, dict):
            normalized = dict(entity)
            if "id" in normalized and isinstance(normalized["id"], str):
                try:
                    normalized["id"] = int(normalized["id"])
                except (ValueError, TypeError):
                    pass
            return normalized

        # Handle Pydantic models
        if hasattr(entity, "model_dump"):
            return entity.model_dump(by_alias=True)

        # Handle objects with id attribute
        if hasattr(entity, "id"):
            content_type = getattr(entity, "contentType", None) or getattr(
                entity, "content_type", None
            )
            return {"contentType": content_type, "id": entity.id}

        return entity

    def _coerce_page_ref(
        self,
        value: Any,
        default_content_type: str | None = None,
    ) -> Any:
        """Normalize a pagination ref to the server's ``{contentType, id}`` link (#23).

        The server requires an entity link, not a bare id or a full model dump.
        Accepts an ``int`` id, a Pydantic model / object with ``id``, or a dict;
        fills in ``contentType`` from the model or the resource default when the
        caller did not supply it.

        Args:
            value: ``int`` id, entity/model, dict link, or None.
            default_content_type: Fallback contentType (resource's entity type).

        Returns:
            A clean ``{"contentType": ..., "id": int}`` dict, or the value
            unchanged if it cannot be interpreted.
        """
        if value is None:
            return None
        ct = default_content_type or self._page_content_type
        # Entity / Pydantic model with an id → clean link (NOT a full dump, which
        # carries extra fields the server rejects with 422).
        if not isinstance(value, dict | int) and hasattr(value, "id"):
            model_ct = getattr(value, "content_type", None) or getattr(value, "contentType", None)
            return {"contentType": model_ct or ct, "id": value.id}
        if isinstance(value, bool):  # guard: bool is an int subclass
            return value
        if isinstance(value, int):
            return {"contentType": ct, "id": value}
        if isinstance(value, dict):
            link = dict(value)
            if "id" in link and isinstance(link["id"], str):
                try:
                    link["id"] = int(link["id"])
                except (ValueError, TypeError):
                    pass
            if "contentType" not in link and ct:
                link["contentType"] = ct
            return link
        return value

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
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Build standard list parameters for pagination and filtering.

        Args:
            filter: Filter ID or configuration.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            fields: Additional fields to include.
            sort_by: Sort fields.
            only_requested_fields: Return only requested fields.
            **extra_params: Additional parameters (e.g., statuses, status, q).

        Returns:
            Dictionary with non-None parameters.
        """
        params: dict[str, Any] = {}

        if filter is not None:
            params["filter"] = filter
        if limit is not None:
            params["limit"] = limit
        if page_after is not None:
            params["pageAfter"] = self._coerce_page_ref(page_after, page_content_type)
        if page_before is not None:
            params["pageBefore"] = self._coerce_page_ref(page_before, page_content_type)
        if page_with is not None:
            params["pageWith"] = self._coerce_page_ref(page_with, page_content_type)
        if fields is not None:
            params["fields"] = fields
        if sort_by:
            params["sortBy"] = sort_by
        if only_requested_fields is not None:
            params["onlyRequestedFields"] = only_requested_fields

        # Add extra params (like statuses, status, q, baseOn, etc.)
        # Filter out None values to avoid sending null in JSON
        filtered_extra = {k: v for k, v in extra_params.items() if v is not None}

        # Normalize BaseEntity in extra params (e.g., baseOn)
        for key, value in filtered_extra.items():
            if key in ("baseOn", "base_on") and isinstance(value, dict):
                params[key if key == "baseOn" else "baseOn"] = self._normalize_base_entity(value)
            else:
                params[key] = value

        return params if params else {}

    _Q_ALLOWED_FIELDS = ("name", "statement")

    def _q_to_filter(self, filter_content_type: str, q: str, q_in: list[str]) -> dict[str, Any]:
        """Convert a free-text query into a FilterBuilder filter.

        Megaplan ignores a raw ``q`` param (it is not in the RAML), so a
        ``q=`` that the user expects to search silently returns 0 (#11).
        Only ``name`` and ``statement`` are filterable server-side; other
        text fields (``description``/``subject``/...) are silently ignored.

        Args:
            filter_content_type: e.g. ``"TaskFilter"`` / ``"TradeFilter"``.
            q: Search needle.
            q_in: Fields to search; subset of ``name``/``statement``.

        Returns:
            A filter dict ready for the ``filter`` query param.

        Raises:
            NotImplementedError: If ``q_in`` contains a non-filterable field.
        """
        from megaplan_sdk.filter_builder import FilterBuilder

        invalid = [f for f in q_in if f not in self._Q_ALLOWED_FIELDS]
        if invalid:
            raise NotImplementedError(
                f"Server-side text filter on {invalid} is silently ignored by "
                f"Megaplan; only {list(self._Q_ALLOWED_FIELDS)} work. (#11)"
            )
        builder = FilterBuilder(filter_content_type)
        for i, field_name in enumerate(q_in):
            if i:
                builder.or_()
            builder.field(field_name).contains(q)
        return builder.build()

    async def _iterate_generic(
        self,
        content_type: str,
        list_method: Any,  # Method bound to instance, not a standalone Callable
        limit: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Generic iterator for paginating through resources.

        Args:
            content_type: Entity type for pageAfter (e.g. "Task", "Deal").
            list_method: The list() method to call for pagination.
            limit: Items per page.
            **kwargs: Additional parameters to pass to list_method.

        Yields:
            Individual items from the paginated results.
        """
        page_after = None

        while True:
            items: list[T] = await list_method(limit=limit, page_after=page_after, **kwargs)
            if not items:
                break

            for item in items:
                yield item

            if len(items) < limit:
                break

            last_item = items[-1]
            item_id = getattr(last_item, "id", None)
            if item_id is None:
                logger.warning(f"Entity without id during pagination: {type(last_item).__name__}")
                break
            page_after = {"contentType": content_type, "id": item_id}

    async def _get_entity_comments(
        self,
        entity_type: str,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list["Comment"]:
        """Generic method to get comments for any entity.

        Args:
            entity_type: API path segment (e.g. "todo" for tasks, "project", "deal", "contractor").
            entity_id: Entity identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of comments.
        """
        from megaplan_sdk.models.comment import Comment

        path = self._build_path("api", "v3", entity_type, str(entity_id), "comments")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        return [Comment(**item) if isinstance(item, dict) else item for item in data]

    async def _create_entity_comment(
        self,
        entity_type: str,
        entity_id: int,
        text: str,
        attaches: "list[dict[str, Any]] | None" = None,
        **extra_fields: Any,
    ) -> "Comment":
        """Generic method to create comment for any entity.

        Args:
            entity_type: API path segment.
            entity_id: Entity identifier.
            text: Comment text.
            attaches: File attachments.
            **extra_fields: Additional fields (e.g. work for tasks).

        Returns:
            Created comment.
        """
        from megaplan_sdk.models.comment import Comment

        path = self._build_path("api", "v3", entity_type, str(entity_id), "comments")

        comment_data: dict[str, Any] = {"content": text}
        if attaches:
            comment_data["attaches"] = attaches
        comment_data.update(extra_fields)

        response = await self._http.post(path, json_data=comment_data)
        return Comment(**response["data"])

    async def _get_list(
        self,
        path: str,
        model_class: type[T],
        params: dict[str, Any] | None = None,
    ) -> list[T]:
        """Generic method to fetch and parse list response.

        Args:
            path: API endpoint path.
            model_class: Pydantic model class for items.
            params: Query parameters.

        Returns:
            List of model instances.
        """
        response = await self._http.get(path, params=params)
        data = self._parse_list_response(response)

        return [model_class(**item) if isinstance(item, dict) else item for item in data]

    async def _create_entity(
        self,
        entity_type: str,
        data: dict[str, Any],
        model_class: type[T],
    ) -> T:
        """Generic create method.

        Args:
            entity_type: API resource type (e.g. "task", "project").
            data: Entity data.
            model_class: Pydantic model class.

        Returns:
            Created entity instance.
        """
        path = self._build_path("api", "v3", entity_type)
        response = await self._http.post(path, json_data=data)
        return model_class(**response["data"])

    async def _get_entity(
        self,
        entity_type: str,
        entity_id: int,
        model_class: type[T],
    ) -> T:
        """Generic get method.

        Args:
            entity_type: API resource type.
            entity_id: Entity identifier.
            model_class: Pydantic model class.

        Returns:
            Entity instance.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id))
        response = await self._http.get(path)
        return model_class(**response["data"])

    async def _update_entity(
        self,
        entity_type: str,
        entity_id: int,
        data: dict[str, Any],
        model_class: type[T],
    ) -> T:
        """Generic update method.

        Args:
            entity_type: API resource type.
            entity_id: Entity identifier.
            data: Updated entity data.
            model_class: Pydantic model class.

        Returns:
            Updated entity instance.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id))
        response = await self._http.post(path, json_data=data)
        return model_class(**response["data"])

    async def _delete_entity(
        self,
        entity_type: str,
        entity_id: int,
    ) -> None:
        """Generic delete method.

        Args:
            entity_type: API resource type.
            entity_id: Entity identifier.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id))
        await self._http.delete(path)

    async def _get_entity_cached(
        self,
        entity_type: str,
        entity_id: int,
        model_class: type[T],
        use_cache: bool = True,
    ) -> T:
        """Get entity with optional caching.

        Fetches entity from cache if available and not expired,
        otherwise fetches from API and caches result.

        Args:
            entity_type: API resource type (e.g., "employee", "task").
            entity_id: Entity identifier.
            model_class: Pydantic model class for parsing.
            use_cache: Whether to use cache (default: True).

        Returns:
            Entity instance.

        Examples:
            >>> employee = await resource._get_entity_cached(
            ...     "employee", 123, Employee
            ... )
        """
        # Determine contentType from entity_type
        content_type = self._entity_type_to_content_type(entity_type)

        if use_cache:
            cached = self._cache_get(content_type, entity_id, model_class)
            if cached is not None:
                return cached

        entity = await self._get_entity(entity_type, entity_id, model_class)

        if use_cache:
            self._cache_put(content_type, entity_id, entity)

        return entity

    def _cache_get(self, content_type: str, entity_id: int, model_class: type[T]) -> T | None:
        """Read an entity from cache, parsing the stored payload into a model.

        The cache storage format is decided here and in _cache_put ONLY —
        no other code may interpret cached payloads.
        """
        if not self._cache:
            return None
        cached = self._cache.get(content_type, entity_id)
        if cached is None:
            return None
        return model_class(**cached) if isinstance(cached, dict) else cached  # type: ignore[no-any-return]

    def _cache_put(self, content_type: str, entity_id: int, entity: Any) -> None:
        """Store an entity in cache as a by-alias dict (the storage format)."""
        if self._cache:
            self._cache.set(content_type, entity_id, entity.model_dump(by_alias=True))

    async def _load_related_entities(
        self,
        entities: list[Any],
        entity_type: str,
        model_class: type[T],
    ) -> dict[int, T]:
        """Batch load related entities with caching.

        Collects unique entity IDs, checks cache for each,
        then fetches missing ones in parallel.

        Args:
            entities: List of BaseEntity references to load (can contain None).
            entity_type: API resource type (e.g., "employee", "contractor").
            model_class: Pydantic model class.

        Returns:
            Dict mapping entity ID to loaded entity.

        Examples:
            >>> # Load all unique responsible employees from tasks
            >>> responsible_refs = [task.responsible for task in tasks]
            >>> employees = await resource._load_related_entities(
            ...     responsible_refs, "employee", Employee
            ... )
            >>> # employees = {123: Employee(...), 456: Employee(...)}
        """
        # Collect unique IDs (filter out None and extract id attribute)
        unique_ids: set[int] = set()
        for entity in entities:
            if entity is not None and hasattr(entity, "id"):
                unique_ids.add(entity.id)

        if not unique_ids:
            return {}

        content_type = self._entity_type_to_content_type(entity_type)
        result: dict[int, T] = {}
        ids_to_fetch: set[int] = set()

        # Check cache for each ID
        for entity_id in unique_ids:
            cached = self._cache_get(content_type, entity_id, model_class)
            if cached is not None:
                result[entity_id] = cached
            else:
                ids_to_fetch.add(entity_id)

        # Fetch missing entities in parallel
        if ids_to_fetch:
            fetch_tasks = [
                self._get_entity_cached(entity_type, entity_id, model_class, use_cache=True)
                for entity_id in ids_to_fetch
            ]
            fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for entity_id, entity in zip(ids_to_fetch, fetched, strict=True):
                if not isinstance(entity, Exception):
                    result[entity_id] = entity  # type: ignore[assignment]
                # Ignore exceptions during batch loading

        return result

    async def _bulk_get_entities_by_links(
        self, links: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """POST /api/v3/bulk/getEntitiesByLinks (raw, internal).

        Body is a plain JSON array of ``{"contentType", "id"}`` links.
        The endpoint silently drops inaccessible entities and does NOT
        preserve order. Do NOT use for Employee — the server 500s (#FR-1).
        """
        path = self._build_path("api", "v3", "bulk", "getEntitiesByLinks")
        response = await self._http.post(path, json_data=links)
        data: list[dict[str, Any]] = response.get("data", [])
        return data

    async def _get_many_via_bulk(
        self,
        content_type: str,
        ids: list[int],
        model_class: type[T],
        use_cache: bool = True,
    ) -> dict[int, T]:
        """Batch-fetch entities by id via the bulk endpoint, keyed by id.

        Missing/inaccessible ids are absent from the result. Cache is read
        and populated. Order is irrelevant since the result is a dict.
        """
        result: dict[int, T] = {}
        missing: list[int] = []
        for entity_id in dict.fromkeys(ids):  # de-dupe, preserve order
            if use_cache:
                cached = self._cache_get(content_type, entity_id, model_class)
                if cached is not None:
                    result[entity_id] = cached
                    continue
            missing.append(entity_id)

        if missing:
            links = [{"contentType": content_type, "id": str(i)} for i in missing]
            for item in await self._bulk_get_entities_by_links(links):
                entity = model_class(**item)
                entity_id = int(item["id"])
                result[entity_id] = entity
                if use_cache:
                    self._cache_put(content_type, entity_id, entity)
        return result

    async def _get_many_sequential(
        self,
        entity_type: str,
        ids: list[int],
        model_class: type[T],
        use_cache: bool = True,
    ) -> dict[int, T]:
        """Fetch entities by id via parallel single gets, keyed by id.

        Fallback for entity types the bulk endpoint cannot handle (Employee
        500s — #FR-1). Inaccessible ids are dropped.
        """
        unique = list(dict.fromkeys(ids))
        fetched = await asyncio.gather(
            *(
                self._get_entity_cached(entity_type, i, model_class, use_cache=use_cache)
                for i in unique
            ),
            return_exceptions=True,
        )
        result: dict[int, T] = {}
        for entity_id, entity in zip(unique, fetched, strict=True):
            if not isinstance(entity, Exception):
                result[entity_id] = entity
        return result

    @staticmethod
    def _entity_type_to_content_type(entity_type: str) -> str:
        """Convert API entity type to contentType.

        Uses explicit mapping to avoid issues with capitalize() on CamelCase names.
        For example, "contractorCompany" would become "Contractorcompany" with capitalize(),
        but API expects "ContractorCompany".

        Args:
            entity_type: API resource type (e.g., "employee", "task", "todo", "contractorCompany").

        Returns:
            ContentType string (e.g., "Employee", "Task", "ContractorCompany").

        Examples:
            >>> BaseResource._entity_type_to_content_type("employee")
            'Employee'
            >>> BaseResource._entity_type_to_content_type("task")
            'Task'
            >>> BaseResource._entity_type_to_content_type("todo")
            'Task'
            >>> BaseResource._entity_type_to_content_type("contractorCompany")
            'ContractorCompany'
        """
        return content_type_for(entity_type)

    @staticmethod
    def _parse_contractor_response(data: dict[str, Any]) -> "Contractor":
        """Parse contractor response and return appropriate type.

        Args:
            data: Contractor data dictionary.

        Returns:
            Contractor, ContractorCompany, or ContractorHuman instance.
        """
        from megaplan_sdk.models.contractor import Contractor, ContractorCompany, ContractorHuman

        content_type = data.get("contentType", ContentType.CONTRACTOR)
        if content_type == ContentType.CONTRACTOR_COMPANY:
            return ContractorCompany(**data)
        elif content_type == ContentType.CONTRACTOR_HUMAN:
            return ContractorHuman(**data)
        return Contractor(**data)

    async def _get_entity_related_list(
        self,
        entity_type: str,
        entity_id: int,
        related_type: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        model_class: type[T] | None = None,
    ) -> list[Any] | list[T]:
        """Generic method to get related list (auditors, executors, milestones).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            model_class: Optional Pydantic model class for parsing items.
                If provided, returns list[model_class], otherwise returns list[dict].

        Returns:
            List of related entities (parsed if model_class provided, otherwise raw dicts).
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), related_type)

        # Build params - always include limit for milestones to avoid 500 errors
        if related_type == "milestones" and limit is None:
            # Default limit for milestones to avoid API 500 errors
            params = self._build_list_params(limit=100)
        else:
            params = self._build_list_params(
                limit=limit,
                page_after=page_after,
                page_before=page_before,
                page_with=page_with,
            )

        response = await self._http.get(path, params=params if params else None)
        data = self._parse_list_response(response)

        if model_class:
            return [model_class(**item) if isinstance(item, dict) else item for item in data]
        return data

    async def _add_entity_related(
        self,
        entity_type: str,
        entity_id: int,
        related_type: str,
        related_id: int,
        related_content_type: str = ContentType.EMPLOYEE,
        data_override: dict[str, Any] | None = None,
    ) -> Any:
        """Generic method to add related entity (auditor, executor, milestone).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            related_id: Related entity ID.
            related_content_type: Content type of related entity (usually "Employee").
            data_override: Optional data override (for milestones with custom data).

        Returns:
            Added related entity.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), related_type)

        if data_override:
            related_data = data_override
        else:
            related_data = {"id": related_id, "contentType": related_content_type}

        response = await self._http.post(path, json_data=related_data)
        return self._parse_single_response(response)

    async def _remove_entity_related(
        self,
        entity_type: str,
        entity_id: int,
        related_type: str,
        related_id: int,
        related_content_type: str = ContentType.EMPLOYEE,
    ) -> None:
        """Generic method to remove related entity (auditor, executor, milestone).

        Args:
            entity_type: API resource type (e.g., "task", "project").
            entity_id: Entity identifier.
            related_type: Related resource type (e.g., "auditors", "executors", "milestones").
            related_id: Related entity ID.
            related_content_type: Content type of related entity (usually "Employee").
        """
        path = self._build_path(
            "api",
            "v3",
            entity_type,
            str(entity_id),
            related_type,
            related_content_type,
            str(related_id),
        )
        await self._http.delete(path)

    async def _get_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generic method to get history log for any entity.

        Args:
            entity_type: API resource type (e.g., "task", "project", "deal").
            entity_id: Entity identifier.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of history entries.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "history")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )

        response = await self._http.get(path, params=params if params else None)
        return self._parse_list_response(response)

    async def _search_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        query: str,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generic method to search in entity history log.

        Args:
            entity_type: API resource type (e.g., "task", "project", "deal").
            entity_id: Entity identifier.
            query: Search query.
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.

        Returns:
            List of matching history entries.
        """
        path = self._build_path("api", "v3", entity_type, str(entity_id), "history", "search")

        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
        )
        params_dict: dict[str, Any] = params if params is not None else {}
        params_dict["q"] = query

        response = await self._http.get(path, params=params_dict)
        return self._parse_list_response(response)

    async def _fetch_details_parallel(
        self,
        fetch_map: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute fetch tasks in parallel safely.

        Uses return_exceptions=True to prevent one failed fetch
        from breaking the entire request. Errors are logged but
        don't stop execution.

        Args:
            fetch_map: Dictionary of task_name -> coroutine.

        Returns:
            Dictionary of task_name -> result (None on error).
        """
        if not fetch_map:
            return {}

        results = await asyncio.gather(*fetch_map.values(), return_exceptions=True)

        final_data: dict[str, Any] = {}
        for key, result in zip(fetch_map.keys(), results, strict=True):
            if isinstance(result, NotImplementedError):
                # A knowingly unsupported feature must fail loudly,
                # not degrade to None
                raise result
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {key}: {result}")
                final_data[key] = None
            else:
                final_data[key] = result

        return final_data

    def _parse_list_response(self, response: dict[str, Any]) -> list[Any]:
        """Parse list response from API.

        Args:
            response: API response dictionary.

        Returns:
            List of items from response data.
        """
        data = response.get("data", [])
        return data if isinstance(data, list) else []

    def _parse_single_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse single entity response from API.

        Args:
            response: API response dictionary.

        Returns:
            Entity data dictionary.
        """
        data = response.get("data", {})
        return data if isinstance(data, dict) else {}

    async def _expand_and_wrap(
        self,
        entities: list[Any],
        expand: list[str] | None,
    ) -> list[Any]:
        """Run the declarative expand pipeline over listed entities.

        Loads the reference fields requested in ``expand`` per ``_expand_rules``
        (cache-first, batched), then assembles the result. Wrap mode
        (``_details_model`` declared): each entity is wrapped into the details
        container with loaded relatives in the rules' ``details_field``s.
        Replace mode: reference fields are replaced with loaded entities on
        immutable copies of the listed entities.

        Args:
            entities: Listed entities to expand.
            expand: Requested field names (unknown names are ignored).
                None or empty list returns ``entities`` unchanged.

        Returns:
            List of details containers (wrap mode) or entity copies
            (replace mode).
        """
        if not expand or not entities:
            return entities

        loaded_maps: dict[str, dict[int, Any]] = {}
        for field_name in expand:
            rule = self._expand_rules.get(field_name)
            if rule is None:
                continue
            refs = [
                ref
                for entity in entities
                if (ref := getattr(entity, field_name, None)) is not None and hasattr(ref, "id")
            ]
            if refs:
                loaded_maps[field_name] = await self._load_related_entities(
                    refs, rule.entity_type, rule.model
                )

        if self._details_model is not None:
            return self._wrap_into_details(entities, loaded_maps)
        return self._replace_references(entities, loaded_maps)

    def _wrap_into_details(
        self,
        entities: list[Any],
        loaded_maps: dict[str, dict[int, Any]],
    ) -> list[Any]:
        """Wrap entities into the details container with loaded relatives."""
        if self._details_model is None or self._main_field is None:
            raise TypeError(
                f"{type(self).__name__} must declare _details_model and _main_field "
                "to use wrap mode"
            )
        results: list[Any] = []
        for entity in entities:
            kwargs: dict[str, Any] = {self._main_field: entity}
            for field_name, rule in self._expand_rules.items():
                if rule.details_field is None:
                    continue
                ref = getattr(entity, field_name, None)
                loaded = loaded_maps.get(field_name, {})
                kwargs[rule.details_field] = (
                    loaded.get(ref.id) if ref is not None and hasattr(ref, "id") else None
                )
            results.append(self._details_model(**kwargs))
        return results

    def _replace_references(
        self,
        entities: list[Any],
        loaded_maps: dict[str, dict[int, Any]],
    ) -> list[Any]:
        """Replace reference fields with loaded entities on immutable copies."""
        results: list[Any] = []
        for entity in entities:
            updates: dict[str, Any] = {}
            for field_name, loaded in loaded_maps.items():
                ref = getattr(entity, field_name, None)
                if ref is not None and hasattr(ref, "id") and ref.id in loaded:
                    updates[field_name] = loaded[ref.id]
            results.append(entity.model_copy(update=updates) if updates else entity)
        return results

    async def _get_milestones_generic(
        self,
        entity_type: str,
        entity_id: int,
    ) -> list[Any]:
        """Generic method to get milestones for any entity (task or project).

        Note: Direct endpoint /{entity_type}/{id}/milestones returns 500 error.
        This method uses /{entity_type}/{id} with fields parameter to get milestones.

        Args:
            entity_type: API resource type ("task" or "project").
            entity_id: Entity identifier.

        Returns:
            List of Milestone objects.
        """
        from megaplan_sdk.exceptions import ServerError
        from megaplan_sdk.models.milestone import Milestone

        try:
            path = self._build_path("api", "v3", entity_type, str(entity_id))
            response = await self._http.get(path, params={"fields": ["milestones"]})
            entity_data = response.get("data", {})

            milestones_data = entity_data.get("milestones", [])
            if not milestones_data:
                return []

            if not isinstance(milestones_data, list):
                milestones_data = [milestones_data]

            return [
                Milestone(**item) if isinstance(item, dict) else item for item in milestones_data
            ]
        except ServerError:
            # Return empty list if server error occurs
            return []

    @staticmethod
    def _normalize_datetime_field(
        data_dict: dict[str, Any],
        field_name: str = "date",
    ) -> dict[str, Any]:
        """Normalize DateTime field by converting string to DateTime object.

        Returns a new dictionary with normalized field. Does not mutate the input.

        Args:
            data_dict: Data dictionary to normalize.
            field_name: Name of the field to normalize (default: "date").

        Returns:
            New dictionary with normalized DateTime field.

        Examples:
            >>> data = {"date": "2026-03-15T10:00:00Z"}
            >>> normalized = _normalize_datetime_field(data)
            >>> normalized
            {"date": {"contentType": "DateTime", "value": "2026-03-15T10:00:00Z"}}
        """
        if field_name in data_dict and isinstance(data_dict[field_name], str):
            # API expects DateTime object with contentType and value
            return {
                **data_dict,
                field_name: {"contentType": ContentType.DATE_TIME, "value": data_dict[field_name]},
            }
        return data_dict

    async def _add_milestone_generic(
        self,
        entity_type: str,
        entity_id: int,
        milestone_data: Any,
    ) -> Any:
        """Generic method to add milestone to any entity (task or project).

        Args:
            entity_type: API resource type ("task" or "project").
            entity_id: Entity identifier.
            milestone_data: Milestone data as Milestone object or dict.
                Required fields: description, type, date.
                Type must be one of: "report", "reminder", "note".
                Date can be ISO 8601 string, DateTime object, or dict.

        Returns:
            Created Milestone object.
        """
        from megaplan_sdk.models.milestone import Milestone

        # 1. Convert to dict
        if isinstance(milestone_data, Milestone):
            data_dict = milestone_data.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        else:
            data_dict = dict(milestone_data)
            data_dict.pop("id", None)
            if "contentType" not in data_dict:
                data_dict["contentType"] = "Milestone"

        # 2. Normalize date field (unified for both cases)
        data_dict = self._normalize_datetime_field(data_dict, "date")

        # 3. Send request
        path = self._build_path("api", "v3", entity_type, str(entity_id), "milestones")
        response = await self._http.post(path, json_data=data_dict)
        data = response.get("data", response)
        return Milestone(**data) if isinstance(data, dict) else data

    @staticmethod
    def _parse_mixed_task_project_response(
        data: list[dict[str, Any]],
    ) -> list[Any]:
        """Parse response containing mixed Task/Project entities.

        Determines entity type by contentType field and creates appropriate model.

        Args:
            data: List of entity dictionaries from API response.

        Returns:
            List of Task or Project instances.

        Examples:
            >>> data = [
            ...     {"contentType": "Task", "id": 1, "name": "Task 1"},
            ...     {"contentType": "Project", "id": 2, "name": "Project 1"},
            ... ]
            >>> entities = BaseResource._parse_mixed_task_project_response(data)
            >>> type(entities[0]).__name__
            'Task'
            >>> type(entities[1]).__name__
            'Project'
        """
        from megaplan_sdk.models.project import Project
        from megaplan_sdk.models.task import Task

        result: list[Any] = []
        for item in data:
            if not isinstance(item, dict):
                result.append(item)
                continue

            content_type = item.get("contentType", "")
            if content_type == ContentType.TASK:
                result.append(Task(**item))
            elif content_type == ContentType.PROJECT:
                result.append(Project(**item))
            else:
                # Unknown type - try Task first, then Project
                try:
                    result.append(Task(**item))
                except Exception:
                    try:
                        result.append(Project(**item))
                    except Exception:
                        # If both fail, append raw dict
                        result.append(item)

        return result
