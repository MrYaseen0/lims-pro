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

## 2026-09-22 — Seeded critical (panic) thresholds
- **Context:** Critical alerts existed in code (`check_critical_values`) but seeded CBC ranges carried no `critical_low`/`critical_high`, so no alert could ever fire on real data.
- **Decision:** Seeded default critical thresholds (Hemoglobin, WBC/TLC, Platelets, Creatinine, Sodium, Potassium, Calcium) in `seed_data.py`; backfill adds missing thresholds to existing ranges without overwriting admin-customized values.
- **Alternatives:** Leave thresholds admin-only (zero coverage by default).
- **Reason:** Panic values must work out of the box; backfill preserves local customization.
- **Consequences:** Live result entry now raises `critical_alerts`; UI panel added in Review Queue.
- **Revisit trigger:** When lab-specific panic limits are validated by a pathologist.

## 2026-09-22 — Phase-2: refresh-token rotation design
- **Context:** Only an 8h HttpOnly access cookie existed; no way to stay signed in safely.
- **Decision:** Opaque refresh tokens (`secrets.token_urlsafe(32)`); store ONLY the SHA-256 hex digest in a `refresh_tokens` collection (user_id, expires_at ~30d, revoked, rotated_from). `POST /api/auth/refresh` rotates (new token, old revoked); reuse of a revoked token revokes ALL of that user's tokens (theft detection); `POST /api/auth/logout` revokes the presented token. Raw token never stored or logged. Frontend axios interceptor retries once after a silent refresh.
- **Alternatives:** Long-lived JWT refresh tokens in DB; rotating JWTs.
- **Reason:** Opaque + hashed storage means a DB leak yields nothing usable; rotation bounds token lifetime; reuse detection matches OWASP guidance.
- **Consequences:** New `REFRESH_COOKIE_NAME` / `REFRESH_TOKEN_EXPIRY_DAYS` config; tests assert the raw token never appears in the collection.
- **Revisit trigger:** If sliding expiration or device-scoped sessions are requested.

## 2026-09-22 — Phase-2: patient portal mounted
- **Context:** `backend/patient_portal.py` existed standalone, unmounted.
- **Decision:** Integrated as `app/routers/portal.py` under `/api/portal/*`: staff-generated token-link/OTP access (`POST /api/portal/access`), token-only read of approved reports (`GET /api/portal/reports?token=`), audit logs (`GET /api/portal/access-logs`, admin). Only token hashes stored.
- **Alternatives:** Keep unmounted; full patient accounts with passwords.
- **Reason:** Token links need no patient passwords and fit the "share report with patient" flow; hashes keep the DB safe.
- **Consequences:** Collections `portal_sessions`, `portal_otps`, `portal_access_logs` are live and indexed.
- **Revisit trigger:** If patients need interactive accounts (payments, appointments).

## 2026-09-22 — Phase-2: age/gender ranges + delta checks
- **Context:** Reference ranges were one-size-fits-all per parameter (e.g. Hemoglobin).
- **Decision:** Range entries accept optional `age_min`, `age_max`, `gender` ("M"/"F"/null=any); `compute_result_flags(..., age_years, gender)` picks the most-specific matching entry, falling back to the generic entry. Seeded Hemoglobin variants: adult M 14–18, adult F 12–16, child 11–15. Delta checks: optional `delta_limit_percent` per range (default 20); on result entry the latest previous result for the same patient/test/parameter is compared, and breaches are stored on the result doc + returned as `delta_warnings` (frontend shows an amber badge).
- **Alternatives:** Separate test codes per demographic; delta checks as a batch job.
- **Reason:** Keeps one test code; most-specific-wins is backward compatible (old calls unchanged); inline delta check gives immediate technician feedback.
- **Consequences:** `ranges.py` stays pure and unit-tested; result docs carry a `delta` field.
- **Revisit trigger:** If ranges need finer bands (neonatal, geriatric) — extend entry fields, same matcher.

## 2026-09-22 — Phase-2: inventory, QC, branches, Urdu reports, barcode labels
- **Context:** Phase-2 roadmap items 4–7.
- **Decision:** `inventory_items` CRUD (admin/lab_manager) with `/alerts` buckets (expired / expiring≤30d / low_stock); QC via pure `evaluate_westgard(values, mean, sd)` (1_2s, 1_3s, 2_2s, R_4s, 4_1s, 10_x) with violations stored per run and an inline-SVG Levey–Jennings chart (no new npm deps); `branches` collection with a seeded MAIN branch, `branch_id` backfilled onto users/patients/orders/inventory_items, non-admin users scoped to their branch, admin override via `?branch_id` or `X-Branch-Id` header; report view gets an English/اردو toggle (RTL, system fonts only, no external downloads); barcode labels at `/samples/:id/label` as a chromeless print route with print CSS; Google Fonts `@import` removed from `index.css` (system font stack) so the UI builds and renders fully offline.
- **Alternatives:** Chart library (recharts); Google Fonts kept; per-branch databases.
- **Reason:** No new dependencies; single-DB `branch_id` scoping is the smallest correct multi-branch step; RTL toggle reuses the existing report component.
- **Consequences:** 11 routers under `/api`; frontend has Inventory + QC pages and a branch selector; suite grew 46 → 89 tests.
- **Revisit trigger:** Real per-branch data isolation needs, or a second report language.
