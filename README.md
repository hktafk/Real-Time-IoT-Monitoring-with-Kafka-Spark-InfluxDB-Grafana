# Confluent MQTT Project

This project contains a complete IoT data pipeline using MQTT, Modbus, Spark, and InfluxDB.

## Components

- **modbus-simulator/**: Modbus device simulator
- **mqtt-forwarder/**: MQTT message forwarder
- **spark/**: Spark streaming application for data processing
- **New folder/**: Jupyter notebooks for development and testing

## Configuration Files

- `docker-compose.yml`: Docker services orchestration
- `mosquitto.conf`: MQTT broker configuration
- `telegraf.conf`: Telegraf configuration for data collection

## Getting Started

1. Run the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. The system will start all required services including MQTT broker, data simulators, and processing components.

## Architecture

The system follows a typical IoT data pipeline:
1. Modbus Simulator generates device data
2. MQTT Forwarder publishes data to MQTT broker
3. Spark processes the streaming data
4. Data is stored in InfluxDB for analysis