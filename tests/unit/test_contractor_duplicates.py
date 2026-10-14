"""Read-only contractor duplicate routes."""

import json
from urllib.parse import unquote


async def test_possible_duplicates_resolves_subtype(contractors, megaplan_api):
    assert hasattr(contractors, "possible_duplicates")
    megaplan_api.get("contractor/1", data={"id": 1, "contentType": "ContractorHuman"})
    route = megaplan_api.get(
        "contractorHuman/1/possibleDuplicates", data=[{"id": 2, "contentType": "ContractorCompany"}]
    )
    assert (await contractors.possible_duplicates(1))[0].id == 2
    assert route.call_count == 1


async def test_find_duplicates_and_similar(contractors, megaplan_api):
    assert hasattr(contractors, "find_duplicates")
    route = megaplan_api.get("contractorCompany/possibleDuplicates", data=[])
    contacts = [{"contentType": "ContactInfo", "type": "email", "value": "test@example.com"}]
    assert await contractors.find_duplicates(name="Example", contact_info=contacts, limit=5) == []
    query = json.loads(unquote(route.calls[0].request.url.query.decode()))
    assert query == {"name": "Example", "contactInfo": contacts, "limit": 5}
    megaplan_api.get("contractorCompany/1/similar", data=[])
    assert await contractors.get_similar(1, content_type="ContractorCompany") == []
