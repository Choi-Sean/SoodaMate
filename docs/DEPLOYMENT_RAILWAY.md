# Deploying the backend to Railway

Current deployment target (supersedes `docs/DEPLOYMENT_GCP.md`, kept only as a reference for the original GCP-based plan — this project's database is a real hosted MSSQL instance, not Cloud SQL, and Railway builds directly from `backend/Dockerfile`, so most of that guide's Cloud SQL/GCS-specific steps no longer apply).

## 0. Prerequisites (manual — the user does this)

1. A [Railway](https://railway.app/) account (GitHub login is simplest).
2. This repo pushed to a GitHub repository Railway can access (Railway deploys from a connected repo, not a local folder).

## 1. Create the service

In the Railway dashboard: **New Project → Deploy from GitHub repo** → select this repo.

Since `backend/` is a subfolder (this is a monorepo with `backend/`, `mobile/`, `web/`), set the service's **Root Directory** to `backend` in the service's Settings tab. Railway will then find `backend/Dockerfile` and `backend/railway.json` automatically (the latter sets `builder: DOCKERFILE`, a health check on `/health`, and a restart policy).

## 2. Environment variables

In the service's **Variables** tab, set everything `backend/.env` has locally, pointed at real values instead of dev placeholders:

| Variable | Notes |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | a real random value (`openssl rand -hex 32`), not the dev placeholder |
| `DATABASE_URL` | the real MSSQL connection string (same shape as local `.env` — `mssql+aioodbc://...&MARS_Connection=yes`) |
| `GOOGLE_OAUTH_CLIENT_ID`, `KAKAO_REST_API_KEY` | once those accounts exist |
| `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS` | photo storage — GCS is still used for this even though the DB moved off GCP; `GOOGLE_APPLICATION_CREDENTIALS` needs the service-account JSON's *contents*, not just a path, since there's no persistent disk to read a file from — see note below |
| `FIREBASE_CREDENTIALS_PATH` | same file-vs-path issue as above |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | from the Stripe Dashboard, once that account exists |
| `WEB_BASE_URL` | the deployed marketing site's real URL (Vercel), used for Stripe Checkout success/cancel redirects |
| `CORS_ORIGINS` | the mobile app doesn't need CORS (native, not browser), but the web shop page's `fetch()` calls do — include the Vercel site's URL |

**Credential-file variables on Railway**: Railway's filesystem is ephemeral and there's no simple "upload a file" step for env vars the way some other host UIs offer. The pragmatic fix once GCS/Firebase are actually needed: change `storage_service.py` / `push_service.py` to accept the service-account JSON *content* from an env var (`GOOGLE_APPLICATION_CREDENTIALS_JSON`) and write it to a temp file at startup, or use `google.oauth2.service_account.Credentials.from_service_account_info(json.loads(...))` directly instead of a file path. Not yet done — flagging so it isn't a surprise when Phase 10-equivalent GCS wiring actually gets exercised on Railway.

## 3. First deploy

Push to the connected branch (or click **Deploy** in the dashboard) — Railway builds the Dockerfile and starts the service. Watch the build logs for the ODBC driver install step; it's the slowest part of the build.

## 4. Run migrations / initial schema

There's no separate migration step wired into the Railway build — the schema was created once, directly, against the real database (see `docs/ARCHITECTURE.md`'s note on this project's DB history: no Alembic migrations have been generated/run yet, `Base.metadata.create_all` was used directly). Any new columns/tables going forward should go through a proper Alembic migration run from a developer machine with `DATABASE_URL` pointed at the real instance, not through Railway's deploy step.

## 5. Verify

```bash
curl https://<your-railway-service>.up.railway.app/health
```

Then point `mobile/.env` and `mobile/eas.json`'s build profiles' `EXPO_PUBLIC_API_BASE_URL` at that URL (replacing the `REPLACE-WITH-YOUR-CLOUD-RUN-URL` placeholders left over from the original GCP-based plan).

## Redeploying

Push to the connected branch — Railway rebuilds and redeploys automatically. No manual script to run, unlike the GCP guide's `cloudrun-deploy.sh`.
