# Stamp Stock Manager

A Django application for managing products, stock, sales, returns, suppliers, reports, audit history and user roles.

## Run locally

Use Python 3.12 (or another version supported by Django 5.2):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` for local development. Set `DEBUG=True`; leave `DATABASE_URL` blank to use the local SQLite database, or configure a PostgreSQL URL. Then run:

```powershell
python manage.py migrate
python manage.py seed_sample
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The sample command creates local starter accounts (`owner` / `stamp1234` and `cashier` / `cashier1234`). It is disabled when `DEBUG=False`; change these demo passwords before using a local database with real data.

## Deploy to Vercel with Neon

The Django project package is `stamp_manager`; Vercel serves its `stamp_manager.wsgi:application` entry point. Production uses Neon PostgreSQL through `DATABASE_URL`; production settings fail clearly if the URL or secret is missing. The included [`VERCEL_DEPLOYMENT.md`](VERCEL_DEPLOYMENT.md) has the full setup, environment variables, migration steps, and troubleshooting guide.

Configure `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` in Vercel. Set the production domain in the host and CSRF variables. Vercel's build hook in `pyproject.toml` applies migrations, and `STATIC_ROOT` is configured for collected static files. Vercel's Django support serves static assets through its CDN. Local SQLite and local media files are not persistent production storage.

The project has no user-uploaded media fields or local media handling.

## GitHub upload

The `.gitignore` excludes local databases, credentials, virtual environments, generated static files and Vercel's local project metadata. Commit `.env.example`, but never commit `.env` or production secrets.

```powershell
git add .
git commit -m "Prepare Django app for Vercel deployment"
git push
```

## Notes

- Stock sales snapshot item names and prices and save sales, sale items, stock movements and audit entries together.
- Custom stamp orders do not deduct stock.
- Returns restore stock and update the original sale totals.
- Deactivated products remain attached to historical sales.
- Administrator users can manage products, stock, suppliers and accounts. Sales users can record sales and returns and view reports.
