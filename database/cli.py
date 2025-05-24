"""Command-line interface for the sensor data generator."""
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import time

from sqlalchemy.orm import Session

from .models.base import get_db, engine
from .db import init_db, reset_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Sensor Data Generator for TimescaleDB")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Init database command
    init_parser = subparsers.add_parser("init", help="Initialize the database")
    
    # Reset database command
    reset_parser = subparsers.add_parser("reset", help="Reset the database (drop and recreate all tables)")
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    try:
        if args.command == "init":
            init_db()
        elif args.command == "reset":
            confirm = input("Are you sure you want to reset the database? This will delete all data. (y/n): ")
            if confirm.lower() == 'y':
                reset_db()
    finally:
        db.close()

if __name__ == "__main__":
    main()
