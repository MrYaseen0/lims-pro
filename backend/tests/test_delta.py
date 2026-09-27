"""Delta checks: pure check_delta math + end-to-end via /results."""
import pytest

import server
from server import check_delta
from tests.conftest import make_test_doc, make_patient_via_api, make_order_via_api


def test_check_delta_warning():
    d = check_delta(10.0, 13.0, 20)
    assert d["previous_value"] == 10.0
    assert d["current_value"] == 13.0
    assert d["change_percent"] == pytest.approx(30.0)
    assert d["warning"] is True


def test_check_delta_no_warning():
    d = check_delta(10.0, 11.0, 20)
    assert d["change_percent"] == pytest.approx(10.0)
    assert d["warning"] is False


def test_check_delta_boundary_not_warning():
    d = check_delta(10.0, 12.0, 20)
    assert d["change_percent"] == pytest.approx(20.0)
    assert d["warning"] is False  # strictly greater-than triggers


def test_check_delta_undefined_cases():
    assert check_delta(None, 11.0, 20) is None
    assert check_delta(10.0, None, 20) is None
    assert check_delta(0, 11.0, 20) is None  # percent change undefined
    assert check_delta("hemolyzed", 11.0, 20) is None
    assert check_delta("10", "13", 20)["warning"] is True  # numeric strings ok


async def test_delta_e2e_second_entry_warns(client, admin_client):
    test_doc = await make_test_doc("CBC")  # default ranges, delta limit 20
    patient = await make_patient_via_api(admin_client, age=30, gender="male")
    order1 = await make_order_via_api(admin_client, patient["id"], test_doc)
    r1 = await admin_client.post("/api/results", json={
        "order_id": order1["id"], "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14.0},
    })
    assert r1.status_code == 200, r1.text
    assert "delta_warnings" not in r1.json()  # no previous result -> no warnings

    order2 = await make_order_via_api(admin_client, patient["id"], test_doc)
    r2 = await admin_client.post("/api/results", json={
        "order_id": order2["id"], "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 18.0},  # +28.6% vs 14.0
    })
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body.get("delta_warnings"), "expected delta_warnings in response"
    w = body["delta_warnings"][0]
    assert w["parameter"] == "Hemoglobin (Hb)"
    assert w["previous_value"] == 14.0
    assert w["current_value"] == 18.0
    assert w["change_percent"] == pytest.approx(28.571, rel=1e-3)
    assert w["warning"] is True

    # Stored on the result doc.
    stored = await server.db.orders.find_one({"id": order2["id"]})
    result = [t for t in stored["tests"] if t["test_id"] == test_doc["id"]][0]["result"]
    assert result["delta"]["Hemoglobin (Hb)"]["warning"] is True
    assert result["delta"]["Hemoglobin (Hb)"]["change_percent"] == pytest.approx(28.571, rel=1e-3)


async def test_delta_e2e_small_change_no_warning(client, admin_client):
    test_doc = await make_test_doc("CBC")
    patient = await make_patient_via_api(admin_client, age=30, gender="male")
    order1 = await make_order_via_api(admin_client, patient["id"], test_doc)
    await admin_client.post("/api/results", json={
        "order_id": order1["id"], "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14.0},
    })
    order2 = await make_order_via_api(admin_client, patient["id"], test_doc)
    r2 = await admin_client.post("/api/results", json={
        "order_id": order2["id"], "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14.5},  # +3.6% -> no warning
    })
    assert r2.status_code == 200, r2.text
    assert "delta_warnings" not in r2.json()
