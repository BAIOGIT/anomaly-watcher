"""Command-line interface for anomaly detection."""
import argparse
import json
from datetime import datetime
from .detector import SensorAnomalyDetector


def train_models_cmd(args):
    """Train anomaly detection models."""
    detector = SensorAnomalyDetector()
    
    categories = args.categories.split(',') if args.categories else None
    
    print(f"Training models for {args.hours} hours of data...")
    detector.train_models(hours=args.hours, categories=categories)
    
    # Show model status
    status = detector.get_model_status()
    print("\nModel Status:")
    for category, info in status.items():
        if info['trained']:
            print(f"✓ {category}: {info['sample_count']} samples, {info['sensor_count']} sensors")
        else:
            print(f"✗ {category}: Not trained")


def detect_anomalies_cmd(args):
    """Detect anomalies for sensor(s)."""
    detector = SensorAnomalyDetector()
    
    if args.sensor_id:
        # Single sensor
        result = detector.detect_anomalies_for_sensor(args.sensor_id, hours=args.hours)
        print(json.dumps(result, indent=2, default=str))
        
    elif args.category:
        # All sensors in category
        results = detector.detect_anomalies_for_category(args.category, hours=args.hours)
        print(json.dumps(results, indent=2, default=str))
        
    else:
        # Real-time anomalies across all sensors
        anomalies = detector.get_real_time_anomalies(minutes=args.hours * 60)
        print(f"Found {len(anomalies)} recent anomalies:")
        print(json.dumps(anomalies, indent=2, default=str))


def status_cmd(args):
    """Show model training status."""
    detector = SensorAnomalyDetector()
    status = detector.get_model_status()
    
    print("Anomaly Detection Model Status:")
    print("-" * 50)
    
    for category, info in status.items():
        if info['trained']:
            print(f"✓ {category.upper()}")
            print(f"  Trained: {info['trained_at']}")
            print(f"  Sensors: {info['sensor_count']}")
            print(f"  Samples: {info['sample_count']}")
            print(f"  Contamination: {info['contamination_rate']:.1%}")
        else:
            print(f"✗ {category.upper()}")
            print(f"  Status: Not trained")
            print(f"  Contamination: {info['contamination_rate']:.1%}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Sensor Anomaly Detection CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train anomaly detection models")
    train_parser.add_argument("--hours", type=int, default=168, 
                             help="Hours of historical data to use for training (default: 168 = 1 week)")
    train_parser.add_argument("--categories", type=str, 
                             help="Comma-separated list of categories to train (default: all)")
    train_parser.set_defaults(func=train_models_cmd)
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect anomalies")
    detect_parser.add_argument("--sensor-id", type=str, help="Specific sensor ID to analyze")
    detect_parser.add_argument("--category", type=str, help="Category to analyze")
    detect_parser.add_argument("--hours", type=float, default=1.0, 
                              help="Hours of recent data to analyze (default: 1)")
    detect_parser.set_defaults(func=detect_anomalies_cmd)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show model training status")
    status_parser.set_defaults(func=status_cmd)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()