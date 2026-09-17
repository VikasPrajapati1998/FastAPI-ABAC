"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Role = Literal["admin", "user", "tester"]
Sensitivity = Literal["public", "internal", "confidential"]
Effect = Literal["allow", "deny"]
Action = Literal["create", "read", "update", "delete", "*"]


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    role: Role = "user"
    department: str = "general"
    clearance_level: int = Field(default=1, ge=1, le=3)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    department: str
    clearance_level: int
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Documents ----------

class DocumentCreate(BaseModel):
    title: str
    content: str
    department: str = "general"
    sensitivity: Sensitivity = "public"


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    department: Optional[str] = None
    sensitivity: Optional[Sensitivity] = None


class DocumentOut(BaseModel):
    id: int
    title: str
    content: str
    owner_id: int
    department: str
    sensitivity: Sensitivity
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Policies ----------

class PolicyCondition(BaseModel):
    attribute: str  # e.g. "subject.role", "resource.sensitivity"
    operator: Literal["eq", "ne", "gte", "lte", "gt", "lt", "in"]
    value: Any


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    effect: Effect
    action: Action
    resource_type: str = "document"
    conditions: List[PolicyCondition] = []
    priority: int = 100
    is_active: bool = True


class PolicyOut(BaseModel):
    id: int
    name: str
    description: str
    effect: Effect
    action: Action
    resource_type: str
    conditions: List[PolicyCondition]
    priority: int
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Access check (debug/learning endpoint) ----------

class AccessCheckRequest(BaseModel):
    document_id: int
    action: Literal["read", "update", "delete"]


class AccessCheckResponse(BaseModel):
    decision: Literal["allow", "deny"]
    matched_policy: Optional[str] = None
    reason: str
    subject_attributes: dict
    resource_attributes: dict
