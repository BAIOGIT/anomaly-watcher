"""Anomaly detection monitoring service."""
import sys
import os
import logging
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.anomaly_detection.detectors.isolation_forest import IsolationForestDetector
from core.anomaly_detection.detectors.statistical import StatisticalDetector
from core.anomaly_detection.anomaly_service import AnomalyService
from database.models.base import get_db
from database.models.sensor_data import SensorData

logger = logging.getLogger(__name__)

class AnomalyMonitor:
    """Monitor for detecting and storing anomalies."""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        
        # Initialize detectors with error handling
        try:
            self.detectors = {
                'isolation_forest': IsolationForestDetector(contamination=0.1),
                'statistical': StatisticalDetector(z_threshold=2.5)
            }
            logger.info(f"Initialized anomaly monitor with threshold {threshold}")
            logger.info(f"Available detectors: {list(self.detectors.keys())}")
            
            # Test the detectors
            test_values = [1.0, 2.0, 1.5, 1.8, 10.0]  # Last value is an anomaly
            for name, detector in self.detectors.items():
                try:
                    scores = detector.detect(test_values)
                    logger.info(f"Detector {name} test passed: {len(scores)} scores generated")
                except Exception as e:
                    logger.error(f"Detector {name} test failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize detectors: {e}")
            raise
    
    def run_detection_cycle(self, window_minutes: int = 15) -> int:
        """Run one cycle of anomaly detection."""
        try:
            # Get recent sensor data
            sensor_data = self._get_recent_data(window_minutes)
            
            if not sensor_data:
                logger.warning("No sensor data available for anomaly detection")
                return 0
            
            anomalies_detected = 0
            
            # Group data by sensor_id
            sensor_groups = {}
            for reading in sensor_data:
                if reading.sensor_id not in sensor_groups:
                    sensor_groups[reading.sensor_id] = []
                sensor_groups[reading.sensor_id].append(reading)
            
            logger.info(f"Processing {len(sensor_groups)} sensors with {len(sensor_data)} total readings")
            
            # Run detection on each sensor group
            for sensor_id, readings in sensor_groups.items():
                if len(readings) < 5:  # Need minimum data points
                    logger.debug(f"Skipping {sensor_id}: insufficient data ({len(readings)} points)")
                    continue
                
                # Sort readings by timestamp to ensure correct order
                readings.sort(key=lambda x: x.timestamp)
                
                # Prepare data for detection
                values = [r.value for r in readings]
                timestamps = [r.timestamp for r in readings]
                
                logger.debug(f"Analyzing {sensor_id}: {len(values)} values, range {min(values):.2f}-{max(values):.2f}")
                
                # Run each detector
                for detector_name, detector in self.detectors.items():
                    try:
                        anomaly_scores = detector.detect(values)
                        
                        # Store anomalies above threshold with the ORIGINAL timestamp
                        for i, score in enumerate(anomaly_scores):
                            if score >= self.threshold:
                                # Use the timestamp from the actual sensor reading
                                anomaly_timestamp = timestamps[i]
                                
                                # Check if we already detected this anomaly to avoid duplicates
                                if not self._is_duplicate_anomaly(sensor_id, anomaly_timestamp, detector_name):
                                    # Store the anomaly with the original timestamp
                                    AnomalyService.store_anomaly(
                                        sensor_id=sensor_id,
                                        timestamp=anomaly_timestamp,  # THIS IS THE KEY CHANGE
                                        anomaly_score=score,
                                        value=values[i],
                                        unit=readings[i].unit,
                                        category=readings[i].category,
                                        location=readings[i].location or 'unknown',
                                        model_name=detector_name,
                                        anomaly_type=self._classify_anomaly_type(values, i),
                                        context={
                                            'window_size': len(values),
                                            'detector_params': detector.get_params(),
                                            'detection_time': datetime.utcnow().isoformat()  # When detection occurred
                                        }
                                    )
                                    anomalies_detected += 1
                                    logger.info(f"ANOMALY: {sensor_id} at {anomaly_timestamp} (score: {score:.3f}, value: {values[i]:.2f})")
                                
                    except Exception as e:
                        logger.error(f"Error in {detector_name} detection for {sensor_id}: {e}")
            
            logger.info(f"Detection cycle complete: {anomalies_detected} anomalies detected")
            return anomalies_detected
            
        except Exception as e:
            logger.error(f"Error in detection cycle: {e}")
            return 0

    def _is_duplicate_anomaly(self, sensor_id: str, timestamp: datetime, model_name: str) -> bool:
        """Check if we've already detected this anomaly to avoid duplicates."""
        db = next(get_db())
        try:
            from database.models.anomaly import Anomaly
            
            # Check for existing anomaly within 1 minute of this timestamp
            time_window = timedelta(minutes=1)
            existing = db.query(Anomaly).filter(
                Anomaly.sensor_id == sensor_id,
                Anomaly.model_name == model_name,
                Anomaly.timestamp >= timestamp - time_window,
                Anomaly.timestamp <= timestamp + time_window
            ).first()
            
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate anomaly: {e}")
            return False
        finally:
            db.close()
            
    def _get_recent_data(self, window_minutes: int) -> List[SensorData]:
        """Get recent sensor data for analysis."""
        db = next(get_db())
        try:
            start_time = datetime.utcnow() - timedelta(minutes=window_minutes)
            
            query = db.query(SensorData).filter(
                SensorData.timestamp >= start_time
            ).order_by(SensorData.timestamp.desc()).limit(1000)
            
            return query.all()
            
        finally:
            db.close()
    
    def _classify_anomaly_type(self, values: List[float], anomaly_index: int) -> str:
        """Simple classification of anomaly type."""
        if anomaly_index == 0 or anomaly_index == len(values) - 1:
            return 'boundary'
        
        current_val = values[anomaly_index]
        prev_val = values[anomaly_index - 1]
        next_val = values[anomaly_index + 1] if anomaly_index + 1 < len(values) else current_val
        
        # Simple heuristics
        if current_val > max(prev_val, next_val) * 1.5:
            return 'spike'
        elif current_val < min(prev_val, next_val) * 0.5:
            return 'drop'
        else:
            return 'deviation'

def main():
    """Main entry point for anomaly monitoring."""
    parser = argparse.ArgumentParser(description="Anomaly Detection Monitor")
    parser.add_argument("--interval", type=int, default=90, help="Check interval in seconds")
    parser.add_argument("--window", type=int, default=15, help="Analysis window in minutes")
    parser.add_argument("--threshold", type=float, default=0.7, help="Anomaly threshold")
    parser.add_argument("--duration", type=float, help="Run duration in hours")
    
    args = parser.parse_args()
    
    monitor = AnomalyMonitor(threshold=args.threshold)
    
    logger.info(f"Starting anomaly monitoring (interval: {args.interval}s, window: {args.window}m)")
    
    start_time = datetime.utcnow() + timedelta(hours=2)
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"Starting detection cycle #{cycle_count}")
            
            anomalies = monitor.run_detection_cycle(args.window)
            
            # Check duration limit
            if args.duration:
                elapsed = (datetime.utcnow() + timedelta(hours=2) - start_time).total_seconds() / 3600
                if elapsed >= args.duration:
                    logger.info(f"Duration limit reached ({args.duration} hours)")
                    break
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()