"""Validation utilities for integration tests."""

from datetime import datetime
from typing import Any

from utils import print_error, print_warning


def validate_search_results(
    results: list[Any],
    search_term: str,
    field_name: str = "name",
    case_sensitive: bool = False,
) -> tuple[bool, list[str]]:
    """Validate that all search results contain the search term.

    Args:
        results: List of results to validate.
        search_term: Term to search for.
        field_name: Name of the field to check (default: "name").
        case_sensitive: Whether search should be case-sensitive (default: False).

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    if not results:
        return True, []

    errors: list[str] = []
    search_lower = search_term.lower() if not case_sensitive else search_term

    for i, result in enumerate(results):
        # Get field value
        field_value = getattr(result, field_name, None)
        if field_value is None:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"does not have field '{field_name}'"
            )
            continue

        # Convert to string and check
        field_str = str(field_value)
        if not case_sensitive:
            field_str = field_str.lower()

        if search_lower not in field_str:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}, "
                f"{field_name}: '{field_value}') does not contain search term '{search_term}'"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_date_range(
    results: list[Any],
    date_field: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[bool, list[str]]:
    """Validate that all results have dates within the specified range.

    Args:
        results: List of results to validate.
        date_field: Name of the date field to check.
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    if not results:
        return True, []

    errors: list[str] = []

    for i, result in enumerate(results):
        # Get date value
        date_value = getattr(result, date_field, None)
        if date_value is None:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"does not have field '{date_field}'"
            )
            continue

        # Convert to datetime if it's a string
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                errors.append(
                    f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                    f"has invalid date format in '{date_field}': '{date_value}'"
                )
                continue

        if not isinstance(date_value, datetime):
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"has non-datetime value in '{date_field}': {type(date_value)}"
            )
            continue

        # Check range
        if start_date and date_value < start_date:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"has date {date_value} before start_date {start_date}"
            )

        if end_date and date_value > end_date:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"has date {date_value} after end_date {end_date}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_status_filter(
    results: list[Any],
    expected_statuses: list[str],
    status_field: str = "status",
) -> tuple[bool, list[str]]:
    """Validate that all results have one of the expected statuses.

    Args:
        results: List of results to validate.
        expected_statuses: List of expected status values.
        status_field: Name of the status field to check (default: "status").

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    if not results:
        return True, []

    errors: list[str] = []
    expected_set = set(expected_statuses)

    for i, result in enumerate(results):
        status_value = getattr(result, status_field, None)
        if status_value is None:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"does not have field '{status_field}'"
            )
            continue

        status_str = str(status_value)
        if status_str not in expected_set:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}, "
                f"status: '{status_str}') is not in expected statuses {expected_statuses}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_base_entity_filter(
    results: list[Any],
    expected_entity: dict[str, Any],
    entity_field: str,
) -> tuple[bool, list[str]]:
    """Validate that all results are related to the expected base entity.

    Args:
        results: List of results to validate.
        expected_entity: Expected base entity (dict with contentType and id).
        entity_field: Name of the field containing the related entity.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    if not results:
        return True, []

    errors: list[str] = []
    expected_content_type = expected_entity.get("contentType")
    expected_id = expected_entity.get("id")

    for i, result in enumerate(results):
        entity_value = getattr(result, entity_field, None)
        if entity_value is None:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"does not have field '{entity_field}'"
            )
            continue

        # Handle BaseEntity object
        if hasattr(entity_value, "content_type"):
            actual_content_type = entity_value.content_type
            actual_id = entity_value.id
        elif hasattr(entity_value, "contentType"):
            actual_content_type = entity_value.contentType
            actual_id = entity_value.id
        elif isinstance(entity_value, dict):
            actual_content_type = entity_value.get("contentType") or entity_value.get("content_type")
            actual_id = entity_value.get("id")
        else:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"has invalid format for '{entity_field}': {type(entity_value)}"
            )
            continue

        if actual_content_type != expected_content_type or actual_id != expected_id:
            errors.append(
                f"Result {i} (ID: {getattr(result, 'id', 'unknown')}) "
                f"has {entity_field} with contentType='{actual_content_type}', id={actual_id}, "
                f"expected contentType='{expected_content_type}', id={expected_id}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def log_api_error(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
    error: Exception | None = None,
    response_status: int | None = None,
    response_body: str | dict[str, Any] | None = None,
) -> None:
    """Log API error with full details.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Full URL of the request.
        params: Query parameters.
        json_data: JSON body of the request.
        error: Exception that occurred.
        response_status: HTTP status code of the response.
        response_body: Response body.
    """
    print_error("\n" + "=" * 70)
    print_error("API ERROR DETECTED - DETAILED INFORMATION")
    print_error("=" * 70)

    print_error(f"\nHTTP Method: {method}")
    print_error(f"URL: {url}")

    if params:
        print_error(f"\nQuery Parameters:")
        import json

        print_error(json.dumps(params, indent=2, ensure_ascii=False))

    if json_data:
        print_error(f"\nRequest Body:")
        import json

        print_error(json.dumps(json_data, indent=2, ensure_ascii=False))

    if response_status:
        print_error(f"\nResponse Status: {response_status}")

    if response_body:
        print_error(f"\nResponse Body:")
        if isinstance(response_body, dict):
            import json

            print_error(json.dumps(response_body, indent=2, ensure_ascii=False))
        else:
            print_error(str(response_body))

    if error:
        print_error(f"\nException Type: {type(error).__name__}")
        print_error(f"Exception Message: {str(error)}")
        print_error(f"\nStack Trace:")
        import traceback

        print_error(traceback.format_exc())

    print_error("=" * 70 + "\n")
