"""Entity registry: the single authority for Megaplan API naming.

One entry per entity type answers every naming question the SDK has:
the polymorphic ``contentType`` string, the filter ``contentType`` and the
filter endpoint path segment, plus legacy aliases the API uses in paths
("todo" for tasks, "trade" for deals). Resources must consult this module
instead of keeping their own string tables.
"""

from dataclasses import dataclass

from megaplan_sdk.constants import ContentType


@dataclass(frozen=True)
class EntityInfo:
    """Naming facts for one entity type.

    Attributes:
        entity_type: Canonical API path segment (e.g. "task", "deal").
        content_type: Polymorphic contentType string (e.g. "Task").
        filter_content_type: contentType of the entity's saved filters.
            None means the regular ``{ContentType}Filter`` pattern applies.
        aliases: Legacy path segments the API also uses for this entity.
    """

    entity_type: str
    content_type: str
    filter_content_type: str | None = None
    aliases: tuple[str, ...] = ()


_ENTITIES: tuple[EntityInfo, ...] = (
    EntityInfo("task", ContentType.TASK, aliases=("todo",)),
    # The single irregular filter name: deals use TradeFilter, not DealFilter.
    EntityInfo("deal", ContentType.DEAL, filter_content_type="TradeFilter", aliases=("trade",)),
    EntityInfo("project", ContentType.PROJECT),
    EntityInfo("employee", ContentType.EMPLOYEE),
    EntityInfo("contractor", ContentType.CONTRACTOR),
    EntityInfo("contractorCompany", ContentType.CONTRACTOR_COMPANY),
    EntityInfo("contractorHuman", ContentType.CONTRACTOR_HUMAN),
    EntityInfo("contractorCategory", ContentType.CONTRACTOR_CATEGORY),
    EntityInfo("department", ContentType.DEPARTMENT),
    EntityInfo("comment", ContentType.COMMENT),
    EntityInfo("group", ContentType.GROUP),
    EntityInfo("knowledgeBase", ContentType.KNOWLEDGE_BASE),
    EntityInfo("knowledgeArticle", ContentType.KNOWLEDGE_ARTICLE),
)

ENTITY_REGISTRY: dict[str, EntityInfo] = {
    key: info for info in _ENTITIES for key in (info.entity_type, *info.aliases)
}


def content_type_for(entity_type: str) -> str:
    """Resolve an API entity type (or alias) to its contentType string.

    Args:
        entity_type: API path segment (e.g. "employee", "todo", "contractorCompany").

    Returns:
        contentType string (e.g. "Employee", "Task", "ContractorCompany").
        Unknown types fall back to ``capitalize()``.
    """
    info = ENTITY_REGISTRY.get(entity_type)
    if info is not None:
        return info.content_type
    return entity_type.capitalize()


def filter_content_type_for(entity_type: str) -> str:
    """Resolve an entity type to the contentType of its saved filters.

    Args:
        entity_type: API path segment or alias (e.g. "task", "deal", "trade").

    Returns:
        Filter contentType string (e.g. "TaskFilter", "TradeFilter").
    """
    info = ENTITY_REGISTRY.get(entity_type)
    if info is not None and info.filter_content_type is not None:
        return info.filter_content_type
    return f"{content_type_for(entity_type)}Filter"


def filter_path_for(entity_type: str) -> str:
    """Resolve an entity type to the filter endpoint path segment.

    Args:
        entity_type: API path segment, alias, or an already-normalized
            filter path (e.g. "task", "trade", "taskFilter").

    Returns:
        Path segment for /api/v3/{path} (e.g. "taskFilter", "tradeFilter").
        The caller's casing is preserved for unknown types
        (e.g. "fileStorage" -> "fileStorageFilter").
    """
    if entity_type.endswith("Filter"):
        return entity_type
    filter_content_type = filter_content_type_for(entity_type)
    # Unknown types keep the caller's casing: derive the path from the raw
    # input, not from the capitalized fallback contentType.
    if ENTITY_REGISTRY.get(entity_type) is None:
        return f"{entity_type}Filter"
    return filter_content_type[0].lower() + filter_content_type[1:]
