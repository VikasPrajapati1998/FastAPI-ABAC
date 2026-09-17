"""Application entry point.

Run with:  uvicorn main:app --reload
Then open: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.routers import auth, documents, policies, users
from app.seed import seed_if_empty

app = FastAPI(
    title="ABAC Demo API",
    description="A minimal Attribute-Based Access Control system built with FastAPI + SQLite.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """Create tables and seed demo data on first run."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(policies.router)


@app.get("/", tags=["health"])
def health_check():
    """Simple liveness check."""
    return {"status": "ok", "docs": "/docs"}
