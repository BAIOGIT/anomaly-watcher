from sqlalchemy import Column, String, Float, DateTime, JSON, text, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from .base import Base

class Anomaly(Base):
    """Model for storing detected anomalies."""
    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)  # When the anomalous reading occurred
    sensor_id = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    location = Column(String(100))
    model_name = Column(String(50), nullable=False)
    anomaly_type = Column(String(50))
    context = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))  # When anomaly was detected

    # Add indexes for performance
    __table_args__ = (
        Index('idx_anomalies_timestamp', 'timestamp'),
        Index('idx_anomalies_sensor_id', 'sensor_id'),
        Index('idx_anomalies_category', 'category'),
        Index('idx_anomalies_score', 'anomaly_score'),
        Index('idx_anomalies_sensor_timestamp', 'sensor_id', 'timestamp'),  # Composite index for duplicates
    )

    def __repr__(self):
        return f"<Anomaly(sensor_id={self.sensor_id}, timestamp={self.timestamp}, score={self.anomaly_score:.2f})>"