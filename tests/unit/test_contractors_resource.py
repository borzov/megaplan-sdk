"""Unit tests for ContractorsResource."""


async def test_list_contractors(megaplan_api, contractors):
    """Test listing contractors."""
    megaplan_api.get(
        "contractor",
        data=[
            {"id": 1, "contentType": "ContractorCompany", "name": "Company 1"},
            {"id": 2, "contentType": "ContractorHuman", "name": "Person 1"},
        ],
    )

    result = await contractors.list()

    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Company 1"
    assert result[1].id == 2


async def test_get_contractor(megaplan_api, contractors):
    """Test getting a contractor by ID."""
    megaplan_api.get(
        "contractor/1",
        data={"id": 1, "contentType": "ContractorCompany", "name": "Test Company"},
    )

    contractor = await contractors.get(1)

    assert contractor.id == 1
    assert contractor.name == "Test Company"


async def test_get_deals(megaplan_api, contractors):
    """Test getting contractor deals."""
    megaplan_api.get(
        "contractor/1/deals",
        data=[
            {"id": 10, "contentType": "Deal", "name": "Deal 1"},
            {"id": 20, "contentType": "Deal", "name": "Deal 2"},
        ],
    )

    deals = await contractors.get_deals(1)

    assert len(deals) == 2
    assert deals[0].id == 10
    assert deals[0].name == "Deal 1"
    assert deals[1].id == 20
    assert deals[1].name == "Deal 2"


async def test_get_deals_with_limit(megaplan_api, contractors):
    """Test getting contractor deals with limit parameter."""
    megaplan_api.get(
        "contractor/123/deals",
        data=[{"id": 5, "contentType": "Deal", "name": "Limited Deal"}],
    )

    deals = await contractors.get_deals(123, limit=10)

    assert len(deals) == 1
    assert deals[0].id == 5


async def test_get_deals_empty(megaplan_api, contractors):
    """Test getting contractor deals when no deals exist."""
    megaplan_api.get("contractor/999/deals", data=[])

    deals = await contractors.get_deals(999)

    assert len(deals) == 0
    assert deals == []
