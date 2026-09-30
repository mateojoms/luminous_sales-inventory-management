# Stamp Stock Manager

A Django application for managing products, stock, sales, returns, suppliers, reports, audit history and user roles.

## Run locally

Use Python 3.12 (or another version supported by Django 5.2):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_sample
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The sample command creates local starter accounts (`owner` / `stamp1234` and `cashier` / `cashier1234`). It is disabled when `DEBUG=False`; change these demo passwords before using a local database with real data.

The `.env` file accepts `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`. Older `DJANGO_*` names are also accepted. Leave `DATABASE_URL` empty to use SQLite locally, or set it to a PostgreSQL connection URL for local PostgreSQL development.

Local development uses `db.sqlite3`. That file is intentionally ignored by Git so local business data is not uploaded.

## Deploy to Vercel

Vercel detects this project from `manage.py` and serves Django static files because `STATIC_ROOT` is configured. A PostgreSQL database is required for persistent hosted data; Vercel function storage is not a persistent database.

1. Push this repository to GitHub, then import it in Vercel.
2. Add a PostgreSQL database through a Vercel Marketplace provider and connect its `DATABASE_URL` to the project for Production and Preview environments as appropriate.
3. Set these Vercel environment variables:
   - `SECRET_KEY`: a unique, randomly generated secret.
   - `DEBUG`: `False`.
   - `DATABASE_URL`: supplied by the PostgreSQL integration.
   - `ALLOWED_HOSTS`: `.vercel.app` and any custom domain, comma-separated. Vercel's `VERCEL_URL` is included automatically.
   - `CSRF_TRUSTED_ORIGINS`: HTTPS origins for the Vercel domain and any custom domain, comma-separated. The current `VERCEL_URL` origin is included automatically.
4. Deploy. The Vercel build hook in `pyproject.toml` applies database migrations. Keep Preview and Production database URLs appropriately separated if you use preview deployments.
5. Run `python manage.py createsuperuser` with the production `DATABASE_URL` configured to create your first administrator. Do not run `seed_sample` on a live database unless you intend to create the sample accounts and data.

There is no `vercel.json` because Vercel detects `manage.py`; `pyproject.toml` selects this project's WSGI application and applies migrations during the build. `STATIC_ROOT` lets Vercel collect and serve static files. See [Vercel's Django deployment guide](https://vercel.com/docs/frameworks/full-stack/django).

The project currently has no user-uploaded media fields or local media handling. If uploads are added later, production files will need persistent object storage; Vercel's function filesystem is not persistent.

## GitHub upload

The `.gitignore` excludes local databases, credentials, virtual environments, generated static files and Vercel's local project metadata. Commit `.env.example`, but never commit `.env` or production secrets.

```powershell
git init
git add .
git commit -m "Prepare Django app for deployment"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

## Notes

- Stock sales snapshot item names and prices and save sales, sale items, stock movements and audit entries together.
- Custom stamp orders do not deduct stock.
- Returns restore stock and update the original sale totals.
- Deactivated products remain attached to historical sales.
- Administrator users can manage products, stock, suppliers and accounts. Sales users can record sales and returns and view reports.
