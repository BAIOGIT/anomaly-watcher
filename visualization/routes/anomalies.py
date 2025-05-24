# visualization/routes/anomalies.py
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional

from database.models.base import get_db
from core.anomaly_detection.anomaly_service import AnomalyService

anomaly_bp = Blueprint('anomaly', __name__)

@anomaly_bp.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """Get anomalies based on filters."""
    sensor_id = request.args.get('sensor_id')
    category = request.args.get('category')
    hours = int(request.args.get('hours', 24))
    min_score = float(request.args.get('min_score', 0.7))
    limit = int(request.args.get('limit', 1000))
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    db = next(get_db())
    try:
        anomalies = AnomalyService.get_anomalies(
            sensor_id=sensor_id,
            category=category,
            start_time=start_time,
            min_score=min_score,
            limit=limit,
            db=db
        )
        
        return jsonify([{
            'id': str(a.id),
            'timestamp': a.timestamp.isoformat(),
            'sensor_id': a.sensor_id,
            'category': a.category,
            'anomaly_score': a.anomaly_score,
            'value': a.value,
            'unit': a.unit,
            'location': a.location,
            'model_used': a.model_used,
            'context': a.context
        } for a in anomalies])
    finally:
        db.close()

@anomaly_bp.route('/api/anomalies/stats', methods=['GET'])
def get_anomaly_stats():
    """Get anomaly statistics."""
    hours = int(request.args.get('hours', 24))
    category = request.args.get('category')
    
    db = next(get_db())
    try:
        stats = AnomalyService.get_anomaly_stats(
            hours=hours,
            category=category,
            db=db
        )
        
        return jsonify({
            'total_anomalies': stats['total_anomalies'],
            'by_category': stats['by_category'],
            'recent_anomalies': [{
                'id': str(a.id),
                'timestamp': a.timestamp.isoformat(),
                'sensor_id': a.sensor_id,
                'category': a.category,
                'anomaly_score': a.anomaly_score,
                'value': a.value,
                'unit': a.unit
            } for a in stats['recent_anomalies']]
        })
    finally:
        db.close()