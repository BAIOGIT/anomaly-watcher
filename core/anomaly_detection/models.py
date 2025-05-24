"""
Data models and schemas for the anomaly detection module.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Dict, Tuple
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

@dataclass
class AnomalyDetectionModel:
    """
    Wrapper class for anomaly detection models with additional metadata.
    """
    model: BaseEstimator
    scaler: Any  # Typically a scikit-learn scaler
    feature_names: Optional[List[str]] = None
    contamination: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict if samples are anomalies.
        
        Args:
            X: Input data (n_samples, n_features)
            
        Returns:
            Array of predictions (1 for anomaly, -1 for normal)
        """
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Compute the anomaly score for each sample.
        
        Args:
            X: Input data (n_samples, n_features)
            
        Returns:
            Array of anomaly scores (lower scores are more anomalous)
        """
        X_scaled = self.scaler.transform(X)
        return self.model.score_samples(X_scaled)
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Compute the decision function of the model.
        
        Args:
            X: Input data (n_samples, n_features)
            
        Returns:
            Array of decision function values (higher values are more anomalous)
        """
        return -self.score_samples(X)  # Convert to positive is better

@dataclass
class TrainingConfig:
    """Configuration for model training."""
    contamination: float = 0.1
    random_state: int = 42
    test_size: float = 0.2
    n_estimators: int = 100
    max_samples: str = 'auto'
    max_features: float = 1.0
    bootstrap: bool = False
    n_jobs: int = -1
    verbose: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'contamination': self.contamination,
            'random_state': self.random_state,
            'n_estimators': self.n_estimators,
            'max_samples': self.max_samples,
            'max_features': self.max_features,
            'bootstrap': self.bootstrap,
            'n_jobs': self.n_jobs,
            'verbose': self.verbose
        }

@dataclass
class AnomalyDetectionResult:
    """Container for anomaly detection results."""
    is_anomaly: np.ndarray
    anomaly_scores: np.ndarray
    decision_scores: Optional[np.ndarray] = None
    threshold: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            'is_anomaly': self.is_anomaly.tolist(),
            'anomaly_scores': self.anomaly_scores.tolist(),
            'decision_scores': self.decision_scores.tolist() if self.decision_scores is not None else None,
            'threshold': self.threshold
        }

class BaseAnomalyDetector:
    """Base class for anomaly detectors."""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def fit(self, X: np.ndarray):
        """Fit the model to training data."""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict anomalies. Returns (is_anomaly, scores)."""
        raise NotImplementedError


class IsolationForestDetector(BaseAnomalyDetector):
    """Isolation Forest anomaly detector."""
    
    def __init__(self, contamination: float = 0.1, n_estimators: int = 100, random_state: int = 42):
        super().__init__()
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1
        )
        self.contamination = contamination
    
    def fit(self, X: np.ndarray):
        """Fit the Isolation Forest model."""
        # Scale the features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict anomalies using Isolation Forest."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Scale the features
        X_scaled = self.scaler.transform(X)
        
        # Get predictions (-1 = anomaly, 1 = normal)
        predictions = self.model.predict(X_scaled)
        is_anomaly = predictions == -1
        
        # Get anomaly scores (lower = more anomalous)
        scores = self.model.score_samples(X_scaled)
        # Convert to positive scores (higher = more anomalous)
        anomaly_scores = -scores
        
        return is_anomaly, anomaly_scores


class LOFDetector(BaseAnomalyDetector):
    """Local Outlier Factor anomaly detector."""
    
    def __init__(self, contamination: float = 0.1, n_neighbors: int = 20):
        super().__init__()
        self.model = LocalOutlierFactor(
            contamination=contamination,
            n_neighbors=n_neighbors,
            novelty=True  # Enable prediction on new data
        )
        self.contamination = contamination
    
    def fit(self, X: np.ndarray):
        """Fit the LOF model."""
        # Scale the features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict anomalies using LOF."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Scale the features
        X_scaled = self.scaler.transform(X)
        
        # Get predictions (-1 = anomaly, 1 = normal)
        predictions = self.model.predict(X_scaled)
        is_anomaly = predictions == -1
        
        # Get anomaly scores (lower = more anomalous)
        scores = self.model.score_samples(X_scaled)
        # Convert to positive scores (higher = more anomalous)
        anomaly_scores = -scores
        
        return is_anomaly, anomaly_scores


class OneClassSVMDetector(BaseAnomalyDetector):
    """One-Class SVM anomaly detector."""
    
    def __init__(self, nu: float = 0.1, kernel: str = 'rbf', gamma: str = 'scale'):
        super().__init__()
        self.model = OneClassSVM(
            nu=nu,
            kernel=kernel,
            gamma=gamma
        )
        self.nu = nu
    
    def fit(self, X: np.ndarray):
        """Fit the One-Class SVM model."""
        # Scale the features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict anomalies using One-Class SVM."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Scale the features
        X_scaled = self.scaler.transform(X)
        
        # Get predictions (-1 = anomaly, 1 = normal)
        predictions = self.model.predict(X_scaled)
        is_anomaly = predictions == -1
        
        # Get decision function scores (higher = more normal)
        scores = self.model.decision_function(X_scaled)
        # Convert to anomaly scores (higher = more anomalous)
        anomaly_scores = -scores.flatten()
        
        return is_anomaly, anomaly_scores
