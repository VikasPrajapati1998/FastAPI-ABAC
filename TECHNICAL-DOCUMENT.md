# Technical Document — ABAC Engine

This explains *how* the Attribute-Based Access Control system makes
decisions, so you can understand the concept, not just the code.

## 1. What ABAC is, concretely

In Role-Based Access Control (RBAC), you'd write something like:

```python
if user.role == "admin":
    allow()
```

Access depends only on role. ABAC instead makes decisions from **attributes**
of three things:

- **Subject** — who is asking (`role`, `department`, `clearance_level`, `id`)
- **Resource** — what they're asking about (`department`, `sensitivity`, `owner_id`)
- **Action** — what they want to do (`create`, `read`, `update`, `delete`)

A **policy** is a rule that compares these attributes and produces `allow`
or `deny`. Nothing is hardcoded to a role — a policy could just as easily
key off department, clearance, or ownership, and multiple attributes can be
combined with AND.

## 2. Where each piece lives

| Concept | Table / File |
|---|---|
| Subject attributes | `User` model (`app/models.py`) — `role`, `department`, `clearance_level` |
| Resource attributes | `Document` model — `department`, `sensitivity`, `owner_id` |
| Policy rules | `Policy` model — `effect`, `action`, `conditions` (JSON), `priority` |
| Decision logic | `app/abac.py::evaluate()` |

## 3. Anatomy of a policy

A `Policy` row looks like this conceptually:

```json
{
  "name": "same-department-read",
  "effect": "allow",
  "action": "read",
  "resource_type": "document",
  "priority": 40,
  "conditions": [
    {"attribute": "subject.department", "operator": "eq", "value": "resource.department"},
    {"attribute": "resource.sensitivity", "operator": "in", "value": ["public", "internal"]}
  ]
}
```

- `attribute` — a path into the subject or resource dict (`subject.<field>`,
  `resource.<field>`), or the literal string `"action"`.
- `operator` — one of `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`.
- `value` — either a literal (e.g. `"confidential"`, `3`, `["public","internal"]`)
  or, if it's a string shaped like `subject.x` / `resource.x`, it is resolved
  dynamically too — that's what lets a policy compare two attributes to each
  other (e.g. `subject.id == resource.owner_id` to express "you own this").

All conditions in one policy are ANDed. To express OR, write two separate
policies with the same effect/action.

## 4. Decision algorithm (`abac.evaluate`)

```
1. Load active policies where resource_type matches
   and action matches (policy action == request action, or policy action == "*")
2. Sort by priority ascending
3. For each policy, check whether ALL of its conditions hold
   -> collect the list of "matched" policies
4. If any matched policy has effect="deny" -> DENY (deny always wins)
5. Else if any matched policy has effect="allow" -> ALLOW
6. Else -> DENY (default-deny: no rule said yes)
```

This is a standard, simple ABAC combining algorithm: **deny-overrides,
default-deny**. It means:
- You can never accidentally allow something by forgetting a deny rule —
  the safe default is always "no access."
- A deny policy is a hard stop, regardless of what any allow policy says.

## 5. Seeded example policies and what they teach

| Policy | Effect | Teaches |
|---|---|---|
| `admin-full-access` | allow `*` if `subject.role == admin` | A role-based rule is just a special case of ABAC — one attribute, one condition. |
| `owner-full-access` | allow `*` if `subject.id == resource.owner_id` | Cross-attribute comparison — ownership, not role, grants access. |
| `deny-confidential-without-clearance` | deny `*` if `resource.sensitivity == confidential AND subject.clearance_level < 3` | Deny-overrides — this can revoke access an allow rule would otherwise grant (except the two allows above still win against it only if evaluated with lower priority number... see note below). |
| `same-department-read` | allow `read` if `subject.department == resource.department AND resource.sensitivity in [public, internal]` | Combining two attributes with AND; environment-like scoping by department. |
| `tester-read-all-non-confidential` | allow `read` if `subject.role == tester AND sensitivity in [public, internal]` | A role can still be one attribute among several. |

**Note on priority vs. deny-overrides:** priority only decides which
*matching* policies are collected before the deny/allow-overrides step —
deny still wins over allow regardless of relative priority once both are in
the matched set. Priority mainly matters for readability/ordering and for
resolving ties among same-effect policies (the first match found is
reported as "the" matched policy in the response). Try lowering
`admin-full-access`'s priority number or editing `deny-confidential...` via
`/policies` to see this interact live.

## 6. Extending it

- **New resource type**: add a model + router, and use
  `abac.evaluate(db, subject, resource, action, resource_type="your_type")`.
  Policies are already generic over `resource_type`.
- **New subject/resource attribute**: add a column to `User`/`Document`,
  include it in `user_to_subject_attributes()` / `document_to_resource_attributes()`,
  then reference it from a policy's `conditions` — no engine code changes needed.
- **New operator**: add an entry to `_OPERATORS` in `app/abac.py`.

## 7. Auth summary

- Passwords are hashed directly with the `bcrypt` library.
- Login issues a JWT (`python-jose`, HS256) containing the user's email as
  `sub`, expiring after 60 minutes (`app/security.py`).
- `get_current_user` (dependency) decodes the token on every protected
  request and loads the corresponding `User` row — this becomes the ABAC
  subject.
