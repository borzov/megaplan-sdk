"""Unit tests for EmployeesResource — filter/q raise NotImplementedError (#13)."""

import pytest

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
