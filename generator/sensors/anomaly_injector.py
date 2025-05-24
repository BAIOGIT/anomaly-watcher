"""Anomaly injection utilities for testing anomaly detection."""
import random
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class AnomalyInjector:
    """Inject various types of anomalies into sensor data for testing."""
    
    def __init__(self):
        self.active_anomalies = {}  # Track ongoing anomalies per sensor
        self.anomaly_history = []   # Log of injected anomalies
        
        # Anomaly patterns by sensor category
        self.anomaly_patterns = {
            'oven': {
            'spike': {'min': 50, 'max': 100, 'duration': (2*6, 8*6)},      # Temperature spikes
            'drop': {'min': -30, 'max': -10, 'duration': (3*6, 10*6)},     # Sudden cooling
            'drift': {'rate': 2.0, 'duration': (10*6, 30*6)},              # Gradual drift
            'oscillation': {'amplitude': 15, 'frequency': 0.3, 'duration': (5*6, 15*6)}
            },
            'heater': {
            'spike': {'min': 30, 'max': 70, 'duration': (3*6, 12*6)},
            'drop': {'min': -20, 'max': -5, 'duration': (5*6, 15*6)},
            'drift': {'rate': 1.5, 'duration': (15*6, 45*6)},
            'oscillation': {'amplitude': 10, 'frequency': 0.2, 'duration': (8*6, 20*6)}
            },
            'lamp': {
            'flicker': {'duration': (5*6, 20*6)},                          # Rapid on/off
            'stuck': {'value': 0, 'duration': (10*6, 60*6)},               # Stuck off
            'stuck_on': {'value': 1, 'duration': (15*6, 120*6)}            # Stuck on
            },
            'fan': {
            'spike': {'min': 200, 'max': 500, 'duration': (3*6, 10*6)},    # RPM spikes
            'stall': {'value': 0, 'duration': (5*6, 30*6)},                # Fan stops
            'vibration': {'amplitude': 50, 'frequency': 0.5, 'duration': (10*6, 25*6)},
            'overspeed': {'min': 300, 'max': 800, 'duration': (2*6, 15*6)}
            },
            'pm': {
            'pollution_spike': {'min': 50, 'max': 150, 'duration': (10*6, 60*6)},  # Dust/smoke
            'sensor_drift': {'rate': 3.0, 'duration': (30*6, 120*6)},
            'calibration_error': {'offset': 25, 'duration': (60*6, 300*6)},
            'dust_storm': {'min': 100, 'max': 250, 'duration': (20*6, 180*6)}
            }
        }
    
    def should_inject_anomaly(self, 
                             sensor_id: str, 
                             category: str, 
                             injection_rate: float = 0.02) -> bool:
        """Determine if an anomaly should be injected."""
        # Don't inject if anomaly is already active
        if sensor_id in self.active_anomalies:
            return False
        
        # Random chance based on injection rate
        return random.random() < injection_rate
    
    def inject_anomaly(self, 
                      sensor_id: str, 
                      category: str, 
                      anomaly_type: str = None) -> Dict[str, Any]:
        """Inject a specific type of anomaly."""
        if category not in self.anomaly_patterns:
            return None
        
        patterns = self.anomaly_patterns[category]
        
        # Select anomaly type
        if anomaly_type is None:
            anomaly_type = random.choice(list(patterns.keys()))
        elif anomaly_type not in patterns:
            return None
        
        pattern = patterns[anomaly_type]
        
        # Generate anomaly parameters
        if 'duration' in pattern:
            duration = random.randint(*pattern['duration'])
        else:
            duration = random.randint(30, 150)
        
        anomaly_data = {
            'sensor_id': sensor_id,
            'category': category,
            'type': anomaly_type,
            'started_at': datetime.now(),
            'duration': duration,
            'remaining_duration': duration,
            'pattern': pattern.copy(),
            'phase': 0.0  # For oscillating anomalies
        }
        
        # Add specific parameters based on anomaly type
        if 'min' in pattern and 'max' in pattern:
            anomaly_data['magnitude'] = random.uniform(pattern['min'], pattern['max'])
        elif 'value' in pattern:
            anomaly_data['value'] = pattern['value']
        elif 'rate' in pattern:
            anomaly_data['rate'] = pattern['rate'] * random.uniform(0.5, 2.0)
        elif 'offset' in pattern:
            anomaly_data['offset'] = pattern['offset'] * random.uniform(0.5, 1.5)
        
        # Store active anomaly
        self.active_anomalies[sensor_id] = anomaly_data
        
        # Log anomaly injection
        log_entry = {
            'sensor_id': sensor_id,
            'category': category,
            'type': anomaly_type,
            'started_at': anomaly_data['started_at'],
            'duration': duration,
            'magnitude': anomaly_data.get('magnitude', 'N/A')
        }
        self.anomaly_history.append(log_entry)
        
        print(f"🚨 INJECTED ANOMALY: {sensor_id} ({category}) - {anomaly_type} for {duration} readings")
        
        return anomaly_data
    
    def apply_anomaly(self, sensor_id: str, normal_value: float, sensor_type: str) -> float:
        """Apply active anomaly to a sensor value."""
        if sensor_id not in self.active_anomalies:
            return normal_value
        
        anomaly = self.active_anomalies[sensor_id]
        anomaly_type = anomaly['type']
        
        # Apply anomaly based on type
        if anomaly_type == 'spike':
            return normal_value + anomaly['magnitude']
        
        elif anomaly_type == 'drop':
            return max(0, normal_value + anomaly['magnitude'])  # Prevent negative values
        
        elif anomaly_type == 'drift':
            # Gradual drift over time
            progress = 1.0 - (anomaly['remaining_duration'] / anomaly['duration'])
            drift_amount = anomaly['rate'] * progress
            return normal_value + drift_amount
        
        elif anomaly_type == 'oscillation':
            # Sinusoidal oscillation
            frequency = anomaly['pattern']['frequency']
            amplitude = anomaly['pattern']['amplitude']
            phase = anomaly['phase']
            oscillation = amplitude * math.sin(2 * math.pi * frequency * phase)
            anomaly['phase'] += 1  # Increment phase
            return normal_value + oscillation
        
        elif anomaly_type == 'flicker' and sensor_type == 'digital':
            # Rapid on/off for digital sensors
            return random.choice([0, 1])
        
        elif anomaly_type in ['stuck', 'stuck_on', 'stall']:
            # Force specific value
            return anomaly['value']
        
        elif anomaly_type == 'vibration':
            # Add high-frequency noise
            frequency = anomaly['pattern']['frequency']
            amplitude = anomaly['pattern']['amplitude']
            noise = amplitude * random.uniform(-1, 1) * math.sin(anomaly['phase'] * frequency)
            anomaly['phase'] += 1
            return normal_value + noise
        
        elif anomaly_type == 'overspeed':
            return normal_value + anomaly['magnitude']
        
        elif anomaly_type == 'pollution_spike':
            return normal_value + anomaly['magnitude']
        
        elif anomaly_type == 'sensor_drift':
            # Similar to drift but for PM sensors
            progress = 1.0 - (anomaly['remaining_duration'] / anomaly['duration'])
            drift_amount = anomaly['rate'] * progress
            return normal_value + drift_amount
        
        elif anomaly_type == 'calibration_error':
            return normal_value + anomaly['offset']
        
        elif anomaly_type == 'dust_storm':
            return normal_value + anomaly['magnitude']
        
        return normal_value
    
    def update_anomalies(self):
        """Update active anomalies and remove expired ones."""
        expired_sensors = []
        
        for sensor_id, anomaly in self.active_anomalies.items():
            anomaly['remaining_duration'] -= 1
            
            if anomaly['remaining_duration'] <= 0:
                expired_sensors.append(sensor_id)
                print(f"✅ ANOMALY ENDED: {sensor_id} ({anomaly['category']}) - {anomaly['type']}")
        
        # Remove expired anomalies
        for sensor_id in expired_sensors:
            del self.active_anomalies[sensor_id]
    
    def get_active_anomalies(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active anomalies."""
        return self.active_anomalies.copy()
    
    def get_anomaly_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get anomaly history for the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.anomaly_history if a['started_at'] > cutoff]
    
    def force_anomaly(self, sensor_id: str, category: str, anomaly_type: str, duration: int = None):
        """Force inject a specific anomaly (for testing)."""
        if duration:
            # Temporarily override duration
            original_duration = self.anomaly_patterns[category][anomaly_type].get('duration', (5, 30))
            self.anomaly_patterns[category][anomaly_type]['duration'] = (duration, duration)
            
            result = self.inject_anomaly(sensor_id, category, anomaly_type)
            
            # Restore original duration
            self.anomaly_patterns[category][anomaly_type]['duration'] = original_duration
            
            return result
        else:
            return self.inject_anomaly(sensor_id, category, anomaly_type)
    
    def clear_all_anomalies(self):
        """Clear all active anomalies (emergency stop)."""
        count = len(self.active_anomalies)
        self.active_anomalies.clear()
        print(f"🛑 CLEARED {count} active anomalies")