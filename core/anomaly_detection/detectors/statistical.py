"""Statistical anomaly detector using Z-score and other statistical methods."""
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class StatisticalDetector:
    """Statistical anomaly detector using Z-score and IQR methods."""
    
    def __init__(self, z_threshold: float = 2.5, iqr_multiplier: float = 1.5):
        """
        Initialize statistical detector.
        
        Args:
            z_threshold: Z-score threshold for anomaly detection
            iqr_multiplier: IQR multiplier for outlier detection
        """
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        
    def detect(self, values: List[float]) -> List[float]:
        """
        Detect anomalies using statistical methods.
        
        Args:
            values: List of sensor values
            
        Returns:
            List of anomaly scores (0-1, where 1 is most anomalous)
        """
        if len(values) < 3:
            return [0.0] * len(values)
        
        try:
            data = np.array(values)
            anomaly_scores = []
            
            # Calculate statistics
            mean = np.mean(data)
            std = np.std(data)
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            
            # Avoid division by zero
            if std == 0:
                return [0.0] * len(values)
            
            for value in values:
                # Z-score based detection
                z_score = abs(value - mean) / std
                z_anomaly_score = min(z_score / self.z_threshold, 1.0)
                
                # IQR based detection
                iqr_lower = q1 - self.iqr_multiplier * iqr
                iqr_upper = q3 + self.iqr_multiplier * iqr
                
                if value < iqr_lower or value > iqr_upper:
                    if iqr > 0:
                        if value < iqr_lower:
                            iqr_anomaly_score = min((iqr_lower - value) / iqr, 1.0)
                        else:
                            iqr_anomaly_score = min((value - iqr_upper) / iqr, 1.0)
                    else:
                        iqr_anomaly_score = 0.5 if value != mean else 0.0
                else:
                    iqr_anomaly_score = 0.0
                
                # Combine scores (take maximum)
                combined_score = max(z_anomaly_score, iqr_anomaly_score)
                anomaly_scores.append(combined_score)
            
            return anomaly_scores
            
        except Exception as e:
            logger.error(f"Error in statistical detection: {e}")
            return [0.0] * len(values)
    
    def get_params(self) -> Dict[str, Any]:
        """Get detector parameters."""
        return {
            'z_threshold': self.z_threshold,
            'iqr_multiplier': self.iqr_multiplier,
            'detector_type': 'statistical'
        }