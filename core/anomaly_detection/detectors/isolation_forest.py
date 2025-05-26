"""Isolation Forest based anomaly detector."""
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class IsolationForestDetector:
    """Isolation Forest anomaly detector."""
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize Isolation Forest detector.
        
        Args:
            contamination: Expected proportion of outliers in the dataset
            random_state: Random state for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        
    def detect(self, values: List[float]) -> List[float]:
        """
        Detect anomalies in the given values.
        
        Args:
            values: List of sensor values
            
        Returns:
            List of anomaly scores (0-1, where 1 is most anomalous)
        """
        if len(values) < 5:
            # Not enough data for detection
            return [0.0] * len(values)
        
        try:
            # Convert to numpy array and reshape
            data = np.array(values).reshape(-1, 1)
            
            # Scale the data
            scaled_data = self.scaler.fit_transform(data)
            
            # Initialize and fit the model
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100
            )
            
            # Fit and predict
            predictions = self.model.fit_predict(scaled_data)
            decision_scores = self.model.decision_function(scaled_data)
            
            # Convert decision scores to anomaly scores (0-1)
            # Isolation Forest returns negative scores for anomalies
            # Normalize to 0-1 range where 1 is most anomalous
            min_score = np.min(decision_scores)
            max_score = np.max(decision_scores)
            
            if max_score == min_score:
                # All values are the same
                return [0.0] * len(values)
            
            # Invert and normalize scores (lower decision_function scores = higher anomaly scores)
            normalized_scores = (max_score - decision_scores) / (max_score - min_score)
            
            # Apply threshold based on predictions
            # If prediction is -1 (anomaly), ensure score is at least 0.5
            anomaly_scores = []
            for i, (pred, score) in enumerate(zip(predictions, normalized_scores)):
                if pred == -1:  # Anomaly detected
                    anomaly_scores.append(max(0.5, float(score)))
                else:
                    anomaly_scores.append(float(score) * 0.4)  # Normal points get lower scores
            
            return anomaly_scores
            
        except Exception as e:
            logger.error(f"Error in Isolation Forest detection: {e}")
            return [0.0] * len(values)
    
    def get_params(self) -> Dict[str, Any]:
        """Get detector parameters."""
        return {
            'contamination': self.contamination,
            'random_state': self.random_state,
            'detector_type': 'isolation_forest'
        }