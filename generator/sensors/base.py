"""Base sensor class for all sensor implementations."""
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional
from .anomaly_injector import AnomalyInjector


class BaseSensor:
    """Base class for all sensor types."""
    
    # Global anomaly injector shared across all sensors
    _anomaly_injector = None
    _anomaly_injection_enabled = False
    _anomaly_injection_rate = 0.02  # 2% chance per reading
    
    def __init__(self, location: str, sensor_id: str = None):
        self.location = location
        self.sensor_id = sensor_id or self._generate_sensor_id()
        self.last_value = None
        self.reading_count = 0
        
        # Initialize global anomaly injector if not already done
        if BaseSensor._anomaly_injector is None:
            BaseSensor._anomaly_injector = AnomalyInjector()
    
    @classmethod
    def enable_anomaly_injection(cls, injection_rate: float = 0.02):
        """Enable anomaly injection for all sensors."""
        cls._anomaly_injection_enabled = True
        cls._anomaly_injection_rate = injection_rate
        print(f"🚨 ANOMALY INJECTION ENABLED (rate: {injection_rate:.1%})")
    
    @classmethod
    def disable_anomaly_injection(cls):
        """Disable anomaly injection for all sensors."""
        cls._anomaly_injection_enabled = False
        print("✅ ANOMALY INJECTION DISABLED")
    
    @classmethod
    def force_anomaly(cls, sensor_id: str, category: str, anomaly_type: str, duration: int = None):
        """Force inject an anomaly for testing."""
        if cls._anomaly_injector:
            return cls._anomaly_injector.force_anomaly(sensor_id, category, anomaly_type, duration)
    
    @classmethod
    def get_anomaly_status(cls):
        """Get current anomaly injection status."""
        if cls._anomaly_injector:
            return {
                'enabled': cls._anomaly_injection_enabled,
                'injection_rate': cls._anomaly_injection_rate,
                'active_anomalies': cls._anomaly_injector.get_active_anomalies(),
                'anomaly_history': cls._anomaly_injector.get_anomaly_history(hours=1)
            }
        return {'enabled': False}
    
    def _generate_sensor_id(self) -> str:
        """Generate a unique sensor ID."""
        return f"{self.category}-{self.location}-{str(uuid.uuid4())[:8]}"
    
    @property
    def category(self) -> str:
        """Return the sensor category (oven, heater, etc.)."""
        raise NotImplementedError
    
    @property
    def sensor_type(self) -> str:
        """Return the sensor type (digital, analog)."""
        raise NotImplementedError
    
    @property
    def unit(self) -> str:
        """Return the measurement unit."""
        raise NotImplementedError
    
    @property
    def min_value(self) -> float:
        """Return the minimum possible value."""
        raise NotImplementedError
    
    @property
    def max_value(self) -> float:
        """Return the maximum possible value."""
        raise NotImplementedError
    
    def _generate_realistic_value(self) -> float:
        """Generate a realistic sensor value. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def generate_reading(self, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a sensor reading with optional anomaly injection."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Generate normal value
        value = self._generate_realistic_value()
        
        # Apply anomaly injection if enabled
        if (BaseSensor._anomaly_injection_enabled and 
            BaseSensor._anomaly_injector):
            
            # Check for new anomaly injection
            if BaseSensor._anomaly_injector.should_inject_anomaly(
                self.sensor_id, 
                self.category, 
                BaseSensor._anomaly_injection_rate
            ):
                BaseSensor._anomaly_injector.inject_anomaly(self.sensor_id, self.category)
            
            # Apply existing anomaly
            value = BaseSensor._anomaly_injector.apply_anomaly(
                self.sensor_id, 
                value, 
                self.sensor_type
            )
            
            # Update anomaly states
            BaseSensor._anomaly_injector.update_anomalies()
        
        # Ensure value is within bounds
        value = max(self.min_value, min(self.max_value, value))
        
        # Store last value for next generation
        self.last_value = value
        self.reading_count += 1
        
        return {
            'sensor_id': self.sensor_id,
            'timestamp': timestamp,
            'category': self.category,
            'type': self.sensor_type,
            'value': value,
            'unit': self.unit,
            'location': self.location
        }