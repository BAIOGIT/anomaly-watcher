"""Database initialization and management."""
import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .models.base import Base, engine
from .models.sensor_data import SensorData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database and create tables."""
    try:
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Create TimescaleDB hypertable
        logger.info("Creating TimescaleDB hypertable...")
        SensorData.create_hypertable(engine)
        
        # Create indexes
        logger.info("Creating indexes...")
        with engine.connect() as conn:
            # Create additional indexes for common query patterns
            conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_type_timestamp 
            ON sensors_data (type, timestamp DESC);
            """))
            
            conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_category_timestamp 
            ON sensors_data (category, timestamp DESC);
            """))
            
            conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_location_timestamp 
            ON sensors_data (location, timestamp DESC);
            """))
            
            conn.commit()
        
        logger.info("Database initialized successfully!")
        
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise

def reset_db():
    """Drop all tables and recreate them."""
    try:
        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped.")
        
        # Reinitialize the database
        init_db()
        
    except SQLAlchemyError as e:
        logger.error(f"Error resetting database: {e}")
        raise

if __name__ == "__main__":
    init_db()
