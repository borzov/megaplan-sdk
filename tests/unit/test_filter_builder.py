"""Unit tests for FilterBuilder."""

import pytest

from megaplan_sdk.filter_builder import (
    FilterBuilder,
    ProjectFilterBuilder,
    TaskFilterBuilder,
    TradeFilterBuilder,
)


class TestFilterBuilderString:
    """Tests for FilterTermString operations."""

    def test_simple_contains(self):
        """Test simple contains condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field("name").contains("test").build()

        assert result["contentType"] == "TaskFilter"
        assert len(result["config"]["termGroup"]["terms"]) == 1
        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermString"
        assert term["field"] == "name"
        assert term["comparison"] == "contains"
        assert term["value"] == "test"

    def test_multiple_conditions_and(self):
        """Test multiple conditions with AND."""
        builder = FilterBuilder("TaskFilter")
        result = (
            builder.field("name").contains("test").and_().field("status").equals("active").build()
        )

        assert len(result["config"]["termGroup"]["terms"]) == 2
        assert result["config"]["termGroup"]["join"] == "and"

    def test_multiple_conditions_or(self):
        """Test multiple conditions with OR."""
        builder = FilterBuilder("TaskFilter")
        result = (
            builder.field("name").contains("test").or_().field("status").equals("active").build()
        )

        assert len(result["config"]["termGroup"]["terms"]) == 2
        assert result["config"]["termGroup"]["join"] == "or"

    def test_starts_with(self):
        """Test starts_with condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field("name").starts_with("prefix").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "starts_with"
        assert term["value"] == "prefix"

    def test_not_contains(self):
        """Test not_contains condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field("name").not_contains("exclude").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "not_contains"

    def test_not_equals(self):
        """Test not_equals condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field("status").not_equals("inactive").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "not_equals"


class TestFilterBuilderNumber:
    """Tests for FilterTermNumber operations."""

    def test_number_equals(self):
        """Test number equals condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").equals(1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermNumber"
        assert term["field"] == "amount"
        assert term["comparison"] == "equals"
        assert term["value"] == 1000

    def test_number_greater_than(self):
        """Test number greater_than condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").greater_than(1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "more"

    def test_number_less_than(self):
        """Test number less_than condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").less_than(5000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "less"

    def test_number_between(self):
        """Test number between condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").between(1000, 5000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "interval"
        assert term["value"] == {"min": 1000, "max": 5000}

    def test_number_greater_than_or_equal(self):
        """Test number greater_than_or_equal condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").greater_than_or_equal(1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "more_eq"

    def test_number_less_than_or_equal(self):
        """Test number less_than_or_equal condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_number("amount").less_than_or_equal(5000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "less_eq"


class TestFilterBuilderBool:
    """Tests for FilterTermBool operations."""

    def test_bool_equals_true(self):
        """Test boolean equals true condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_bool("is_completed").equals(True).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermBool"
        assert term["field"] == "is_completed"
        assert term["comparison"] == "equals"
        assert term["value"] is True

    def test_bool_equals_false(self):
        """Test boolean equals false condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_bool("is_urgent").equals(False).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["value"] is False


class TestFilterBuilderDate:
    """Tests for FilterTermDate operations."""

    def test_date_equals(self):
        """Test date equals condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_date("created_at").equals("2025-01-01").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermDate"
        assert term["field"] == "created_at"
        assert term["comparison"] == "equals"
        assert term["value"] == "2025-01-01"

    def test_date_greater_than(self):
        """Test date greater_than condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_date("created_at").greater_than("2025-01-01").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "more"

    def test_date_less_than(self):
        """Test date less_than condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_date("created_at").less_than("2025-12-31").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "less"

    def test_date_between(self):
        """Test date between condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_date("created_at").between("2025-01-01", "2025-12-31").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "interval"
        assert term["value"] == {"min": "2025-01-01", "max": "2025-12-31"}


class TestFilterBuilderEnum:
    """Tests for FilterTermEnum operations."""

    def test_enum_in_list(self):
        """Test enum in_list condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_enum("status").in_list(["active", "pending"]).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermEnum"
        assert term["field"] == "status"
        assert term["comparison"] == "equals"
        assert term["value"] == ["active", "pending"]

    def test_enum_equals_single(self):
        """Test enum equals with single value."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_enum("status").equals("active").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["value"] == ["active"]

    def test_enum_not_equals(self):
        """Test enum not_equals condition."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_enum("status").not_equals("inactive").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "not_equals"
        assert term["value"] == ["inactive"]


class TestFilterBuilderRef:
    """Tests for FilterTermRef operations."""

    def test_ref_equals(self):
        """Test ref equals condition."""
        builder = FilterBuilder("TaskFilter")
        entity = {"contentType": "Employee", "id": 123}
        result = builder.field_ref("responsible").equals(entity).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermRef"
        assert term["field"] == "responsible"
        assert term["comparison"] == "equals"
        assert term["value"] == [entity]

    def test_ref_in_list(self):
        """Test ref in_list condition."""
        builder = FilterBuilder("TaskFilter")
        entities = [
            {"contentType": "Employee", "id": 123},
            {"contentType": "Employee", "id": 456},
        ]
        result = builder.field_ref("responsible").in_list(entities).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["value"] == entities


class TestFilterBuilderNestedGroups:
    """Tests for nested groups."""

    def test_simple_nested_group(self):
        """Test simple nested group."""
        builder = FilterBuilder("TaskFilter")
        result = (
            builder.field("name")
            .contains("test")
            .and_()
            .group()
            .field("status")
            .equals("active")
            .or_()
            .field("priority")
            .equals("high")
            .end_group()
            .build()
        )

        terms = result["config"]["termGroup"]["terms"]
        assert len(terms) == 2
        assert terms[0]["contentType"] == "FilterTermString"
        assert terms[1]["contentType"] == "FilterTermGroup"
        assert terms[1]["join"] == "or"
        assert len(terms[1]["terms"]) == 2

    def test_nested_group_error_unmatched(self):
        """Test error for unmatched end_group."""
        builder = FilterBuilder("TaskFilter")
        builder.field("name").contains("test")

        with pytest.raises(ValueError, match="end_group.*without matching group"):
            builder.end_group()

    def test_nested_group_error_unclosed(self):
        """Test error for unclosed group."""
        builder = FilterBuilder("TaskFilter")
        builder.field("name").contains("test").and_().group()

        with pytest.raises(ValueError, match="Unmatched group"):
            builder.build()


class TestFilterBuilderShortcuts:
    """Tests for shortcut methods."""

    def test_field_eq_string(self):
        """Test field_eq with string."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_eq("status", "active").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermString"
        assert term["value"] == "active"

    def test_field_eq_number(self):
        """Test field_eq with number."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_eq("amount", 1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermNumber"
        assert term["value"] == 1000

    def test_field_eq_bool(self):
        """Test field_eq with boolean."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_eq("is_completed", True).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermBool"
        assert term["value"] is True

    def test_field_contains(self):
        """Test field_contains shortcut."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_contains("name", "test").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "contains"

    def test_field_gt(self):
        """Test field_gt shortcut."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_gt("amount", 1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermNumber"
        assert term["comparison"] == "more"

    def test_field_lt(self):
        """Test field_lt shortcut."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_lt("amount", 5000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "less"

    def test_field_in(self):
        """Test field_in shortcut."""
        builder = FilterBuilder("TaskFilter")
        result = builder.field_in("status", ["active", "pending"]).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermEnum"
        assert term["value"] == ["active", "pending"]

    def test_where_equals(self):
        """Test where method with equals."""
        builder = FilterBuilder("TaskFilter")
        result = builder.where("status", "active").build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "equals"

    def test_where_in(self):
        """Test where method with in operator."""
        builder = FilterBuilder("TaskFilter")
        result = builder.where("status", "in", ["active", "pending"]).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["contentType"] == "FilterTermEnum"
        assert term["value"] == ["active", "pending"]

    def test_where_between(self):
        """Test where method with between operator."""
        builder = FilterBuilder("TaskFilter")
        result = builder.where("amount", "between", (100, 500)).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "interval"
        assert term["value"] == {"min": 100, "max": 500}

    def test_where_gt(self):
        """Test where method with greater_than operator."""
        builder = FilterBuilder("TaskFilter")
        result = builder.where("amount", "gt", 1000).build()

        term = result["config"]["termGroup"]["terms"][0]
        assert term["comparison"] == "more"


class TestSpecializedBuilders:
    """Tests for specialized builder classes."""

    def test_task_filter_builder(self):
        """Test TaskFilterBuilder."""
        builder = TaskFilterBuilder()
        result = builder.field("name").contains("test").build()

        assert result["contentType"] == "TaskFilter"

    def test_trade_filter_builder(self):
        """Test TradeFilterBuilder."""
        builder = TradeFilterBuilder()
        result = builder.field("name").contains("test").build()

        assert result["contentType"] == "TradeFilter"

    def test_project_filter_builder(self):
        """Test ProjectFilterBuilder."""
        builder = ProjectFilterBuilder()
        result = builder.field("name").contains("test").build()

        assert result["contentType"] == "ProjectFilter"


class TestFilterBuilderErrors:
    """Tests for error handling."""

    def test_no_field_before_condition(self):
        """Test error when condition added without field."""
        builder = FilterBuilder("TaskFilter")

        with pytest.raises(ValueError, match="field.*must be called"):
            builder.contains("test")

    def test_no_conditions_before_build(self):
        """Test error when build called without conditions."""
        builder = FilterBuilder("TaskFilter")

        with pytest.raises(ValueError, match="At least one condition"):
            builder.build()

    def test_wrong_field_type_for_operator(self):
        """Test error when wrong field type used with operator."""
        builder = FilterBuilder("TaskFilter")

        with pytest.raises(ValueError, match="greater_than.*requires"):
            builder.field("name").greater_than(1000)

    def test_wrong_field_type_for_in_list(self):
        """Test error when in_list used with wrong field type."""
        builder = FilterBuilder("TaskFilter")

        with pytest.raises(ValueError, match="in_list.*requires"):
            builder.field("name").in_list(["test"])
