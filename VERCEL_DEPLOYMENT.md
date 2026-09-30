# Vercel deployment with Neon PostgreSQL

This existing Django project uses the `stamp_manager` package and `stamp_manager.wsgi:application`. Vercel detects Django from `manage.py`; `vercel.json` selects its Django framework support. The `pyproject.toml` Vercel build hook runs `python manage.py migrate --noinput` during deployment. Static source files are in `static/`, with `STATIC_ROOT=staticfiles/` for collection and Vercel CDN serving.

## A. Prepare the local project

From the project directory, install dependencies and make a local environment file:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For SQLite local development, edit `.env` and set `DEBUG=True`, set a private local `SECRET_KEY`, and leave `DATABASE_URL` empty. Then:

```powershell
python manage.py migrate
python manage.py runserver
```

The sample data command is for local development only; do not run it against production unless you intend to create its demo accounts and data.

## B. Create or connect the GitHub repository

Create an empty GitHub repository, then from this project directory:

```powershell
git add .
git commit -m "Prepare Django app for Vercel deployment"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

If a remote is already configured, inspect it with `git remote -v` and push to that remote instead of adding another. `.env` and SQLite database files are ignored; `.env.example` contains placeholders and is safe to commit. Check `git status` before pushing.

## C. Create a Neon PostgreSQL database

1. Create a Neon project and database in the Neon console.
2. Select the database and branch to use for this deployment.
3. In the connection details, choose the pooled connection option when available and copy the connection string.
4. Treat the copied URL as a password: do not paste it into source files, commits, screenshots, or chat.

Use separate Neon branches/databases for Preview and Production if preview deployments should not alter production data.

## D–F. Set and test `DATABASE_URL` locally

For an isolated PostgreSQL check, set the copied URL only in your local ignored `.env`:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

The project parses `DATABASE_URL` with `dj-database-url` and connects through `psycopg[binary]`. TLS is required automatically when `DEBUG=False`; Neon URLs can also explicitly include `sslmode=require`. Test the connection by running:

```powershell
python manage.py check
python manage.py migrate --plan
```

`migrate --plan` checks the connection and shows pending operations without changing the database. The real `migrate` command applies them. Do not set `DEBUG=False` without both a PostgreSQL `DATABASE_URL` and a `SECRET_KEY`.

## G–H. Connect GitHub to Vercel and configure variables

1. In Vercel, choose **Add New Project** and import the GitHub repository.
2. Keep the project root at the repository root. Vercel recognizes this Django project from `manage.py` and uses the `stamp_manager` WSGI application.
3. In Project Settings → Environment Variables, configure the following for Production (and Preview if you deploy previews):

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | A newly generated private Django secret. |
| `DEBUG` | `False` |
| `DATABASE_URL` | The Neon connection URL for the matching environment. |
| `ALLOWED_HOSTS` | Comma-separated hostnames, such as `your-project.vercel.app`; omit the scheme. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated full HTTPS origins, such as `https://your-project.vercel.app`. |

Include any custom production hostname in both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. Vercel's `VERCEL_URL` is added to hosts and as an HTTPS CSRF origin automatically. Explicit values are still recommended, especially for custom domains. The variables `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` are accepted as backwards-compatible aliases, but use the names above.

## I–K. Deploy, inspect logs, and test

Deploy from Vercel, or push a commit to the connected branch. The existing Vercel build hook applies migrations with `migrate --noinput`. Open the deployment's **Build Logs** and confirm the install/build completed and migrations ran. Then open the assigned deployment URL and test sign-in and the main inventory/sales pages. Create the initial administrator using a Vercel production shell if available, or run `createsuperuser` from a controlled environment configured with the same production `DATABASE_URL` and `SECRET_KEY`:

```powershell
python manage.py createsuperuser
```

Do not run a database reset or use demo seeding on the production database.

## Environment-specific behavior and Vercel limits

- `DEBUG=True` with no `DATABASE_URL` uses the ignored local `db.sqlite3` for development. When `DEBUG=False`, the app requires `DATABASE_URL` and rejects non-PostgreSQL database URLs; it never silently falls back to SQLite.
- Production `DEBUG=False` requires `SECRET_KEY`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. HTTPS proxy handling, SSL redirect, secure session/CSRF cookies and HSTS are enabled in production settings. Local HTTP development is unaffected when `DEBUG=True`.
- Vercel functions do not provide a traditional persistent server filesystem. Neon is the production database; local SQLite must not be used as production storage.
- This app currently has no upload fields or media handling. If uploads are introduced, local media files must not be relied on for permanent production storage; add a persistent media solution as a separate requirement.
- Static sources remain in `static/`, `STATIC_ROOT` is `staticfiles/`, and generated collected files are ignored by Git. Static collection and Vercel's Django asset handling must succeed as part of deployment.
- Production secrets belong in Vercel environment variables and ignored local `.env` files, never in source control.
- The configured Vercel build hook applies database migrations to the configured database. Review Vercel logs and migration plans before deploying schema changes.

## Credential rotation before first push

An earlier committed version of `.env.example` contained secret-looking Django and Neon values. Replacing the current file does not remove those values from Git history. Before pushing or deploying, rotate the Django signing key and the Neon database password if those earlier values are still active. Store the replacements only in local `.env` and Vercel environment variables.

## Troubleshooting

- **ImproperlyConfigured: Set SECRET_KEY**: add `SECRET_KEY` to the Vercel environment for the deployment target, then redeploy.
- **Missing/invalid `DATABASE_URL` or connection errors**: verify the correct Neon URL, password encoding, database/branch, network access, and TLS setting. Ensure `DATABASE_URL` is set for the same Vercel environment being deployed.
- **DisallowedHost**: add the requested hostname (without `https://`) to `ALLOWED_HOSTS` and redeploy.
- **CSRF origin failure**: add the complete origin including `https://` to `CSRF_TRUSTED_ORIGINS`.
- **Static assets missing**: inspect collectstatic/build output, confirm source files are in `static/`, and confirm `STATIC_ROOT` is configured in settings.
- **Migration failure**: inspect the build log and run `python manage.py migrate --plan` against the intended database before retrying. Do not delete or reset migrations.
- **Python package/import error**: confirm the package is in `requirements.txt`, then inspect the Vercel dependency installation log.
