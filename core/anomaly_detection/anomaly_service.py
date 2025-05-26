# core/anomaly_detection/anomaly_service.py
"""Service for managing anomaly detection and storage."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, desc

from database.models.anomaly import Anomaly
from database.models.sensor_data import SensorData
from database.models.base import get_db, engine

logger = logging.getLogger(__name__)

class AnomalyService:
    """Service for anomaly detection and management."""
    
    @staticmethod
    def store_anomaly(
        sensor_id: str,
        timestamp: datetime,  # This should be the sensor reading timestamp
        anomaly_score: float,
        value: float,
        unit: str,
        category: str,
        location: str,
        model_name: str,
        anomaly_type: str = None,
        context: Dict[str, Any] = None,
        db: Session = None
    ) -> Anomaly:
        """Store a detected anomaly in the database."""
        
        if db is None:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
            
        try:
            # Ensure timestamp is timezone-aware
            if timestamp.tzinfo is None:
                from datetime import timezone
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            anomaly = Anomaly(
                sensor_id=sensor_id,
                timestamp=timestamp,  # Use the actual sensor reading timestamp
                anomaly_score=anomaly_score,
                value=value,
                unit=unit,
                category=category,
                location=location,
                model_name=model_name,
                anomaly_type=anomaly_type,
                context=context or {},
                created_at=datetime.utcnow()  # When the anomaly was detected/stored
            )
            
            db.add(anomaly)
            db.commit()
            db.refresh(anomaly)
            
            logger.info(f"Stored anomaly: {sensor_id} at {timestamp} (score: {anomaly_score:.3f})")
            return anomaly
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing anomaly: {e}")
            raise
        finally:
            if close_db:
                db.close()
                
    @staticmethod
    def get_anomalies(
        sensor_id: Optional[str] = None,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_score: float = 0.0,
        limit: int = 1000,
        db: Session = None
    ) -> List[Anomaly]:
        """Retrieve anomalies based on filters."""
        
        if db is None:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
            
        try:
            query = db.query(Anomaly)
            
            # Apply filters
            if sensor_id:
                query = query.filter(Anomaly.sensor_id == sensor_id)
            if category:
                query = query.filter(Anomaly.category == category)
            if start_time:
                query = query.filter(Anomaly.timestamp >= start_time)
            if end_time:
                query = query.filter(Anomaly.timestamp <= end_time)
            if min_score > 0:
                query = query.filter(Anomaly.anomaly_score >= min_score)
            
            # Order by timestamp descending and limit
            query = query.order_by(desc(Anomaly.timestamp)).limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error retrieving anomalies: {e}")
            raise
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_anomaly_stats(hours: int = 24, category: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
        """Get anomaly statistics for the dashboard."""
        
        if db is None:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
            
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Base query
            query = db.query(Anomaly).filter(Anomaly.timestamp >= start_time)
            if category:
                query = query.filter(Anomaly.category == category)
            
            # Total count
            total_anomalies = query.count()
            
            # Count by category
            category_query = text("""
                SELECT category, COUNT(*) as count 
                FROM anomalies 
                WHERE timestamp >= :start_time
                GROUP BY category
                ORDER BY count DESC
            """)
            
            with engine.connect() as conn:
                result = conn.execute(category_query, {"start_time": start_time})
                by_category = {row.category: row.count for row in result}
            
            # Recent anomalies
            recent_anomalies = query.order_by(desc(Anomaly.timestamp)).limit(10).all()
            
            return {
                'total_anomalies': total_anomalies,
                'by_category': by_category,
                'recent_anomalies': recent_anomalies
            }
            
        except Exception as e:
            logger.error(f"Error getting anomaly stats: {e}")
            raise
        finally:
            if close_db:
                db.close()