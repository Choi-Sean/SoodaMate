FROM python:3.11-slim

WORKDIR /app

# Microsoft ODBC Driver 17 for SQL Server (matches python:3.11-slim's Debian
# 12/bookworm base) — required for pyodbc/aioodbc to reach the MSSQL database.
# Microsoft's own prod.list already embeds "[arch=... signed-by=/usr/share/keyrings/microsoft-prod.gpg]"
# (matching the keyring path below), so it's piped straight through with no
# further edits. An earlier version of this ran the fetched list through
# `sed` to inject a signed-by clause, which was needed back when Microsoft
# served a plain unsigned `deb ...` line; now that clause is already
# present, so the sed just duplicated the `[...]` block and broke apt's
# parser ("Malformed entry ... URI parse" — a real Railway build failure).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 apt-transport-https ca-certificates gcc g++ unixodbc-dev \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Railway (and Cloud Run) inject $PORT at runtime; default to 8080 for local
# `docker run`. Shell form so the env var actually expands.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
