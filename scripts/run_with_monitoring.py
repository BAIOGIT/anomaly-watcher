"""Script to run data generation with simultaneous anomaly monitoring."""
import subprocess
import threading
import time
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_data_generation(interval: int, sensors: int, duration: int = None, 
                       anomaly_rate: float = 0.0, demo_mode: bool = False):
    """Run continuous data generation with anomaly injection."""
    cmd = [
        "python", "-m", "generator.cli", "continuous",
        "--interval", str(interval),
        "--sensors", str(sensors)
    ]
    
    if duration:
        cmd.extend(["--duration", str(duration)])
    
    if anomaly_rate > 0:
        cmd.extend(["--anomaly-rate", str(anomaly_rate)])
    
    if demo_mode:
        cmd.append("--demo")
    
    logger.info(f"Starting data generation: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Data generation failed: {e}")
    except KeyboardInterrupt:
        logger.info("Data generation interrupted")


def run_anomaly_monitoring(check_interval: int, window: int, threshold: float, duration: float = None):
    """Run anomaly monitoring."""
    cmd = [
        "python", "-m", "core.anomaly_detection.monitor",
        "--interval", str(check_interval),
        "--window", str(window),
        "--threshold", str(threshold)
    ]
    
    if duration:
        cmd.extend(["--duration", str(duration)])
    
    logger.info(f"Starting anomaly monitoring: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Anomaly monitoring failed: {e}")
    except KeyboardInterrupt:
        logger.info("Anomaly monitoring interrupted")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run data generation with anomaly monitoring")
    
    # Data generation options
    parser.add_argument("--data-interval", type=int, default=60,
                       help="Data generation interval in seconds (default: 60)")
    parser.add_argument("--sensors", type=int, default=5,
                       help="Number of sensors for data generation (default: 5)")
    
    # Anomaly injection options
    parser.add_argument("--anomaly-rate", type=float, default=0.03,
                       help="Anomaly injection rate 0.0-1.0 (default: 0.03 = 3%%)")
    parser.add_argument("--demo-anomalies", action="store_true",
                       help="Enable demo mode with example anomalies")
    
    # Monitoring options
    parser.add_argument("--monitor-interval", type=int, default=90,
                       help="Anomaly check interval in seconds (default: 90)")
    parser.add_argument("--window", type=int, default=15,
                       help="Analysis window in minutes (default: 15)")
    parser.add_argument("--threshold", type=float, default=0.6,
                       help="Anomaly alert threshold (default: 0.6)")
    
    # General options
    parser.add_argument("--duration", type=float,
                       help="Duration to run in hours (default: indefinite)")
    parser.add_argument("--monitor-only", action="store_true",
                       help="Only run monitoring (no data generation)")
    parser.add_argument("--data-only", action="store_true",
                       help="Only run data generation (no monitoring)")
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING SENSOR MONITORING SYSTEM WITH ANOMALY INJECTION")
    logger.info("=" * 80)
    
    if args.anomaly_rate > 0 or args.demo_anomalies:
        logger.info(f"🚨 ANOMALY INJECTION ENABLED:")
        logger.info(f"   Rate: {args.anomaly_rate:.1%}")
        logger.info(f"   Demo Mode: {args.demo_anomalies}")
    
    # Convert duration to minutes for data generation if specified
    data_duration = int(args.duration * 60) if args.duration else None
    
    threads = []
    
    try:
        if not args.monitor_only:
            # Start data generation in a separate thread
            data_thread = threading.Thread(
                target=run_data_generation,
                args=(args.data_interval, args.sensors, data_duration, 
                      args.anomaly_rate, args.demo_anomalies),
                name="DataGeneration"
            )
            data_thread.daemon = True
            data_thread.start()
            threads.append(data_thread)
            logger.info("✅ Data generation started")
        
        if not args.data_only:
            # Wait a bit for data generation to start
            if not args.monitor_only:
                logger.info("Waiting 45 seconds for initial data and anomalies...")
                time.sleep(45)
            
            # Start anomaly monitoring in a separate thread
            monitor_thread = threading.Thread(
                target=run_anomaly_monitoring,
                args=(args.monitor_interval, args.window, args.threshold, args.duration),
                name="AnomalyMonitoring"
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            threads.append(monitor_thread)
            logger.info("✅ Anomaly monitoring started")
        
        # Wait for threads to complete
        logger.info("🔄 System running... Press Ctrl+C to stop")
        logger.info("📊 Expected anomalies with demo mode: spikes, drops, stalls, flickers")
        
        while True:
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                logger.info("All processes completed")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        logger.info("=" * 80)
        logger.info("📊 SYSTEM SHUTDOWN COMPLETE")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()