# Architecture

```text
ABAC/
├── main.py                 # FastAPI app instance, startup (create tables + seed), router registration
├── requirements.txt        # Python dependencies
├── abac.db                 # SQLite database file (auto-created on first run)
├── README.md                # User-facing usage docs
├── TECHNICAL-DOCUMENT.md    # ABAC design/internals documentation
│
├── app/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy engine, SessionLocal, Base, get_db() dependency
│   ├── models.py             # ORM models: User, Document, Policy
│   ├── schemas.py            # Pydantic request/response models
│   ├── security.py           # Password hashing (bcrypt) + JWT create/decode
│   ├── dependencies.py       # get_current_user, require_admin FastAPI dependencies
│   ├── abac.py                # THE POLICY ENGINE: evaluate() decides allow/deny
│   ├── seed.py                # Seeds demo users, documents, and policies on first run
│   │
│   └── routers/
│       ├── __init__.py
│       ├── auth.py            # POST /auth/register, POST /auth/login
│       ├── users.py            # GET /users/me, GET /users (admin only)
│       ├── documents.py        # CRUD /documents + POST /documents/access-check (ABAC-protected)
│       └── policies.py         # CRUD /policies (admin only) — edit ABAC rules at runtime
│
└── .claude/
    ├── CLAUDE.md              # Project conventions and architecture decisions
    ├── ARCHITECTURE.md        # This file
    └── .claudeignore          # Paths excluded from Claude's context
```

## Module relationships

```
main.py
  ├── includes routers: auth, users, documents, policies
  └── on startup: Base.metadata.create_all() + seed.seed_if_empty()

routers/documents.py
  ├── depends on dependencies.get_current_user  (who is asking)
  └── calls abac.evaluate(db, subject_attrs, resource_attrs, action)  (may they do this)

abac.py
  └── reads Policy rows from the database (via database.get_db session)

routers/policies.py
  ├── depends on dependencies.require_admin
  └── writes Policy rows that abac.evaluate() reads
```

## Entry point
`main.py` — run with `uvicorn main:app --reload`, then open `/docs`.

## Data flow for an access decision
1. Client calls e.g. `GET /documents/3` with a Bearer JWT.
2. `get_current_user` resolves the JWT to a `User` row (the SUBJECT).
3. The route loads the `Document` row (the RESOURCE).
4. `abac.user_to_subject_attributes()` / `document_to_resource_attributes()`
   turn both into plain attribute dicts.
5. `abac.evaluate()` loads active `Policy` rows for `resource_type="document"`
   and `action` matching (or `"*"`), checks each policy's JSON conditions
   against the dicts, and returns the first matching deny, else first
   matching allow, else default-deny.
6. The route raises `403` on deny, or proceeds and returns the resource.
