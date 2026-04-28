# Playto Payout Engine

A minimal payout engine for Playto Pay — helps Indian agencies and freelancers collect international payments and withdraw to Indian bank accounts.

## Features

- **Merchant Ledger**: Immutable credit/debit transaction ledger with balance derived via database aggregation (no floats, no stored balance column)
- **Payout Request API**: POST to `/api/v1/payouts` with idempotency key header
- **Background Worker**: Celery task processes payouts (70% success, 20% failure, 10% stuck)
- **State Machine**: Enforced transitions — no illegal backwards transitions
- **Concurrency Safety**: PostgreSQL `SELECT FOR UPDATE` prevents overdraft on simultaneous requests
- **Idempotency**: Per-merchant idempotency keys with 24-hour expiry
- **Retry Logic**: Stuck payouts retried with exponential backoff (max 3 attempts)
- **React Dashboard**: Balance cards, ledger activity, payout form, live-updating payout history

## Tech Stack

- **Backend**: Django + Django REST Framework
- **Frontend**: React + Tailwind CSS
- **Database**: PostgreSQL
- **Background Jobs**: Celery + Redis
- **Deployment**: Docker Compose

## Prerequisites

- Docker & Docker Compose
- (Optional for local dev) Python 3.11+, Node.js 18+

## Quick Start with Docker

1. Clone the repository:
```bash
git clone <repo-url>
cd playto-payout
```

2. (Optional) Set merchant ID for frontend — edit `frontend/.env`:
```
REACT_APP_MERCHANT_ID=<merchant-uuid>
```

3. Start all services:
```bash
docker-compose up --build
```

4. Seed the database with test merchants:
```bash
docker-compose exec web python seed.py
```

5. Access the app:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1/

## Manual Setup (Local Development)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/playto
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key
ALLOWED_HOSTS=*
```

Run migrations and seed:
```bash
python manage.py migrate
python seed.py
```

Start the server:
```bash
python manage.py runserver
```

Start Celery worker (new terminal):
```bash
cd backend
source venv/bin/activate
celery -A playto worker -l info
```

Start Celery beat (new terminal):
```bash
cd backend
source venv/bin/activate
celery -A playto beat -l info
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_MERCHANT_ID=<merchant-uuid>
```

Start the dev server:
```bash
npm start
```

## API Endpoints

All endpoints require `X-Merchant-ID` header (UUID) and are under `/api/v1/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/merchants/me/` | GET | Merchant dashboard data (balances) |
| `/transactions/` | GET | Transaction ledger (credits & debits) |
| `/payouts/` | GET | List payout history |
| `/payouts/` | POST | Request a payout |
| `/payouts/<id>/` | GET | Payout detail |

### Payout Request

```bash
curl -X POST http://localhost:8000/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "X-Merchant-ID: <merchant-uuid>" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"amount_paise": 500000, "bank_account_id": "HDFC0001234"}'
```

## Running Tests

```bash
cd backend
python manage.py test ledger
```

Tests cover:
- **Concurrency**: Two simultaneous payout requests cannot overdraft
- **Idempotency**: Duplicate requests with same key return identical response
- **State Machine**: Illegal transitions (e.g., failed → completed) are blocked

## Project Structure

```
playto-payout/
├── backend/
│   ├── ledger/           # Django app (models, views, tasks, tests)
│   ├── playto/           # Django project config
│   ├── seed.py           # Seed script for test merchants
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/   # Dashboard, PayoutForm, PayoutTable
│       ├── api.js        # API client
│       └── App.js        # Main app with merchant selector
├── docker-compose.yml
├── EXPLAINER.md          # Architecture decisions and AI audit
└── README.md
```

## Key Design Decisions

- **No stored balance column**: Balance is derived from `SUM(credits) - SUM(debits)` in PostgreSQL — single source of truth
- **`BigIntegerField` in paise**: No floats, no decimal precision issues
- **Pessimistic locking**: `select_for_update()` prevents race conditions on payout requests
- **Idempotency**: Database-level unique constraint on `(merchant, key)` with stored response bodies
- **Debit on completion**: Funds held conceptually via payout status, only debited when payout succeeds
