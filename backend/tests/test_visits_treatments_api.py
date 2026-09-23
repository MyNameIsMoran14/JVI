from httpx import AsyncClient


async def test_create_and_list_visits(api_client: AsyncClient, authed_headers: dict[str, str]) -> None:
    create = await api_client.post(
        "/api/v1/visits",
        headers=authed_headers,
        json={"date": "2026-01-15", "doctor": "Иванова", "summary": "Плановый осмотр"},
    )
    assert create.status_code == 200
    assert create.json()["doctor"] == "Иванова"

    listing = await api_client.get("/api/v1/visits", headers=authed_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_create_and_list_treatments(api_client: AsyncClient, authed_headers: dict[str, str]) -> None:
    create = await api_client.post(
        "/api/v1/treatments",
        headers=authed_headers,
        json={"regimen": "VRd", "cycle_no": 3, "start_date": "2026-01-01"},
    )
    assert create.status_code == 200
    assert create.json()["regimen"] == "VRd"

    listing = await api_client.get("/api/v1/treatments", headers=authed_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
