# Cloth POS — Backend

FastAPI + SQLAlchemy 2 + Alembic on Neon Postgres. Built to run on Vercel (serverless).

## Install

Requires Python 3.12+ (Windows PowerShell shown; on macOS/Linux use `source .venv/bin/activate`).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values by hand. Never commit `.env`.

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Neon **pooled** URL (host contains `-pooler`), `postgresql+psycopg://...?sslmode=require` |
| `DATABASE_URL_DIRECT` | no | Neon **direct** URL, used only by Alembic |
| `JWT_SECRET` | yes | 32+ random characters |
| `JWT_EXPIRE_MINUTES` | no | default 720 |
| `FRONTEND_URL` | no | comma-separated allowed origins, no `*` |
| `R2_*` | no | the app starts without them |

## Database

Migrations are never run at app startup. Run them from your laptop:

```powershell
alembic upgrade head
```

Load demo data (safe to run twice):

```powershell
python -m scripts.seed
```

Demo logins: `owner` / `owner123` and `cashier` / `cashier123`. **Change these before real use.**

## Run

```powershell
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health (pings the database): http://localhost:8000/health

## Test

```powershell
pytest
```

Tests use an in-memory SQLite database and override `DATABASE_URL`, so they never touch Neon.

## Deploy (Vercel, from the dashboard)

Vercel finds `app` in `app/main.py` automatically. `.python-version` pins Python 3.12 and
`vercel.json` keeps tests, migrations and scripts out of the bundle.

1. Run `alembic upgrade head` and `python -m scripts.seed` from your laptop against Neon first.
2. Vercel dashboard: Add New → Project → import `Cloth-brand-backend`. Framework: FastAPI.
3. Add environment variables: `DATABASE_URL` (pooled URL), `JWT_SECRET` (a new random value),
   `JWT_EXPIRE_MINUTES`, `FRONTEND_URL`. `DATABASE_URL_DIRECT` and `R2_*` are not needed yet.
4. Deploy. Open `https://<project>.vercel.app/health`, then `/docs`.

The first request after idle time can take a few seconds (Vercel and Neon wake up).

## Layout

```
app/
  main.py        FastAPI app (CORS, error handlers, routers)
  core/          config, db, security (bcrypt + JWT), deps (auth + ShopScope), errors, rate_limit
  models/        SQLAlchemy models (money = Integer rupees, quantity = Numeric(10,2))
  schemas/       Pydantic request/response models
  routers/       thin HTTP layer
  services/      business logic
alembic/         migrations
scripts/seed.py  demo data
tests/           pytest
```

Errors always look like `{"code": "...", "message": "..."}`.
