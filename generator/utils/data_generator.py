"""Utility functions for generating sample sensor data."""
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..sensors import OvenSensor, HeaterSensor, LampSensor, PMSensor, DigitalFanSensor, RPMFanSensor

LOCATIONS = ["restaurant", "supermarket", "factory"]

SENSOR_CLASSES = [
    OvenSensor,
    HeaterSensor,
    LampSensor,
    RPMFanSensor,
    PMSensor,
]

def generate_sensor_id(sensor_type: str, location: str) -> str:
    """Generate a unique sensor ID based on type and location."""
    return f"{sensor_type}-{location}-{str(uuid.uuid4())[:8]}"

def create_sensor_fleet(num_sensors: int) -> List:
    """Create a fleet of various sensors using all sensor classes in order."""
    sensors = []
    num_sensor_classes = len(SENSOR_CLASSES)
    for i in range(num_sensors):
        sensor_class = SENSOR_CLASSES[i % num_sensor_classes]
        location = random.choice(LOCATIONS)
        sensor = sensor_class(location)
        sensors.append(sensor)
        # For RPM fan sensors, create correlated digital fan and lamp sensors
        if sensor_class == RPMFanSensor:
            # Create digital fan sensor linked to RPM fan
            digital_fan = DigitalFanSensor(location)
            digital_fan.set_rpm_sensor(sensor)  # Link digital fan to RPM fan
            sensors.append(digital_fan)
    return sensors

def generate_sensor_reading(
    sensor: Any,  # Changed from sensor_type to sensor object
    timestamp: datetime,
    last_value: float = None,
    state_duration: int = 5,
    noise_level: float = 0.1,
) -> Dict[str, Any]:
    """
    Generate a single sensor reading with realistic values using sensor classes.

    Args:
        sensor (Any): Sensor object instance.
        timestamp (datetime): Timestamp for the reading.
        last_value (float): Last recorded value for the sensor.
        state_duration (int): Number of readings to maintain the same state.
        noise_level (float): Noise level for analog sensors.

    Returns:
        Dict[str, Any]: Sensor reading.
    """
    # Use the sensor's generate_reading method instead of manual logic
    return sensor.generate_reading(timestamp)

def generate_time_series(
    start_time: datetime,
    end_time: datetime,
    interval: int = 300,  # 5 minutes in seconds
    num_sensors: int = 6,
) -> List[Dict[str, Any]]:
    """Generate time series data for multiple sensors."""
    data = []
    sensors = create_sensor_fleet(num_sensors)
    
    current_time = start_time
    while current_time <= end_time:
        for sensor in sensors:
            reading = sensor.generate_reading(current_time)
            data.append(reading)
        
        current_time += timedelta(seconds=interval)
    
    return data
