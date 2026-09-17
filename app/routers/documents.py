"""Example protected resource: documents.

Every operation here is authorized purely through app.abac.evaluate() --
there is no hardcoded 'if role == admin' logic. Change the Policy rows
(via /policies) and behaviour changes without touching this file.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import abac
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, User
from app.schemas import AccessCheckRequest, AccessCheckResponse, DocumentCreate, DocumentOut, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_document_or_404(db: Session, document_id: int) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _authorize(db: Session, user: User, action: str, resource_attrs: dict) -> abac.Decision:
    subject_attrs = abac.user_to_subject_attributes(user)
    decision = abac.evaluate(db, subject_attrs, resource_attrs, action)
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)
    return decision


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Create a document owned by the current user, subject to ABAC policies."""
    # The document doesn't exist yet, so its resource attributes are derived
    # from the request itself, with the creator as the owner.
    resource_attrs = {
        "id": None,
        "owner_id": user.id,
        "department": payload.department,
        "sensitivity": payload.sensitivity,
    }
    _authorize(db, user, "create", resource_attrs)

    document = Document(
        title=payload.title, content=payload.content,
        owner_id=user.id, department=payload.department, sensitivity=payload.sensitivity,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List only the documents the current user is allowed to read (per ABAC)."""
    subject_attrs = abac.user_to_subject_attributes(user)
    visible = []
    for document in db.query(Document).all():
        resource_attrs = abac.document_to_resource_attributes(document)
        if abac.evaluate(db, subject_attrs, resource_attrs, "read").allowed:
            visible.append(document)
    return visible


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_document_or_404(db, document_id)
    resource_attrs = abac.document_to_resource_attributes(document)
    _authorize(db, user, "read", resource_attrs)
    return document


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = _get_document_or_404(db, document_id)
    resource_attrs = abac.document_to_resource_attributes(document)
    _authorize(db, user, "update", resource_attrs)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_document_or_404(db, document_id)
    resource_attrs = abac.document_to_resource_attributes(document)
    _authorize(db, user, "delete", resource_attrs)

    db.delete(document)
    db.commit()


@router.post("/access-check", response_model=AccessCheckResponse)
def access_check(
    payload: AccessCheckRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Learning aid: explain what the ABAC engine would decide for a given
    document/action, without actually performing the action."""
    document = _get_document_or_404(db, payload.document_id)
    subject_attrs = abac.user_to_subject_attributes(user)
    resource_attrs = abac.document_to_resource_attributes(document)
    decision = abac.evaluate(db, subject_attrs, resource_attrs, payload.action)
    return AccessCheckResponse(
        decision="allow" if decision.allowed else "deny",
        matched_policy=decision.matched_policy,
        reason=decision.reason,
        subject_attributes=subject_attrs,
        resource_attributes=resource_attrs,
    )
