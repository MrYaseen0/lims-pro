# Architecture — LIMS.Pro

> Verified against the codebase on 2026-09-22. Every claim cites a current file.

## Components

### Backend (`backend/`)
- **Entry:** `backend/server.py` — 38-line compatibility shim. `uvicorn server:app` re-exports the FastAPI app and test helpers (`db`, `init_db`, `hash_password`, `audit_logger`, …) from `backend/app/`.
- **App:** `backend/app/main.py` — creates the FastAPI app, mounts 7 routers under `/api`, configures CORS from `CORS_ORIGINS` env.
- **Routers** (`backend/app/routers/`): `auth`, `patients`, `orders`, `results`, `reports`, `billing`, `analytics`. Each owns its URL paths; all mounted with `prefix="/api"`.
- **Core** (`backend/app/core/`):
  - `config.py` — env config; **fail-fast** `RuntimeError` if `JWT_SECRET` missing.
  - `database.py` — Motor (async MongoDB) client + `db` handle.
  - `deps.py` — `get_current_user`, `require_role`, `check_login_rate_limit` (10/min/IP sliding window → 429).
  - `security.py` — bcrypt hashing, HS256 JWT create/verify.
  - `pagination.py` — `paginate()` helper, `X-Total-Count` header.
- **Services** (`backend/app/services/`): `ranges.py` (reference-range checks, H/L flags, critical-value detection), `seed_data.py` (doctors, test catalogue).
- **Models** (`backend/app/models/schemas.py`) — Pydantic v2 request/response schemas; strict types block NoSQL operator injection.
- **Standalone:** `backend/patient_portal.py` (exists, **unmounted**), `backend/audit_logger.py` (active, writes audit trail).

### Frontend (`frontend/`)
- React 18 + Tailwind. Entry `src/index.js` → `src/App.js`.
- 16 pages in `src/pages/` (Dashboard, Patients, Orders, CreateOrder, OrderDetail, Samples, TechnicianQueue, PathologistQueue, Reports, Billing, InvoiceDetail, Analytics, Tests, Settings, Login, PatientDetail).
- API client `src/lib/api.js` — `fetch` with `credentials: 'include'` (HttpOnly cookie auth).
- Shared `src/components/Pagination.js` (patients partially wired; orders pending).

## Data flow (result entry → critical alert)
```
Technician POST /api/results  (results.py)
  → validate Pydantic schema (schemas.py)
  → ranges.py: H/L flag per parameter vs reference range
  → ranges.py: check_critical_values() vs critical_low/critical_high
  → write result doc to db (orders/results)
  → if violations: insert into db.critical_alerts (status=pending)
Pathologist GET /api/critical-alerts → POST /api/critical-alerts/{id}/acknowledge
  (roles: pathologist, lab_manager, admin, doctor)
```

## Trust boundaries
| Boundary | Enforcement | File |
|---|---|---|
| Anonymous | Login 10/min/IP → 429 | `core/deps.py` |
| Authenticated | HttpOnly JWT cookie (`samesite=lax`), HS256 verify | `routers/auth.py`, `core/security.py` |
| Role-gated | `require_role(...)` per route | `core/deps.py` |
| Input | Pydantic strict types (blocks `$ne`/`$gt` injection) | `models/schemas.py` |
| Headers | `SecurityHeadersMiddleware`: nosniff, DENY, strict-origin-when-cross-origin | `app/main.py` |

## Storage (MongoDB)
Collections: `users`, `patients`, `doctors`, `tests`, `orders`, `samples`, `invoices`, `critical_alerts`, `counters`. Indexes ensured at startup via `ensure_indexes`. Test DB: `lims_test_db`.

## External services
None in the request path. Docker Compose runs `backend` + `frontend` (+ MongoDB expected externally/by compose). CI: `.github/workflows/ci.yml`.

## Deployment
- `docker-compose.yml` — backend (uvicorn), frontend (nginx build), MongoDB.
- `backend/Dockerfile`, `frontend/Dockerfile`.
- No reverse proxy / WAF / global rate limiting yet (see DECISIONS.md).
