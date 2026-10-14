"""Contact and address models for contractor profiles."""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity


class AliasItemAccess:
    """Read a model by API alias or field name.

    Profile values used to be plain dicts. ``get`` and ``__getitem__`` keep
    those lookups working. This is not a ``dict``: there is no ``keys`` or
    ``items``.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Return the field for ``key``, or ``default`` when it is absent."""
        try:
            return self[key]
        except KeyError:
            return default

    def __getattr__(self, key: str) -> Any:
        """Preserve former extra-field alias attributes as dictionary values."""
        model = cast(BaseModel, self)
        name = _field_name(type(model), key)
        if name is not None and name != key:
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key) from None
        return cast(Any, super()).__getattr__(key)

    def __getitem__(self, key: str) -> Any:
        """Return a field by its name, alias, or preserved extra key."""
        if not isinstance(key, str):
            raise KeyError(key)
        model = cast(BaseModel, self)
        field_name = _field_name(type(model), key)
        if field_name is not None:
            if field_name not in model.model_fields_set:
                raise KeyError(key)
            alias = type(model).model_fields[field_name].alias or field_name
            return model.model_dump(by_alias=True, exclude_unset=True)[alias]
        extra = getattr(self, "model_extra", None) or {}
        if key in extra:
            return extra[key]
        raise KeyError(key)


def _field_name(model: type[BaseModel], key: str) -> str | None:
    if key in model.model_fields:
        return key
    for name, field in model.model_fields.items():
        if field.alias == key:
            return name
    return None


def parse_contact_item(item: Any) -> Any:
    """Parse one ``contactInfo`` entry as ``Address`` or ``ContactInfo``."""
    if not isinstance(item, dict):
        return item
    if item.get("contentType") == "Address":
        return Address.model_validate(item)
    return ContactInfo.model_validate(item)


class AddressType(BaseModel):
    """Address type reference.

    ``id`` is a string. It does not use the numeric ``BaseEntity`` identifier.

    Attributes:
        content_type: Always "AddressType".
        id: Address type identifier.
        name: Address type name.
    """

    content_type: str = Field(alias="contentType", default="AddressType")
    id: str
    name: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ContactInfo(AliasItemAccess, BaseModel):
    """One contact value: phone, email, link, or messenger.

    Attributes:
        content_type: Always "ContactInfo".
        type: Contact kind (email, phone, link, and the other RAML kinds).
        value: Contact value. Reading allows it to be missing.
        comment: Optional comment.
        is_main: Whether this is the main value of its kind.
        subject: Owner reference, kept as ``BaseEntity`` to avoid a profile cycle.
    """

    content_type: str = Field(alias="contentType", default="ContactInfo")
    type: str | None = None
    value: str | None = None
    comment: str | None = None
    is_main: bool | None = Field(alias="isMain", default=None)
    subject: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Address(AliasItemAccess, BaseModel):
    """Postal address in either shape returned by the API.

    A contractor card nests ``AddressType`` in ``type``. An employee contact
    omits ``type`` and sends ``city``, ``street``, ``house``, and ``metro``.

    Attributes:
        content_type: Always "Address".
        type: Address type, when the response includes one.
        value: Free-form address text.
        is_main: Whether this is the main address.
        city: City reference.
        street: Street.
        house: House number.
        metro: Metro reference.
    """

    content_type: str = Field(alias="contentType", default="Address")
    type: AddressType | None = None
    value: str | None = None
    is_main: bool | None = Field(alias="isMain", default=None)
    city: BaseEntity | None = None
    street: str | None = None
    house: str | None = None
    metro: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
