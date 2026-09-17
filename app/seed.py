"""Seed the database with example users, documents and ABAC policies.

Runs once at startup, only if the ``users`` table is empty, so it never
overwrites data you create later while testing in Swagger.
"""

import json

from sqlalchemy.orm import Session

from app.models import Document, Policy, User
from app.security import hash_password


def seed_if_empty(db: Session) -> None:
    if db.query(User).count() > 0:
        return  # already seeded

    users = [
        User(email="admin@example.com", hashed_password=hash_password("admin123"),
             full_name="Alice Admin", role="admin", department="it", clearance_level=3),
        User(email="user@example.com", hashed_password=hash_password("user123"),
             full_name="Bob User", role="user", department="sales", clearance_level=1),
        User(email="user2@example.com", hashed_password=hash_password("user123"),
             full_name="Carol User", role="user", department="finance", clearance_level=2),
        User(email="tester@example.com", hashed_password=hash_password("tester123"),
             full_name="Tom Tester", role="tester", department="qa", clearance_level=2),
    ]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)

    bob, carol = users[1], users[2]
    documents = [
        Document(title="Public Onboarding Guide", content="Welcome to the company!",
                 owner_id=bob.id, department="sales", sensitivity="public"),
        Document(title="Sales Playbook", content="Internal sales tactics.",
                 owner_id=bob.id, department="sales", sensitivity="internal"),
        Document(title="Finance Report Q3", content="Confidential financial figures.",
                 owner_id=carol.id, department="finance", sensitivity="confidential"),
    ]
    db.add_all(documents)

    policies = [
        Policy(
            name="admin-full-access",
            description="Admins can perform any action on any document.",
            effect="allow", action="*", resource_type="document", priority=10,
            conditions=json.dumps([{"attribute": "subject.role", "operator": "eq", "value": "admin"}]),
        ),
        Policy(
            name="owner-full-access",
            description="A user can create/read/update/delete their own documents.",
            effect="allow", action="*", resource_type="document", priority=20,
            conditions=json.dumps([{"attribute": "subject.id", "operator": "eq", "value": "resource.owner_id"}]),
        ),
        Policy(
            name="deny-confidential-without-clearance",
            description="Deny access to confidential documents for clearance level < 3.",
            effect="deny", action="*", resource_type="document", priority=30,
            conditions=json.dumps([
                {"attribute": "resource.sensitivity", "operator": "eq", "value": "confidential"},
                {"attribute": "subject.clearance_level", "operator": "lt", "value": 3},
            ]),
        ),
        Policy(
            name="same-department-read",
            description="Users may read (not modify) internal/public documents from their own department.",
            effect="allow", action="read", resource_type="document", priority=40,
            conditions=json.dumps([
                {"attribute": "subject.department", "operator": "eq", "value": "resource.department"},
                {"attribute": "resource.sensitivity", "operator": "in", "value": ["public", "internal"]},
            ]),
        ),
        Policy(
            name="tester-read-all-non-confidential",
            description="Testers can read any public/internal document regardless of department.",
            effect="allow", action="read", resource_type="document", priority=50,
            conditions=json.dumps([
                {"attribute": "subject.role", "operator": "eq", "value": "tester"},
                {"attribute": "resource.sensitivity", "operator": "in", "value": ["public", "internal"]},
            ]),
        ),
    ]
    db.add_all(policies)
    db.commit()
