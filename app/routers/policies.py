"""Admin-only CRUD for ABAC policies themselves.

Editing policies here directly changes how /documents behaves, since
app.abac.evaluate() reads these rows live on every request.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Policy, User
from app.schemas import PolicyCreate, PolicyOut

router = APIRouter(prefix="/policies", tags=["policies"])


def _to_policy_out(policy: Policy) -> PolicyOut:
    return PolicyOut(
        id=policy.id, name=policy.name, description=policy.description,
        effect=policy.effect, action=policy.action, resource_type=policy.resource_type,
        conditions=json.loads(policy.conditions), priority=policy.priority, is_active=policy.is_active,
    )


@router.get("", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    policies = db.query(Policy).order_by(Policy.priority.asc()).all()
    return [_to_policy_out(p) for p in policies]


@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if db.query(Policy).filter(Policy.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy name already exists")

    policy = Policy(
        name=payload.name, description=payload.description, effect=payload.effect,
        action=payload.action, resource_type=payload.resource_type,
        conditions=json.dumps([c.model_dump() for c in payload.conditions]),
        priority=payload.priority, is_active=payload.is_active,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _to_policy_out(policy)


@router.put("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: int, payload: PolicyCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    policy.name = payload.name
    policy.description = payload.description
    policy.effect = payload.effect
    policy.action = payload.action
    policy.resource_type = payload.resource_type
    policy.conditions = json.dumps([c.model_dump() for c in payload.conditions])
    policy.priority = payload.priority
    policy.is_active = payload.is_active
    db.commit()
    db.refresh(policy)
    return _to_policy_out(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(policy_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    db.delete(policy)
    db.commit()
