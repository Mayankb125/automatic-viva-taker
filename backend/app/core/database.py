"""
database.py — SQLAlchemy Database Setup
=========================================
This file sets up everything needed to interact with the SQLite database:

  engine        — The connection to the .db file. SQLAlchemy uses this
                  to send SQL commands to SQLite.

  SessionLocal  — A factory that creates new database sessions.
                  Each API request gets its own session (opened and closed
                  per-request via the get_db() dependency).

  Base          — The base class that all SQLAlchemy model classes must
                  inherit from. Inheriting from Base registers the model's
                  table definition so create_all() can create the table.

  get_db()      — A FastAPI dependency function. Inject it into any route
                  function to get a database session that auto-closes after
                  the request finishes, even if an error occurs.

Usage in route files:
    from app.core.database import get_db
    from fastapi import Depends
    from sqlalchemy.orm import Session

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        result = db.query(SomeModel).all()
        return result
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

# Create the SQLAlchemy engine that connects to the database.
# check_same_thread=False is a SQLite-only argument required when FastAPI
# handles requests across multiple threads. It must not be passed for other
# backends (PostgreSQL, MySQL, etc.), so we detect the driver first.
_url = make_url(DATABASE_URL)
if _url.drivername.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

# SessionLocal is a session factory (not a session itself).
# autocommit=False — changes must be explicitly committed with db.commit()
# autoflush=False  — SQLAlchemy won't auto-push pending changes before queries
# bind=engine      — link sessions created from this factory to our engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models. Every model file (student.py, session.py, etc.)
# imports Base from here and uses it as the parent class, e.g.:
#   class Student(Base):
#       __tablename__ = "students"
#       ...
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session for one request.

    Opens a new session at the start of the request and guarantees it is
    closed when the request finishes (via the finally block), even if an
    exception is raised inside the route handler.

    Inject into any route like this:
        def my_route(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db       # FastAPI injects this db object into the route function
    finally:
        db.close()     # Always close, whether the request succeeded or failed
