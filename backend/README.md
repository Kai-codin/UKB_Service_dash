# Command Dashboard (backend)

Run the FastAPI app and create the initial superuser.

Install dependencies (recommended in a venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a superuser:

```bash
python -m backend.app.cli --username admin --email admin@example.com --password secret
```

Run the app:

```bash
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000

Docker (development)

Build and run with docker-compose:

```bash
docker compose build
docker compose up -d
```

The service will be available at http://127.0.0.1:8000. The SQLite DB and logs are persisted under `backend/app.db` and `backend/logs/` respectively.
