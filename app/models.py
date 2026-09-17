"""SQLAlchemy ORM models.

Three tables demonstrate ABAC end to end:

- ``User``     -> the SUBJECT. Carries attributes (role, department, clearance_level)
                  that policies read to make decisions.
- ``Document`` -> the RESOURCE. Carries attributes (department, sensitivity, owner)
                  that policies compare against the subject's attributes.
- ``Policy``   -> the RULE. A row is one ABAC policy: "allow/deny <action> on
                  <resource_type> when <conditions>". Conditions compare subject
                  and resource attributes at request time -- nothing is hardcoded.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class User(Base):
    """A registered account. Its columns are the SUBJECT attributes for ABAC."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)

    # Subject attributes used by policy conditions (e.g. "subject.role").
    role = Column(String, nullable=False, default="user")  # admin | user | tester
    department = Column(String, nullable=False, default="general")
    clearance_level = Column(Integer, nullable=False, default=1)  # 1 (low) - 3 (high)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    """An example protected resource. Its columns are the RESOURCE attributes."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department = Column(String, nullable=False, default="general")
    # Resource attribute used by policy conditions (e.g. "resource.sensitivity").
    sensitivity = Column(String, nullable=False, default="public")  # public | internal | confidential

    created_at = Column(DateTime, default=datetime.utcnow)


class Policy(Base):
    """One ABAC rule.

    ``conditions`` is a JSON-encoded list of clauses, all ANDed together:
        [{"attribute": "subject.role", "operator": "eq", "value": "admin"}, ...]

    Supported attribute paths: "subject.<field>", "resource.<field>", "action".
    Supported operators: eq, ne, gte, lte, gt, lt, in.
    """

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    effect = Column(String, nullable=False)  # allow | deny
    action = Column(String, nullable=False)  # create | read | update | delete | * (any)
    resource_type = Column(String, nullable=False, default="document")
    conditions = Column(Text, nullable=False, default="[]")  # JSON string, see class docstring
    priority = Column(Integer, nullable=False, default=100)  # lower number = evaluated first
    is_active = Column(Boolean, default=True)
