# Todo App Backend (FastAPI)

This is a FastAPI backend providing CRUD APIs for a Todo application with SQLite persistence.

- Runs on port 3001 by default (`PORT` env var can override)
- SQLite file stored at `todo.db` in the repository (default) or path specified by `SQLITE_DB` environment variable
- CORS allows `http://localhost:3000` for the frontend

## Development

Install dependencies (already pinned in requirements.txt). To run locally:

```
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 3001
```

Or directly:
```
python src/api/main.py
```

OpenAPI docs available at `/docs`.

To regenerate `interfaces/openapi.json`:
```
python -m src.api.generate_openapi
```
