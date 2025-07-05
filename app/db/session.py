from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import OperationalError
import os
from app.core.config import settings
import logging
from sqlalchemy.pool import QueuePool

import app.models

logger = logging.getLogger(__name__)

logger.info("Creating database engine...")
# Convert postgresql:// to postgresql+psycopg:// for psycopg v3
database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
engine = create_engine(
    database_url,
    echo=True,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)
logger.info("Database engine created successfully")

def get_session():
    logger.debug("Creating new database session...")
    session = Session(engine)
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        session.rollback()
        raise
    finally:
        logger.debug("Closing database session...")
        session.close()

def create_db_and_tables():
    try:
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("Database and tables created successfully")
    except OperationalError as e:
        logger.error(f"Error creating database and tables: {str(e)}")
        raise