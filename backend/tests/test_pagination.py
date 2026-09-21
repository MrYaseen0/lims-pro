"""Pagination tests: page_size honored, X-Total-Count header present."""
from tests.conftest import make_patient_via_api, make_test_doc, make_order_via_api


async def test_patients_pagination_headers(admin_client):
    for i in range(5):
        await make_patient_via_api(admin_client, name=f"Paged Patient {i}")
    r = await admin_client.get("/api/patients", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers.get("X-Total-Count") == "5"


async def test_patients_second_page(admin_client):
    for i in range(5):
        await make_patient_via_api(admin_client, name=f"Paged Patient {i}")
    r = await admin_client.get("/api/patients", params={"page": 2, "page_size": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers.get("X-Total-Count") == "5"


async def test_page_size_capped(admin_client):
    for i in range(3):
        await make_patient_via_api(admin_client, name=f"Cap Patient {i}")
    r = await admin_client.get("/api/patients", params={"page": 1, "page_size": 500})
    assert r.status_code == 200
    # MAX_PAGE_SIZE is 100; all 3 fit anyway, header must reflect the true total
    assert r.headers.get("X-Total-Count") == "3"
    assert len(r.json()) == 3


async def test_orders_pagination_header(admin_client):
    test_doc = await make_test_doc()
    patient = await make_patient_via_api(admin_client, name="Order Pager")
    await make_order_via_api(admin_client, patient["id"], test_doc)
    await make_order_via_api(admin_client, patient["id"], test_doc)
    r = await admin_client.get("/api/orders", params={"page": 1, "page_size": 1})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.headers.get("X-Total-Count") == "2"
