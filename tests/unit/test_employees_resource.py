"""Unit tests for EmployeesResource — filter/q raise NotImplementedError (#13)."""

import pytest


async def test_employee_filter_raises_not_implemented(employees):
    """filter= on employees.list must raise NotImplementedError (silently ignored by server)."""
    with pytest.raises(NotImplementedError):
        await employees.list(filter={"contentType": "EmployeeFilter"})


async def test_employee_q_raises_not_implemented(employees):
    """q= on employees.list must raise NotImplementedError (silently ignored by server)."""
    with pytest.raises(NotImplementedError):
        await employees.list(q="Мужейко")


async def test_get_me_raises_value_error(employees):
    """employees.get("me") must raise ValueError pointing to get_current()."""
    with pytest.raises(ValueError, match="get_current"):
        await employees.get("me")


async def test_employees_get_many_uses_sequential_gets(megaplan_api, employees):
    """employees.get_many uses parallel single GETs (no bulk POST)."""
    for eid, name in [(1000003, "Борзов"), (1000028, "Мужейко")]:
        megaplan_api.get(
            f"employee/{eid}",
            data={"contentType": "Employee", "id": str(eid), "lastName": name},
        )
    result = await employees.get_many([1000003, 1000028])
    assert set(result.keys()) == {1000003, 1000028}
    assert result[1000003].last_name == "Борзов"


async def test_employee_department_id_raises_not_implemented(employees):
    """#26: department_id= is not a working server filter — must raise."""
    with pytest.raises(NotImplementedError):
        await employees.list(department_id=1000004)


async def test_employee_status_raises_not_implemented(employees):
    """#27: status= is not a working server filter — must raise."""
    with pytest.raises(NotImplementedError):
        await employees.list(status="active")
