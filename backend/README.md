# backend — SuDa Date API

FastAPI + PostgreSQL backend.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
cp .env.example .env
```

Start Postgres (from `../infra`: `docker compose up postgres`, exposed on host port `5433` — see compose file comments), then:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

(`--port 8001` avoids clashing with anything else already on 8000 on your machine; use whatever's free for you.)

API docs: http://localhost:8001/docs

## Tests

Tests need a real Postgres reachable at `TEST_DATABASE_URL` (defaults to
`postgresql+asyncpg://suda:suda@localhost:5433/suda_date_test`). The schema is
dropped and recreated before every test, so point this at a disposable
database, never at your dev or prod database.

```bash
pytest
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```
