"""Filter builder for creating filter objects with all FilterTerm types.

Provides a fluent builder API for constructing filter objects that can be used
with list() methods for text search and filtering.
"""

from __future__ import annotations

from typing import Any


class FilterBuilder:
    """Builder for creating filter objects with all FilterTerm types.

    Provides a fluent API for building filter configurations that can be used
    with resource list() methods (e.g., client.deals.list(), client.tasks.list()).

    Supports all FilterTerm types: String, Number, Date, Bool, Enum, Ref.

    Example:
        >>> # Simple text search
        >>> filter_obj = FilterBuilder("TradeFilter").field("name").contains("Leader").build()
        >>> deals = await client.deals.list(filter=filter_obj)
        >>>
        >>> # Multiple conditions with different types
        >>> filter_obj = (
        ...     FilterBuilder("TaskFilter")
        ...     .field("name").contains("договор")
        ...     .and_()
        ...     .field_number("amount").greater_than(1000)
        ...     .and_()
        ...     .field_date("created_at").greater_than("2025-01-01")
        ...     .build()
        ... )
        >>> tasks = await client.tasks.list(filter=filter_obj)
        >>>
        >>> # Nested groups
        >>> filter_obj = (
        ...     FilterBuilder("TaskFilter")
        ...     .field("name").contains("договор")
        ...     .and_()
        ...     .group()
        ...         .field("status").equals("active")
        ...         .or_()
        ...         .field("priority").equals("high")
        ...     .end_group()
        ...     .build()
        ... )
    """

    def __init__(self, content_type: str) -> None:
        """Initialize filter builder.

        Args:
            content_type: Filter content type (e.g., "TaskFilter", "TradeFilter", "ProjectFilter").
        """
        self._content_type = content_type
        self._groups_stack: list[dict[str, Any]] = []
        self._current_group: dict[str, Any] = {"terms": [], "join": "and"}
        self._current_field: str | None = None
        self._current_field_type: str | None = None

    # Field type selectors
    def field(self, field_name: str) -> FilterBuilder:
        """Set string field name for the next condition.

        Args:
            field_name: Name of the field to filter by (e.g., "name", "status").

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "string"
        return self

    def field_number(self, field_name: str) -> FilterBuilder:
        """Set numeric field name for the next condition.

        Args:
            field_name: Name of the numeric field to filter by.

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "number"
        return self

    def field_date(self, field_name: str) -> FilterBuilder:
        """Set date field name for the next condition.

        Args:
            field_name: Name of the date field to filter by.

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "date"
        return self

    def field_bool(self, field_name: str) -> FilterBuilder:
        """Set boolean field name for the next condition.

        Args:
            field_name: Name of the boolean field to filter by.

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "bool"
        return self

    def field_enum(self, field_name: str) -> FilterBuilder:
        """Set enum field name for the next condition.

        Args:
            field_name: Name of the enum field to filter by.

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "enum"
        return self

    def field_ref(self, field_name: str) -> FilterBuilder:
        """Set reference field name for the next condition.

        Args:
            field_name: Name of the reference field to filter by.

        Returns:
            Self for method chaining.
        """
        self._current_field = field_name
        self._current_field_type = "ref"
        return self

    # String operators
    def contains(self, value: str) -> FilterBuilder:
        """Add condition: field contains value (string only).

        Args:
            value: Value to search for.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before or wrong field type.
        """
        return self._add_term("contains", value, "string")

    def starts_with(self, value: str) -> FilterBuilder:
        """Add condition: field starts with value (string only).

        Args:
            value: Value to match at the start.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before or wrong field type.
        """
        return self._add_term("starts_with", value, "string")

    def equals(self, value: Any) -> FilterBuilder:
        """Add condition: field equals value.

        Works with all field types. Type is determined by field type selector.

        Args:
            value: Value to match (str, int, float, bool, dict, list).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before.
        """
        if self._current_field_type is None:
            raise ValueError("field() or field_*() must be called before adding a condition")
        return self._add_term("equals", value, self._term_type_for_value(value))

    def not_contains(self, value: str) -> FilterBuilder:
        """Add condition: field does not contain value (string only).

        Args:
            value: Value that should not be present.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before or wrong field type.
        """
        return self._add_term("not_contains", value, "string")

    def not_equals(self, value: Any) -> FilterBuilder:
        """Add condition: field does not equal value.

        Works with all field types except string (use not_contains for strings).

        Args:
            value: Value that should not match.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before.
        """
        if self._current_field_type is None:
            raise ValueError("field() or field_*() must be called before adding a condition")
        return self._add_term("not_equals", value, self._term_type_for_value(value))

    # Number operators
    def greater_than(self, value: int | float | str) -> FilterBuilder:
        """Add condition: field > value (number or date).

        Args:
            value: Value to compare against (int/float for number, str for date).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_number() or field_date() was not called before.
        """
        if self._current_field_type not in ("number", "date"):
            raise ValueError("greater_than() requires field_number() or field_date()")
        comparison = "more"
        return self._add_term(comparison, value, self._current_field_type)

    def less_than(self, value: int | float | str) -> FilterBuilder:
        """Add condition: field < value (number or date).

        Args:
            value: Value to compare against (int/float for number, str for date).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_number() or field_date() was not called before.
        """
        if self._current_field_type not in ("number", "date"):
            raise ValueError("less_than() requires field_number() or field_date()")
        comparison = "less"
        return self._add_term(comparison, value, self._current_field_type)

    def greater_than_or_equal(self, value: int | float) -> FilterBuilder:
        """Add condition: field >= value (number only).

        Args:
            value: Value to compare against.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_number() was not called before.
        """
        if self._current_field_type != "number":
            raise ValueError("greater_than_or_equal() requires field_number()")
        return self._add_term("more_eq", value, "number")

    def less_than_or_equal(self, value: int | float) -> FilterBuilder:
        """Add condition: field <= value (number only).

        Args:
            value: Value to compare against.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_number() was not called before.
        """
        if self._current_field_type != "number":
            raise ValueError("less_than_or_equal() requires field_number()")
        return self._add_term("less_eq", value, "number")

    def between(self, min_value: int | float | str, max_value: int | float | str) -> FilterBuilder:
        """Add condition: min_value <= field <= max_value (number or date).

        Args:
            min_value: Minimum value (inclusive).
            max_value: Maximum value (inclusive).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_number() or field_date() was not called before.
        """
        if self._current_field_type not in ("number", "date"):
            raise ValueError("between() requires field_number() or field_date()")
        if self._current_field_type == "number":
            value = {"min": min_value, "max": max_value}
        else:
            value = {"min": min_value, "max": max_value}
        return self._add_term("interval", value, self._current_field_type)

    # Enum/List operators
    def in_list(self, values: list[Any]) -> FilterBuilder:
        """Add condition: field in values (enum or ref).

        Args:
            values: List of values to match.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_enum() or field_ref() was not called before.
        """
        if self._current_field_type not in ("enum", "ref"):
            raise ValueError("in_list() requires field_enum() or field_ref()")
        return self._add_term("equals", values, self._current_field_type)

    def not_in_list(self, values: list[Any]) -> FilterBuilder:
        """Add condition: field not in values (enum or ref).

        Args:
            values: List of values that should not match.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field_enum() or field_ref() was not called before.
        """
        if self._current_field_type not in ("enum", "ref"):
            raise ValueError("not_in_list() requires field_enum() or field_ref()")
        return self._add_term("not_equals", values, self._current_field_type)

    # Join operators
    def and_(self) -> FilterBuilder:
        """Set join operator to AND for next condition.

        Returns:
            Self for method chaining.
        """
        self._current_group["join"] = "and"
        return self

    def or_(self) -> FilterBuilder:
        """Set join operator to OR for next condition.

        Returns:
            Self for method chaining.
        """
        self._current_group["join"] = "or"
        return self

    # Nested groups
    def group(self) -> FilterBuilder:
        """Start a nested group of conditions.

        Returns:
            Self for method chaining.

        Example:
            >>> builder = FilterBuilder("TaskFilter")
            >>> builder.field("name").contains("test")
            >>> builder.and_().group()
            >>> builder.field("status").equals("active")
            >>> builder.or_().field("priority").equals("high")
            >>> builder.end_group()
        """
        self._groups_stack.append(self._current_group)
        self._current_group = {"terms": [], "join": "and"}
        return self

    def end_group(self) -> FilterBuilder:
        """End current nested group and merge with parent.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If end_group() called without matching group().

        Example:
            >>> builder = FilterBuilder("TaskFilter")
            >>> builder.field("name").contains("test")
            >>> builder.and_().group()
            >>> builder.field("status").equals("active")
            >>> builder.end_group()
        """
        if not self._groups_stack:
            raise ValueError("end_group() called without matching group()")

        nested_group = {
            "contentType": "FilterTermGroup",
            "join": self._current_group["join"],
            "terms": self._current_group["terms"],
        }

        self._current_group = self._groups_stack.pop()
        self._current_group["terms"].append(nested_group)
        return self

    # Shortcut methods
    def field_eq(self, field: str, value: Any) -> FilterBuilder:
        """Shortcut: field equals value (auto-detect type).

        Args:
            field: Field name.
            value: Value to match.

        Returns:
            Self for method chaining.
        """
        if isinstance(value, bool):
            return self.field_bool(field).equals(value)
        elif isinstance(value, int | float):
            return self.field_number(field).equals(value)
        elif isinstance(value, str):
            return self.field(field).equals(value)
        else:
            return self.field(field).equals(str(value))

    def field_contains(self, field: str, value: str) -> FilterBuilder:
        """Shortcut: field contains value (string only).

        Args:
            field: Field name.
            value: Value to search for.

        Returns:
            Self for method chaining.
        """
        return self.field(field).contains(value)

    def field_gt(self, field: str, value: int | float) -> FilterBuilder:
        """Shortcut: field > value (number or date).

        Args:
            field: Field name.
            value: Value to compare against.

        Returns:
            Self for method chaining.
        """
        return self.field_number(field).greater_than(value)

    def field_lt(self, field: str, value: int | float) -> FilterBuilder:
        """Shortcut: field < value (number or date).

        Args:
            field: Field name.
            value: Value to compare against.

        Returns:
            Self for method chaining.
        """
        return self.field_number(field).less_than(value)

    def field_in(self, field: str, values: list[Any]) -> FilterBuilder:
        """Shortcut: field in values (enum or ref).

        Args:
            field: Field name.
            values: List of values to match.

        Returns:
            Self for method chaining.
        """
        return self.field_enum(field).in_list(values)

    def where(self, field: str, operator: str | Any, value: Any | None = None) -> FilterBuilder:
        """Universal method for adding conditions.

        Args:
            field: Field name.
            operator: Operator name or value (if value is None, operator is treated as value for equals).
            value: Value (optional, if None, operator is used as value for equals).

        Returns:
            Self for method chaining.

        Example:
            >>> builder.where("status", "active")  # equals
            >>> builder.where("status", "in", ["active", "pending"])
            >>> builder.where("amount", "between", (100, 500))
        """
        if value is None:
            return self.field_eq(field, operator)

        operator_str = str(operator).lower()
        if operator_str == "in":
            return self.field_in(field, value if isinstance(value, list) else [value])
        elif operator_str == "between":
            if isinstance(value, tuple | list) and len(value) == 2:
                return self.field_number(field).between(value[0], value[1])
            else:
                raise ValueError("between() requires tuple/list with 2 values")
        elif operator_str in ("gt", "greater_than", ">"):
            return self.field_gt(field, value)
        elif operator_str in ("lt", "less_than", "<"):
            return self.field_lt(field, value)
        elif operator_str == "contains":
            return self.field_contains(field, value)
        elif operator_str == "equals" or operator_str == "eq":
            return self.field_eq(field, value)
        else:
            return self.field_eq(field, value)

    def build(self) -> dict[str, Any]:
        """Build final filter object.

        Returns:
            Dictionary ready to be passed as filter parameter to list() methods.

        Raises:
            ValueError: If no conditions were added or unmatched group().
        """
        if self._groups_stack:
            raise ValueError("Unmatched group() calls. All groups must be closed with end_group()")

        if not self._current_group["terms"]:
            raise ValueError("At least one condition must be added before building")

        return {
            "contentType": self._content_type,
            "config": {
                "contentType": "FilterConfig",
                "termGroup": {
                    "contentType": "FilterTermGroup",
                    "join": self._current_group["join"],
                    "terms": self._current_group["terms"],
                },
            },
        }

    def _term_type_for_value(self, value: Any) -> str:
        """Resolve the term type for an equals/not_equals value (#29).

        ``field()`` defaults the term type to ``"string"``. A bool/number value
        on such a generic field must build ``FilterTermBool``/``FilterTermNumber``
        — a ``FilterTermString`` carrying a bool/number is rejected by the
        server ("'stdClass' is not assignable to '<Filter>'"). This mirrors
        :meth:`field_eq` so ``field('x').equals(True)`` == ``field_eq('x', True)``.
        Explicit ``field_bool``/``field_number``/... selectors are respected.
        """
        term_type = self._current_field_type or "string"
        if term_type == "string" and not isinstance(value, str):
            if isinstance(value, bool):
                return "bool"
            if isinstance(value, int | float):
                return "number"
        return term_type

    def _add_term(self, comparison: str, value: Any, term_type: str) -> FilterBuilder:
        """Add a FilterTerm to the current group.

        Args:
            comparison: Comparison operator.
            value: Value to compare against.
            term_type: Type of term ("string", "number", "date", "bool", "enum", "ref").

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If field() was not called before.
        """
        if self._current_field is None:
            raise ValueError("field() or field_*() must be called before adding a condition")

        term_content_type_map = {
            "string": "FilterTermString",
            "number": "FilterTermNumber",
            "date": "FilterTermDate",
            "bool": "FilterTermBool",
            "enum": "FilterTermEnum",
            "ref": "FilterTermRef",
        }

        term: dict[str, Any] = {
            "contentType": term_content_type_map[term_type],
            "field": self._current_field,
        }

        if term_type == "bool":
            term["value"] = bool(value)
            term["comparison"] = "equals"
        elif term_type == "enum":
            term["comparison"] = comparison
            if isinstance(value, list):
                term["value"] = value
            else:
                term["value"] = [value]
        elif term_type == "ref":
            term["comparison"] = comparison
            if isinstance(value, list):
                term["value"] = value
            else:
                term["value"] = [value]
        else:
            term["comparison"] = comparison
            term["value"] = value

        self._current_group["terms"].append(term)
        self._current_field = None
        self._current_field_type = None

        return self


# Specialized builder classes
class TaskFilterBuilder(FilterBuilder):
    """Builder for TaskFilter with pre-configured content type."""

    def __init__(self) -> None:
        """Initialize TaskFilter builder."""
        super().__init__("TaskFilter")


class TradeFilterBuilder(FilterBuilder):
    """Builder for TradeFilter with pre-configured content type."""

    def __init__(self) -> None:
        """Initialize TradeFilter builder."""
        super().__init__("TradeFilter")


class ProjectFilterBuilder(FilterBuilder):
    """Builder for ProjectFilter with pre-configured content type."""

    def __init__(self) -> None:
        """Initialize ProjectFilter builder."""
        super().__init__("ProjectFilter")
