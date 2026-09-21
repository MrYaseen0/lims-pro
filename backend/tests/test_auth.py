"""Auth tests: login, logout, cookies, seed protection, rate limiting."""
from tests.conftest import make_user, login


async def test_login_sets_httponly_cookie(admin_client):
    # admin_client fixture already asserted the cookie exists on login
    assert "lims_token" in admin_client.cookies


async def test_login_cookie_is_httponly(client, admin_user):
    user, password = admin_user
    r = await client.post("/api/auth/login", json={"email": user["email"], "password": password})
    assert r.status_code == 200
    assert "httponly" in r.headers.get("set-cookie", "").lower()


async def test_login_wrong_password_401(client, admin_user):
    user, _ = admin_user
    r = await client.post("/api/auth/login", json={"email": user["email"], "password": "WrongPass999"})
    assert r.status_code == 401


async def test_login_unknown_email_401(client):
    r = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Whatever123"})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_me_with_cookie(admin_client):
    r = await admin_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


async def test_bearer_fallback_still_works(client, admin_user):
    user, password = admin_user
    r = await login(client, user["email"], password)
    token = r.json()["access_token"]
    # new client without cookies, Authorization header only
    import httpx, server
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c2:
        r2 = await c2.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200


async def test_logout_clears_cookie(admin_client):
    r = await admin_client.post("/api/auth/logout")
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert "lims_token" in set_cookie


async def test_seed_bootstrap_allowed_when_no_users(client):
    r = await client.post("/api/seed")
    assert r.status_code == 200


async def test_seed_unauthenticated_401_when_users_exist(client, admin_user):
    r = await client.post("/api/seed")
    assert r.status_code == 401


async def test_seed_non_admin_403(tech_client):
    r = await tech_client.post("/api/seed")
    assert r.status_code == 403


async def test_seed_admin_ok(admin_client):
    r = await admin_client.post("/api/seed")
    assert r.status_code == 200


async def test_patients_requires_auth(client):
    r = await client.get("/api/patients")
    assert r.status_code == 401


async def test_login_rate_limited_after_10_failures(client, admin_user):
    user, _ = admin_user
    for _ in range(10):
        r = await client.post("/api/auth/login", json={"email": user["email"], "password": "WrongPass999"})
        assert r.status_code == 401
    r = await client.post("/api/auth/login", json={"email": user["email"], "password": "WrongPass999"})
    assert r.status_code == 429
