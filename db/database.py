from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Fetching the database URL from the environment settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Creating the database engine (check_same_thread=False is required for SQLite)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Creating a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Creating a Base class for our classes definitions
Base = declarative_base()