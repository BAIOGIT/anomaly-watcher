"""Utility functions for anomaly detection."""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import json


def calculate_anomaly_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate anomaly detection metrics."""
    try:
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
    except ImportError:
        print("scikit-learn is required for metrics calculation")
        return {}
    
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1_score': f1_score(y_true, y_pred, zero_division=0)
    }
    
    return metrics


def prepare_time_series_features(values: np.ndarray, 
                                window_size: int = 10,
                                include_statistics: bool = True) -> np.ndarray:
    """Prepare time series features for anomaly detection."""
    if len(values) == 0:
        return np.array([])
    
    features = []
    
    # Raw values
    features.append(values)
    
    if include_statistics and len(values) > window_size:
        # Rolling statistics
        df = pd.DataFrame({'value': values})
        
        # Rolling mean
        rolling_mean = df['value'].rolling(window=window_size, min_periods=1).mean()
        features.append(rolling_mean.values)
        
        # Rolling standard deviation
        rolling_std = df['value'].rolling(window=window_size, min_periods=1).std().fillna(0)
        features.append(rolling_std.values)
        
        # Rolling min/max
        rolling_min = df['value'].rolling(window=window_size, min_periods=1).min()
        rolling_max = df['value'].rolling(window=window_size, min_periods=1).max()
        features.extend([rolling_min.values, rolling_max.values])
    
    # Rate of change
    if len(values) > 1:
        rate_of_change = np.diff(values, prepend=values[0])
        features.append(rate_of_change)
    
    # Combine features
    if len(features) == 1:
        return features[0].reshape(-1, 1)
    
    feature_matrix = np.column_stack(features)
    
    # Handle NaN values
    feature_matrix = np.nan_to_num(feature_matrix, nan=0.0)
    
    return feature_matrix


def detect_sensor_type_anomalies(sensor_type: str, values: np.ndarray) -> Dict[str, Any]:
    """Detect anomalies specific to sensor types."""
    anomalies = {
        'type': sensor_type,
        'value_anomalies': [],
        'pattern_anomalies': []
    }
    
    if sensor_type == 'digital':
        # For digital sensors (0/1), check for impossible values
        invalid_values = np.where((values < 0) | (values > 1))[0]
        if len(invalid_values) > 0:
            anomalies['value_anomalies'] = invalid_values.tolist()
    
    elif sensor_type == 'analog':
        # For analog sensors, check for extreme outliers
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 3 * iqr
        upper_bound = q3 + 3 * iqr
        
        outliers = np.where((values < lower_bound) | (values > upper_bound))[0]
        if len(outliers) > 0:
            anomalies['value_anomalies'] = outliers.tolist()
    
    return anomalies


def format_anomaly_report(anomalies: List[Dict[str, Any]], 
                         sensor_info: Dict[str, str] = None) -> str:
    """Format anomaly detection results into a readable report."""
    if not anomalies:
        return "No anomalies detected."
    
    report = []
    report.append("ANOMALY DETECTION REPORT")
    report.append("=" * 50)
    
    if sensor_info:
        report.append(f"Sensor: {sensor_info.get('sensor_id', 'Unknown')}")
        report.append(f"Category: {sensor_info.get('category', 'Unknown')}")
        report.append(f"Location: {sensor_info.get('location', 'Unknown')}")
        report.append("-" * 30)
    
    for i, anomaly in enumerate(anomalies, 1):
        report.append(f"Anomaly #{i}:")
        report.append(f"  Timestamp: {anomaly.get('timestamp', 'Unknown')}")
        report.append(f"  Value: {anomaly.get('value', 'Unknown')}")
        report.append(f"  Score: {anomaly.get('anomaly_score', 0):.3f}")
        if 'expected_range' in anomaly:
            report.append(f"  Expected Range: {anomaly['expected_range']}")
        report.append("")
    
    return "\n".join(report)


def save_anomaly_results(results: Dict[str, Any], filename: str = None):
    """Save anomaly detection results to a file."""
    if filename is None:
        filename = f"anomaly_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert datetime objects to strings for JSON serialization
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=json_serializer)
    
    print(f"Results saved to {filename}")
