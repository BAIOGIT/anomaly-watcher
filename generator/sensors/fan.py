"""Fan sensor simulation (both digital and RPM)."""
import random
import math
from datetime import datetime
from .base import BaseSensor


class DigitalFanSensor(BaseSensor):
    """Simulates a digital fan on/off sensor linked to RPM fan operation."""
    
    def __init__(self, location: str, sensor_id: str = None, rpm_sensor=None):
        super().__init__(location, sensor_id)
        self.rpm_sensor = rpm_sensor  # Reference to associated RPM sensor
        self.startup_delay = 0
        self.shutdown_delay = 0
        self.manual_override = False
        self.override_duration = 0
        
    @property
    def category(self) -> str:
        return "fan"
    
    @property
    def sensor_type(self) -> str:
        return "digital"
    
    @property
    def unit(self) -> str:
        return "io"
    
    @property
    def min_value(self) -> float:
        return 0
    
    @property
    def max_value(self) -> float:
        return 1
    
    def _generate_realistic_value(self) -> float:
        """Generate digital fan state based on RPM sensor status."""
        if self.last_value is None:
            return 0
        
        # Get RPM from associated sensor
        fan_rpm = 0
        if self.rpm_sensor and hasattr(self.rpm_sensor, 'last_value') and self.rpm_sensor.last_value:
            fan_rpm = self.rpm_sensor.last_value
        
        current_state = int(self.last_value)
        
        # Handle manual override (maintenance, testing, etc.)
        if self.manual_override:
            self.override_duration += 1
            if self.override_duration > random.randint(10, 50):
                self.manual_override = False
                self.override_duration = 0
            return current_state  # Keep current state during override
        
        # Main logic: digital fan follows RPM sensor
        if fan_rpm > 10:  # RPM fan is running
            if current_state == 0:  # Digital fan is OFF
                # Small startup delay for realistic behavior
                self.startup_delay += 1
                if self.startup_delay > random.randint(1, 3):
                    self.startup_delay = 0
                    return 1  # Turn ON
                return 0  # Still in startup delay
            else:  # Digital fan is already ON
                self.shutdown_delay = 0
                return 1  # Keep ON
                
        else:  # RPM fan is stopped (RPM ≤ 10)
            if current_state == 1:  # Digital fan is ON
                # Small shutdown delay for realistic behavior
                self.shutdown_delay += 1
                if self.shutdown_delay > random.randint(1, 5):
                    self.shutdown_delay = 0
                    return 0  # Turn OFF
                return 1  # Still in shutdown delay
            else:  # Digital fan is already OFF
                self.startup_delay = 0
                
                # Occasional manual override (testing, maintenance)
                if random.random() < 0.02:  # 2% chance
                    self.manual_override = True
                    self.override_duration = 0
                    return 1
                
                return 0  # Keep OFF
    
    def set_rpm_sensor(self, rpm_sensor):
        """Set the associated RPM sensor for correlation."""
        self.rpm_sensor = rpm_sensor


class RPMFanSensor(BaseSensor):
    """Simulates a fan RPM sensor with realistic acceleration/deceleration."""
    
    def __init__(self, location: str, sensor_id: str = None):
        super().__init__(location, sensor_id)
        self.target_rpm = 0
        self.acceleration = random.uniform(15, 25)  # RPM change per reading
        self.deceleration = random.uniform(20, 30)  # RPM change per reading
        self.speed_levels = self._get_speed_levels()
        self.current_speed_level = 0
        self.vibration_amplitude = 0
        
    @property
    def category(self) -> str:
        return "fan"
    
    @property
    def sensor_type(self) -> str:
        return "analog"
    
    @property
    def unit(self) -> str:
        return "rpm"
    
    @property
    def min_value(self) -> float:
        return 0
    
    @property
    def max_value(self) -> float:
        return 1200
    
    def _generate_realistic_value(self) -> float:
        """Generate realistic RPM values with proper acceleration curves."""
        if self.last_value is None:
            return 0
        
        current_hour = datetime.now().hour
        is_business_hours = self._is_business_hours(current_hour)
        
        # Change speed level based on demand
        if random.random() < 0.1:  # 10% chance to change speed
            self.current_speed_level = self._get_demand_speed_level(current_hour, is_business_hours)
            self.target_rpm = self.speed_levels[self.current_speed_level]
            
        current_rpm = self.last_value
        rpm_difference = self.target_rpm - current_rpm
        
        # Realistic acceleration/deceleration curves
        if abs(rpm_difference) > 10:
            if rpm_difference > 0:  # Accelerating
                # Motor startup characteristics - slower at low RPM, faster in mid-range
                if current_rpm < 100:
                    accel_rate = self.acceleration * 0.6  # Slower startup
                elif current_rpm < 300:
                    accel_rate = self.acceleration * 1.2  # Faster mid-range
                else:
                    accel_rate = self.acceleration * 0.8  # Slower at high RPM
                
                rpm_change = random.uniform(accel_rate * 0.8, accel_rate * 1.2)
                current_rpm = min(self.target_rpm, current_rpm + rpm_change)
                
            else:  # Decelerating
                # Deceleration with motor braking and friction
                decel_rate = self.deceleration
                if current_rpm > 800:
                    decel_rate *= 1.3  # Air resistance increases
                
                rpm_change = random.uniform(decel_rate * 0.8, decel_rate * 1.2)
                current_rpm = max(self.target_rpm, current_rpm - rpm_change)
        
        # Add realistic vibration and bearing noise
        if current_rpm > 0:
            # Vibration increases with RPM and age simulation
            self.vibration_amplitude = min(15, current_rpm / 80 + random.uniform(0, 5))
            vibration = random.uniform(-self.vibration_amplitude, self.vibration_amplitude)
            current_rpm += vibration
            
            # Periodic maintenance effects (bearing wear, imbalance)
            if random.random() < 0.01:  # 1% chance of mechanical noise
                current_rpm += random.uniform(-20, 20)
        
        # Motor cogging at very low speeds
        if 0 < current_rpm < 50:
            current_rpm += random.uniform(-10, 10)
        
        return max(0, min(self.max_value, current_rpm))
    
    def _is_business_hours(self, hour: int) -> bool:
        """Check if current hour is business hours."""
        if self.location == "restaurant":
            return hour in range(10, 23)
        elif self.location == "supermarket":
            return hour in range(7, 22)
        elif self.location == "factory":
            return hour in range(6, 18)
        return False
    
    def _get_speed_levels(self) -> list:
        """Get realistic speed levels for different fan applications."""
        if self.location == "restaurant":
            # Kitchen exhaust fan speeds
            return [0, 200, 400, 600, 800, 1000]
        elif self.location == "supermarket":
            # HVAC circulation fan speeds
            return [0, 150, 300, 500, 700, 900]
        elif self.location == "factory":
            # Industrial ventilation fan speeds
            return [0, 300, 500, 700, 900, 1200]
        return [0, 200, 400, 600, 800, 1000]
    
    def _get_demand_speed_level(self, hour: int, is_business_hours: bool) -> int:
        """Determine appropriate speed level based on demand."""
        if not is_business_hours:
            # Low speed for security/maintenance ventilation
            return random.choice([0, 1])
        
        # Business hours demand based on location
        if self.location == "restaurant":
            if hour in [11, 12, 13, 18, 19, 20, 21]:  # Meal times
                return random.choice([3, 4, 5])  # High speed
            else:
                return random.choice([1, 2, 3])  # Medium speed
                
        elif self.location == "supermarket":
            if hour in [10, 11, 17, 18, 19]:  # Peak shopping
                return random.choice([2, 3, 4])  # Medium-high speed
            else:
                return random.choice([1, 2])     # Low-medium speed
                
        elif self.location == "factory":
            if hour in [8, 9, 10, 14, 15, 16]:  # Active work periods
                return random.choice([3, 4, 5])  # High speed
            else:
                return random.choice([2, 3])     # Medium speed
        
        return random.choice([1, 2, 3])  # Default medium range