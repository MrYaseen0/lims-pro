"""Inventory API: CRUD, filters, and stock/expiry alerts."""
from datetime import date, timedelta

from tests.conftest import make_user, login


def _item(**overrides):
    base = {
        "name": "CBC Reagent Kit",
        "category": "reagent",
        "lot_number": "LOT-001",
        "quantity": 10,
        "unit": "kits",
        "min_stock": 5,
        "expiry_date": (date.today() + timedelta(days=90)).isoformat(),
        "supplier": "Acme Labs",
    }
    base.update(overrides)
    return base


async def test_inventory_crud(client, admin_client):
    r = await admin_client.post("/api/inventory", json=_item())
    assert r.status_code == 200, r.text
    item = r.json()
    item_id = item["id"]
    assert item["quantity"] == 10

    r = await admin_client.get(f"/api/inventory/{item_id}")
    assert r.status_code == 200 and r.json()["name"] == "CBC Reagent Kit"

    r = await admin_client.put(f"/api/inventory/{item_id}", json={"quantity": 3})
    assert r.status_code == 200, r.text
    assert r.json()["quantity"] == 3

    r = await admin_client.get("/api/inventory", params={"category": "reagent"})
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1"
    r = await admin_client.get("/api/inventory", params={"search": "acme"})
    assert r.headers["X-Total-Count"] == "1"
    r = await admin_client.get("/api/inventory", params={"search": "no-such-thing"})
    assert r.headers["X-Total-Count"] == "0"

    r = await admin_client.delete(f"/api/inventory/{item_id}")
    assert r.status_code == 200, r.text
    r = await admin_client.get(f"/api/inventory/{item_id}")
    assert r.status_code == 404


async def test_inventory_validation(client, admin_client):
    r = await admin_client.post("/api/inventory", json=_item(category="bogus"))
    assert r.status_code == 400
    r = await admin_client.post("/api/inventory", json=_item(name=""))
    assert r.status_code == 400
    r = await admin_client.post("/api/inventory", json=_item(expiry_date="not-a-date"))
    assert r.status_code == 400


async def test_inventory_alerts_buckets(client, admin_client):
    today = date.today()
    await admin_client.post("/api/inventory", json=_item(
        name="Expired Item", quantity=100, min_stock=5,
        expiry_date=(today - timedelta(days=1)).isoformat()))
    await admin_client.post("/api/inventory", json=_item(
        name="Expiring Soon Item", quantity=100, min_stock=5,
        expiry_date=(today + timedelta(days=10)).isoformat()))
    await admin_client.post("/api/inventory", json=_item(
        name="Low Stock Item", quantity=2, min_stock=5,
        expiry_date=(today + timedelta(days=200)).isoformat()))
    await admin_client.post("/api/inventory", json=_item(
        name="Healthy Item", quantity=100, min_stock=5,
        expiry_date=(today + timedelta(days=200)).isoformat()))

    r = await admin_client.get("/api/inventory/alerts")
    assert r.status_code == 200, r.text
    alerts = r.json()
    assert [i["name"] for i in alerts["expired"]] == ["Expired Item"]
    assert [i["name"] for i in alerts["expiring_soon"]] == ["Expiring Soon Item"]
    assert [i["name"] for i in alerts["low_stock"]] == ["Low Stock Item"]


async def test_inventory_roles(client, admin_client):
    tech, tech_pw = await make_user("technician")
    await login(client, tech["email"], tech_pw)
    r = await client.post("/api/inventory", json=_item())
    assert r.status_code == 403
    r = await client.get("/api/inventory")
    assert r.status_code == 403
    r = await client.get("/api/inventory/alerts")
    assert r.status_code == 403
