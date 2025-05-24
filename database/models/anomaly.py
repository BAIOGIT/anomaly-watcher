from sqlalchemy import Column, String, Float, DateTime, JSON, text, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from .base import Base

class Anomaly(Base):
    """Model for storing detected anomalies."""
    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    sensor_id = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    location = Column(String(100))
    model_name = Column(String(50), nullable=False)  # Match dashboard expectation
    anomaly_type = Column(String(50))  # For dashboard classification
    context = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Add indexes for performance
    __table_args__ = (
        Index('idx_anomalies_timestamp', 'timestamp'),
        Index('idx_anomalies_sensor_id', 'sensor_id'),
        Index('idx_anomalies_category', 'category'),
        Index('idx_anomalies_score', 'anomaly_score'),
    )

    def __repr__(self):
        return f"<Anomaly(sensor_id={self.sensor_id}, timestamp={self.timestamp}, score={self.anomaly_score:.2f})>"

    @classmethod
    def create_table(cls, engine):
        """Create the anomaly detections table with indexes."""
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Create the table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    timestamp TIMESTAMPTZ NOT NULL,
                    sensor_id VARCHAR(100) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    anomaly_score FLOAT NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR(20) NOT NULL,
                    location VARCHAR(100),
                    model_used VARCHAR(50) NOT NULL,
                    context JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (sensor_id) REFERENCES sensors_data(sensor_id) ON DELETE CASCADE
                )
            """))
            
            # Create indexes
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_anomaly_detections_timestamp 
                ON {cls.__tablename__} (timestamp DESC)
            """))
            
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_anomaly_detections_sensor_id 
                ON {cls.__tablename__} (sensor_id)
            """))
            
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_anomaly_detections_category 
                ON {cls.__tablename__} (category)
            """))
            
            conn.commit()