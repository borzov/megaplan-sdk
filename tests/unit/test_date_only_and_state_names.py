"""Typed birthdays (#FR-G) and state-name normalization (#NOTE-2)."""

from datetime import date

from megaplan_sdk.helpers import normalize_state_name
from megaplan_sdk.models.employee import Employee

EMPLOYEE = {
    "contentType": "Employee",
    "id": 1,
    "firstName": "Максим",
    "birthday": {"contentType": "DateOnly", "year": 1987, "month": 2, "day": 7},
}


def test_birthday_is_typed_and_converts_to_a_date():
    """Consumers should not have to know about the year/month/day dict."""
    employee = Employee(**EMPLOYEE)

    assert employee.birthday is not None
    assert (employee.birthday.month, employee.birthday.day) == (2, 7)
    assert employee.birthday.date == date(1987, 2, 7)


def test_birthday_day_and_month_survive_a_bogus_year():
    """Accounts do contain nonsense years; the day still has to be usable."""
    employee = Employee(
        **{**EMPLOYEE, "birthday": {"contentType": "DateOnly", "month": 2, "day": 7}}
    )

    assert employee.birthday is not None
    assert (employee.birthday.month, employee.birthday.day) == (2, 7)
    assert employee.birthday.date is None


def test_missing_birthday_stays_none():
    """No birthday means None, not an empty DateOnly."""
    employee = Employee(**{k: v for k, v in EMPLOYEE.items() if k != "birthday"})

    assert employee.birthday is None


def test_state_name_normalization_strips_emoji_and_case():
    """Accounts hold both «Договор» and «Договор 📝»; filters must match both."""
    assert normalize_state_name("Договор 📝") == "договор"
    assert normalize_state_name("Договор") == "договор"
    assert normalize_state_name("  Новая   заявка 📨 ") == "новая заявка"


def test_state_name_normalization_handles_missing_names():
    """A state without a name normalizes to an empty string, not a crash."""
    assert normalize_state_name(None) == ""
    assert normalize_state_name("") == ""
