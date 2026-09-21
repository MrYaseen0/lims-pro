# Decisions — LIMS.Pro

Dated log of lasting technical choices. Newest last.

## 2026-09-21 — Monolith split into `backend/app/` package
- **Context:** `backend/server.py` had grown into a single large file; changes were hard to scope.
- **Decision:** Split into routers/services/core/models; keep `server.py` as a thin shim.
- **Alternatives:** Keep monolith; full rewrite with new entry point.
- **Reason:** Incremental, preserves `uvicorn server:app` contract and all existing tests.
- **Consequences:** 7 routers under `/api`; all 38 original route/method combos verified identical.
- **Revisit trigger:** If the shim starts accumulating logic again.

## 2026-09-21 — JWT fail-fast on missing secret
- **Context:** A missing `JWT_SECRET` could silently fall back to a dev default.
- **Decision:** `config.py` raises `RuntimeError` at import if `JWT_SECRET` is unset.
- **Alternatives:** Default dev secret with warning.
- **Reason:** Fail-closed beats fail-open for auth secrets.
- **Consequences:** Deployment must set `JWT_SECRET`; tests set a test-only value.
- **Revisit trigger:** None — permanent.

## 2026-09-21 — Critical/panic value alerts
- **Context:** Lab safety requires flagging life-threatening results immediately.
- **Decision:** `check_critical_values()` in `services/ranges.py`; violations written to `db.critical_alerts` (status `pending` → `acknowledged`); acknowledge restricted to pathologist/lab_manager/admin/doctor.
- **Alternatives:** Email/SMS push on detection.
- **Reason:** In-app workflow first; notification providers (WhatsApp) still pending as configurable stub.
- **Consequences:** New collection + 2 endpoints; 3 tests currently failing (fix in progress).
- **Revisit trigger:** When WhatsApp/report-ready provider is chosen.

## 2026-09-21 — Tracked `.env` files removed
- **Context:** `backend/.env` with a real JWT secret was committed to the public repo.
- **Decision:** Deleted both `.env` files from tracking; added `.env.example` placeholders.
- **Alternatives:** Leave and rotate silently.
- **Reason:** Stop the leak; secret rotation still required (history retains it).
- **Consequences:** **JWT_SECRET must be rotated**; consider history rewrite.
- **Revisit trigger:** After rotation + decision on `git filter-repo`.

## 2026-09-22 — Critical-values tests fixed (outdated `test_ids` format)
- **Context:** 3 tests in `test_critical_values.py` failed with 422 — they sent `test_ids`, but the refactored API expects `tests` (list of `OrderTestItem`).
- **Decision:** Fixed the tests to match the current API; added `price` to the test doc fixture.
- **Alternatives:** Change the API back to accept `test_ids`.
- **Reason:** The API is correct and consistent (all other tests use `tests`); the test file was stale.
- **Consequences:** Full suite green: 44 passed.
- **Revisit trigger:** None.

## 2026-09-22 — Security headers middleware added
- **Context:** Security assessment flagged missing `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- **Decision:** Added `SecurityHeadersMiddleware` (pure Starlette, no new deps) in `app/main.py`.
- **Alternatives:** `secure` package dependency.
- **Reason:** Zero-dependency, covers the API's needs; HSTS intentionally omitted (requires HTTPS, breaks local dev).
- **Consequences:** All API responses now carry the three headers; verified via curl.
- **Revisit trigger:** Before production HTTPS deployment — add HSTS + CSP.

## 2026-09-22 — Skill library adopted (`.agents/skills/`)
- **Context:** 27-repo analysis recommended one small operating file + focused skills over giant prompts.
- **Decision:** Added `AGENTS.md`, 8 skills (`repo-map`, `architecture`, `decisions`, `prompt-enhancer`, `testing`, `security-review`, `release-check`, `responsive-ui`), `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`.
- **Alternatives:** Ad-hoc agent instructions per task.
- **Reason:** Repeatable verification; project memory survives compaction.
- **Consequences:** Every task routes through the narrowest skill set; completion requires real command evidence.
- **Revisit trigger:** After a skill proves useless in two consecutive tasks — then cut it.
