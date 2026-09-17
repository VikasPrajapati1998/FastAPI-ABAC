# Setup

## Requirements
- Python 3.9+ (developed/tested against 3.12)
- pip

## Install

```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

(A `venv\` already exists in the project root; activate it, don't recreate it.)

## Environment variables
None required. `app/security.py` uses a fixed demo `SECRET_KEY` constant
(explicitly not production-safe — see `.claude/CLAUDE.md`).

## Run

```cmd
uvicorn main:app --reload
```

Then open Swagger UI at: http://127.0.0.1:8000/docs

## Database
SQLite file `abac.db` is created automatically on first startup in the
project root, and seeded with demo users/documents/policies if empty.
Delete `abac.db` and restart the app to reset to a fresh seeded state.

## Seeded demo accounts
| Email | Password | Role | Department | Clearance |
|---|---|---|---|---|
| admin@example.com | admin123 | admin | it | 3 |
| user@example.com | user123 | user | sales | 1 |
| user2@example.com | user123 | user | finance | 2 |
| tester@example.com | tester123 | tester | qa | 2 |

## Build / deployment
None — this is a local learning project, run directly with uvicorn.
