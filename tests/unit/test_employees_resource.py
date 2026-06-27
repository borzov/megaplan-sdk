"""Unit tests for EmployeesResource — filter/q raise NotImplementedError (#13)."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.employees import EmployeesResource


@pytest.mark.asyncio
async def test_employee_filter_raises_not_implemented():
    """filter= on employees.list must raise NotImplementedError (silently ignored by server)."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(NotImplementedError):
            await EmployeesResource(http).list(filter={"contentType": "EmployeeFilter"})


@pytest.mark.asyncio
async def test_employee_q_raises_not_implemented():
    """q= on employees.list must raise NotImplementedError (silently ignored by server)."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(NotImplementedError):
            await EmployeesResource(http).list(q="Мужейко")


@pytest.mark.asyncio
async def test_get_me_raises_value_error():
    """employees.get("me") must raise ValueError pointing to get_current()."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(ValueError, match="get_current"):
            await EmployeesResource(http).get("me")


@pytest.mark.asyncio
@respx.mock
async def test_employees_get_many_uses_sequential_gets():
    """employees.get_many uses parallel single GETs (no bulk POST)."""
    for eid, name in [(1000003, "Борзов"), (1000028, "Мужейко")]:
        respx.get(f"https://example.com/api/v3/employee/{eid}").mock(
            return_value=Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": {"contentType": "Employee", "id": str(eid), "lastName": name},
                },
            )
        )
    async with HTTPClient("https://example.com", access_token="token") as http:
        result = await EmployeesResource(http).get_many([1000003, 1000028])
    assert set(result.keys()) == {1000003, 1000028}
    assert result[1000003].last_name == "Борзов"


@pytest.mark.asyncio
async def test_employee_department_id_raises_not_implemented():
    """#26: department_id= is not a working server filter — must raise."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(NotImplementedError):
            await EmployeesResource(http).list(department_id=1000004)


@pytest.mark.asyncio
async def test_employee_status_raises_not_implemented():
    """#27: status= is not a working server filter — must raise."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(NotImplementedError):
            await EmployeesResource(http).list(status="active")
