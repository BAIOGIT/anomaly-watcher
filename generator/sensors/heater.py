"""Heater temperature sensor simulation."""
import random
from datetime import datetime
from .base import BaseSensor


class HeaterSensor(BaseSensor):
    """Simulates an industrial heater temperature sensor."""
    
    def __init__(self, location: str, sensor_id: str = None):
        super().__init__(location, sensor_id)
        self.target_temp = 20.0
        self.heating_rate = random.uniform(5, 10)   # degrees per minute
        self.cooling_rate = random.uniform(2, 4)    # degrees per minute
        self.modes = ["off", "heating", "maintaining", "eco_mode"]
        self.mode_duration = 0
        self.thermostat_deadband = 3  # Temperature tolerance
        self.eco_active = False
        
    @property
    def category(self) -> str:
        return "heater"
    
    @property
    def sensor_type(self) -> str:
        return "analog"
    
    @property
    def unit(self) -> str:
        return "C"
    
    @property
    def min_value(self) -> float:
        return 5
    
    @property
    def max_value(self) -> float:
        return 180
    
    def _generate_realistic_value(self) -> float:
        """Generate realistic heater temperature based on operating modes."""
        if self.last_value is None:
            self.current_mode = "off"
            return self._get_ambient_temperature()
        
        self.mode_duration += 1
        current_hour = datetime.now().hour
        is_business_hours = self._is_business_hours(current_hour)
        is_cold_period = self._is_cold_period(current_hour)
        
        # Dynamic target temperature based on time and location
        if is_business_hours:
            self.target_temp = self._get_comfort_temperature()
        elif is_cold_period:
            self.target_temp = self._get_comfort_temperature() - 5  # Lower at night
            self.eco_active = True
        else:
            self.target_temp = self._get_ambient_temperature() + 5
            self.eco_active = True
        
        current_temp = self.last_value
        temp_diff = current_temp - self.target_temp
        
        # Mode transitions with realistic thermostat logic
        if self.current_mode == "off":
            # Start heating if temperature drops below target
            if temp_diff < -self.thermostat_deadband:
                self.current_mode = "heating"
                self.mode_duration = 0
            # Natural cooling continues
            else:
                current_temp = self._apply_natural_cooling(current_temp)
                
        elif self.current_mode == "heating":
            # Stop heating when target is reached
            if temp_diff > self.thermostat_deadband:
                self.current_mode = "maintaining"
                self.mode_duration = 0
            else:
                # Continue heating
                heat_gain = self._calculate_heat_gain()
                current_temp += heat_gain
                
        elif self.current_mode == "maintaining":
            # Thermostat cycling behavior
            if temp_diff < -self.thermostat_deadband:
                self.current_mode = "heating"
                self.mode_duration = 0
            elif not is_business_hours and self.mode_duration > 30:
                # Switch to eco mode outside business hours
                self.current_mode = "eco_mode"
                self.mode_duration = 0
            else:
                # Small fluctuations around target
                current_temp = self._maintain_temperature(current_temp)
                
        elif self.current_mode == "eco_mode":
            # Energy saving mode
            if is_business_hours:
                self.current_mode = "heating"
                self.eco_active = False
                self.mode_duration = 0
            else:
                # Minimal heating to prevent freezing
                min_temp = self._get_ambient_temperature()
                if current_temp < min_temp:
                    current_temp += random.uniform(0.5, 2.0)
                else:
                    current_temp = self._apply_natural_cooling(current_temp)
        
        return max(self.min_value, min(self.max_value, current_temp))
    
    def _is_business_hours(self, hour: int) -> bool:
        """Check if current hour is business hours."""
        if self.location == "restaurant":
            return hour in range(9, 24)   # 9 AM - 12 AM
        elif self.location == "supermarket":
            return hour in range(7, 22)   # 7 AM - 10 PM
        elif self.location == "factory":
            return hour in range(6, 18)   # 6 AM - 6 PM
        return False
    
    def _is_cold_period(self, hour: int) -> bool:
        """Check if it's typically colder (night/early morning)."""
        return hour in range(22, 6)  # 10 PM - 6 AM
    
    def _get_ambient_temperature(self) -> float:
        """Get ambient temperature based on location and time."""
        base_temps = {
            "restaurant": random.uniform(16, 22),
            "supermarket": random.uniform(18, 24),
            "factory": random.uniform(12, 20)
        }
        
        # Add seasonal/daily variation
        variation = random.uniform(-3, 3)
        return base_temps.get(self.location, 18) + variation
    
    def _get_comfort_temperature(self) -> float:
        """Get target comfort temperature based on location."""
        comfort_temps = {
            "restaurant": random.uniform(22, 26),  # Customer comfort
            "supermarket": random.uniform(20, 24), # Shopping comfort
            "factory": random.uniform(18, 22)      # Worker comfort
        }
        return comfort_temps.get(self.location, 22)
    
    def _calculate_heat_gain(self) -> float:
        """Calculate heating rate based on current conditions."""
        base_rate = self.heating_rate
        
        # Reduce efficiency in eco mode
        if self.eco_active:
            base_rate *= 0.7
        
        # Add realistic variance
        return random.uniform(base_rate * 0.8, base_rate * 1.2)
    
    def _apply_natural_cooling(self, current_temp: float) -> float:
        """Apply natural heat loss to environment."""
        ambient = self._get_ambient_temperature()
        temp_diff = current_temp - ambient
        
        if temp_diff > 1:
            # Newton's law of cooling - faster cooling when temp difference is larger
            cooling_rate = self.cooling_rate * min(1.5, temp_diff / 20)
            current_temp -= random.uniform(cooling_rate * 0.5, cooling_rate * 1.2)
        else:
            # Small fluctuations around ambient
            current_temp = ambient + random.uniform(-1, 1)
            
        return current_temp
    
    def _maintain_temperature(self, current_temp: float) -> float:
        """Maintain temperature with small fluctuations."""
        # Realistic thermostat behavior with overshoot/undershoot
        variance = 2 if self.eco_active else 1
        fluctuation = random.uniform(-variance, variance)
        
        # Slight trend toward target temperature
        temp_diff = current_temp - self.target_temp
        drift = -temp_diff * 0.1
        
        return current_temp + fluctuation + drift