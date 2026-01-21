# LIMS.Pro - Laboratory Information System

A comprehensive, cloud-ready Laboratory Information System (LIS) for diagnostic laboratories.

## 🚀 Quick Start

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@lims.pro | admin123 |
| **Lab Manager** | manager@lims.pro | password123 |
| **Technician** | technician@lims.pro | password123 |
| **Pathologist** | pathologist@lims.pro | password123 |
| **Receptionist** | receptionist@lims.pro | password123 |

### Setup Demo Data
Click "Setup Demo Data" on the login page, or call:
```bash
curl -X POST {BACKEND_URL}/api/seed
```

## 📋 Core Features

### Modules Implemented
- ✅ **Authentication** - JWT-based with role-based access control
- ✅ **Patient Management** - Registration, search, history
- ✅ **Test Catalog** - Tests, categories, pricing, TAT
- ✅ **Order Management** - Create orders, status tracking
- ✅ **Sample Collection** - Barcode generation, tracking
- ✅ **Technician Workflow** - Result entry, abnormal flagging
- ✅ **Pathologist Review** - Approve/reject with notes
- ✅ **Report Management** - Release reports
- ✅ **Billing & Payments** - Invoices, payment recording
- ✅ **Analytics Dashboard** - Revenue trends, test volumes

### User Roles & Permissions
| Role | Access |
|------|--------|
| Admin | Full system access, user management |
| Lab Manager | All lab operations, reports, analytics |
| Technician | Sample processing, result entry |
| Pathologist | Review queue, approve/reject results |
| Receptionist | Patients, orders, billing |

## 🔄 Order Workflow

```
Registered → Sample Collected → In Lab → Under Review → Approved → Report Released
```

1. **Receptionist** creates order for patient
2. **Collection Staff** collects sample
3. **Technician** enters test results
4. **Pathologist** reviews and approves
5. **Report** released to patient

## 🛠 Tech Stack

- **Backend**: FastAPI (Python) + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Charts**: Recharts
- **Auth**: JWT with bcrypt password hashing

## 📁 Project Structure

```
/app
├── backend/
│   ├── server.py          # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/        # React pages
│   │   ├── components/   # UI components
│   │   ├── context/      # Auth context
│   │   └── lib/          # API client, utilities
│   └── package.json
└── README.md
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - Register user
- `GET /api/auth/me` - Current user info

### Patients
- `GET /api/patients` - List patients
- `POST /api/patients` - Create patient
- `GET /api/patients/{id}` - Patient details

### Tests
- `GET /api/tests` - Test catalog
- `POST /api/tests` - Create test (admin/manager)
- `PUT /api/tests/{id}` - Update test

### Orders
- `GET /api/orders` - List orders
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Order details
- `PUT /api/orders/{id}/status` - Update status

### Samples
- `GET /api/samples` - List samples
- `POST /api/samples` - Collect sample

### Results & Review
- `POST /api/results` - Enter test result
- `GET /api/technician/queue` - Technician work queue
- `POST /api/approve` - Approve/reject result
- `GET /api/pathologist/queue` - Review queue

### Reports
- `GET /api/reports/{order_id}` - Get report data
- `POST /api/reports/{order_id}/release` - Release report

### Billing
- `GET /api/invoices` - List invoices
- `GET /api/invoices/{id}` - Invoice details
- `POST /api/payments` - Record payment

### Analytics
- `GET /api/analytics/dashboard` - Dashboard stats

## ⚠️ Known Limitations (MVP)

| Feature | Status | Notes |
|---------|--------|-------|
| PDF Reports | Mocked | Returns data, no actual PDF |
| Email/SMS | Mocked | Not sending real messages |
| Multi-location | Not implemented | Phase-2 feature |
| Reference Ranges | Basic | Age/gender interpretation planned |
| Audit Logs | Partial | Status history tracked |

## 🔒 Security Features

- JWT token authentication (24h expiry)
- Password hashing with bcrypt
- Role-based access control on all endpoints
- CORS configuration

## 📊 Database Collections

- `users` - System users
- `patients` - Patient records
- `tests` - Test catalog
- `orders` - Lab orders with tests
- `samples` - Sample tracking
- `invoices` - Billing records

## 🚀 Phase-2 Roadmap

1. **PDF Generation** - Professional lab reports with branding
2. **Communications** - Email/SMS notifications
3. **Multi-location** - Central lab + collection centers
4. **Advanced Analytics** - TAT tracking, doctor referrals
5. **Audit Logging** - Complete action history
6. **Reference Ranges** - Age/gender-based interpretations
7. **Barcode Printing** - Label printer support

---

**Version**: 1.0.0 MVP  
**Last Updated**: January 2026
