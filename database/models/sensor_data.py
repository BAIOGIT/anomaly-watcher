"""Sensor data model for TimescaleDB."""
from datetime import datetime
from sqlalchemy import Column, Float, String, DateTime, text, PrimaryKeyConstraint, UniqueConstraint, Index

from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base

class SensorData(Base):
    """Sensor data model for storing time-series data in TimescaleDB."""
    __tablename__ = "sensors_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=text("now()"), index=True)
    sensor_id = Column(String(100), nullable=False, index=True)  # REMOVED unique=True
    type = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    location = Column(String(100))
    sensors_metadata = Column(String(500))
    
    # TimescaleDB compatible constraints - composite unique constraint with timestamp
    __table_args__ = (
        UniqueConstraint('sensor_id', 'timestamp', name='uq_sensor_timestamp'),
        Index('idx_sensor_category_time', 'category', 'timestamp'),
        Index('idx_sensor_location_time', 'location', 'timestamp'),
        Index('idx_sensor_type_time', 'type', 'timestamp'),
    )

    def __repr__(self):
        return f"<SensorData(id={self.id}, timestamp={self.timestamp}, sensor_id={self.sensor_id}, " \
               f"type={self.type}, value={self.value}{self.unit})>"

    @classmethod
    def create_hypertable(cls, engine):
        """Create TimescaleDB hypertable for sensor data."""
        from sqlalchemy import text

        with engine.connect() as conn:
            # Check if table already exists and is a hypertable
            check_hypertable = text("""
                SELECT COUNT(*) FROM timescaledb_information.hypertables 
                WHERE hypertable_name = :table_name
            """)
            result = conn.execute(check_hypertable, {"table_name": cls.__tablename__})
            
            if result.scalar() > 0:
                print(f"Hypertable {cls.__tablename__} already exists")
                return

            # Create the table manually with composite primary key
            create_table_sql = text(f"""
                CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                    id UUID NOT NULL DEFAULT gen_random_uuid(),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    sensor_id VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR(20) NOT NULL,
                    location VARCHAR(100),
                    sensors_metadata VARCHAR(500),
                    PRIMARY KEY (id, timestamp)
                )
            """)
            conn.execute(create_table_sql)

            # Create the composite unique constraint that includes timestamp
            unique_constraint_sql = text(f"""
                ALTER TABLE {cls.__tablename__} 
                ADD CONSTRAINT uq_sensor_timestamp 
                UNIQUE (sensor_id, timestamp)
            """)
            try:
                conn.execute(unique_constraint_sql)
            except Exception as e:
                print(f"Constraint may already exist: {e}")

            # Convert to hypertable
            hypertable_sql = text(f"""
                SELECT create_hypertable(
                    '{cls.__tablename__}',
                    'timestamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE,
                    create_default_indexes => FALSE
                )
            """)
            conn.execute(hypertable_sql)

            # Create indexes after hypertable creation
            indexes_sql = [
                f"CREATE INDEX IF NOT EXISTS idx_sensors_data_sensor_id ON {cls.__tablename__} (sensor_id, timestamp DESC)",
                f"CREATE INDEX IF NOT EXISTS idx_sensors_data_category ON {cls.__tablename__} (category, timestamp DESC)",
                f"CREATE INDEX IF NOT EXISTS idx_sensors_data_type ON {cls.__tablename__} (type, timestamp DESC)",
                f"CREATE INDEX IF NOT EXISTS idx_sensors_data_location ON {cls.__tablename__} (location, timestamp DESC)"
            ]
            
            for idx_sql in indexes_sql:
                conn.execute(text(idx_sql))

            # Set chunk time interval
            interval_sql = text(f"""
                SELECT set_chunk_time_interval(
                    '{cls.__tablename__}',
                    INTERVAL '1 day'
                )
            """)
            conn.execute(interval_sql)

            # Enable compression
            compress_sql = text(f"""
                ALTER TABLE {cls.__tablename__} 
                SET (timescaledb.compress, timescaledb.compress_segmentby = 'sensor_id')
            """)
            conn.execute(compress_sql)

            # Add compression policy
            policy_sql = text(f"""
                SELECT add_compression_policy('{cls.__tablename__}', INTERVAL '7 days')
            """)
            conn.execute(policy_sql)

            conn.commit()
            print(f"Hypertable {cls.__tablename__} created successfully")