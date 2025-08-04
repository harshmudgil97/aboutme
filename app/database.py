from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create synchronous engine for regular operations
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    echo=True if settings.environment == "development" else False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """Initialize database tables"""
    try:
        from app.models.tender import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

async def test_db_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        # Test query
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False