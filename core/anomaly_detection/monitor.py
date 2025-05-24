"""Real-time anomaly monitoring script that runs alongside data generation."""
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
import pytz

from database.models.base import get_db, engine
from .detector import SensorAnomalyDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealTimeAnomalyMonitor:
    """Real-time anomaly detection monitor."""
    
    def __init__(self, 
                 check_interval: int = 60,  # seconds
                 analysis_window: int = 15,  # minutes 
                 alert_threshold: float = 0.7,  # anomaly score threshold
                 model_dir: str = "models/anomaly_detection"):
        self.check_interval = check_interval
        self.analysis_window = analysis_window
        self.alert_threshold = alert_threshold
        self.detector = SensorAnomalyDetector(model_dir)
        self.last_check = datetime.now()
        self.anomaly_history = []
        self.alert_count = 0
        
        # Check if models are loaded
        status = self.detector.get_model_status()
        trained_models = [cat for cat, info in status.items() if info['trained']]
        
        if not trained_models:
            logger.error("No trained models found! Please train models first.")
            raise ValueError("No trained models available for monitoring")
        
        logger.info(f"✓ Loaded models for: {', '.join(trained_models)}")
    
    def get_recent_sensor_data(self, minutes: int = 15) -> Dict[str, List[Dict]]:
        """Get recent sensor data grouped by sensor_id."""
        query = text("""
            SELECT 
                sensor_id,
                category,
                timestamp,
                value,
                unit,
                location
            FROM sensors_data 
            WHERE timestamp >= NOW() - make_interval(mins => :minutes)
            ORDER BY sensor_id, timestamp DESC
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {'minutes': minutes})
            data = result.fetchall()
        
        # Group by sensor_id
        grouped_data = {}
        for row in data:
            sensor_id = row.sensor_id
            if sensor_id not in grouped_data:
                grouped_data[sensor_id] = []
            
            # Ensure timestamp is timezone-naive for comparison
            timestamp = row.timestamp
            if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            
            grouped_data[sensor_id].append({
                'sensor_id': row.sensor_id,
                'category': row.category,
                'timestamp': timestamp,
                'value': float(row.value),
                'unit': row.unit,
                'location': row.location
            })
        
        return grouped_data
    
    def detect_anomalies_in_batch(self, sensor_data: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Detect anomalies for all sensors in a batch."""
        all_anomalies = []
        
        for sensor_id, readings in sensor_data.items():
            if not readings:
                continue
                
            try:
                category = readings[0]['category']
                
                # Check if we have a model for this category
                if category not in self.detector.models:
                    logger.debug(f"No model for category: {category}")
                    continue
                
                # Use the detector to find anomalies
                hours = self.analysis_window / 60.0
                result = self.detector.detect_anomalies_for_sensor(sensor_id, hours=hours)
                
                if result.get('anomalies'):
                    for anomaly in result['anomalies']:
                        # Filter by threshold
                        if anomaly['anomaly_score'] >= self.alert_threshold:
                            # Ensure timestamp is timezone-naive
                            anomaly_timestamp = anomaly['timestamp']
                            if hasattr(anomaly_timestamp, 'tzinfo') and anomaly_timestamp.tzinfo is not None:
                                anomaly_timestamp = anomaly_timestamp.replace(tzinfo=None)
                            
                            anomaly_info = {
                                **anomaly,
                                'timestamp': anomaly_timestamp,
                                'sensor_id': sensor_id,
                                'category': category,
                                'location': readings[0]['location'],
                                'unit': readings[0]['unit'],
                                'detected_at': datetime.now(),
                                'alert_level': self._get_alert_level(anomaly['anomaly_score'])
                            }
                            all_anomalies.append(anomaly_info)
                            
            except Exception as e:
                logger.error(f"Error detecting anomalies for sensor {sensor_id}: {e}")
                continue
        
        return all_anomalies
    
    def _get_alert_level(self, score: float) -> str:
        """Determine alert level based on anomaly score."""
        if score >= 0.9:
            return "CRITICAL"
        elif score >= 0.8:
            return "HIGH"
        elif score >= 0.7:
            return "MEDIUM"
        else:
            return "LOW"
    
    def log_anomaly(self, anomaly: Dict[str, Any]):
        """Log an anomaly detection."""
        level = anomaly['alert_level']
        sensor_id = anomaly['sensor_id']
        category = anomaly['category']
        value = anomaly['value']
        score = anomaly['anomaly_score']
        timestamp = anomaly['timestamp']
        
        log_msg = (f"{level} ANOMALY: {sensor_id} ({category}) "
                  f"Value={value} Score={score:.3f} Time={timestamp}")
        
        if level in ["CRITICAL", "HIGH"]:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def save_anomaly_to_db(self, anomaly: Dict[str, Any]):
        """Save anomaly to database for historical tracking."""
        # This would save to an anomalies table if you create one
        # For now, we'll just add to history
        self.anomaly_history.append(anomaly)
        
        # Keep only last 1000 anomalies in memory
        if len(self.anomaly_history) > 1000:
            self.anomaly_history = self.anomaly_history[-1000:]
    
    def generate_summary_report(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate a summary report of detected anomalies."""
        if not anomalies:
            return "No anomalies detected in this cycle."
        
        # Group by category and alert level
        by_category = {}
        by_level = {}
        
        for anomaly in anomalies:
            category = anomaly['category']
            level = anomaly['alert_level']
            
            by_category[category] = by_category.get(category, 0) + 1
            by_level[level] = by_level.get(level, 0) + 1
        
        report = [
            f"=== ANOMALY DETECTION SUMMARY ===",
            f"Detection Window: {self.analysis_window} minutes",
            f"Total Anomalies: {len(anomalies)}",
            f"",
            f"By Category:",
        ]
        
        for category, count in sorted(by_category.items()):
            report.append(f"  {category}: {count}")
        
        report.extend([
            f"",
            f"By Alert Level:",
        ])
        
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if level in by_level:
                report.append(f"  {level}: {by_level[level]}")
        
        report.append(f"=" * 35)
        
        return "\n".join(report)
    
    def run_single_check(self):
        """Run a single anomaly detection check."""
        logger.info(f"Running anomaly check (window: {self.analysis_window} min)...")
        
        # Get recent sensor data
        sensor_data = self.get_recent_sensor_data(self.analysis_window)
        
        if not sensor_data:
            logger.info("No recent sensor data found")
            return
        
        logger.info(f"Analyzing data from {len(sensor_data)} sensors...")
        
        # Detect anomalies
        anomalies = self.detect_anomalies_in_batch(sensor_data)
        
        # Process and log anomalies
        new_anomalies = 0
        for anomaly in anomalies:
            # Check if this is a new anomaly (not seen in last check)
            if anomaly['timestamp'] > self.last_check:
                new_anomalies += 1
                self.log_anomaly(anomaly)
                self.save_anomaly_to_db(anomaly)
                self.alert_count += 1
        
        # Generate summary
        if new_anomalies > 0:
            logger.info(f"🚨 {new_anomalies} new anomalies detected!")
            summary = self.generate_summary_report(anomalies)
            logger.info(f"\n{summary}")
        else:
            logger.info("✅ No new anomalies detected")
        
        self.last_check = datetime.now()
    
    def run_continuous_monitoring(self, duration_hours: float = None):
        """Run continuous anomaly monitoring."""
        logger.info("=" * 60)
        logger.info("🔍 STARTING REAL-TIME ANOMALY MONITORING")
        logger.info("=" * 60)
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Analysis window: {self.analysis_window} minutes")
        logger.info(f"Alert threshold: {self.alert_threshold}")
        
        end_time = None
        if duration_hours:
            end_time = datetime.now() + timedelta(hours=duration_hours)
            logger.info(f"Will run for {duration_hours} hours until {end_time}")
        
        try:
            cycle = 0
            while True:
                if end_time and datetime.now() >= end_time:
                    logger.info("Duration reached. Stopping monitoring.")
                    break
                
                cycle += 1
                start_time = datetime.now()
                
                logger.info(f"\n--- Monitoring Cycle #{cycle} ---")
                
                try:
                    self.run_single_check()
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                
                # Calculate sleep time
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.check_interval - elapsed)
                
                if sleep_time > 0:
                    logger.info(f"Waiting {sleep_time:.1f}s until next check...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Cycle took {elapsed:.1f}s (longer than {self.check_interval}s interval)")
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in monitoring: {e}")
            raise
        finally:
            logger.info("=" * 60)
            logger.info(f"📊 MONITORING SUMMARY")
            logger.info(f"Total cycles: {cycle}")
            logger.info(f"Total alerts: {self.alert_count}")
            logger.info(f"Anomalies in history: {len(self.anomaly_history)}")
            logger.info("=" * 60)
    
    def get_recent_anomalies(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get anomalies from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [a for a in self.anomaly_history if a['detected_at'] > cutoff]
        return sorted(recent, key=lambda x: x['detected_at'], reverse=True)


def main():
    """Main entry point for anomaly monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time Anomaly Monitoring")
    parser.add_argument("--interval", type=int, default=60, 
                       help="Check interval in seconds (default: 60)")
    parser.add_argument("--window", type=int, default=15, 
                       help="Analysis window in minutes (default: 15)")
    parser.add_argument("--threshold", type=float, default=0.7, 
                       help="Alert threshold (0.0-1.0, default: 0.7)")
    parser.add_argument("--duration", type=float, 
                       help="Duration to run in hours (default: indefinite)")
    parser.add_argument("--model-dir", type=str, default="models/anomaly_detection",
                       help="Directory containing trained models")
    
    args = parser.parse_args()
    
    try:
        monitor = RealTimeAnomalyMonitor(
            check_interval=args.interval,
            analysis_window=args.window,
            alert_threshold=args.threshold,
            model_dir=args.model_dir
        )
        
        monitor.run_continuous_monitoring(duration_hours=args.duration)
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        exit(1)


if __name__ == "__main__":
    main()