"""Refresh-token rotation: issuance, rotation, reuse detection, logout."""
import hashlib
import json

import server
from tests.conftest import make_user, login


def _raw_refresh(client):
    return client.cookies.get("refresh_token")


def _spoof_refresh_cookie(client, raw):
    """Replace the jar's refresh_token value in place.

    (httpx normalizes the request host "test" to "test.local" for stored
    cookies, so Cookies.set(domain="test") would create a second, unsent
    entry instead of replacing the real one.)
    """
    for ck in client.cookies.jar:
        if ck.name == "refresh_token":
            ck.value = raw
            return
    raise AssertionError("no refresh_token cookie in jar to spoof")


def _digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


async def test_login_sets_refresh_cookie(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    raw = _raw_refresh(client)
    assert raw, "refresh_token cookie not set on login"
    docs = await server.db.refresh_tokens.find({"user_id": user["id"]}).to_list(10)
    assert len(docs) == 1
    assert docs[0]["token_hash"] == _digest(raw)
    assert docs[0]["revoked"] is False
    assert docs[0]["rotated_from"] is None


async def test_refresh_rotates_token(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    old_raw = _raw_refresh(client)
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200, r.text
    new_raw = _raw_refresh(client)
    assert new_raw and new_raw != old_raw
    old_doc = await server.db.refresh_tokens.find_one({"token_hash": _digest(old_raw)})
    assert old_doc["revoked"] is True
    new_doc = await server.db.refresh_tokens.find_one({"token_hash": _digest(new_raw)})
    assert new_doc is not None and new_doc["revoked"] is False
    assert new_doc["rotated_from"] == old_doc["id"]


async def test_refresh_reuse_revokes_all_tokens(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    old_raw = _raw_refresh(client)
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200, r.text
    # Present the OLD (now revoked) token again -> reuse detected.
    _spoof_refresh_cookie(client, old_raw)
    r2 = await client.post("/api/auth/refresh")
    assert r2.status_code == 401, r2.text
    docs = await server.db.refresh_tokens.find({"user_id": user["id"]}).to_list(10)
    assert docs and all(d["revoked"] for d in docs)


async def test_refresh_missing_cookie_401(client):
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_refresh_unknown_token_401(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    _spoof_refresh_cookie(client, "bogus-token-value")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_logout_revokes_presented_token(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    raw = _raw_refresh(client)
    r = await client.post("/api/auth/logout")
    assert r.status_code == 200, r.text
    doc = await server.db.refresh_tokens.find_one({"token_hash": _digest(raw)})
    assert doc["revoked"] is True
    # The revoked token can no longer be used (reuse path -> 401).
    client.cookies.clear()
    r2 = await client.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={raw}"})
    assert r2.status_code == 401


async def test_raw_token_never_stored(client):
    user, password = await make_user("admin")
    await login(client, user["email"], password)
    raw = _raw_refresh(client)
    await client.post("/api/auth/refresh")
    new_raw = _raw_refresh(client)
    docs = await server.db.refresh_tokens.find({}).to_list(10)
    assert docs
    blob = json.dumps(docs, default=str)
    for secret in (raw, new_raw):
        assert secret not in blob
        for d in docs:
            assert d["token_hash"] != secret
            assert all(v != secret for v in d.values() if isinstance(v, str))
