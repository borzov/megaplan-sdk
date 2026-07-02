# Megaplan SDK

Async Python SDK for Megaplan CRM API v3. Resources wrap API endpoints; models
mirror API entities; the SDK's job is to hide Megaplan API quirks behind a
typed interface.

## Language

**Resource**:
A module wrapping one API entity's endpoints (tasks, deals, projects, …). All
resources inherit from BaseResource.
_Avoid_: service, client (reserved for MegaplanClient), repository

**Expand**:
The `expand=` parameter of `list()`: batch-loading of related entities
referenced by the listed entities, cache-first, in one pass.
_Avoid_: prefetch, join, include (reserved for `include_*` in full details)

**ExpandRule**:
A declarative rule on a resource class describing how one expandable field is
loaded: source field name → (entity type, model, target). The set of rules is
the resource's whole contribution to the expand pipeline.
_Avoid_: expand_config (the legacy inline tuple dict)

**Wrap mode**:
Expand result shape where each listed entity is wrapped into a FullDetails
container holding the loaded relatives (tasks, deals, projects).
_Avoid_: container mode

**Replace mode**:
Expand result shape where reference fields are replaced with fully loaded
entities on immutable copies of the listed entities; the return type stays the
plain entity list (employees).
_Avoid_: in-place mode, mutation (implementation must stay immutable)

**EntityRegistry**:
The single authority for API naming (`registry.py`): one entry per entity type
holds its contentType, filter contentType, and legacy aliases ("todo" for
tasks, "trade" for deals). Resources consult it instead of keeping string
tables.
_Avoid_: mapping table, normalize function

**FullDetails container**:
A model (TaskFullDetails, DealFullDetails, ProjectFullDetails) wrapping the
main entity plus loaded relatives; proxies unknown attributes to the main
entity via MainEntityProxyMixin.
_Avoid_: DTO, view model
