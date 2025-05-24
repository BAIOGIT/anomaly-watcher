"""Module to read data from the sensors_data table."""
import time
from sqlalchemy import create_engine, text
from typing import List, Dict

# Replace with your actual database connection string
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/sensor_data"

def read_sensor_data(limit: int = 10, loop: bool = False) -> List[Dict]:
    """
    Read data from the sensors_data table.

    Args:
        limit (int): Number of rows to fetch.

    Returns:
        List[Dict]: List of rows as dictionaries.
    """
    engine = create_engine(DATABASE_URL)

    query = text(f"SELECT * FROM sensors_data ORDER BY timestamp DESC LIMIT :limit")
    count = text("SELECT COUNT(*) FROM sensors_data")
    
    rows = []

    with engine.connect() as conn:
        while True:
            result = conn.execute(count)
            total_rows = result.fetchone()[0]
            print(f"Total rows in sensors_data: {total_rows}")

            result = conn.execute(query, {"limit": limit})
            rows = [dict(row._mapping) for row in result]  # Use ._mapping to convert Row to a dictionary
        
            for row in rows:
                print(row)

            if loop:
                time.sleep(1)  # Sleep for a second before the next query
            else:
                break
    return rows

if __name__ == "__main__":
    # Example usage
    data = read_sensor_data(limit=10000, loop=True)