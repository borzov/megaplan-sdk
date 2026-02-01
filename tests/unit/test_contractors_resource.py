"""Unit tests for ContractorsResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.contractors import ContractorsResource


@pytest.mark.asyncio
@respx.mock
async def test_list_contractors():
    """Test listing contractors."""
    respx.get("https://example.com/api/v3/contractor").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "ContractorCompany", "name": "Company 1"},
                    {"id": 2, "contentType": "ContractorHuman", "name": "Person 1"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ContractorsResource(http_client)
        contractors = await resource.list()

        assert len(contractors) == 2
        assert contractors[0].id == 1
        assert contractors[0].name == "Company 1"
        assert contractors[1].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_contractor():
    """Test getting a contractor by ID."""
    respx.get("https://example.com/api/v3/contractor/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "ContractorCompany", "name": "Test Company"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ContractorsResource(http_client)
        contractor = await resource.get(1)

        assert contractor.id == 1
        assert contractor.name == "Test Company"


@pytest.mark.asyncio
@respx.mock
async def test_get_deals():
    """Test getting contractor deals."""
    respx.get("https://example.com/api/v3/contractor/1/deals").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 10, "contentType": "Deal", "name": "Deal 1"},
                    {"id": 20, "contentType": "Deal", "name": "Deal 2"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ContractorsResource(http_client)
        deals = await resource.get_deals(1)

        assert len(deals) == 2
        assert deals[0].id == 10
        assert deals[0].name == "Deal 1"
        assert deals[1].id == 20
        assert deals[1].name == "Deal 2"


@pytest.mark.asyncio
@respx.mock
async def test_get_deals_with_limit():
    """Test getting contractor deals with limit parameter."""
    respx.get("https://example.com/api/v3/contractor/123/deals").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 5, "contentType": "Deal", "name": "Limited Deal"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ContractorsResource(http_client)
        deals = await resource.get_deals(123, limit=10)

        assert len(deals) == 1
        assert deals[0].id == 5


@pytest.mark.asyncio
@respx.mock
async def test_get_deals_empty():
    """Test getting contractor deals when no deals exist."""
    respx.get("https://example.com/api/v3/contractor/999/deals").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ContractorsResource(http_client)
        deals = await resource.get_deals(999)

        assert len(deals) == 0
        assert deals == []
