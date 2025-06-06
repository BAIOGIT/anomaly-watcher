"""Database initialization and management."""
import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .models.base import Base, engine
from .models.sensor_data import SensorData
from .models.anomaly import Anomaly

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database and create tables."""
    try:
        # Enable required extensions
        logger.info("Enabling database extensions...")
        with engine.connect() as conn:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE'))
            conn.commit()
        
        # Create SensorData hypertable (this will create the table too)
        logger.info("Creating SensorData hypertable...")
        SensorData.create_hypertable(engine)

        # Create Anomaly table using SQLAlchemy
        logger.info("Creating Anomaly table...")
        Anomaly.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("Database initialized successfully!")
        
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise
    
def reset_db():
    """Drop all tables and recreate them."""
    try:
        logger.warning("🚨 RESETTING DATABASE - ALL DATA WILL BE LOST!")
        
        with engine.connect() as conn:
            # Drop tables in the correct order to avoid foreign key issues
            logger.info("Dropping anomalies table...")
            conn.execute(text('DROP TABLE IF EXISTS anomalies CASCADE'))
            
            logger.info("Dropping sensors_data table...")
            conn.execute(text('DROP TABLE IF EXISTS sensors_data CASCADE'))
            
            # Drop any other tables that might exist
            conn.execute(text('DROP TABLE IF EXISTS anomaly_detections CASCADE'))
            
            conn.commit()
        
        logger.info("Recreating database schema...")
        init_db()
        
        logger.info("✅ Database reset completed successfully!")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Error resetting database: {e}")
        raise

if __name__ == "__main__":
    init_db()
