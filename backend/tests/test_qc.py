"""QC module: pure Westgard rules + control/run API."""
from server import evaluate_westgard
from tests.conftest import make_user, login


def test_westgard_no_violations():
    assert evaluate_westgard([100, 101, 99, 100.5], 100, 2) == []


def test_westgard_1_2s_warning_only():
    assert evaluate_westgard([100, 105.5], 100, 2) == ["1_2s"]


def test_westgard_1_3s():
    v = evaluate_westgard([100, 107], 100, 2)
    assert "1_2s" in v and "1_3s" in v


def test_westgard_2_2s():
    v = evaluate_westgard([100, 105, 106], 100, 2)
    assert "2_2s" in v


def test_westgard_r_4s():
    v = evaluate_westgard([100, 105, 95], 100, 2)
    assert "R_4s" in v
    assert "2_2s" not in v


def test_westgard_4_1s():
    assert evaluate_westgard([103, 103.5, 104, 103], 100, 2) == ["4_1s"]


def test_westgard_10_x():
    assert evaluate_westgard([101] * 10, 100, 2) == ["10_x"]


def test_westgard_guards():
    assert evaluate_westgard([], 100, 2) == []
    assert evaluate_westgard([100], 100, 0) == []
    assert evaluate_westgard([100], 100, -1) == []
    # Single point can only trigger 1_2s/1_3s, never multi-point rules.
    assert evaluate_westgard([107], 100, 2) == ["1_2s", "1_3s"]


async def test_qc_control_crud(client, admin_client):
    r = await admin_client.post("/api/qc/controls", json={
        "name": "Hb Control L1", "target_mean": 100, "sd": 2, "unit": "g/dL",
    })
    assert r.status_code == 200, r.text
    control = r.json()
    cid = control["id"]

    r = await admin_client.get("/api/qc/controls")
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1"

    r = await admin_client.get(f"/api/qc/controls/{cid}")
    assert r.status_code == 200 and r.json()["target_mean"] == 100

    r = await admin_client.put(f"/api/qc/controls/{cid}", json={"sd": 2.5})
    assert r.status_code == 200 and r.json()["sd"] == 2.5

    r = await admin_client.delete(f"/api/qc/controls/{cid}")
    assert r.status_code == 200, r.text
    r = await admin_client.get(f"/api/qc/controls/{cid}")
    assert r.status_code == 404


async def test_qc_run_logging_and_chart(client, admin_client):
    r = await admin_client.post("/api/qc/controls", json={
        "name": "Glucose Control", "target_mean": 100, "sd": 2, "unit": "mg/dL",
    })
    cid = r.json()["id"]

    r = await admin_client.post(f"/api/qc/controls/{cid}/runs", json={"measured_value": 101})
    assert r.status_code == 200, r.text
    assert r.json()["violations"] == []

    r = await admin_client.post(f"/api/qc/controls/{cid}/runs", json={"measured_value": 105})
    assert r.status_code == 200, r.text
    assert r.json()["violations"] == ["1_2s"]

    r = await admin_client.get(f"/api/qc/controls/{cid}/runs")
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "2"

    r = await admin_client.get(f"/api/qc/controls/{cid}/chart-data")
    assert r.status_code == 200, r.text
    chart = r.json()
    assert chart["mean"] == 100 and chart["sd"] == 2
    assert chart["lines"] == {
        "mean": 100, "plus1sd": 102, "minus1sd": 98,
        "plus2sd": 104, "minus2sd": 96, "plus3sd": 106, "minus3sd": 94,
    }
    assert len(chart["points"]) == 2
    assert chart["points"][0]["value"] == 101
    assert chart["points"][1]["violations"] == ["1_2s"]


async def test_qc_roles(client, admin_client):
    r = await admin_client.post("/api/qc/controls", json={
        "name": "Role Control", "target_mean": 50, "sd": 1,
    })
    cid = r.json()["id"]

    tech, tech_pw = await make_user("technician")
    await login(client, tech["email"], tech_pw)
    r = await client.post(f"/api/qc/controls/{cid}/runs", json={"measured_value": 50})
    assert r.status_code == 200, r.text  # technicians may log runs
    r = await client.post("/api/qc/controls", json={"name": "Nope", "target_mean": 1, "sd": 1})
    assert r.status_code == 403  # but not manage controls
