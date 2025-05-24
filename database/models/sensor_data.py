"""Sensor data model for TimescaleDB."""
from datetime import datetime
from sqlalchemy import Column, Float, String, DateTime, text, PrimaryKeyConstraint

from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base

class SensorData(Base):
    """Sensor data model for storing time-series data in TimescaleDB."""
    __tablename__ = "sensors_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=text("now()"), index=True)
    sensor_id = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # e.g., 'analog', 'digital', 'serial'
    category = Column(String(50), nullable=False)  # e.g., 'oven', 'heater', 'fan', 'fridge', 'pump', 'valve', 'sensor'
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # e.g., 'C', 'F', '%', 'hPa'
    location = Column(String(100))  # Optional location identifier e.g., 'restaurant', 'factory', 'supermarket'
    sensors_metadata = Column(String(500))  # Additional metadata as JSON string
    
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
    )

    # No special table args needed - we'll handle TimescaleDB features in create_hypertable
    
    def __repr__(self):
        return f"<SensorData(id={self.id}, timestamp={self.timestamp}, sensor_id={self.sensor_id}, " \
               f"type={self.type}, value={self.value}{self.unit})>"

    @classmethod
    def create_hypertable(cls, engine):
        """Create TimescaleDB hypertable for sensor data."""
        from sqlalchemy import text

        with engine.connect() as conn:
            # Enable required extensions
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE'))
            conn.commit()

            # Create the table with a composite primary key (id, timestamp)
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                    id UUID NOT NULL DEFAULT uuid_generate_v4(),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    sensor_id VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR(20) NOT NULL,
                    location VARCHAR(100),
                    sensors_metadata VARCHAR(500)
                )
            """
            conn.execute(text(create_table_sql))
            conn.commit()

            # Create indexes
            index_sql = f"""
                -- Create index on sensor_id for better query performance
                CREATE INDEX IF NOT EXISTS idx_sensors_data_sensor_id 
                ON {cls.__tablename__} (sensor_id, timestamp DESC)
            """
            conn.execute(text(index_sql))

            # Convert to hypertable
            hypertable_sql = f"""
                SELECT create_hypertable(
                    '{cls.__tablename__}',
                    'timestamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                )
            """
            conn.execute(text(hypertable_sql))

            # Set chunk time interval
            interval_sql = f"""
                SELECT set_chunk_time_interval(
                    '{cls.__tablename__}',
                    INTERVAL '1 day'
                )
            """
            conn.execute(text(interval_sql))

            # Enable compression
            compress_sql = f"""
                ALTER TABLE {cls.__tablename__} 
                SET (timescaledb.compress, timescaledb.compress_segmentby = 'sensor_id')
            """
            conn.execute(text(compress_sql))

            # Add compression policy
            policy_sql = f"""
                SELECT add_compression_policy('{cls.__tablename__}', INTERVAL '7 days')
            """
            conn.execute(text(policy_sql))

            conn.commit()