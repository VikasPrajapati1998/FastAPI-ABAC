# API Test Payloads (for Swagger UI)

Copy-paste these directly into `/docs`. Suggested order: run **Auth** first,
click **Authorize** with the login response, then test the rest.

Seeded accounts are listed in `.claude/SETUP.md` (e.g. `admin@example.com` /
`admin123`).

---

## Auth

### POST /auth/register
```json
{
  "email": "newuser@example.com",
  "password": "newuser123",
  "full_name": "New Test User",
  "role": "user",
  "department": "sales",
  "clearance_level": 1
}
```

Try also with `"role": "tester"` and `"role": "admin"` to create accounts for
each of the three roles.

### POST /auth/login
This endpoint takes a **form**, not JSON (Swagger renders it as separate
fields, not a "Request body" box). Fill in:
- `username`: `admin@example.com`
- `password`: `admin123`
- leave `client_id`, `client_secret`, `scope`, `grant_type` empty

Response gives `access_token` — copy it, click **Authorize** (top right of
Swagger page) and paste it into the `value` field (just the token, Swagger
adds the `Bearer ` prefix itself).

Other seeded logins to try (same form, different values):
- `user@example.com` / `user123`
- `user2@example.com` / `user123`
- `tester@example.com` / `tester123`

---

## Users

### GET /users/me
No body. Requires Authorize to be set. Returns the logged-in user's attributes.

### GET /users
No body. Admin only — try as admin (succeeds) then as `user@example.com` (expect `403`).

---

## Documents

### POST /documents
```json
{
  "title": "My Test Document",
  "content": "Some example content.",
  "department": "sales",
  "sensitivity": "internal"
}
```

Try `"sensitivity": "public"`, `"internal"`, and `"confidential"` as
different users to see ABAC in action.

### GET /documents
No body. Returns only documents the logged-in user is allowed to read.

### GET /documents/{document_id}
No body. Path param, e.g. `document_id = 1`. Seeded documents are ids `1`–`3`
(see `.claude/SETUP.md` / `app/seed.py`):
- `1` = "Public Onboarding Guide" (public, sales, owned by Bob)
- `2` = "Sales Playbook" (internal, sales, owned by Bob)
- `3` = "Finance Report Q3" (confidential, finance, owned by Carol)

### PUT /documents/{document_id}
Path param `document_id`, body (all fields optional — only send what you
want to change):
```json
{
  "title": "Updated Title",
  "content": "Updated content.",
  "department": "sales",
  "sensitivity": "internal"
}
```

### DELETE /documents/{document_id}
No body. Path param only, e.g. `document_id = 1`.

### POST /documents/access-check
```json
{
  "document_id": 3,
  "action": "read"
}
```
`action` must be `"read"`, `"update"`, or `"delete"`. Use this to see
exactly which policy fired and why, without actually performing the action.
Try `document_id: 3` (confidential, owned by Carol) logged in as
`user@example.com` (clearance 1, department sales) to see a deny, then as
`admin@example.com` to see an allow.

---

## Policies

All admin only.

### GET /policies
No body. Lists all seeded + custom policies.

### POST /policies
Example — allow testers to also read confidential documents:
```json
{
  "name": "tester-read-confidential",
  "description": "Testers may read confidential documents too.",
  "effect": "allow",
  "action": "read",
  "resource_type": "document",
  "conditions": [
    {"attribute": "subject.role", "operator": "eq", "value": "tester"},
    {"attribute": "resource.sensitivity", "operator": "eq", "value": "confidential"}
  ],
  "priority": 45,
  "is_active": true
}
```

Another example — deny all deletes for non-admins:
```json
{
  "name": "deny-delete-for-non-admins",
  "description": "Only admins may delete documents.",
  "effect": "deny",
  "action": "delete",
  "resource_type": "document",
  "conditions": [
    {"attribute": "subject.role", "operator": "ne", "value": "admin"}
  ],
  "priority": 5,
  "is_active": true
}
```

Cross-attribute example — allow reading documents in a department only if
your clearance is at least 2:
```json
{
  "name": "dept-read-min-clearance",
  "description": "Department-matched reads require clearance >= 2.",
  "effect": "allow",
  "action": "read",
  "resource_type": "document",
  "conditions": [
    {"attribute": "subject.department", "operator": "eq", "value": "resource.department"},
    {"attribute": "subject.clearance_level", "operator": "gte", "value": 2}
  ],
  "priority": 42,
  "is_active": true
}
```

Valid `operator` values: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`.
For `in`, `value` must be a list, e.g. `["public", "internal"]`.
For cross-attribute comparisons, `value` can be a string like
`"resource.owner_id"` or `"subject.department"` instead of a literal.

### PUT /policies/{policy_id}
Path param `policy_id` (e.g. `1`). Body is the full `PolicyCreate` shape
(same as POST) — all fields are replaced, not merged:
```json
{
  "name": "same-department-read",
  "description": "Users may read public/internal documents from their own department.",
  "effect": "allow",
  "action": "read",
  "resource_type": "document",
  "conditions": [
    {"attribute": "subject.department", "operator": "eq", "value": "resource.department"},
    {"attribute": "resource.sensitivity", "operator": "in", "value": ["public", "internal"]}
  ],
  "priority": 40,
  "is_active": true
}
```

### DELETE /policies/{policy_id}
No body. Path param only, e.g. `policy_id = 6` (delete a custom policy you
created — deleting seeded policies changes default behavior).

---

## Suggested experiment sequence

1. Login as `user@example.com`, `GET /documents` — see only doc `1` and `2`.
2. `POST /documents/access-check` for `document_id: 3`, `action: "read"` — see deny reason (confidential + low clearance).
3. Login as `admin@example.com`, `POST /policies` with the "tester-read-confidential" example above.
4. Login as `tester@example.com`, `POST /documents/access-check` for `document_id: 3`, `action: "read"` — now allowed, and `matched_policy` shows your new rule.
5. `DELETE /policies/{policy_id}` (as admin) to remove it and confirm tester access reverts to deny.
