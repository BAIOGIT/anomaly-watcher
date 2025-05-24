#!/usr/bin/env python3
"""Test script for the sensor data generator."""
import sys
import os
import logging
from datetime import datetime, timedelta

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generator.models import SensorData, get_db
from generator.utils import generate_time_series

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_data_generation():
    """Test data generation and database operations."""
    logger.info("Starting data generation test...")
    
    # Generate test data
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)  # Generate 1 hour of data
    
    logger.info(f"Generating test data from {start_time} to {end_time}")
    test_data = generate_time_series(
        start_time=start_time,
        end_time=end_time,
        interval=60,  # 1 minute interval
        num_sensors=2  # Just 2 sensors for testing
    )
    
    logger.info(f"Generated {len(test_data)} data points")
    
    # Connect to the database
    db = next(get_db())
    
    try:
        # Count records before insert
        count_before = db.query(SensorData).count()
        logger.info(f"Records in database before: {count_before}")
        
        # Insert test data
        logger.info("Inserting test data into the database...")
        for item in test_data:
            db.add(SensorData(**item))
        db.commit()
        
        # Count records after insert
        count_after = db.query(SensorData).count()
        logger.info(f"Records in database after: {count_after}")
        
        # Verify the data was inserted
        assert count_after == count_before + len(test_data), \
            f"Expected {len(test_data)} new records, got {count_after - count_before}"
            
        # Query some data back
        latest = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        logger.info(f"Latest record: {latest}")
        
        # Get sensor types
        sensor_types = db.query(SensorData.type).distinct().all()
        logger.info(f"Sensor types in database: {[t[0] for t in sensor_types]}")
        
        logger.info("✅ Data generation test completed successfully!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_data_generation()
