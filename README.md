# LIMS.Pro — Laboratory Information System

A full-stack Laboratory Information Management System (LIMS) for diagnostic laboratories:
patient registration, test catalog, orders, sample tracking, result entry with automatic
H/L flagging and critical-value alerts, pathologist review, PDF report generation,
billing, and analytics — with role-based access control throughout.

## 🚀 Quick Start

### Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@lims.pro | admin123 |
| Lab Manager | manager@lims.pro | password123 |
| Technician | technician@lims.pro | password123 |
| Pathologist | pathologist@lims.pro | password123 |
| Receptionist | receptionist@lims.pro | password123 |

### Seed demo data

Click **"Setup Demo Data"** on the login page, or call:

```bash
curl -X POST {BACKEND_URL}/api/seed
```

Note: seeding an already-seeded database requires an admin login — the login-page
button works unauthenticated only on a fresh database.

### Run the backend

```bash
cd backend
# one-time: create backend/.env with a real secret (backend refuses to boot without one)
python -c "import secrets; print(secrets.token_hex(32))"
# add to backend/.env: JWT_SECRET=<output>
uvicorn server:app --reload
```

The backend entry point is always `uvicorn server:app`. `backend/server.py` is a
compatibility shim over the real application in `backend/app/`.

### Run the frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Set `REACT_APP_BACKEND_URL` in `frontend/.env` to the backend URL (default `http://localhost:8000`).
Production build: `npm run build` (must pass after any UI change).

## 📋 Modules (UI pages)

| Page | Route | What it does |
|------|-------|--------------|
| Login | `/login` | Email/password sign-in, demo-data seed button |
| Dashboard | `/dashboard` | Today's orders, revenue, pending counts, recent activity |
| Patients | `/patients` | Registration (yearly serial `0001-09-2026`), debounced search, pagination |
| Patient Detail | `/patients/:id` | Patient profile + full order history |
| Test Catalog | `/tests` | Test catalog with categories, pricing, reference ranges; create/edit (admin, manager) |
| Orders | `/orders` | Order list with status/priority filters |
| Create Order | `/orders/new` | Patient lookup, test selection, referred-by doctor, priority |
| Order Detail | `/orders/:id` | Status timeline, barcode, result entry, PDF generation/download |
| Samples | `/samples` | Sample collection and status tracking (`pending → collected → received → processing`) |
| Lab Queue | `/technician` | Technician work queue, per-parameter result entry, automatic H/L/N flags |
| Review Queue | `/pathologist` | Pathologist approve/reject with notes |
| Critical Alerts | (via Review Queue) | `critical_low`/`critical_high` values raise alerts; acknowledge by pathologist, lab manager, admin or doctor |
| Reports | `/reports` | Approved orders, generate and download PDF lab reports |
| Billing | `/billing` | Invoices, payment status, record payments |
| Invoice Detail | `/billing/:id` | Invoice line items, payment history |
| Analytics | `/analytics` | Revenue trends, test volumes, order stats |
| Settings | `/settings` | User management (register users), laboratory information (admin only) |

### User roles & navigation access

| Role | Pages |
|------|-------|
| Admin | Everything, incl. user management and Settings |
| Lab Manager | Everything except user management |
| Receptionist | Patients, Orders, Billing |
| Technician | Orders, Samples, Lab Queue |
| Pathologist | Orders, Review Queue, Reports |
| Collection Staff | Samples only |

## 🔄 Order workflow

```
registered → sample_collected → in_lab → under_review → approved → report_released
```

1. **Receptionist** registers the patient and creates an order (tests, priority, referring doctor)
2. **Collection staff** collects the sample (barcode generated)
3. **Technician** enters results per parameter — values are auto-flagged H/L/N against
   reference ranges; critical values raise alerts in `critical_alerts`
4. **Pathologist** reviews the queue, approves or rejects with notes, acknowledges critical alerts
5. **Report** is generated as PDF and released

## 🛠 Tech stack

- **Backend**: FastAPI (Python) + MongoDB (Motor async driver), Pydantic validation
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui, React Router, Recharts
- **Auth**: JWT (8h) in HttpOnly cookie, bcrypt password hashing, server-side role guards
- **PDF**: real PDF report generation (`backend/pdf_generator.py`)
- **Tests**: 44 pytest backend tests (`backend/tests/`); frontend verified via `npm run build`

## 📁 Project structure

```
lims-pro/
├── AGENTS.md                 # agent operating rules for this repo
├── .agents/skills/           # repo-map, architecture, decisions, testing,
│                             #   security-review, release-check, responsive-ui,
│                             #   prompt-enhancer
├── docs/
│   ├── ARCHITECTURE.md       # backend/frontend structure, data flow, boot sequence
│   └── DECISIONS.md          # dated technical decisions
├── backend/
│   ├── server.py             # entry shim — run: uvicorn server:app
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # FastAPI app, middleware, router wiring
│   │   ├── core/             # config, database, deps, pagination, security
│   │   ├── models/           # Pydantic schemas (orders, patients, results…)
│   │   ├── routers/          # auth, patients, orders, results, reports,
│   │   │                     #   billing, analytics
│   │   └── services/         # ranges.py (H/L flagging), seed_data.py
│   ├── audit_logger.py       # audit event logging (active)
│   ├── pdf_generator.py      # lab report PDF generation
│   ├── patient_portal.py     # patient portal (exists, not mounted yet)
│   ├── config.py / locations.py
│   └── tests/                # pytest suite (auth, roles, ranges, pagination,
│                             #   critical values, results e2e)
├── frontend/
│   ├── src/
│   │   ├── pages/            # 15 pages (see Modules table)
│   │   ├── components/       # Layout + shadcn/ui components
│   │   ├── context/          # AuthContext
│   │   └── lib/              # api.js (axios client), utils.js
│   └── package.json
├── docker-compose.yml        # backend + frontend + MongoDB
├── DEPLOYMENT.md             # deployment guide
├── MVP_BASELINE.md           # MVP scope baseline
└── README.md
```

## 🔌 API endpoints

All routes are prefixed with `/api`. Auth: HttpOnly cookie (`lims_token`) or
`Authorization: Bearer` header.

### Auth & users
- `POST /api/auth/register` — create user (admin)
- `POST /api/auth/login` — login, sets HttpOnly cookie (rate-limited: 10/min per IP)
- `POST /api/auth/logout` — clear cookie
- `GET /api/auth/me` — current user
- `GET /api/users`, `PUT /api/users/{user_id}` — user management (admin)
- `POST /api/seed` — seed demo data

### Patients & doctors
- `GET /api/patients` — paginated list (`page`, `page_size`, `search`; `X-Total-Count` header)
- `POST /api/patients` — register patient (yearly serial auto-assigned)
- `GET /api/patients/{id}`, `PUT /api/patients/{id}` — detail / update
- `GET /api/doctors` — referring-doctor list

### Orders & samples
- `GET /api/orders` — paginated list with status/priority filters
- `POST /api/orders` — create order
- `GET /api/orders/{id}`, `PUT /api/orders/{id}/status` — detail / status update
- `GET /api/samples`, `POST /api/samples` — sample list / collect
- `PUT /api/samples/{id}/status` — sample status update

### Tests, results & review
- `GET /api/tests`, `POST /api/tests`, `PUT /api/tests/{id}`, `DELETE /api/tests/{id}` — test catalog CRUD
- `GET /api/test-categories` — category list
- `POST /api/results` — enter results (auto H/L flags; critical values create alerts)
- `GET /api/technician/queue` — technician work queue
- `GET /api/pathologist/queue` — pathologist review queue
- `POST /api/approve` — approve/reject with notes
- `GET /api/critical-alerts` — list alerts
- `POST /api/critical-alerts/{id}/acknowledge` — acknowledge (pathologist, lab_manager, admin, doctor)

### Reports
- `GET /api/reports/{order_id}` — report data
- `POST /api/reports/{order_id}/release` — release report
- `POST /api/reports/{order_id}/generate-pdf` — generate PDF
- `GET /api/reports/{order_id}/download/{filename}` — download PDF
- `GET /api/reports/{order_id}/pdf-stream` — stream PDF

### Billing
- `GET /api/invoices`, `GET /api/invoices/{id}` — invoices
- `POST /api/payments` — record payment

### Analytics
- `GET /api/analytics/dashboard` — dashboard stats

## 🧪 Testing

```bash
cd backend
/tmp/limsvenv/bin/pytest -q        # 44 tests: auth, roles, ranges, pagination, critical values, results e2e
cd ../frontend
npm run build                      # production build must pass after UI changes
```

The `testing` skill (`.agents/skills/testing/SKILL.md`) documents the full
verification gate: targeted pytest → full suite → frontend build → boot smoke test.

## 🔒 Security features

- JWT in HttpOnly cookie (8h expiry), bcrypt password hashing
- Backend refuses to boot without `JWT_SECRET` (fail-fast)
- Login rate limiting: 10 attempts/min per IP, then HTTP 429
- Security headers: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`
- Pydantic validation at every API boundary; NoSQL-injection payloads rejected
- Server-side role enforcement (`require_role`) — the UI nav is convenience only
- MongoDB indexes ensured at startup

⚠️ **Production notes**: the login limiter is in-memory (per process) — add a
reverse proxy / WAF with global rate limiting before going live. Enable HSTS and
a Content-Security-Policy when serving over HTTPS. `patient_portal.py` is not
mounted yet.

## 📊 Database collections

`users`, `patients`, `orders`, `samples`, `tests`, `doctors`, `invoices`,
`audit_logs`, `critical_alerts`, `refresh_tokens`, `portal_sessions`, `portal_otps`

## 🤖 Agent skills

`.agents/skills/` contains executable playbooks derived from the repo analysis:
`repo-map`, `architecture`, `decisions`, `prompt-enhancer`, `testing`,
`security-review`, `release-check`, `responsive-ui`. `AGENTS.md` routes each task
to the right skill and sets the verification rules (real command output, never
assumed success).

## ⚠️ Known limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Email/SMS notifications | Not implemented | — |
| Multi-branch/location | Not implemented | Phase-2 |
| Age/gender-specific reference ranges | Planned | Current ranges are basic per-test/per-parameter |
| Refresh-token rotation | Not implemented | Short-lived (8h) access cookie only |
| Patient portal | Code exists, unmounted | `backend/patient_portal.py` not wired into `main.py` |
| Referral commissions | Not implemented | — |
| Inventory / QC modules | Not implemented | — |

## 🗺 Phase-2 roadmap

1. Mount patient portal; refresh-token rotation with hashed token identifiers
2. Age/gender-specific reference ranges, delta checks against previous results
3. Referral commission tracking + frontend view
4. Inventory/reagent management with expiry alerts
5. QC module (Levey–Jennings, Westgard rules)
6. Multi-branch support, Urdu report option
7. Printable barcode labels (strings already generated; print flow pending)

---

**Stack**: FastAPI + MongoDB · React + Tailwind + shadcn/ui
**Version**: 1.1.0 · **Last updated**: September 2026
