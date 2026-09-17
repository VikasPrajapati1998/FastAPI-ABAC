"""User profile and admin user-listing endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_my_profile(current_user: User = Depends(get_current_user)):
    """Return the logged-in user's own profile and attributes."""
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """List all users. Admin only (system administration, not an ABAC resource)."""
    return db.query(User).all()
