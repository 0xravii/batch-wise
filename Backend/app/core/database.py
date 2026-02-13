from sqlmodel import create_engine, Session, SQLModel
from typing import Generator
import os
from contextlib import contextmanager

# Get DB URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine with connection pool settings
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=5,  # Maximum number of connections to keep in pool
    max_overflow=10,  # Maximum overflow connections
    # pool_timeout=30,  # Timeout for getting connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    # connect_args={
    #     "timeout": 10  # Connection timeout in seconds
    # }
)

def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()
