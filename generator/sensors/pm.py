"""Particulate Matter (PM) sensor simulation."""
import random
import math
from datetime import datetime
from .base import BaseSensor


class PMSensor(BaseSensor):
    """Simulates a Particulate Matter (PM2.5) sensor with realistic EPA AirWatch environmental patterns."""
    
    def __init__(self, location: str, sensor_id: str = None):
        super().__init__(location, sensor_id)
        self.base_level = self._get_location_base_level()
        self.spike_duration = 0
        self.spike_intensity = 1.0
        self.weather_factor = 1.0
        self.daily_trend = 0
        self.filter_efficiency = random.uniform(0.7, 0.95)
        self.mode_duration = 0
        
    @property
    def category(self) -> str:
        return "pm"
    
    @property
    def sensor_type(self) -> str:
        return "analog"
    
    @property
    def unit(self) -> str:
        return "ug/m3"
    
    @property
    def min_value(self) -> float:
        return 0
    
    @property
    def max_value(self) -> float:
        return 300  # EPA AirWatch "Very poor" max
    
    def _generate_realistic_value(self) -> float:
        """Generate realistic PM2.5 values based on EPA AirWatch categories and location activities."""
        if self.last_value is None:
            self.current_mode = "normal"
            return self.base_level + random.uniform(-2, 2)
        
        current_hour = datetime.now().hour
        is_peak_activity = self._is_peak_activity_time(current_hour)
        is_business_hours = self._is_business_hours(current_hour)
        
        current_pm = self.last_value
        
        # Base drift toward location baseline
        baseline_drift = (self.base_level - current_pm) * 0.1
        current_pm += baseline_drift
        
        if is_peak_activity:
            # Activity-based increases
            if self.location == "restaurant":
                # Cooking activities - can spike to Poor/Very Poor
                if random.random() < 0.25:  # 25% chance of cooking spike
                    cooking_spike = random.uniform(20, 60)  # Into Poor range (50-100)
                    current_pm += cooking_spike
                else:
                    current_pm += random.uniform(5, 15)  # Regular cooking increase
                    
            elif self.location == "factory":
                # Industrial activities - frequent Poor/Very Poor spikes
                if random.random() < 0.3:  # 30% chance of industrial spike
                    industrial_spike = random.uniform(30, 80)  # Into Poor/Very Poor range
                    current_pm += industrial_spike
                else:
                    current_pm += random.uniform(8, 20)  # Regular industrial increase
                    
            elif self.location == "supermarket":
                # Minimal increase from customer activity
                current_pm += random.uniform(2, 8)
        else:
            # Non-peak periods - gradual decrease
            if current_pm > self.base_level:
                # Air filtration and natural settling
                if is_business_hours:
                    reduction = random.uniform(3, 8)  # HVAC active
                else:
                    reduction = random.uniform(1, 5)  # Natural settling
                current_pm -= reduction
            else:
                # Small fluctuations around baseline
                current_pm += random.uniform(-3, 3)
        
        # Location-specific extreme events
        if random.random() < 0.05:  # 5% chance of extreme event
            if self.location == "restaurant":
                # Burnt food, grease fire, etc. - Very Poor range
                extreme_spike = random.uniform(50, 120)  # Very Poor (100-300)
                current_pm += extreme_spike
            elif self.location == "factory":
                # Equipment malfunction, dust explosion, etc.
                extreme_spike = random.uniform(80, 150)  # Very Poor range
                current_pm += extreme_spike
        
        # Weather effects
        if random.random() < 0.02:  # 2% chance of weather event
            weather_multiplier = random.uniform(1.5, 3.0)  # Dust storms, etc.
            current_pm *= weather_multiplier
        
        # Ensure we stay within EPA AirWatch ranges
        return max(self.min_value, min(self.max_value, current_pm))
    
    def _get_location_base_level(self) -> float:
        """Get baseline PM2.5 levels based on location type (EPA AirWatch ranges)."""
        location_baselines = {
            # Restaurant: Fair to Poor baseline (cooking environment)
            "restaurant": random.uniform(30, 45),      # Fair (25-50) to Poor entry
            
            # Supermarket: Good to Fair baseline (retail environment)
            "supermarket": random.uniform(15, 28),     # Good (>25) to Fair (25-50)
            
            # Factory: Poor baseline (industrial environment)
            "factory": random.uniform(55, 75),         # Poor (50-100) range
        }
        return location_baselines.get(self.location, 25)
    
    def _is_peak_activity_time(self, hour: int) -> bool:
        """Determine if current hour is peak activity time for the location."""
        if self.location == "restaurant":
            return hour in [11, 12, 13, 18, 19, 20, 21]  # Meal preparation times
        elif self.location == "supermarket":
            return hour in [9, 10, 11, 17, 18, 19, 20]   # Peak shopping hours
        elif self.location == "factory":
            return hour in [7, 8, 9, 10, 13, 14, 15, 16] # Active production shifts
        return False
    
    def _is_business_hours(self, hour: int) -> bool:
        """Check if current hour is business hours (affects HVAC/filtration)."""
        if self.location == "restaurant":
            return hour in range(10, 24)  # 10 AM - 12 AM
        elif self.location == "supermarket":
            return hour in range(7, 22)   # 7 AM - 10 PM
        elif self.location == "factory":
            return hour in range(6, 18)   # 6 AM - 6 PM
        return False