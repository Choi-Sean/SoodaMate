# backend — SuDa Mate API

FastAPI + MSSQL (SQL Server) backend.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
cp .env.example .env
```

**No Docker, no local containers** — set `DATABASE_URL` in `.env` to a real, directly-reachable SQL Server instance (see `docs/ENV_VARS.md` at the repo root for the connection-string shape and the `MARS_Connection=yes` requirement). Tables aren't managed by Alembic yet (`Base.metadata.create_all` was used directly against the real database); stored procedures live in `../infra/mssql/stored_procedures.sql` and are applied by running that script against the same instance.

```bash
uvicorn app.main:app --reload --port 8001
```

(`--port 8001` avoids clashing with anything else already on 8000 on your machine; use whatever's free for you.)

API docs: http://localhost:8001/docs

## Tests

Tests run against the **same real MSSQL instance** `DATABASE_URL` points at (there is no separate disposable test database — set `TEST_DATABASE_URL` only if you want to point tests somewhere else). Each test run drops and recreates the schema, so never point this at a database with real user data.

```bash
pytest
```

Full-suite runs against a remote hosted instance can take several minutes — most of that is network round-trip latency per test, not local compute. `pytest-timeout` (`pyproject.toml`, 120s per test, `thread` method since Windows has no `SIGALRM`) guards against a silent hang turning into an unbounded wait — if a test exceeds it, pytest reports a `Failed: Timeout` with a thread-dump traceback pointing at exactly where it stalled.

**Known flaky failure, not a product bug**: on Windows, roughly 1 run in 4 crashes with `Windows fatal exception: access violation` at a seemingly random WebSocket test (pyodbc/aioodbc connection teardown racing Python's GC finalizer on a different thread — a C-extension thread-safety issue, not something in this app's code). If a run crashes like this, just re-run it; see the comment in `app/database.py` for what was already tried (switching off `NullPool` for tests makes it *worse* — a different, more frequent "attached to a different loop" failure — so don't retry that without re-reading the comment first).

## Stored procedures

Core transactional logic (`sp_RecordSwipe`, `sp_UpsertBlock`, `sp_UpsertPushToken`) lives in `../infra/mssql/stored_procedures.sql`, not in SQLAlchemy — apply/update it by connecting directly to the database and running the script (e.g. via `sqlcmd` or Azure Data Studio), same as the table schema itself.
