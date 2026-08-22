"""Unit tests for the entity registry (single authority for API naming)."""

from megaplan_sdk.registry import (
    content_type_for,
    filter_content_type_for,
    filter_path_for,
)


class TestContentTypeFor:
    """entity_type -> contentType resolution."""

    def test_regular_entities(self):
        assert content_type_for("task") == "Task"
        assert content_type_for("project") == "Project"
        assert content_type_for("deal") == "Deal"
        assert content_type_for("employee") == "Employee"
        assert content_type_for("department") == "Department"

    def test_todo_entity_resolves_to_todo_content_type(self):
        """/api/v3/todo is the Todo (Дела) resource, not tasks."""
        assert content_type_for("todo") == "Todo"

    def test_task_still_resolves_to_task(self):
        assert content_type_for("task") == "Task"

    def test_trade_alias_maps_to_deal(self):
        """API's legacy "trade" naming refers to deals."""
        assert content_type_for("trade") == "Deal"

    def test_camel_case_entities_keep_casing(self):
        """capitalize() would produce "Contractorcompany" — registry must not."""
        assert content_type_for("contractorCompany") == "ContractorCompany"
        assert content_type_for("contractorHuman") == "ContractorHuman"
        assert content_type_for("knowledgeBase") == "KnowledgeBase"
        assert content_type_for("knowledgeArticle") == "KnowledgeArticle"

    def test_unknown_entity_falls_back_to_capitalize(self):
        assert content_type_for("widget") == "Widget"


class TestFilterContentTypeFor:
    """entity_type -> filter contentType (for {"contentType": ..., "id": ...} links)."""

    def test_regular_filter_types(self):
        assert filter_content_type_for("task") == "TaskFilter"
        assert filter_content_type_for("project") == "ProjectFilter"
        assert filter_content_type_for("employee") == "EmployeeFilter"
        assert filter_content_type_for("contractor") == "ContractorFilter"

    def test_deal_filter_is_trade_filter(self):
        """The single irregular case: deals use TradeFilter, not DealFilter."""
        assert filter_content_type_for("deal") == "TradeFilter"
        assert filter_content_type_for("trade") == "TradeFilter"

    def test_todo_is_its_own_filter_type(self):
        """Todo (Дела) is a separate entity, not a Task alias — regular pattern applies."""
        assert filter_content_type_for("todo") == "TodoFilter"


class TestFilterPathFor:
    """entity_type -> API path segment for filter endpoints."""

    def test_regular_paths(self):
        assert filter_path_for("task") == "taskFilter"
        assert filter_path_for("project") == "projectFilter"
        assert filter_path_for("employee") == "employeeFilter"
        assert filter_path_for("contractor") == "contractorFilter"

    def test_deal_and_trade_map_to_trade_filter(self):
        assert filter_path_for("deal") == "tradeFilter"
        assert filter_path_for("trade") == "tradeFilter"

    def test_already_normalized_path_returned_as_is(self):
        assert filter_path_for("taskFilter") == "taskFilter"
        assert filter_path_for("tradeFilter") == "tradeFilter"

    def test_filter_only_types_follow_the_pattern(self):
        """Types that exist only as filters derive their path mechanically."""
        assert filter_path_for("doc") == "docFilter"
        assert filter_path_for("offer") == "offerFilter"
        assert filter_path_for("invoice") == "invoiceFilter"
        assert filter_path_for("report") == "reportFilter"

    def test_camel_case_preserved_in_derived_paths(self):
        """The legacy table lowercased input, making its own camelCase keys
        unreachable ("fileStorage" -> "filestorageFilter"). The registry must
        preserve the caller's casing."""
        assert filter_path_for("fileStorage") == "fileStorageFilter"
        assert filter_path_for("customCrm") == "customCrmFilter"
