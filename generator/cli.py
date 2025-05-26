"""Command-line interface for the sensor data generator."""
import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from database.models.base import get_db, engine
from database.models.sensor_data import SensorData
from .utils.data_generator import create_sensor_fleet
from .utils.reader import read_sensor_data
from .sensors.base import BaseSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# If still failing, create a simple insert function
def insert_sensor_data(readings):
    """Fallback insert function."""
    from database.models.base import get_db
    from database.models.sensor_data import SensorData
    
    # Use next() to get the actual session from the generator
    db = next(get_db())
    try:
        sensor_objects = []
        for reading in readings:
            sensor_obj = SensorData(
                sensor_id=reading['sensor_id'],
                timestamp=reading['timestamp'],
                category=reading['category'],
                type=reading['type'],
                value=reading['value'],
                unit=reading['unit'],
                location=reading['location']
            )
            sensor_objects.append(sensor_obj)
        
        db.add_all(sensor_objects)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def generate_sample_data(
    db: Session,
    num_days: int = 30,
    interval_minutes: int = 5,
    num_sensors: int = 5,
    anomaly_rate: float = 0.0
):
    """Generate sample sensor data and save to the database."""
    end_time = datetime.utcnow() + timedelta(hours=2)  # Start from today
    start_time = end_time - timedelta(days=num_days)
    interval_seconds = interval_minutes * 60
    
    logger.info(f"Generating {num_days} days of sample data...")
    logger.info(f"Time range: {start_time} to {end_time}")
    logger.info(f"Interval: {interval_minutes} minutes")
    logger.info(f"Number of sensors: {num_sensors}")
    
    if anomaly_rate > 0:
        BaseSensor.enable_anomaly_injection(anomaly_rate)
        logger.info(f"🚨 Anomaly injection enabled at {anomaly_rate:.1%}")
    
    # Create sensor fleet using new sensor classes
    sensors = create_sensor_fleet(num_sensors)
    
    # Generate time series data
    data = []
    current_time = start_time
    total_readings = 0
    
    logger.info("Starting data generation...")
    
    while current_time <= end_time:
        for sensor in sensors:
            reading = sensor.generate_reading(current_time)
            data.append(reading)
            total_readings += 1
        
        current_time += timedelta(seconds=interval_seconds)
        
        # Show progress every 10000 readings
        if total_readings % 10000 == 0:
            progress = ((current_time - start_time) / (end_time - start_time)) * 100
            logger.info(f"Progress: {progress:.1f}% - {total_readings} readings generated")
    
    # Save to database
    logger.info(f"Saving {len(data)} records to database...")
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        db.bulk_insert_mappings(SensorData, batch)
        db.commit()
        logger.info(f"Saved batch {i//batch_size + 1}/{(len(data)-1)//batch_size + 1}")
    
    logger.info("Sample data generation complete!")
    
    # Show anomaly summary if enabled
    if anomaly_rate > 0:
        anomaly_status = BaseSensor.get_anomaly_status()
        if anomaly_status['enabled']:
            history = anomaly_status.get('anomaly_history', [])
            logger.info(f"Anomalies injected: {len(history)}")


def continuous_data_generation(
    db: Session,
    interval_seconds: int = 5,
    num_sensors: int = 5,
    duration_minutes: int = None,
    anomaly_rate: float = 0.0,
    anomaly_demo: bool = False
):
    """Continuously generate and insert sensor data at regular intervals."""
    logger.info(f"Starting continuous data generation with {interval_seconds}s interval...")
    
    if anomaly_rate > 0:
        BaseSensor.enable_anomaly_injection(anomaly_rate)
        logger.info(f"🚨 Anomaly injection enabled at {anomaly_rate:.1%}")
    
    if anomaly_demo:
        BaseSensor.enable_anomaly_injection(0.05)  # 5% rate for demo
        logger.info("🧪 DEMO MODE: Will inject example anomalies for testing")
    
    end_time = None
    if duration_minutes:
        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        logger.info(f"Will run for {duration_minutes} minutes until {end_time}")
    
    # Create sensor fleet using new sensor classes
    sensors = create_sensor_fleet(num_sensors)
    
    cycle = 0
    total_readings = 0
    
    try:
        while True:
            if end_time and datetime.utcnow() >= end_time:
                logger.info("Duration reached. Stopping data generation.")
                break
                
            cycle += 1
            current_time = datetime.utcnow()
            data = []
            
            for sensor in sensors:
                reading = sensor.generate_reading(current_time)
                data.append(reading)
            
            # Save to database
            db.bulk_insert_mappings(SensorData, data)
            db.commit()
            
            total_readings += len(data)
            logger.info(f"Cycle {cycle}: Generated {len(data)} records at {current_time}")
            
            # Demo mode: inject some specific anomalies
            if anomaly_demo and cycle % 20 == 0:  # Every 20 cycles
                demo_anomalies = [
                    ('oven', 'spike'),
                    ('pm', 'pollution_spike'), 
                    ('fan', 'stall'),
                    ('lamp', 'flicker'),
                    ('heater', 'oscillation')
                ]
                
                # Pick a random sensor and anomaly type
                import random
                sensor = random.choice(sensors)
                anomaly_type = random.choice([a[1] for a in demo_anomalies if a[0] == sensor.category])
                if anomaly_type:
                    BaseSensor.force_anomaly(sensor.sensor_id, sensor.category, anomaly_type, duration=10)
            
            # Show status every 10 cycles
            if cycle % 10 == 0:
                anomaly_status = BaseSensor.get_anomaly_status()
                active_count = len(anomaly_status.get('active_anomalies', {}))
                logger.info(f"Status: {total_readings} total readings, {active_count} active anomalies")
                
                # Show active anomalies
                if active_count > 0:
                    for sensor_id, anomaly in anomaly_status['active_anomalies'].items():
                        remaining = anomaly['remaining_duration']
                        logger.info(f"  🚨 {sensor_id}: {anomaly['type']} ({remaining} readings left)")
            
            # Wait for the next interval
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Data generation stopped by user")
        logger.info(f"Total readings generated: {total_readings}")
        
        # Show final anomaly summary
        anomaly_status = BaseSensor.get_anomaly_status()
        if anomaly_status['enabled']:
            history = anomaly_status.get('anomaly_history', [])
            logger.info(f"Anomalies injected: {len(history)}")
            for anomaly in history[-5:]:  # Show last 5
                logger.info(f"  {anomaly['sensor_id']}: {anomaly['type']} at {anomaly['started_at']}")
                
    except Exception as e:
        logger.error(f"Error during data generation: {e}")
        raise


def run_continuous_generation(interval: int, sensors: int, duration: int = None, 
                            anomaly_rate: float = 0.0, anomaly_demo: bool = False):
    """Run continuous data generation with optional anomaly injection (new style)."""
    print(f"Creating fleet of {sensors} sensors...")
    sensor_fleet = create_sensor_fleet(sensors)
    
    # Enable anomaly injection if requested
    if anomaly_rate > 0:
        BaseSensor.enable_anomaly_injection(anomaly_rate)
    
    # Demo mode: inject specific anomalies for testing
    if anomaly_demo:
        BaseSensor.enable_anomaly_injection(0.05)  # 5% rate for demo
        print("🧪 DEMO MODE: Will inject example anomalies for testing")
    
    print(f"Starting continuous generation (interval: {interval}s)")
    if duration:
        print(f"Will run for {duration} minutes")
        end_time = datetime.now() + timedelta(minutes=duration)
    else:
        print("Running indefinitely (Ctrl+C to stop)")
        end_time = None
    
    cycle = 0
    total_readings = 0
    
    try:
        while True:
            if end_time and datetime.now() >= end_time:
                break
            
            cycle += 1
            start_time = datetime.now()
            
            # Generate readings for all sensors
            readings = []
            for sensor in sensor_fleet:
                reading = sensor.generate_reading(start_time)
                readings.append(reading)
            
            # Insert into database
            try:
                insert_sensor_data(readings)
                total_readings += len(readings)
                print(f"✓ Cycle {cycle}: Inserted {len(readings)} readings")
            except Exception as e:
                print(f"✗ Database insert error: {e}")
                continue
            
            # Demo mode: inject some specific anomalies
            if anomaly_demo and cycle % 20 == 0:  # Every 20 cycles
                demo_anomalies = [
                    ('oven', 'spike'),
                    ('pm', 'pollution_spike'),
                    ('fan', 'stall'),
                    ('lamp', 'flicker'),
                    ('heater', 'oscillation')
                ]
                
                # Pick a random sensor and anomaly type
                import random
                sensor = random.choice(sensor_fleet)
                anomaly_type = random.choice([a[1] for a in demo_anomalies if a[0] == sensor.category])
                if anomaly_type:
                    BaseSensor.force_anomaly(sensor.sensor_id, sensor.category, anomaly_type, duration=10)
            
            # Show status every 10 cycles
            if cycle % 10 == 0:
                anomaly_status = BaseSensor.get_anomaly_status()
                active_count = len(anomaly_status.get('active_anomalies', {}))
                print(f"Cycle {cycle}: {total_readings} readings generated, {active_count} active anomalies")
                
                # Show active anomalies
                if active_count > 0:
                    for sensor_id, anomaly in anomaly_status['active_anomalies'].items():
                        remaining = anomaly['remaining_duration']
                        print(f"  🚨 {sensor_id}: {anomaly['type']} ({remaining} readings left)")
            
            # Sleep until next interval
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except KeyboardInterrupt:
        print(f"\nGeneration stopped. Total readings: {total_readings}")
        
        # Show final anomaly summary
        anomaly_status = BaseSensor.get_anomaly_status()
        if anomaly_status['enabled']:
            history = anomaly_status.get('anomaly_history', [])
            print(f"Anomalies injected in last hour: {len(history)}")
            for anomaly in history[-5:]:  # Show last 5
                print(f"  {anomaly['sensor_id']}: {anomaly['type']} at {anomaly['started_at']}")


def run_single_generation(count: int, sensors: int, anomaly_rate: float = 0.0):
    """Generate a specific number of readings."""
    print(f"Creating fleet of {sensors} sensors...")
    sensor_fleet = create_sensor_fleet(sensors)
    
    if anomaly_rate > 0:
        BaseSensor.enable_anomaly_injection(anomaly_rate)
        print(f"Anomaly injection enabled at {anomaly_rate:.1%}")
    
    print(f"Generating {count} readings...")
    
    all_readings = []
    for i in range(count):
        timestamp = datetime.now()
        for sensor in sensor_fleet:
            reading = sensor.generate_reading(timestamp)
            all_readings.append(reading)
    
    # Insert all readings
    try:
        insert_sensor_data(all_readings)
        print(f"✓ Generated and inserted {len(all_readings)} readings")
    except Exception as e:
        print(f"✗ Database insert error: {e}")
        return
    
    # Show anomaly summary
    anomaly_status = BaseSensor.get_anomaly_status()
    if anomaly_status['enabled']:
        active = len(anomaly_status.get('active_anomalies', {}))
        history = len(anomaly_status.get('anomaly_history', []))
        print(f"Anomalies: {active} active, {history} total injected")


def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Sensor Data Generator for TimescaleDB with Anomaly Injection")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Generate sample data command (original functionality)
    sample_parser = subparsers.add_parser("sample", help="Generate historical sample data")
    sample_parser.add_argument("--days", type=int, default=7, 
                              help="Number of days of historical data to generate (default: 7)")
    sample_parser.add_argument("--interval", type=int, default=1, 
                              help="Interval between data points in minutes (default: 1)")
    sample_parser.add_argument("--sensors", type=int, default=5, 
                              help="Number of sensors to generate data for (default: 5)")
    sample_parser.add_argument("--anomaly-rate", type=float, default=0.0,
                              help="Anomaly injection rate 0.0-1.0 (default: 0.0)")
    
    # Continuous data generation command (enhanced with anomalies)
    continuous_parser = subparsers.add_parser("continuous", help="Generate continuous data in real-time")
    continuous_parser.add_argument("--interval", type=int, default=60, 
                                  help="Interval between generations in seconds (default: 60)")
    continuous_parser.add_argument("--sensors", type=int, default=5, 
                                  help="Number of sensors in the fleet (default: 5)")
    continuous_parser.add_argument("--duration", type=int, 
                                  help="Duration in minutes (default: indefinite)")
    continuous_parser.add_argument("--anomaly-rate", type=float, default=0.0,
                                  help="Anomaly injection rate 0.0-1.0 (default: 0.0)")
    continuous_parser.add_argument("--demo", action="store_true",
                                  help="Enable demo mode with example anomalies")
    
    # Single generation command  
    single_parser = subparsers.add_parser("single", help="Generate a specific number of readings")
    single_parser.add_argument("--count", type=int, default=100, 
                              help="Number of readings to generate (default: 100)")
    single_parser.add_argument("--sensors", type=int, default=5, 
                              help="Number of sensors in the fleet (default: 5)")
    single_parser.add_argument("--anomaly-rate", type=float, default=0.0,
                              help="Anomaly injection rate 0.0-1.0 (default: 0.0)")
    
    # Read data from the database command
    read_parser = subparsers.add_parser("read", help="Read data from the database")
    read_parser.add_argument("--limit", type=int, default=10, 
                            help="Number of rows to fetch (default: 10)")
    read_parser.add_argument("--loop", action="store_true", 
                            help="Loop the read operation")
    
    # Anomaly control commands
    anomaly_parser = subparsers.add_parser("anomaly", help="Anomaly injection control")
    anomaly_subparsers = anomaly_parser.add_subparsers(dest="anomaly_command", required=True)
    
    # Force anomaly
    force_parser = anomaly_subparsers.add_parser("force", help="Force inject an anomaly")
    force_parser.add_argument("sensor_id", help="Target sensor ID")
    force_parser.add_argument("category", choices=["oven", "heater", "lamp", "fan", "pm"],
                             help="Sensor category")
    force_parser.add_argument("type", help="Anomaly type (spike, drop, drift, etc.)")
    force_parser.add_argument("--duration", type=int, default=10,
                             help="Duration in readings (default: 10)")
    
    # Show anomaly status
    status_parser = anomaly_subparsers.add_parser("status", help="Show anomaly injection status")
    
    # Clear anomalies
    clear_parser = anomaly_subparsers.add_parser("clear", help="Clear all active anomalies")

    args = parser.parse_args()
    
    if args.command in ["sample"] or (args.command == "continuous" and not hasattr(args, 'anomaly_rate')):
        # Use original database session approach for sample and legacy continuous
        db = next(get_db())
        
        try:
            if args.command == "sample":
                generate_sample_data(
                    db=db,
                    num_days=args.days,
                    interval_minutes=args.interval,
                    num_sensors=args.sensors,
                    anomaly_rate=getattr(args, 'anomaly_rate', 0.0)
                )
            elif args.command == "continuous":
                # Legacy style
                continuous_data_generation(
                    db=db,
                    interval_seconds=args.interval,
                    num_sensors=args.sensors,
                    duration_minutes=args.duration
                )
        finally:
            db.close()
            
    elif args.command == "continuous":
        # New style with anomaly injection
        run_continuous_generation(
            interval=args.interval,
            sensors=args.sensors,
            duration=args.duration,
            anomaly_rate=getattr(args, 'anomaly_rate', 0.0),
            anomaly_demo=getattr(args, 'demo', False)
        )
            
    elif args.command == "read":
        read_sensor_data(limit=args.limit, loop=args.loop)
        
    elif args.command == "single":
        run_single_generation(
            count=args.count,
            sensors=args.sensors,
            anomaly_rate=args.anomaly_rate
        )
        
    elif args.command == "anomaly":
        if args.anomaly_command == "force":
            result = BaseSensor.force_anomaly(args.sensor_id, args.category, args.type, args.duration)
            if result:
                print(f"✓ Forced {args.type} anomaly on {args.sensor_id}")
            else:
                print(f"✗ Failed to inject anomaly")
        elif args.anomaly_command == "status":
            status = BaseSensor.get_anomaly_status()
            print("Anomaly Injection Status:")
            print(f"  Enabled: {status['enabled']}")
            if status['enabled']:
                print(f"  Rate: {status['injection_rate']:.1%}")
                print(f"  Active: {len(status.get('active_anomalies', {}))}")
                print(f"  History (1h): {len(status.get('anomaly_history', []))}")
        elif args.anomaly_command == "clear":
            if BaseSensor._anomaly_injector:
                BaseSensor._anomaly_injector.clear_all_anomalies()
            print("✓ Cleared all active anomalies")


if __name__ == "__main__":
    main()