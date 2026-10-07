"""Bind a shared method to one resource's own id keyword.

Several resources expose the same operation (journal, todos, comments) under
their own parameter name — ``task_id``, ``deal_id``, ``project_id``. Callers
and the published docs use those names as keywords, so a method lifted onto a
shared mixin cannot simply be renamed to ``entity_id``.

``with_id_param`` renames the method's ``entity_id`` parameter to the
resource's alias by rebuilding its code object. Argument binding stays native:
a foreign keyword and a missing id raise the ordinary ``TypeError`` a
dedicated method would, instead of a hand-built one, and a method never
accepts every resource's keyword at once.
"""

from __future__ import annotations

import types
from typing import Any


def with_id_param(method: Any, alias: str) -> Any:
    """Return ``method`` with its ``entity_id`` parameter renamed to ``alias``.

    Args:
        method: A function whose signature contains an ``entity_id`` parameter.
        alias: The resource's own keyword (e.g. ``"task_id"``).

    Returns:
        A function with identical behaviour and ``entity_id`` renamed.
    """
    code = method.__code__
    index = code.co_varnames.index("entity_id")
    renamed = types.FunctionType(
        code.replace(
            co_varnames=(*code.co_varnames[:index], alias, *code.co_varnames[index + 1 :])
        ),
        method.__globals__,
        method.__name__,
        method.__defaults__,
        method.__closure__,
    )
    renamed.__annotations__ = {
        alias if name == "entity_id" else name: annotation
        for name, annotation in method.__annotations__.items()
    }
    renamed.__doc__ = method.__doc__
    renamed.__qualname__ = method.__qualname__
    renamed.__module__ = method.__module__
    return renamed


class IdParamMeta(type):
    """Rename ``entity_id`` to ``_history_id_param`` on the mixin's own methods.

    A resource opts in by declaring ``_history_id_param`` (a string) in its own
    body. Classes that do not — the mixin itself, and resources like
    contractors whose methods stay hand-written — are left untouched.

    ``_own_id_param_methods`` lists the methods this mixin itself defines with an
    ``entity_id`` parameter. ``_id_param_methods`` is the union across every
    such mixin in the MRO: a class inherits both, so neither mixin's list may
    overwrite the other's. A resource that overrides one of them with its own
    signature (``TodosResource.get_comments`` takes only ``todo_id``) is left
    exactly as written: renaming needs an ``entity_id`` parameter the override
    does not have.
    """

    _own_id_param_methods: tuple[str, ...] = ()
    _id_param_methods: tuple[str, ...] = ()

    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> None:
        super().__init__(name, bases, namespace)
        cls._id_param_methods = tuple(
            dict.fromkeys(
                method_name
                for base in reversed(cls.__mro__)
                for method_name in base.__dict__.get("_own_id_param_methods", ())
            )
        )
        alias = namespace.get("_history_id_param")
        if not isinstance(alias, str):
            return
        for method_name in cls._id_param_methods:
            method = getattr(cls, method_name, None)
            owner = _method_owner(cls, method_name)
            # Only a method a mixin introduced. A resource that overrides it
            # (TodosResource.get_comments takes only todo_id) is its own owner
            # and is left exactly as written.
            if owner is None or owner is cls:
                continue
            setattr(cls, method_name, with_id_param(method, alias))


def _method_owner(cls: type, method_name: str) -> type | None:
    """The mixin that introduces ``method_name``, if it is one of these mixins.

    The most specific class wins, so a resource that overrides the method is
    found first and rejected: renaming applies only to a method a mixin
    introduced, never to one the resource wrote itself.
    """
    for base in cls.__mro__:
        if method_name not in base.__dict__:
            continue
        # From the class body, not the MRO: a resource inherits the mixin's
        # list, and reading it here would make the resource look like the mixin
        # that introduced the method.
        if method_name in base.__dict__.get("_own_id_param_methods", ()):
            return base
        return None
    return None
