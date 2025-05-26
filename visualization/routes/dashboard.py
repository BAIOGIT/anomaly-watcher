from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import text
from datetime import datetime, timedelta

import logging

logger = logging.getLogger(__name__)

from database.models.base import get_db, engine
from database.db import reset_db

dashboard_bp = Blueprint('dashboard', __name__)

def read_sensor_data_from_db(hours: int = 24, limit: int = 1000):
    """
    Read sensor data from TimescaleDB.
    
    Args:
        hours (int): Number of hours of data to fetch
        limit (int): Maximum number of records to fetch
    
    Returns:
        List[Dict]: List of sensor readings
    """
    query = text(f"""
        SELECT 
            id,
            timestamp,
            sensor_id,
            type,
            category,
            value,
            unit,
            location,
            sensors_metadata
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
        ORDER BY timestamp DESC, sensor_id
        LIMIT :limit
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"hours": hours, "limit": limit})
        rows = [dict(row._mapping) for row in result]
    
    return rows

def get_sensor_statistics():
    """Get summary statistics about sensors."""
    query = text("""
        SELECT 
            category,
            type,
            COUNT(*) as sensor_count,
            COUNT(DISTINCT sensor_id) as unique_sensors,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            MAX(timestamp) as last_reading
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY category, type
        ORDER BY category, type
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]
    
    return rows

def get_recent_alerts():
    """Get recent sensor alerts based on thresholds."""
    query = text("""
        SELECT 
            timestamp,
            sensor_id,
            category,
            location,
            value,
            unit,
            CASE 
                WHEN category = 'oven' AND value > 300 THEN 'HIGH_TEMP'
                WHEN category = 'heater' AND value > 160 THEN 'HIGH_TEMP'
                WHEN category = 'pm' AND value > 200 THEN 'HIGH_PM'
                WHEN category = 'fan' AND type = 'analog' AND value = 0 THEN 'FAN_STOPPED'
            END as alert_type
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        AND (
            (category = 'oven' AND value > 300) OR
            (category = 'heater' AND value > 160) OR
            (category = 'pm' AND value > 100) OR
            (category = 'fan' AND type = 'analog' AND value = 0)
        )
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]
    
    return rows

def get_sensor_time_series(sensor_id: str = None, category: str = None, hours: int = 24, interval: str = '5 minutes'):
    """Get time series data for charts."""
    where_clause = f"WHERE timestamp >= NOW() + INTERVAL '2 hours' - INTERVAL '{hours} hours'"
    params = {}
    
    if sensor_id:
        where_clause += " AND sensor_id = :sensor_id"
        params["sensor_id"] = sensor_id
    elif category:
        where_clause += " AND category = :category"
        params["category"] = category
    
    query = text(f"""
        SELECT 
            time_bucket('{interval}', timestamp) AS time_bucket,
            sensor_id,
            category,
            type,
            location,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as reading_count,
            FIRST(unit, timestamp) as unit
        FROM sensors_data 
        {where_clause}
        GROUP BY time_bucket, sensor_id, category, type, location
        ORDER BY time_bucket DESC, sensor_id
        LIMIT 1000
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = [dict(row._mapping) for row in result]
    
    return rows

@dashboard_bp.route('/dashboard')
def dashboard():
    """Main dashboard page."""
    # Get recent data for overview
    recent_data = read_sensor_data_from_db(hours=1, limit=100)
    statistics = get_sensor_statistics()
    alerts = get_recent_alerts()
    
    return render_template('dashboard.html', 
                         sensor_data=recent_data,
                         statistics=statistics,
                         alerts=alerts)

@dashboard_bp.route('/api/sensor-data')
def api_sensor_data():
    """API endpoint for sensor data."""
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 1000, type=int)
    
    # Use string formatting for INTERVAL
    query = text(f"""
        SELECT 
            id,
            timestamp,
            sensor_id,
            type,
            category,
            value,
            unit,
            location,
            sensors_metadata
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
        ORDER BY timestamp DESC, sensor_id
        LIMIT :limit
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        rows = [dict(row._mapping) for row in result]
    
    return jsonify(rows)

@dashboard_bp.route('/api/sensor-statistics')
def api_sensor_statistics():
    """API endpoint for sensor statistics."""
    statistics = get_sensor_statistics()
    return jsonify(statistics)

@dashboard_bp.route('/api/sensor-alerts')
def api_sensor_alerts():
    """API endpoint for recent alerts."""
    alerts = get_recent_alerts()
    return jsonify(alerts)

@dashboard_bp.route('/api/sensor-timeseries')
def api_sensor_timeseries():
    """API endpoint for time series data."""
    sensor_id = request.args.get('sensor_id')
    category = request.args.get('category')
    hours = request.args.get('hours', 24, type=int)
    interval_seconds = request.args.get('interval', 300, type=int)  # Default 5 minutes
    
    # Convert seconds to PostgreSQL interval format
    if interval_seconds >= 3600:
        interval = f"{interval_seconds // 3600} hours"
    elif interval_seconds >= 60:
        interval = f"{interval_seconds // 60} minutes"
    else:
        interval = f"{interval_seconds} seconds"
    
    # print(f"API called with: hours={hours}, interval={interval}, category={category}")  # Debug log
    
    timeseries_data = get_sensor_time_series(
        sensor_id=sensor_id, 
        category=category, 
        hours=hours,
        interval=interval
    )
    
    # print(f"Returning {len(timeseries_data)} data points")  # Debug log
    return jsonify(timeseries_data)

@dashboard_bp.route('/api/live-data')
def api_live_data():
    """API endpoint for live/real-time data (last 5 minutes)."""
    query = text("""
        SELECT 
            timestamp,
            sensor_id,
            category,
            type,
            value,
            unit,
            location
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '5 seconds'
        ORDER BY timestamp DESC
        LIMIT 100
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]
    
    return jsonify(rows)

@dashboard_bp.route('/api/sensor-categories')
def api_sensor_categories():
    """API endpoint to get available sensor categories."""
    query = text("""
        SELECT DISTINCT 
            category,
            type,
            COUNT(DISTINCT sensor_id) as sensor_count
        FROM sensors_data 
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY category, type
        ORDER BY category, type
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]
    
    return jsonify(rows)

@dashboard_bp.route('/api/anomalies-timeseries')
def api_anomalies_timeseries():
    """API endpoint for anomaly data overlay."""
    sensor_id = request.args.get('sensor_id')
    category = request.args.get('category')
    hours = request.args.get('hours', 24, type=int)
    interval_seconds = request.args.get('interval', 300, type=int)  # Get same interval as sensor data

    # Convert seconds to PostgreSQL interval format (same as sensor timeseries)
    if interval_seconds >= 3600:
        interval = f"{interval_seconds // 3600} hours"
    elif interval_seconds >= 60:
        interval = f"{interval_seconds // 60} minutes"
    else:
        interval = f"{interval_seconds} seconds"

    # Use direct SQL query for better performance
    where_clause = "WHERE timestamp >= NOW() - INTERVAL :hours"  # timestamp is the anomaly occurrence time
    params = {"hours": f"{hours} hours"}

    if sensor_id:
        where_clause += " AND sensor_id = :sensor_id"
        params["sensor_id"] = sensor_id
    elif category:
        where_clause += " AND category = :category"
        params["category"] = category

    query = f"""
        SELECT 
            date_trunc('minute', timestamp) AS timestamp,  -- Set seconds to 0
            sensor_id,
            category,
            value,
            unit,
            location,
            anomaly_score,
            model_name,
            anomaly_type,
            created_at          -- When the anomaly was detected
        FROM anomalies 
        {where_clause}
        ORDER BY timestamp DESC  -- Order by when anomaly occurred
        LIMIT 500
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        anomaly_data = [dict(row._mapping) for row in result]

    return jsonify(anomaly_data)

@dashboard_bp.route('/api/reset-database', methods=['POST'])
def api_reset_database():
    """API endpoint to reset the database."""
    try:
        logger.warning("Database reset requested via dashboard")
        
        # Perform the reset
        reset_db()
        
        logger.info("Database reset completed successfully")
        return jsonify({
            'success': True,
            'message': 'Database reset successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Database reset failed: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }), 500