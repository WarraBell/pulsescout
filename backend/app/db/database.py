from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create synchronous engine for migrations and utilities
engine = create_engine(
    DATABASE_URL,
    echo=True,
)

# Create async engine for application use
async_engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession)

# Base class for all models
Base = declarative_base()

# Dependency for synchronous endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for asynchronous endpoints
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session