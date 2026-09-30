# Employee Lending System

Django REST API for employee management, contributions, loans, and loan repayments.

## Requirements

- Python 3.12 (the project has been verified with Python 3.12)
- PostgreSQL server
- Git

## First-time setup (Linux/macOS)

Run these commands from the repository root. The virtual environment is local to your machine and is intentionally excluded from Git.

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Create a local PostgreSQL database

Create a PostgreSQL role and database using your local PostgreSQL administrator account. Substitute your own database password; do not commit it to Git.

```sql
CREATE USER lending_user WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE lending_db OWNER lending_user;
```

For example, run those SQL statements in `psql` as a PostgreSQL administrator. If you already have a development database/user, use those instead.

### Configure the application environment

The settings read database configuration from environment variables. Set them in the shell before running Django. `ADMIN_PASSWORD` is used only when the post-migration bootstrap creates the initial `admin@hassy.in` account; choose a strong local development password.

```bash
export DB_NAME='lending_db'
export DB_USER='lending_user'
export DB_PASSWORD='choose-a-local-password'
export DB_HOST='localhost'
export DB_PORT='5432'
export ADMIN_PASSWORD='choose-a-strong-admin-password'
```

These exports apply to the current shell. Set them through your local secret/environment manager for persistence; do not add real credentials to source control. The current settings contain development-only defaults and a development secret key. Do not deploy with those defaults; production settings must source secrets securely and set `DEBUG=False` and appropriate `ALLOWED_HOSTS`.

### Initialize and start

With the virtual environment activated and database variables set:

```bash
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

The development server is available at `http://127.0.0.1:8000/`. The initial administrator is `admin@hassy.in`; use the `ADMIN_PASSWORD` value set before the first migration/bootstrap. If the admin account already exists with an unusable password, setting `ADMIN_PASSWORD` later does not reset it automatically—use the project's approved password-reset/admin process.

## Running again later

```bash
cd /path/to/practice
source venv/bin/activate
# Re-export DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, and ADMIN_PASSWORD
python manage.py runserver
```

Use `python manage.py migrate` after pulling changes that include new migrations.

## Main API routes

- Employee/authentication APIs: `/api/auth/`, `/api/employees/`
- Contributions: `/api/contributions/`
- Loans and loan schedules: `/api/loans/`
- Repayments: `/api/repayments/`

Protected endpoints use JWT access tokens in the `Authorization: Bearer <access-token>` header. See [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md) for workflows, rules, and API details, and [docs/ERD.md](docs/ERD.md) for current and planned schema.

## Git and local files

The repository `.gitignore` excludes the `venv/` environment, Python caches, local environment files/secrets, SQLite databases, logs, generated media/static files, test/coverage output, build artifacts, and common editor/OS files. Keep `requirements.txt`, migrations, source code, and documentation under version control. Never commit `.env` secrets or local database files.
