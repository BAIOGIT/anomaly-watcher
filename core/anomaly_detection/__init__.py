"""
Anomaly Detection Module

This module provides functionality for training anomaly detection models
and detecting anomalies in time series data.
"""

__version__ = '0.1.0'

from .trainer import ModelTrainer
from .detector import SensorAnomalyDetector
from .models import AnomalyDetectionModel

__all__ = ['ModelTrainer', 'SensorAnomalyDetector', 'AnomalyDetectionModel']
