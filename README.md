# Anomaly Watcher - Industrial Sensor Data Generator & Monitor

A Python application for generating realistic industrial sensor data and storing it in TimescaleDB for anomaly detection and monitoring.

## Features

- Generate realistic time-series sensor data for industrial environments (ovens, heaters, fans, lamps, PM sensors)
- Store data in TimescaleDB with proper time-series optimizations and hypertables
- Command-line interface for easy data generation and reading
- Support for both batch and continuous data generation
- Realistic sensor behavior simulation with state persistence
- Database schema optimized for time-series queries and anomaly detection
- Real-time data reading capabilities
- **NEW**: Anomaly injection for testing detection algorithms
- **NEW**: Real-time anomaly monitoring and alerting

## Industrial Sensor Types

The system simulates various industrial sensors commonly found in restaurants, supermarkets, and warehouses:

- **Oven Temperature Sensors**: Analog sensors (0-350°C)
- **Heater Temperature Sensors**: Analog sensors (0-180°C) 
- **Digital Lamps**: Digital I/O sensors (ON/OFF)
- **Digital Fans**: Digital I/O sensors (ON/OFF)
- **Fan Speed Sensors**: Analog RPM sensors (0-1000 RPM)
- **Particulate Matter (PM) Sensors**: Serial sensors (0-36000 PM)

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Poetry (Python package manager)
- PostgreSQL with TimescaleDB extension

## Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd anomaly-watcher
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Start TimescaleDB with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**
   ```bash
   poetry run python -m generator.db
   ```

## Usage

### Generate Sample Data

Generate 7 days of sample data with 5-minute intervals for 6 sensors:
```bash
poetry run python -m generator.cli sample --days 7 --interval 5 --sensors 6
```

Generate sample data with anomaly injection:
```bash
poetry run python -m generator.cli sample --days 7 --interval 1 --sensors 5 --anomaly-rate 0.02
```

### Continuous Data Generation

Generate data in real-time with a 60-second interval:
```bash
poetry run python -m generator.cli continuous --interval 60 --sensors 6 --duration 30
```

Generate with anomaly injection (3% rate):
```bash
poetry run python -m generator.cli continuous --interval 60 --sensors 5 --anomaly-rate 0.03 --duration 60
```

Demo mode with example anomalies:
```bash
poetry run python -m generator.cli continuous --interval 30 --sensors 5 --demo --duration 30
```

### Read Data from Database

Read the latest sensor data:
```bash
poetry run python -m generator.cli read --limit 100
```

### Monitor Data in Real-time

Monitor data continuously with live updates:
```bash
poetry run python -m generator.cli read --loop
```

## Anomaly Detection & Monitoring

### Train Models

First, generate some historical data, then train anomaly detection models:

```bash
# Generate training data (1 week)
poetry run python -m generator.cli sample --days 7 --interval 1 --sensors 5

# Train models on historical data
poetry run python -m core.anomaly_detection.cli train --hours 168

# Check model status
poetry run python -m core.anomaly_detection.cli status
```

### Real-time Monitoring

Run data generation with simultaneous anomaly monitoring:

```bash
# Run both data generation and monitoring
poetry run python scripts/run_with_monitoring.py --duration 2

# Run with custom settings
poetry run python scripts/run_with_monitoring.py \
    --data-interval 30 \
    --monitor-interval 90 \
    --threshold 0.8 \
    --duration 1

# 3% anomaly rate with monitoring
poetry run python scripts/run_with_monitoring.py --anomaly-rate 0.03 --duration 1

# Demo mode with pre-defined anomalies
poetry run python scripts/run_with_monitoring.py --demo-anomalies --duration 0.5
```

### Monitor Existing Data

```bash
# Monitor existing data only
python -m core.anomaly_detection.monitor \
    --interval 60 \
    --window 15 \
    --threshold 0.7

# Using the launcher
poetry run python scripts/run_with_monitoring.py --monitor-only --duration 0.5
```

### Manual Anomaly Control

```bash
# Force specific anomalies during generation
poetry run python -m generator.cli anomaly force oven-restaurant-abc123 oven spike --duration 15
poetry run python -m generator.cli anomaly force fan-factory-def456 fan stall --duration 20
poetry run python -m generator.cli anomaly force pm-supermarket-ghi789 pm pollution_spike --duration 30

# Check anomaly status
poetry run python -m generator.cli anomaly status

# Clear all anomalies
poetry run python -m generator.cli anomaly clear
```

## Anomaly Types

The system can inject various realistic anomalies:

🔥 **Oven**: Temperature spikes (+50-100°C), drops (-30-10°C), drift, oscillation  
🔧 **Heater**: Temperature spikes, drops, gradual drift, oscillation  
💡 **Lamp**: Flicker (rapid on/off), stuck off, stuck on  
🌪️ **Fan**: RPM spikes, stall (stops), vibration, overspeed  
🌫️ **PM**: Pollution spikes (+50-150 µg/m³), sensor drift, calibration errors, dust storms

## Database Schema

The main `sensors_data` table includes the following columns:

- `id`: UUID primary key (composite with timestamp for TimescaleDB)
- `timestamp`: Timestamp of the reading (partitioning column)
- `sensor_id`: Unique identifier for the sensor
- `type`: Type of sensor (analog, digital, serial)
- `category`: Category of the sensor (oven, heater, lamp, fan, pm)
- `value`: Numeric reading value
- `unit`: Unit of measurement (°C, io, rpm, PM)
- `location`: Location of the sensor (restaurant, supermarket, factory)
- `sensors_metadata`: Additional metadata as JSON (firmware version, battery level)

## TimescaleDB Optimizations

- **Hypertables**: Automatic partitioning by timestamp
- **Chunk Intervals**: 1-day chunks for optimal query performance
- **Compression**: Automatic compression for chunks older than 7 days
- **Indexes**: Optimized indexes on sensor_id and timestamp
- **Retention Policies**: Configurable data retention

## Realistic Sensor Behavior

The generator creates realistic sensor data by:

- **State Persistence**: Sensors remember their last values
- **Gradual Changes**: Analog sensors change gradually, not randomly
- **Realistic Ranges**: Each sensor type has appropriate min/max values
- **Location-based IDs**: Sensor IDs include location information
- **Digital Logic**: Digital sensors properly toggle between 0/1 states
- **Industrial Patterns**: Simulates real industrial equipment behavior
- **Anomaly Injection**: Configurable injection of realistic anomalies

## Querying Data

Example queries for anomaly detection:

```sql
-- Get latest readings for all sensors
SELECT * FROM sensors_data 
ORDER BY timestamp DESC 
LIMIT 10;

-- Get average oven temperature by hour for the last 7 days
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    sensor_id,
    AVG(value) as avg_temp
FROM sensors_data 
WHERE category = 'oven' 
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour, sensor_id
ORDER BY hour;

-- Find temperature anomalies (ovens running too hot)
SELECT 
    timestamp,
    sensor_id,
    location,
    value,
    unit
FROM sensors_data 
WHERE category = 'oven' 
  AND value > 300  -- Alert threshold
  AND timestamp > NOW() - INTERVAL '1 day'
ORDER BY timestamp DESC;

-- Monitor fan performance (RPM sensors)
SELECT 
    time_bucket('15 minutes', timestamp) AS interval,
    sensor_id,
    location,
    AVG(value) as avg_rpm,
    MAX(value) as max_rpm,
    MIN(value) as min_rpm
FROM sensors_data 
WHERE category = 'fan' AND type = 'analog'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY interval, sensor_id, location
ORDER BY interval DESC;

-- Detect equipment state changes (digital sensors)
SELECT 
    timestamp,
    sensor_id,
    category,
    location,
    value as state,
    LAG(value) OVER (PARTITION BY sensor_id ORDER BY timestamp) as previous_state
FROM sensors_data 
WHERE type = 'digital'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

## Project Structure

```
anomaly-watcher/
├── generator/
│   ├── cli.py                    # Command-line interface
│   ├── db.py                     # Database initialization
│   ├── sensors/                  # Sensor implementations
│   │   ├── base.py              # Base sensor class
│   │   ├── anomaly_injector.py  # Anomaly injection logic
│   │   └── ...                  # Individual sensor types
│   └── utils/
│       ├── data_generator.py    # Data generation logic
│       └── reader.py            # Data reading utilities
├── core/
│   └── anomaly_detection/       # ML-based anomaly detection
│       ├── cli.py              # Detection CLI
│       ├── detector.py         # Detection algorithms
│       └── monitor.py          # Real-time monitoring
├── scripts/
│   └── run_with_monitoring.py  # Combined runner script
├── database/
│   └── models/
│       └── base.py             # Database configuration
├── docker-compose.yml          # TimescaleDB setup
├── pyproject.toml             # Poetry configuration
└── README.md
```

## Development

### Running the Generator

```bash
# Generate historical data
poetry run python -m generator.cli sample --days 30 --interval 1

# Start real-time generation
poetry run python -m generator.cli continuous --interval 30 --sensors 10

# Read data
poetry run python -m generator.cli read
```

### Train Models

```bash
# Train and save models
poetry run python -m core.anomaly_detection.cli train --hours 168

# Check status (should now show trained models)
poetry run python -m core.anomaly_detection.cli status
```

Models will be saved in `models/anomaly_detection/` directory

### Run Complete System

```bash
# Run both data generation and monitoring
poetry run python -m scripts.run_with_monitoring

# Run with custom settings
poetry run python -m scripts.run_with_monitoring \
    --data-interval 30 \
    --monitor-interval 30 \
    --threshold 0.57 \
    --duration 6 \
    --anomaly-rate 0.02
```

### Database Connection

Default connection: `postgresql://postgres:postgres@localhost:5432/sensor_data`

### Adding New Sensor Types

Edit `SENSOR_CLASSES` in `generator/utils/data_generator.py` to add new sensor configurations.

## License

MIT License