"""Wire field names observed on Megaplan's list routes.

The November 2026 probes requested model aliases and selected API-only names.
Keep these snapshots independent of model changes. A field accepted in a GET
can be absent on a given record or unsuitable for searching or sorting.
"""

from typing import Any

from megaplan_sdk.constants import UNSUPPORTED_DEAL_FIELDS, UNSUPPORTED_TASK_FIELDS

# Each capped route returned 100 for limit=101 and a new entity after its last link.
_CAPPED_ROUTES = {
    "task",
    "deal",
    "contractor",
    "contractorCompany",
    "contractorHuman",
    "payer",
    "todo",
}

_CONTRACTOR_FIELDS = frozenset(
    "birthday contactInfo countDeals description id isDropped lastDealDate mergeInProgress "
    "name payers responsibles status tags timeCreated timeUpdated".split()
)
_CONTRACTOR_REJECTED = frozenset(
    "category contentType customFields email manager phone site".split()
)

CONFIRMED_LIST_FIELDS: dict[str, frozenset[str]] = {
    "task": frozenset(
        "activity actualFinish actualStart attaches auditors comments commentsCount "
        "contractor deadline deals duration executors humanNumber id isFavorite isNegotiation "
        "isOverdue isTemplate isUrgent lastCommentTimeCreated lastView milestones name owner "
        "parent participants plannedFinish project responsible rights statement status "
        "statusChangeTime subTasks tags tagsCount textStatement timeCreated todos "
        "unreadCommentsCount".split()
    ),
    "deal": frozenset(
        "attaches auditors comments commentsCount contractor cost currency debt description id isFavorite "
        "manager name nearTodo number positions possibleActions price program result "
        "shortDescription state stateTimeUpdated tags tagsCount timeCreated timeUpdated "
        "unreadCommentsCount".split()
    ),
    "employee": frozenset(
        "avatar birthday canLogin department fireInProgress firstName id isWorking lastName "
        "middleName name position status timeCreated".split()
    ),
    "project": frozenset(
        "activity actualFinish attaches commentsCount deadline id name owner parent responsible "
        "statement status tags textStatement timeCreated todos".split()
    ),
    "contractor": _CONTRACTOR_FIELDS,
    "contractorCompany": _CONTRACTOR_FIELDS,
    "contractorHuman": _CONTRACTOR_FIELDS | {"firstName", "middleName", "lastName"},
    # Search also accepts arbitrary names and silently omits them. Include only
    # names actually returned in explicitly requested projections on this route.
    "contractorCompany/search": frozenset(
        "avatar birthday canSeeFull commentsCount contactInfo contactInfoCount contentType "
        "countDeals description firstName humanNumber id isDropped isFavorite lastName middleName "
        "name payers position possibleActions preferTransport responsibles responsiblesCount "
        "status subscribed tags tagsCount textDescription timeCreated timeUpdated type "
        "unreadCommentsCount".split()
    ),
    "todo": frozenset(
        "category commentsCount description id isDropped isOverdue name relations responsible "
        "status timeCreated timeFinished userCreated when".split()
    ),
    "payer": frozenset(
        "address bank bik contractor correspondentAccount country currentAccount edrpou firstName "
        "id inn isDropped kpp lastName legalAddress mfo name ogrn okpo type unp".split()
    ),
}

REJECTED_LIST_FIELDS: dict[str, frozenset[str]] = {
    "task": frozenset(UNSUPPORTED_TASK_FIELDS)
    | {
        "actualSubTasks",
        "actualTime",
        "auditor",
        "contentType",
        "description",
        "plannedStart",
        "priority",
        "workTime",
    },
    "deal": frozenset(UNSUPPORTED_DEAL_FIELDS)
    | {
        "actualFinish",
        "contentType",
        "links",
        "paymentMode",
        "relatedTasks",
        "relations",
        "rights",
        "todo",
    },
    "employee": frozenset(
        "accessRole contentType customFields email firedAt hiredAt isAdmin isClient isDropped "
        "manager phone timeUpdated".split()
    ),
    "project": frozenset({"contentType", "description", "priority", "timeUpdated"}),
    "contractor": _CONTRACTOR_REJECTED,
    "contractorCompany": _CONTRACTOR_REJECTED
    | {"actualAddress", "inn", "kpp", "legalAddress", "legalName", "ogrn"},
    "contractorHuman": _CONTRACTOR_REJECTED | {"passport"},
    "contractorCompany/search": frozenset(),
    "todo": frozenset({"contentType"}),
    "payer": frozenset({"contentType"}),
}

_SUGGESTIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "task": {**UNSUPPORTED_TASK_FIELDS, "description": ("statement", "textStatement")},
    "deal": UNSUPPORTED_DEAL_FIELDS,
    "employee": {"isDropped": ("isWorking", "fireInProgress")},
    "project": {"description": ("statement", "textStatement")},
}


def validate_list_options(
    route: str, fields: Any = None, *, fields_strict: bool = False, limit: int | None = None
) -> None:
    """Validate a list projection and page size before a request.

    Args:
        route: List path relative to /api/v3.
        fields: Field names passed to the server.
        fields_strict: Require every requested name to be confirmed on this route.
        limit: Requested page size.

    Raises:
        ValueError: For a known invalid field, an unconfirmed strict projection,
            or a size exceeding a confirmed server cap.
    """
    if route in _CAPPED_ROUTES and limit is not None and limit > 100:
        raise ValueError(f"/{route} returns at most 100 rows per page. Use iterate(limit=100).")
    if fields is None:
        return
    if not isinstance(fields, list | tuple):
        if fields_strict:
            raise ValueError("fields_strict requires a list or tuple of API field names.")
        return
    for field in fields:
        if isinstance(field, str) and field in REJECTED_LIST_FIELDS[route]:
            message = f"/{route} rejects fields=['{field}'] in an ordinary list request (HTTP 422)."
            if field == "contentType":
                message += " contentType is included automatically; omit it from fields."
            suggestions = _SUGGESTIONS.get(route, {}).get(field)
            if suggestions:
                message += f" Use {', '.join(suggestions)}."
            raise ValueError(message)
        if fields_strict and (
            not isinstance(field, str) or field not in CONFIRMED_LIST_FIELDS[route]
        ):
            raise ValueError(f"Field {field!r} is unconfirmed for /{route} (fields_strict=True).")
