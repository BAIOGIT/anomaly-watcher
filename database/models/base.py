"""Base database models and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import os
from dotenv import load_dotenv
import socket

# Load environment variables from .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

# Default database URL for local development
DATABASE_URL = os.getenv("DOCKER_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sensor_data")

try:
    # Try to connect to the database
    engine = create_engine(DATABASE_URL)
    print("Connected to Docker container.")
except Exception as e:
    print(f"Error connecting to database at {DATABASE_URL}: {e}")
    raise

# Create database if it doesn't exist
if not database_exists(engine.url):
    print(f"Creating database: {engine.url.database}")
    create_database(engine.url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
