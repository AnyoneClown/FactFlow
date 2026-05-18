# FactFlow

FactFlow is a Django CRM for uploading spreadsheet fact data and showing yearly aggregated statistics.

The project is being implemented in small task-plan steps from `task.md`.

## Local run

### Local Python run

```bash
poetry install
cp .env.example .env
poetry run python manage.py migrate
poetry run python manage.py bootstrap_local
poetry run python manage.py runserver
```

### Local Docker run

```bash
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, applies migrations, loads demo fixture data, and ensures a superuser exists automatically.

## Docker demo data

`docker compose up --build` now loads demo website data automatically on the first start of an empty database and also ensures a Django superuser exists.

Demo users loaded from `demo_data`:

- `admin@factflow.local`
- `analyst@factflow.local`
- `manager@factflow.local`

All seeded users use the password `factflow123`.

Docker also ensures a superuser exists for Django admin at `/django-admin/`:

- email: `admin@example.com`
- password: `admin12345`

You can override these defaults through `.env`:

- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

If demo fixture data already exists, bootstrap skips reloading it and only verifies the superuser.

## Render deploy

Render deployment can use the native Python environment with `gunicorn` and WhiteNoise. This project is prepared for that flow.

### Build and start commands

Build command:

```bash
./build.sh
```

Pre-deploy command:

```bash
poetry run python manage.py migrate
```

Start command:

```bash
poetry run gunicorn config.wsgi:application
```

### Production environment

Set these environment variables in Render:

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `SECRET_KEY=<long-random-secret>`
- `ALLOWED_HOSTS=<your-render-service>.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://<your-render-service>.onrender.com`
- `DATABASE_URL=<Supabase PostgreSQL connection string>`

Optional hardened production env vars:

- `SECURE_SSL_REDIRECT=True`
- `SECURE_HSTS_SECONDS=31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- `SECURE_HSTS_PRELOAD=True`

### Supabase PostgreSQL

For Render with Supabase PostgreSQL, use a server-side Postgres connection string with SSL enabled. A practical default is the Supabase session pooler string with `sslmode=require`.

Example format:

```text
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require
```

If you use a different Supabase host or port from the project dashboard, keep `sslmode=require` on the URL.

### Deployment checks

Run these before deploying:

```bash
poetry run python manage.py check --deploy
poetry run pytest -q
```
