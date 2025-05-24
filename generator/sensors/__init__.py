"""Sensor simulation modules for different industrial equipment categories."""

from .oven import OvenSensor
from .heater import HeaterSensor
from .lamp import LampSensor
from .fan import DigitalFanSensor, RPMFanSensor
from .pm import PMSensor

__all__ = ['OvenSensor', 'HeaterSensor', 'LampSensor', 'DigitalFanSensor', 'RPMFanSensor', 'PMSensor']