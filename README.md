# ABAC Demo — FastAPI + SQLite

A small, complete Attribute-Based Access Control (ABAC) system, built to be
read and understood, not just run. See `TECHNICAL-DOCUMENT.md` for how the
policy engine actually works.

## Quick start

```cmd
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open Swagger UI: http://127.0.0.1:8000/docs

The SQLite database (`abac.db`) and demo data are created automatically on
first run. See `.claude/SETUP.md` for seeded demo accounts and reset steps.

## What's in the system

- **Auth**: register (`/auth/register`) and login (`/auth/login`) with
  email + password. Login returns a JWT — click "Authorize" in Swagger and
  paste your email/password there (it uses the standard OAuth2 password form).
- **Roles**: exactly three — `admin`, `user`, `tester`. Role is just one
  attribute among several (with `department` and `clearance_level`) that
  ABAC policies can check.
- **Example resource**: `documents`, each with `department`, `sensitivity`
  (`public` / `internal` / `confidential`), and an owner.
- **Policies**: ABAC rules stored in the database (`/policies`, admin only),
  evaluated live on every document request. Change a policy, and access
  behavior changes immediately — no code changes needed.
- **`/documents/access-check`**: a "dry run" endpoint that tells you exactly
  which policy would allow or deny a given action, and why. Use this to
  understand decisions while testing in Swagger.

## Typical test flow in Swagger

1. `POST /auth/login` as `admin@example.com` / `admin123`, click **Authorize**.
2. `GET /policies` to see the seeded ABAC rules.
3. `GET /documents` to see documents filtered by what the current user can read.
4. `POST /documents/access-check` with a document id + action to see the
   engine's reasoning.
5. Log in as `user@example.com` / `user123` (a different department/clearance)
   and repeat — the same endpoints now return different results, entirely
   driven by attribute comparisons, not hardcoded role checks.

See `.claude/SETUP.md` for the full list of seeded accounts.
