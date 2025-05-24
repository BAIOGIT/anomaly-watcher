"""Main entry point for anomaly detection with database integration."""
from .anomaly_detection.detector import SensorAnomalyDetector
import argparse
import sys


def main():
    """Main entry point with database integration."""
    parser = argparse.ArgumentParser(description="Sensor Anomaly Detection")
    parser.add_argument("--train", action="store_true", help="Train models on historical data")
    parser.add_argument("--detect", action="store_true", help="Detect recent anomalies")
    parser.add_argument("--hours", type=int, default=24, help="Hours of data to analyze")
    parser.add_argument("--category", type=str, help="Specific sensor category")
    parser.add_argument("--sensor-id", type=str, help="Specific sensor ID")
    
    args = parser.parse_args()
    
    detector = SensorAnomalyDetector()
    
    if args.train:
        print("Training anomaly detection models...")
        categories = [args.category] if args.category else None
        detector.train_models(hours=args.hours * 7, categories=categories)  # Use 7x hours for training
        
    elif args.detect:
        print(f"Detecting anomalies in last {args.hours} hours...")
        
        if args.sensor_id:
            # Analyze specific sensor
            result = detector.detect_anomalies_for_sensor(args.sensor_id, hours=args.hours)
            print(f"Sensor {args.sensor_id}: {result['anomaly_count']} anomalies found")
            for anomaly in result.get('anomalies', []):
                print(f"  {anomaly['timestamp']}: {anomaly['value']} (score: {anomaly['anomaly_score']:.3f})")
                
        elif args.category:
            # Analyze category
            results = detector.detect_anomalies_for_category(args.category, hours=args.hours)
            total_anomalies = sum(len(r.get('anomalies', [])) for r in results)
            print(f"Category {args.category}: {total_anomalies} total anomalies across {len(results)} sensors")
            
        else:
            # Real-time overview
            anomalies = detector.get_real_time_anomalies(minutes=args.hours * 60)
            print(f"Found {len(anomalies)} recent anomalies:")
            for anomaly in anomalies[:10]:  # Show top 10
                print(f"  {anomaly['sensor_id']} ({anomaly['category']}): {anomaly['value']} at {anomaly['timestamp']}")
    
    else:
        # Show status
        status = detector.get_model_status()
        print("Anomaly Detection Status:")
        for category, info in status.items():
            status_icon = "✓" if info['trained'] else "✗"
            print(f"{status_icon} {category}: {'Trained' if info['trained'] else 'Not trained'}")


if __name__ == "__main__":
    main()