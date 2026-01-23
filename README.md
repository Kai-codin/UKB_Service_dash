# UKB Service Dashboard

This repository contains a Django-based admin dashboard for managing sites, commands, and logs as described in Plan.md.

Quick start

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the example env and edit if you want Postgres:

```bash
cp .env.example .env
# edit .env to set DATABASE_URL if you want Postgres
```

3. Run migrations and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser_custom --username=admin --email=admin@example.com --password=adminpass
python manage.py runserver
```

Files of interest
- `dashboard/` - main app with models, admin, and management commands
- `ukb_service_dash/` - Django project settings and URLs
