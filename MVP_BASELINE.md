# LIMS.Pro MVP Baseline - FROZEN
# Date: January 21, 2026
# Status: STABLE - DO NOT MODIFY WITHOUT BACKWARD COMPATIBILITY

## Services Verified
- Backend: RUNNING (FastAPI on port 8001)
- Frontend: RUNNING (React on port 3000)
- MongoDB: RUNNING (localhost:27017)

## API Version
- Version: 1.0.0
- Base URL: /api

## File Checksums (Integrity Reference)
- server.py: 3ccc67e5ca42805046594ce76b20b41e
- App.js: 83105c1913dfe0eae46b089693348916

## Database Baseline
- Users: 5
- Patients: 6
- Tests: 11
- Orders: 5
- Invoices: 5

## Frozen API Endpoints (DO NOT BREAK)
### Authentication
- POST /api/auth/login
- POST /api/auth/register
- GET /api/auth/me

### Patients
- GET /api/patients
- POST /api/patients
- GET /api/patients/{id}
- PUT /api/patients/{id}

### Tests
- GET /api/tests
- POST /api/tests
- GET /api/tests/{id}
- PUT /api/tests/{id}
- GET /api/test-categories

### Orders
- GET /api/orders
- POST /api/orders
- GET /api/orders/{id}
- PUT /api/orders/{id}/status

### Samples
- GET /api/samples
- POST /api/samples
- PUT /api/samples/{id}/status

### Results
- POST /api/results
- GET /api/technician/queue

### Pathologist
- POST /api/approve
- GET /api/pathologist/queue

### Reports
- GET /api/reports/{order_id}
- POST /api/reports/{order_id}/release

### Billing
- GET /api/invoices
- GET /api/invoices/{id}
- POST /api/payments

### Analytics
- GET /api/analytics/dashboard

### Users
- GET /api/users
- PUT /api/users/{id}

### Utility
- POST /api/seed

## Frozen Data Models
- User: id, email, name, role, phone, is_active, created_at
- Patient: id, patient_id, name, age, gender, phone, email, address, created_at
- Test: id, name, code, category, sample_type, price, turn_around_time, is_active
- Order: id, order_id, patient_id, tests[], status, priority, total_amount, status_history[]
- Sample: id, sample_id, barcode, order_id, sample_type, status, collection_time
- Invoice: id, invoice_id, order_id, patient_id, amount, discount, net_amount, payment_status, payments[]

## Order Status Lifecycle (FROZEN)
registered → sample_collected → in_lab → under_review → approved → report_released

## Role Permissions (FROZEN)
- admin: Full access
- lab_manager: All lab operations
- technician: Samples, results
- pathologist: Review, approve
- receptionist: Patients, orders, billing

## Phase-2 Rules
1. All new endpoints must be ADDITIVE (new routes only)
2. Existing endpoint signatures MUST NOT change
3. Data model changes must be backward-compatible (optional fields only)
4. New features must not break existing workflows
5. Run full regression test suite before merge

---
BASELINE LOCKED: January 21, 2026
