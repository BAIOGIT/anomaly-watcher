"""Lamp sensor simulation."""
import random
from datetime import datetime
from .base import BaseSensor


class LampSensor(BaseSensor):
    """Simulates a digital lamp sensor with realistic day/night and occupancy patterns."""
    
    def __init__(self, location: str, sensor_id: str = None):
        super().__init__(location, sensor_id)
        self.on_duration = 0
        self.off_duration = 0
        self.occupancy_detected = False
        self.motion_timeout = 0
        self.scheduled_on = False
        
    @property
    def category(self) -> str:
        return "lamp"
    
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
        """Generate realistic lamp on/off pattern based on business hours and occupancy."""
        if self.last_value is None:
            self.current_mode = "off"
            return 0
        
        current_hour = datetime.now().hour
        is_business_hours = self._is_business_hours(current_hour)
        is_dark_hours = self._is_dark_hours(current_hour)
        
        # Simulate occupancy/motion detection
        self._update_occupancy(is_business_hours)
        
        # Determine if lights should be scheduled on
        self.scheduled_on = is_business_hours or (is_dark_hours and self.occupancy_detected)
        
        current_state = int(self.last_value)
        
        if current_state == 0:  # Currently OFF
            self.off_duration += 1
            self.on_duration = 0
            
            # Turn on conditions
            should_turn_on = False
            
            if self.scheduled_on:
                # High probability during business hours
                if is_business_hours:
                    should_turn_on = random.random() < 0.8
                # Medium probability for motion detection after hours
                elif self.occupancy_detected:
                    should_turn_on = random.random() < 0.6
            
            # Additional logic for specific locations
            if self.location == "restaurant":
                # Ambient lighting even when closed for security
                if not is_business_hours and random.random() < 0.1:
                    should_turn_on = True
            elif self.location == "supermarket":
                # Some lights stay on for restocking/cleaning
                if 22 <= current_hour <= 6 and random.random() < 0.3:
                    should_turn_on = True
            elif self.location == "factory":
                # Emergency/security lighting
                if not is_business_hours and random.random() < 0.05:
                    should_turn_on = True
            
            if should_turn_on and self.off_duration > random.randint(1, 10):
                self.current_mode = "on"
                return 1
                
        else:  # Currently ON
            self.on_duration += 1
            self.off_duration = 0
            
            # Turn off conditions
            should_turn_off = False
            
            if not self.scheduled_on:
                # High probability to turn off outside business hours
                if not is_business_hours and not self.occupancy_detected:
                    should_turn_off = random.random() < 0.7
                # Turn off when no motion detected
                elif self.motion_timeout > 10:
                    should_turn_off = random.random() < 0.8
            
            # Random turn off even during business hours (motion sensors, energy saving)
            if is_business_hours and self.on_duration > random.randint(30, 180):
                if random.random() < 0.1:  # 10% chance
                    should_turn_off = True
            
            # Location-specific turn-off behavior
            if self.location == "restaurant":
                # Lights turned off in unused sections
                if is_business_hours and random.random() < 0.05:
                    should_turn_off = True
            elif self.location == "supermarket":
                # Section-based lighting control
                if is_business_hours and self.on_duration > 60 and random.random() < 0.1:
                    should_turn_off = True
            
            if should_turn_off:
                self.current_mode = "off"
                return 0
        
        return current_state
    
    def _is_business_hours(self, hour: int) -> bool:
        """Check if current hour is business hours."""
        if self.location == "restaurant":
            return hour in range(11, 24)  # 11 AM - 12 AM
        elif self.location == "supermarket":
            return hour in range(8, 22)   # 8 AM - 10 PM
        elif self.location == "factory":
            return hour in range(6, 18)   # 6 AM - 6 PM
        return False
    
    def _is_dark_hours(self, hour: int) -> bool:
        """Check if it's dark hours when lighting is typically needed."""
        # Approximate dark hours (varies by season, but this is simplified)
        return hour in list(range(18, 24)) + list(range(0, 7))
    
    def _update_occupancy(self, is_business_hours: bool) -> None:
        """Simulate occupancy/motion detection."""
        if is_business_hours:
            # High occupancy during business hours
            self.occupancy_detected = random.random() < 0.9
            self.motion_timeout = 0 if self.occupancy_detected else self.motion_timeout + 1
        else:
            # Lower occupancy outside business hours
            if self.occupancy_detected:
                # Motion timeout - reduce occupancy detection over time
                self.motion_timeout += 1
                if self.motion_timeout > random.randint(5, 20):
                    self.occupancy_detected = False
                    self.motion_timeout = 0
            else:
                # Occasional motion detection (security, cleaning, etc.)
                if random.random() < 0.1:
                    self.occupancy_detected = True
                    self.motion_timeout = 0