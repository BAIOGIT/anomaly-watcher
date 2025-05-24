"""Model persistence utilities for saving and loading trained models."""
import pickle
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ModelPersistence:
    """Handle saving and loading of trained anomaly detection models."""
    
    def __init__(self, model_dir: str = "models/anomaly_detection"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.model_dir / "models_metadata.json"
    
    def save_model(self, category: str, model_data: Dict[str, Any]) -> bool:
        """Save a trained model for a specific category."""
        try:
            # Save the model object
            model_file = self.model_dir / f"{category}_model.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model_data['model'], f)
            
            # Save metadata
            metadata = {
                'category': category,
                'trained_at': model_data['trained_at'].isoformat(),
                'sensor_count': model_data['sensor_count'],
                'sample_count': model_data['sample_count'],
                'metadata': model_data['metadata'],
                'model_file': str(model_file.name)
            }
            
            # Load existing metadata
            all_metadata = self._load_metadata()
            all_metadata[category] = metadata
            
            # Save updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(all_metadata, f, indent=2)
            
            print(f"✓ Saved {category} model to {model_file}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving {category} model: {e}")
            return False
    
    def load_model(self, category: str) -> Optional[Dict[str, Any]]:
        """Load a trained model for a specific category."""
        try:
            # Load metadata
            all_metadata = self._load_metadata()
            if category not in all_metadata:
                return None
            
            metadata = all_metadata[category]
            
            # Load the model object
            model_file = self.model_dir / metadata['model_file']
            if not model_file.exists():
                print(f"✗ Model file not found: {model_file}")
                return None
            
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
            
            # Reconstruct model_data
            model_data = {
                'model': model,
                'metadata': metadata['metadata'],
                'trained_at': datetime.fromisoformat(metadata['trained_at']),
                'sensor_count': metadata['sensor_count'],
                'sample_count': metadata['sample_count']
            }
            
            return model_data
            
        except Exception as e:
            print(f"✗ Error loading {category} model: {e}")
            return None
    
    def load_all_models(self) -> Dict[str, Dict[str, Any]]:
        """Load all saved models."""
        models = {}
        metadata = self._load_metadata()
        
        for category in metadata.keys():
            model_data = self.load_model(category)
            if model_data:
                models[category] = model_data
        
        return models
    
    def get_model_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all saved models."""
        metadata = self._load_metadata()
        status = {}
        
        for category, info in metadata.items():
            model_file = self.model_dir / info['model_file']
            status[category] = {
                'trained': model_file.exists(),
                'trained_at': datetime.fromisoformat(info['trained_at']),
                'sensor_count': info['sensor_count'],
                'sample_count': info['sample_count'],
                'model_file': str(model_file)
            }
        
        return status
    
    def delete_model(self, category: str) -> bool:
        """Delete a saved model."""
        try:
            # Load metadata
            all_metadata = self._load_metadata()
            if category not in all_metadata:
                return False
            
            # Delete model file
            model_file = self.model_dir / all_metadata[category]['model_file']
            if model_file.exists():
                model_file.unlink()
            
            # Remove from metadata
            del all_metadata[category]
            
            # Save updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(all_metadata, f, indent=2)
            
            print(f"✓ Deleted {category} model")
            return True
            
        except Exception as e:
            print(f"✗ Error deleting {category} model: {e}")
            return False
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load models metadata from file."""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def cleanup_old_models(self, days: int = 30):
        """Remove models older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        metadata = self._load_metadata()
        
        for category, info in list(metadata.items()):
            trained_at = datetime.fromisoformat(info['trained_at'])
            if trained_at < cutoff_date:
                self.delete_model(category)
                print(f"✓ Cleaned up old {category} model from {trained_at}")