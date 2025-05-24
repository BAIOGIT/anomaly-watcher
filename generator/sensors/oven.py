"""Oven temperature sensor simulation."""
import random
from datetime import datetime
from .base import BaseSensor


class OvenSensor(BaseSensor):
    """Simulates an industrial oven temperature sensor."""
    
    def __init__(self, location: str, sensor_id: str = None):
        super().__init__(location, sensor_id)
        self.target_temp = 25.0
        self.heating_rate = random.uniform(8, 15)  # degrees per minute
        self.cooling_rate = random.uniform(3, 6)   # degrees per minute
        self.modes = ["off", "preheating", "cooking", "cooling", "maintenance"]
        self.mode_duration = 0
        self.cycle_count = 0
        self.last_maintenance = 0
        
    @property
    def category(self) -> str:
        return "oven"
    
    @property
    def sensor_type(self) -> str:
        return "analog"
    
    @property
    def unit(self) -> str:
        return "C"
    
    @property
    def min_value(self) -> float:
        return 15
    
    @property
    def max_value(self) -> float:
        return 350
    
    def _generate_realistic_value(self) -> float:
        """Generate realistic oven temperature based on operating modes."""
        if self.last_value is None:
            self.current_mode = "off"
            return random.uniform(20, 25)  # Room temperature start
        
        self.mode_duration += 1
        current_hour = datetime.now().hour
        is_business_hours = self._is_business_hours(current_hour)
        
        # Mode transitions based on realistic patterns
        if self.current_mode == "off":
            # Start heating during business hours or based on schedule
            start_probability = 0.15 if is_business_hours else 0.03
            if (self.mode_duration > random.randint(10, 60) and 
                random.random() < start_probability):
                self.current_mode = "preheating"
                # Realistic cooking temperatures by location
                self.target_temp = self._get_cooking_temperature()
                self.mode_duration = 0
                
        elif self.current_mode == "preheating":
            # Move to cooking when near target temperature
            if abs(self.last_value - self.target_temp) < 15:
                self.current_mode = "cooking"
                self.mode_duration = 0
                
        elif self.current_mode == "cooking":
            # Cook for realistic duration based on location
            cooking_time = self._get_cooking_duration()
            if self.mode_duration > cooking_time:
                self.current_mode = "cooling"
                self.cycle_count += 1
                self.mode_duration = 0
                
        elif self.current_mode == "cooling":
            # Cool down and decide next action
            if self.last_value < 80:
                # Check if maintenance is needed
                if (self.cycle_count > random.randint(8, 15) and 
                    self.last_maintenance > 50):
                    self.current_mode = "maintenance"
                    self.last_maintenance = 0
                    self.cycle_count = 0
                else:
                    self.current_mode = "off"
                self.mode_duration = 0
                
        elif self.current_mode == "maintenance":
            # Maintenance mode (cleaning cycle)
            if self.mode_duration > random.randint(15, 30):
                self.current_mode = "off"
                self.mode_duration = 0
        
        self.last_maintenance += 1
        
        # Calculate temperature based on current mode
        current_temp = self.last_value
        
        if self.current_mode == "off":
            # Natural cooling to ambient temperature
            ambient = self._get_ambient_temperature()
            if current_temp > ambient + 2:
                cooling = random.uniform(0.5, 2.0)
                current_temp = max(ambient, current_temp - cooling)
            else:
                current_temp = ambient + random.uniform(-1, 1)
                
        elif self.current_mode == "preheating":
            # Rapid heating with realistic physics
            if current_temp < self.target_temp:
                # Heating slows down as it approaches target (thermal dynamics)
                temp_diff = self.target_temp - current_temp
                heat_rate = self.heating_rate * min(1.0, temp_diff / 100)
                current_temp += random.uniform(heat_rate * 0.8, heat_rate * 1.2)
            return min(self.target_temp + 10, current_temp)
            
        elif self.current_mode == "cooking":
            # Maintain temperature with realistic fluctuations
            temp_variance = 8 if self.location == "restaurant" else 5
            fluctuation = random.uniform(-temp_variance, temp_variance)
            
            # Thermostat behavior - heating elements cycle on/off
            if current_temp < self.target_temp - temp_variance:
                current_temp += random.uniform(2, 8)  # Heating element on
            elif current_temp > self.target_temp + temp_variance:
                current_temp -= random.uniform(1, 4)  # Natural heat loss
            else:
                current_temp += fluctuation
                
        elif self.current_mode == "cooling":
            # Gradual cooling with thermal mass
            cooling_rate = self.cooling_rate
            if current_temp > 150:
                cooling_rate *= 1.5  # Faster cooling when very hot
            elif current_temp < 100:
                cooling_rate *= 0.7  # Slower cooling as it approaches ambient
                
            current_temp -= random.uniform(cooling_rate * 0.8, cooling_rate * 1.2)
            
        elif self.current_mode == "maintenance":
            # High temperature cleaning cycle
            if self.mode_duration < 5:
                # Heat up for cleaning
                current_temp += random.uniform(5, 15)
                self.target_temp = random.uniform(200, 250)
            else:
                # Maintain cleaning temperature
                current_temp = self.target_temp + random.uniform(-10, 10)
        
        return max(self.min_value, min(self.max_value, current_temp))
    
    def _is_business_hours(self, hour: int) -> bool:
        """Check if current hour is business hours based on location."""
        if self.location == "restaurant":
            return hour in range(10, 23)  # 10 AM - 11 PM
        elif self.location == "supermarket":
            return hour in range(6, 22)   # 6 AM - 10 PM (bakery section)
        elif self.location == "factory":
            return hour in range(6, 18)   # 6 AM - 6 PM
        return False
    
    def _get_cooking_temperature(self) -> float:
        """Get realistic cooking temperature based on location."""
        if self.location == "restaurant":
            # Various cooking temperatures
            return random.choice([180, 200, 220, 250, 280, 300])
        elif self.location == "supermarket":
            # Bakery items
            return random.choice([160, 180, 200, 220])
        elif self.location == "factory":
            # Industrial heating/drying
            return random.choice([120, 150, 180, 200, 250])
        return 200
    
    def _get_cooking_duration(self) -> int:
        """Get realistic cooking duration in minutes."""
        if self.location == "restaurant":
            return random.randint(15, 90)  # 15-90 minutes
        elif self.location == "supermarket":
            return random.randint(30, 120) # 30-120 minutes for baking
        elif self.location == "factory":
            return random.randint(60, 180) # 1-3 hours for industrial processes
        return 60
    
    def _get_ambient_temperature(self) -> float:
        """Get ambient temperature based on location."""
        if self.location == "restaurant":
            return random.uniform(22, 28)  # Kitchen ambient
        elif self.location == "supermarket":
            return random.uniform(18, 24)  # Store ambient
        elif self.location == "factory":
            return random.uniform(15, 30)  # Industrial ambient
        return 22