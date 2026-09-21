"""Role-guard tests: technicians are blocked from admin routes but can enter results."""
from tests.conftest import make_user, make_test_doc, make_patient_via_api, make_order_via_api, login


async def test_technician_cannot_create_test(tech_client):
    r = await tech_client.post("/api/tests", json={
        "name": "X", "code": "X", "category": "C",
        "sample_type": "Blood", "price": 100, "turn_around_time": 24,
    })
    assert r.status_code == 403


async def test_technician_cannot_list_users(tech_client):
    r = await tech_client.get("/api/users")
    assert r.status_code == 403


async def test_admin_can_create_test(admin_client):
    r = await admin_client.post("/api/tests", json={
        "name": "Glucose", "code": "GLU", "category": "Biochemistry",
        "sample_type": "Blood", "price": 300, "turn_around_time": 12,
    })
    assert r.status_code == 200
    assert r.json()["code"] == "GLU"


async def test_technician_can_enter_result(tech_client):
    test_doc = await make_test_doc()
    patient = await make_patient_via_api(tech_client)
    order = await make_order_via_api(tech_client, patient["id"], test_doc)
    r = await tech_client.post("/api/results", json={
        "order_id": order["id"],
        "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14},
    })
    assert r.status_code == 200, r.text


async def test_technician_result_missing_order_404(tech_client):
    test_doc = await make_test_doc()
    r = await tech_client.post("/api/results", json={
        "order_id": "no-such-order",
        "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14},
    })
    assert r.status_code == 404


async def test_receptionist_cannot_enter_result(client):
    user, password = await make_user("receptionist")
    await login(client, user["email"], password)
    r = await client.post("/api/results", json={
        "order_id": "x", "test_id": "y", "values": {},
    })
    assert r.status_code == 403
