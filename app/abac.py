"""The ABAC policy engine.

This is the heart of the system. Access decisions are NOT hardcoded
if/else role checks -- they are computed by evaluating ``Policy`` rows
stored in the database against the current subject, resource and action.

Decision algorithm (a common, simple ABAC combining rule):
    1. Load all active policies whose ``resource_type`` and ``action``
       match the request (an action of "*" on a policy matches any action).
    2. Sort by ``priority`` ascending (lower number = evaluated first).
    3. Evaluate each policy's conditions against the subject/resource
       attributes. All conditions in a policy must hold (AND).
    4. The first matching "deny" policy wins immediately (deny overrides).
    5. Otherwise, the first matching "allow" policy wins.
    6. If nothing matches, the default decision is "deny" (default-deny,
       the standard secure-by-default ABAC posture).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Policy

_OPERATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "in": lambda a, b: a in b,
}


@dataclass
class Decision:
    """Result of an access-control check."""

    allowed: bool
    matched_policy: Optional[str] = None
    reason: str = ""
    subject_attributes: dict = field(default_factory=dict)
    resource_attributes: dict = field(default_factory=dict)


def _resolve_attribute(path: str, subject: dict, resource: dict, action: str) -> Any:
    """Resolve an attribute path like 'subject.role' or 'resource.sensitivity'."""
    if path == "action":
        return action
    scope, _, field_name = path.partition(".")
    if scope == "subject":
        return subject.get(field_name)
    if scope == "resource":
        return resource.get(field_name)
    raise ValueError(f"Unknown attribute scope in '{path}'")


def _resolve_value(value: Any, subject: dict, resource: dict, action: str) -> Any:
    """Resolve a condition's ``value``.

    If it is a string that looks like an attribute path ("subject.x" /
    "resource.x"), resolve it dynamically so policies can compare two
    attributes against each other (e.g. subject.id == resource.owner_id).
    Otherwise it is used as a literal constant.
    """
    if isinstance(value, str) and (value.startswith("subject.") or value.startswith("resource.")):
        return _resolve_attribute(value, subject, resource, action)
    return value


def _conditions_match(conditions: list[dict], subject: dict, resource: dict, action: str) -> bool:
    """Return True if every condition in the policy holds (AND semantics)."""
    for condition in conditions:
        actual = _resolve_attribute(condition["attribute"], subject, resource, action)
        expected = _resolve_value(condition["value"], subject, resource, action)
        operator = _OPERATORS[condition["operator"]]
        if not operator(actual, expected):
            return False
    return True


def evaluate(
    db: Session,
    subject: dict,
    resource: dict,
    action: str,
    resource_type: str = "document",
) -> Decision:
    """Evaluate all matching active policies and return the final decision.

    ``subject`` and ``resource`` are plain attribute dictionaries, e.g.
    ``{"role": "user", "department": "sales", "id": 3}``.
    """
    policies = (
        db.query(Policy)
        .filter(Policy.resource_type == resource_type, Policy.is_active.is_(True))
        .order_by(Policy.priority.asc())
        .all()
    )

    matches = []
    for policy in policies:
        if policy.action not in (action, "*"):
            continue
        conditions = json.loads(policy.conditions)
        if _conditions_match(conditions, subject, resource, action):
            matches.append(policy)

    # Deny overrides: any matching deny policy wins outright.
    for policy in matches:
        if policy.effect == "deny":
            return Decision(
                allowed=False,
                matched_policy=policy.name,
                reason=f"Denied by policy '{policy.name}': {policy.description}",
                subject_attributes=subject,
                resource_attributes=resource,
            )

    # Otherwise the first matching allow policy (lowest priority number) wins.
    for policy in matches:
        if policy.effect == "allow":
            return Decision(
                allowed=True,
                matched_policy=policy.name,
                reason=f"Allowed by policy '{policy.name}': {policy.description}",
                subject_attributes=subject,
                resource_attributes=resource,
            )

    # Default-deny: no policy explicitly allowed the request.
    return Decision(
        allowed=False,
        matched_policy=None,
        reason="No matching allow policy found (default-deny).",
        subject_attributes=subject,
        resource_attributes=resource,
    )


def user_to_subject_attributes(user) -> dict:
    """Build the subject attribute dict used by policies from a User row."""
    return {
        "id": user.id,
        "role": user.role,
        "department": user.department,
        "clearance_level": user.clearance_level,
    }


def document_to_resource_attributes(document) -> dict:
    """Build the resource attribute dict used by policies from a Document row."""
    return {
        "id": document.id,
        "owner_id": document.owner_id,
        "department": document.department,
        "sensitivity": document.sensitivity,
    }
