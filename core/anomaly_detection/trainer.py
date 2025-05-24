"""
Model training module for anomaly detection.

This module handles the training of anomaly detection models on time series data.
"""

import numpy as np
from typing import Dict, Any, Tuple
from .models import IsolationForestDetector, LOFDetector, OneClassSVMDetector

class ModelTrainer:
    """Utility class for training anomaly detection models."""
    
    def __init__(self):
        self.available_models = {
            'isolation_forest': IsolationForestDetector,
            'lof': LOFDetector,
            'one_class_svm': OneClassSVMDetector
        }
    
    def train_isolation_forest(self, 
                              X: np.ndarray, 
                              contamination: float = 0.1) -> Tuple[IsolationForestDetector, Dict[str, Any]]:
        """Train an Isolation Forest model."""
        model = IsolationForestDetector(contamination=contamination)
        model.fit(X)
        
        metadata = {
            'model_type': 'isolation_forest',
            'contamination': contamination,
            'n_samples': len(X),
            'n_features': X.shape[1] if len(X.shape) > 1 else 1,
            'training_completed': True
        }
        
        return model, metadata
    
    def train_lof(self, 
                  X: np.ndarray, 
                  contamination: float = 0.1,
                  n_neighbors: int = 20) -> Tuple[LOFDetector, Dict[str, Any]]:
        """Train a Local Outlier Factor model."""
        model = LOFDetector(contamination=contamination, n_neighbors=n_neighbors)
        model.fit(X)
        
        metadata = {
            'model_type': 'lof',
            'contamination': contamination,
            'n_neighbors': n_neighbors,
            'n_samples': len(X),
            'n_features': X.shape[1] if len(X.shape) > 1 else 1,
            'training_completed': True
        }
        
        return model, metadata
    
    def train_one_class_svm(self, 
                           X: np.ndarray, 
                           nu: float = 0.1) -> Tuple[OneClassSVMDetector, Dict[str, Any]]:
        """Train a One-Class SVM model."""
        model = OneClassSVMDetector(nu=nu)
        model.fit(X)
        
        metadata = {
            'model_type': 'one_class_svm',
            'nu': nu,
            'n_samples': len(X),
            'n_features': X.shape[1] if len(X.shape) > 1 else 1,
            'training_completed': True
        }
        
        return model, metadata
    
    def auto_select_model(self, 
                         X: np.ndarray, 
                         contamination: float = 0.1) -> Tuple[Any, Dict[str, Any]]:
        """Automatically select the best model based on data characteristics."""
        n_samples = len(X)
        
        # Choose model based on data size
        if n_samples < 1000:
            # For small datasets, use LOF
            return self.train_lof(X, contamination=contamination)
        elif n_samples > 10000:
            # For large datasets, use Isolation Forest (faster)
            return self.train_isolation_forest(X, contamination=contamination)
        else:
            # For medium datasets, use Isolation Forest (good balance)
            return self.train_isolation_forest(X, contamination=contamination)
