# Project: ABAC Demo (FastAPI + SQLite)

## Purpose
Minimal, educational Attribute-Based Access Control (ABAC) system. Goal is
clarity for learning ABAC concepts, not production hardening.

## Architecture decisions
- **Policies are data, not code.** Access rules live in the `policies` table
  and are evaluated at request time by `app/abac.py::evaluate()`. Route
  handlers never contain `if role == "admin"` style checks for resource
  access — only `require_admin` (a plain role gate) is used, and only for
  the policy-management endpoints themselves, since editing policies is a
  system-administration action, not a resource access decision.
- **Default-deny.** If no policy matches, access is denied. Deny policies
  always override allow policies.
- **Roles are just one attribute among several.** `role`, `department`, and
  `clearance_level` are all ordinary subject attributes. This is what makes
  it ABAC rather than RBAC — nothing is role-only.
- SQLite via SQLAlchemy, single file `abac.db`, created + seeded automatically
  on app startup (see `app/seed.py`). Seeding only runs if `users` table is empty.
- JWT auth (`python-jose`) with a fixed demo secret in `app/security.py` —
  acceptable for a local learning project only.

## Conventions
- One router per resource under `app/routers/`.
- Pydantic schemas in `app/schemas.py`; SQLAlchemy models in `app/models.py`.
- Keep code small — this project intentionally favors compactness and
  readability over extensibility.

## Do not
- Do not add production-hardening features (rate limiting, refresh tokens,
  password reset flows, etc.) unless explicitly asked — out of scope for a
  learning project.
