"""
Anomaly detection for sensor data from TimescaleDB.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.models.base import get_db, engine
from .models import IsolationForestDetector, LOFDetector, OneClassSVMDetector
from .trainer import ModelTrainer
from .persistence import ModelPersistence


class SensorAnomalyDetector:
    """Main anomaly detection class for sensor data."""
    
    def __init__(self, model_dir: str = "models/anomaly_detection"):
        self.models = {}  # Store models per sensor category
        self.trainer = ModelTrainer()
        self.persistence = ModelPersistence(model_dir)
        self.contamination_rates = {
            'oven': 0.05,        # 5% anomalies expected
            'heater': 0.03,      # 3% anomalies expected  
            'lamp': 0.02,        # 2% anomalies expected (digital)
            'fan': 0.04,         # 4% anomalies expected
            'pm': 0.08,          # 8% anomalies expected (environmental)
        }
        
        # Load existing models on initialization
        self._load_saved_models()
    
    def _load_saved_models(self):
        """Load previously saved models."""
        saved_models = self.persistence.load_all_models()
        self.models.update(saved_models)
        
        if saved_models:
            print(f"✓ Loaded {len(saved_models)} saved models: {list(saved_models.keys())}")
    
    def load_sensor_data(self, 
                        sensor_id: str = None, 
                        category: str = None,
                        hours: int = 24,
                        min_samples: int = 100) -> pd.DataFrame:
        """Load sensor data from TimescaleDB."""
        
        # Build query based on parameters
        where_conditions = []
        params = {'hours': hours}
        
        if sensor_id:
            where_conditions.append("sensor_id = :sensor_id")
            params['sensor_id'] = sensor_id
            
        if category:
            where_conditions.append("category = :category")
            params['category'] = category
        
        where_clause = ""
        if where_conditions:
            where_clause = "AND " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                timestamp,
                sensor_id,
                category,
                type,
                value,
                unit,
                location
            FROM sensors_data 
            WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
            {where_clause}
            ORDER BY sensor_id, timestamp
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, params)
            data = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if len(data) < min_samples and min_samples > 1:
            print(f"Warning: Only {len(data)} samples found (minimum {min_samples} recommended)")
        
        return data
    
    def prepare_features(self, data: pd.DataFrame, sensor_id: str = None) -> np.ndarray:
        """Prepare feature matrix for anomaly detection."""
        if sensor_id:
            sensor_data = data[data['sensor_id'] == sensor_id].copy()
        else:
            sensor_data = data.copy()
        
        # Sort by timestamp
        sensor_data = sensor_data.sort_values('timestamp')
        
        if len(sensor_data) == 0:
            return np.array([]).reshape(0, 1)
        
        # Basic features
        features = []
        values = sensor_data['value'].values
        
        # Raw values
        features.append(values)
        
        # Statistical features (rolling windows)
        df_temp = pd.DataFrame({'value': values})
        
        # Rolling statistics (window of 10 readings)
        window_size = min(10, max(2, len(values) // 4))
        if window_size >= 2:
            rolling_mean = df_temp['value'].rolling(window=window_size, min_periods=1).mean()
            rolling_std = df_temp['value'].rolling(window=window_size, min_periods=1).std().fillna(0)
            features.extend([rolling_mean.values, rolling_std.values])
        
        # Rate of change
        if len(values) > 1:
            rate_of_change = np.diff(values, prepend=values[0])
            features.append(rate_of_change)
        
        # Time-based features
        timestamps = pd.to_datetime(sensor_data['timestamp'])
        hour_of_day = timestamps.dt.hour.values
        day_of_week = timestamps.dt.dayofweek.values
        features.extend([hour_of_day, day_of_week])
        
        # Combine all features
        if len(features) == 1:
            feature_matrix = features[0].reshape(-1, 1)
        else:
            feature_matrix = np.column_stack(features)
        
        # Handle any remaining NaN values
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0)
        
        return feature_matrix
    
    def train_models(self, hours: int = 168, categories: List[str] = None, save_models: bool = True):
        """Train anomaly detection models for sensor categories."""
        if categories is None:
            categories = list(self.contamination_rates.keys())
        
        for category in categories:
            print(f"Training model for category: {category}")
            
            try:
                # Load data for this category
                data = self.load_sensor_data(category=category, hours=hours, min_samples=10)
                
                if len(data) == 0:
                    print(f"No data found for category: {category}")
                    continue
                
                # Get unique sensors in this category
                unique_sensors = data['sensor_id'].unique()
                
                # Prepare features for all sensors in this category
                all_features = []
                for sensor_id in unique_sensors:
                    try:
                        features = self.prepare_features(data, sensor_id)
                        if len(features) > 0:
                            all_features.append(features)
                    except Exception as e:
                        print(f"Error preparing features for sensor {sensor_id}: {e}")
                        continue
                
                if not all_features:
                    print(f"No valid features for category: {category}")
                    continue
                
                # Combine features from all sensors
                X = np.vstack(all_features)
                
                if len(X) < 10:
                    print(f"Insufficient samples for {category}: {len(X)} samples")
                    continue
                
                # Train model
                contamination = self.contamination_rates.get(category, 0.05)
                model, metadata = self.trainer.train_isolation_forest(
                    X, contamination=contamination
                )
                
                # Store model in memory
                model_data = {
                    'model': model,
                    'metadata': metadata,
                    'trained_at': datetime.now(),
                    'sensor_count': len(unique_sensors),
                    'sample_count': len(X)
                }
                
                self.models[category] = model_data
                
                # Save model to disk
                if save_models:
                    self.persistence.save_model(category, model_data)
                
                print(f"✓ Trained {category} model on {len(X)} samples from {len(unique_sensors)} sensors")
                
            except Exception as e:
                print(f"Error training model for category {category}: {e}")
    
    def detect_anomalies_for_sensor(self, 
                                   sensor_id: str, 
                                   hours: int = 1) -> Dict[str, Any]:
        """Detect anomalies for a specific sensor."""
        
        try:
            # Load recent data for the sensor
            data = self.load_sensor_data(sensor_id=sensor_id, hours=hours, min_samples=1)
            
            if len(data) == 0:
                return {'sensor_id': sensor_id, 'anomalies': [], 'error': 'No data found'}
            
            category = data['category'].iloc[0]
            
            # Check if we have a trained model for this category
            if category not in self.models:
                return {
                    'sensor_id': sensor_id, 
                    'category': category,
                    'anomalies': [], 
                    'error': f'No trained model for category: {category}'
                }
            
            # Prepare features
            features = self.prepare_features(data, sensor_id)
            
            if len(features) == 0:
                return {
                    'sensor_id': sensor_id,
                    'category': category,
                    'anomalies': [],
                    'error': 'No features could be prepared'
                }
            
            # Get model
            model_info = self.models[category]
            model = model_info['model']
            
            # Detect anomalies
            is_anomaly, scores = model.predict(features)
            
            # Prepare results
            anomalies = []
            for i, (timestamp, value, is_anom, score) in enumerate(zip(
                data['timestamp'], data['value'], is_anomaly, scores
            )):
                if is_anom:
                    anomalies.append({
                        'timestamp': timestamp,
                        'value': float(value),
                        'anomaly_score': float(score),
                        'index': i
                    })
            
            return {
                'sensor_id': sensor_id,
                'category': category,
                'total_readings': len(data),
                'anomaly_count': len(anomalies),
                'anomaly_rate': len(anomalies) / len(data) if len(data) > 0 else 0,
                'anomalies': anomalies,
                'model_info': {
                    'trained_at': model_info['trained_at'],
                    'sample_count': model_info['sample_count']
                }
            }
            
        except Exception as e:
            return {
                'sensor_id': sensor_id,
                'anomalies': [],
                'error': str(e)
            }
    
    def detect_anomalies_for_category(self, 
                                     category: str, 
                                     hours: int = 1) -> List[Dict[str, Any]]:
        """Detect anomalies for all sensors in a category."""
        
        try:
            # Load data for category
            data = self.load_sensor_data(category=category, hours=hours, min_samples=1)
            
            if len(data) == 0:
                return []
            
            results = []
            unique_sensors = data['sensor_id'].unique()
            
            for sensor_id in unique_sensors:
                result = self.detect_anomalies_for_sensor(sensor_id, hours)
                results.append(result)
            
            return results
        
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_real_time_anomalies(self, minutes: int = 15) -> List[Dict[str, Any]]:
        """Get anomalies from the last N minutes across all sensors."""
        hours = minutes / 60.0
        
        all_anomalies = []
        
        for category in self.models.keys():
            category_results = self.detect_anomalies_for_category(category, hours=hours)
            for result in category_results:
                if result.get('anomalies'):
                    all_anomalies.extend([
                        {
                            **anomaly,
                            'sensor_id': result['sensor_id'],
                            'category': result['category']
                        }
                        for anomaly in result['anomalies']
                    ])
        
        # Sort by timestamp (most recent first)
        all_anomalies.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_anomalies
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all trained models."""
        status = {}
        
        for category, model_info in self.models.items():
            status[category] = {
                'trained': True,
                'trained_at': model_info['trained_at'],
                'sensor_count': model_info['sensor_count'],
                'sample_count': model_info['sample_count'],
                'contamination_rate': self.contamination_rates.get(category, 0.05)
            }
        
        # Add untrained categories
        for category in self.contamination_rates.keys():
            if category not in status:
                status[category] = {
                    'trained': False,
                    'contamination_rate': self.contamination_rates[category]
                }
        
        return status


# Legacy function for backward compatibility
def detect_anomalies(data, **kwargs):
    """Legacy function for detecting anomalies."""
    detector = SensorAnomalyDetector()
    # This would need to be implemented based on the old interface
    pass
