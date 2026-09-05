# Deploying to GCP

Backend → Cloud Run (container, built from `backend/Dockerfile`), Postgres → Cloud SQL, photos → Cloud Storage, push → Firebase Cloud Messaging. All scripts referenced below live in `infra/gcp/`.

## 0. Prerequisites (manual, one-time — the user does this)

These require creating/paying for accounts, which is outside what Claude can do on your behalf:

1. A Google Cloud project with **billing enabled**. Note the project ID.
2. [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed locally, then:
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_PROJECT_ID>
   ```
3. Enable the APIs the scripts need:
   ```bash
   gcloud services enable run.googleapis.com sqladmin.googleapis.com \
     storage.googleapis.com secretmanager.googleapis.com \
     cloudbuild.googleapis.com iam.googleapis.com
   ```
4. A [Firebase project](https://console.firebase.google.com/) — click "Add project" and either create a new one or attach Firebase to the same GCP project (recommended, keeps everything in one place). Add an Android app and (later, on a Mac) an iOS app to it — this generates `google-services.json` / `GoogleService-Info.plist` for `mobile/`, and lets you download a service-account JSON for the backend (Project Settings → Service Accounts → Generate new private key).

## 1. Database — Cloud SQL

```bash
export GCP_PROJECT_ID=<your-project-id>
bash infra/gcp/cloudsql-setup.sh
```

Creates a `db-f1-micro` Postgres 16 instance (cheapest tier — resize later if needed), a `suda_date` database, and a `suda` app user (you'll be prompted for its password). Save that password; it goes into the `DATABASE_URL` secret in step 3.

## 2. Photo storage — Cloud Storage

```bash
export GCS_BUCKET_NAME=suda-date-photos-<something-unique>   # bucket names are globally unique
bash infra/gcp/gcs-bucket-setup.sh
```

Creates a public-read bucket with CORS enabled for direct browser/app uploads via presigned URLs (see `backend/app/services/storage_service.py`).

## 3. Secrets — Secret Manager

Create these before running the Cloud Run deploy script (it references them by name):

```bash
# From cloudsql-setup.sh's output:
echo -n "postgresql+asyncpg://suda:<password>@/suda_date?host=/cloudsql/<connection-name>" | \
  gcloud secrets create suda-date-database-url --data-file=-

# Generate a real random secret, not the dev placeholder:
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create suda-date-secret-key --data-file=-

# From Google Cloud Console → APIs & Services → Credentials (OAuth client, Web application type):
echo -n "<your-google-oauth-web-client-id>" | gcloud secrets create suda-date-google-oauth-client-id --data-file=-

# From Kakao Developers → App → App Keys:
echo -n "<your-kakao-rest-api-key>" | gcloud secrets create suda-date-kakao-rest-api-key --data-file=-

# The Firebase service-account JSON downloaded in step 0:
gcloud secrets create suda-date-firebase-credentials --data-file=path/to/firebase-service-account.json
```

Any of these can be skipped for a first deploy (Google/Kakao login and push just no-op until their secret has a real value, same as local dev) — but `suda-date-database-url` and `suda-date-secret-key` are required for the app to boot at all.

## 4. Deploy the backend

```bash
export GCP_PROJECT_ID=<your-project-id>
export GCS_BUCKET_NAME=<the bucket name from step 2>
bash infra/gcp/cloudrun-deploy.sh
```

Builds the image from `backend/Dockerfile` via Cloud Build, creates a dedicated service account with least-privilege roles (`cloudsql.client`, `storage.objectAdmin`, `secretmanager.secretAccessor`), and deploys to Cloud Run. Prints the service URL at the end.

## 5. Run migrations against the deployed database

The deploy script doesn't run Alembic automatically (migrations should be a deliberate, reviewed step, not implicit on every deploy). From a machine with the Cloud SQL Auth Proxy or a direct connection to the instance:

```bash
cd backend
DATABASE_URL="<the same value you put in the suda-date-database-url secret>" \
  .venv/Scripts/python.exe -m alembic upgrade head    # or venv/bin/python on macOS/Linux
```

## 6. Verify

```bash
curl <service-url-from-step-4>/health
```

Then point `mobile/.env`'s `EXPO_PUBLIC_API_BASE_URL` at that URL and re-test signup/discovery/chat end to end against production infra (build order Phase 10's verification step).

## Cost notes

`db-f1-micro` Cloud SQL + Cloud Run's free tier (scales to zero, `--min-instances=0`) + Cloud Storage's free tier for a handful of MB of photos should stay near the free tier for early testing. Cloud SQL is the main fixed cost (~$10-15/mo even idle, since it doesn't scale to zero) — the biggest lever if cost becomes a concern is pausing/deleting the Cloud SQL instance between testing sessions, or moving to Cloud SQL's newer serverless-ish options once they're evaluated.

## Redeploying

Just re-run `bash infra/gcp/cloudrun-deploy.sh` — Cloud Run creates a new revision from the current `backend/` source each time.
