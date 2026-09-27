"""Tests for critical (panic) value detection and acknowledgement workflow."""
import pytest
import server
from tests.conftest import make_user, login, make_patient_via_api


async def make_test_with_critical():
    """Create a test with critical thresholds."""
    test_doc = {
        "id": "test-critical-001",
        "code": "K",
        "name": "Potassium",
        "price": 500.0,
        "reference_ranges": [
            {
                "parameter": "Potassium",
                "normal_range": "3.5 - 5.0",
                "unit": "mmol/L",
                "critical_low": 2.8,
                "critical_high": 6.0,
            }
        ],
    }
    await server.db.tests.insert_one(test_doc)
    return test_doc


async def make_order_for_test(client, patient_id, test_doc):
    """Create an order using the current API format (tests as OrderTestItem list)."""
    r = await client.post("/api/orders", json={
        "patient_id": patient_id,
        "tests": [{
            "test_id": test_doc["id"],
            "test_name": test_doc["name"],
            "test_code": test_doc["code"],
            "price": test_doc["price"],
        }],
    })
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_critical_value_creates_alert(client):
    """A result exceeding critical thresholds creates a critical_alert."""
    tech_user, tech_pw = await make_user("technician")
    # Login
    transport_client = client
    await login(transport_client, tech_user["email"], tech_pw)
    
    # Create patient and order
    patient = await make_patient_via_api(transport_client, name="Critical Patient")
    test_doc = await make_test_with_critical()
    
    # Create order
    order = await make_order_for_test(transport_client, patient["id"], test_doc)
    
    # Enter a critical high result (K+ 6.5 > critical_high 6.0)
    r = await transport_client.post("/api/results", json={
        "order_id": order["id"],
        "test_id": test_doc["id"],
        "values": {"Potassium": 6.5},
    })
    assert r.status_code == 200, r.text
    data = r.json()
    # Should include critical alert info
    assert "_critical_alerts" in data
    assert len(data["_critical_alerts"]) == 1
    assert data["_critical_alerts"][0]["direction"] == "critical_high"
    
    # Verify alert was stored in DB
    alert = await server.db.critical_alerts.find_one({"order_id": order["id"]})
    assert alert is not None
    assert alert["status"] == "pending"
    assert alert["value"] == 6.5


@pytest.mark.asyncio
async def test_non_critical_value_no_alert(client):
    """A normal result does not create a critical alert."""
    tech_user, tech_pw = await make_user("technician")
    await login(client, tech_user["email"], tech_pw)
    
    patient = await make_patient_via_api(client, name="Normal Patient")
    test_doc = await make_test_with_critical()
    
    order = await make_order_for_test(client, patient["id"], test_doc)
    
    # Enter normal result (K+ 4.0, within normal range)
    r = await client.post("/api/results", json={
        "order_id": order["id"],
        "test_id": test_doc["id"],
        "values": {"Potassium": 4.0},
    })
    assert r.status_code == 200
    data = r.json()
    assert "_critical_alerts" not in data
    
    # No alert in DB
    count = await server.db.critical_alerts.count_documents({"order_id": order["id"]})
    assert count == 0


@pytest.mark.asyncio
async def test_acknowledge_critical_alert(client):
    """Pathologist can acknowledge a critical alert."""
    # Create alert via technician
    tech_user, tech_pw = await make_user("technician")
    await login(client, tech_user["email"], tech_pw)
    
    patient = await make_patient_via_api(client, name="Ack Patient")
    test_doc = await make_test_with_critical()
    
    order = await make_order_for_test(client, patient["id"], test_doc)
    
    r = await client.post("/api/results", json={
        "order_id": order["id"],
        "test_id": test_doc["id"],
        "values": {"Potassium": 2.5},  # critical low (< 2.8)
    })
    assert r.status_code == 200
    
    alert = await server.db.critical_alerts.find_one({"order_id": order["id"]})
    assert alert is not None
    alert_id = alert["id"]
    
    # Login as pathologist and acknowledge
    # Need a fresh client to avoid cookie overwrite
    import httpx
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as path_client:
        path_user, path_pw = await make_user("pathologist")
        await login(path_client, path_user["email"], path_pw)
        
        r = await path_client.post(f"/api/critical-alerts/{alert_id}/acknowledge")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_by"] == path_user["id"]
    
    # Verify in DB
    updated = await server.db.critical_alerts.find_one({"id": alert_id})
    assert updated["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_seeded_ranges_include_critical_thresholds(client):
    """Fresh deployments must ship critical thresholds so panic alerts can fire."""
    from app.services.seed_data import ensure_test_reference_ranges, REFERENCE_RANGES

    await ensure_test_reference_ranges()
    cbc = await server.db.tests.find_one({"code": "CBC"})
    assert cbc and cbc.get("reference_ranges"), "CBC ranges not seeded"
    by_param = {r["parameter"]: r for r in cbc["reference_ranges"]}
    assert by_param["Hemoglobin (Hb)"]["critical_low"] == 7.0
    assert by_param["Hemoglobin (Hb)"]["critical_high"] == 20.0
    assert by_param["TLC (WBC)"]["critical_low"] == 2000
    assert by_param["Platelet Count"]["critical_high"] == 1000000

    # Backfill must not overwrite an admin-customized threshold.
    await server.db.tests.update_one(
        {"code": "CBC", "reference_ranges.parameter": "Hemoglobin (Hb)"},
        {"$set": {"reference_ranges.$.critical_high": 21.5}},
    )
    await ensure_test_reference_ranges()
    cbc = await server.db.tests.find_one({"code": "CBC"})
    hb = next(r for r in cbc["reference_ranges"] if r["parameter"] == "Hemoglobin (Hb)")
    assert hb["critical_high"] == 21.5, "admin customization was overwritten"
    assert hb["critical_low"] == 7.0


@pytest.mark.asyncio
async def test_seeded_cbc_raises_alert_end_to_end(client):
    """A panic Hb value against the SEEDED CBC ranges creates an alert."""
    tech_user, tech_pw = await make_user("technician")
    await login(client, tech_user["email"], tech_pw)
    from app.services.seed_data import ensure_test_reference_ranges
    await ensure_test_reference_ranges()
    cbc = await server.db.tests.find_one({"code": "CBC"})

    patient = await make_patient_via_api(client, name="Seed Alert Patient")
    order = await make_order_for_test(client, patient["id"], cbc)
    r = await client.post("/api/results", json={
        "order_id": order["id"],
        "test_id": cbc["id"],
        "values": {"Hemoglobin (Hb)": 22.5},
    })
    assert r.status_code == 200, r.text
    alerts = await server.db.critical_alerts.find({"order_id": order["id"]}).to_list(10)
    assert len(alerts) == 1
    assert alerts[0]["parameter"] == "Hemoglobin (Hb)"
    assert alerts[0]["direction"] == "critical_high"
