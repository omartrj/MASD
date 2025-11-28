# MASD — Monitoring & Analytics of Streaming Data

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E35A16?style=flat&logo=apachespark&logoColor=white) ![Apache Hadoop](https://img.shields.io/badge/Apache%20Hadoop-66CCFF?style=flat&logo=apachehadoop&logoColor=black) ![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-000000?style=flat&logo=apachekafka&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)

Project for the **Data Intensive Application & Big Data** exam, University of Perugia.

A data streaming pipeline that simulates IoT sensors, sends data to Kafka, processes it with Spark on a Hadoop cluster, and finally saves it to MongoDB. The entire environment is containerized with Docker Compose.

**Author**: Omar Criacci (omar.criacci@student.unipg.it)  
**Version**: 1.0.0

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Quick Start](#-quickstart)
    - [Automatic (Recommended)](#automatic-recommended)
    - [Manual Startup (without jq)](#manual-startup-without-jq)
- [Usage Example](#-usage-example)
- [Web Interfaces](#-web-interfaces)
- [Simulator Configuration](#%EF%B8%8F-simulator-configuration)
- [Architecture](#%EF%B8%8F-architecture)
- [Structure](#-structure)
- [Useful Commands](#-useful-commands)

## ✅ Prerequisites

- Docker and Docker Compose
- jq (optional, for the simulation script)
- At least 8 GB of RAM - *but more is better*

## 🚀 Quickstart

### Automatic (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/omartrj/MASD.git
   cd MASD
   ```

2. Start the entire stack (Kafka, MongoDB, Hadoop, Spark):
   ```bash
   # Minimal setup
   docker compose up -d --build
   
   # To also start the web UIs for Kafka and MongoDB (optional):
   docker compose --profile web-ui up -d --build
   
   # To scale the Hadoop cluster (optional):
   docker compose up -d --build --scale hdfs-datanode=2 --scale yarn-nodemanager=2

   # Everything
   docker compose --profile web-ui up -d --build --scale hdfs-datanode=2 --scale yarn-nodemanager=2
   ```

3. Start the simulators:
   ```bash
   ./run_simulation.sh -c simulator/config.json
   ```

   **Note**: To stop the simulators, press `CTRL+C`. The script will automatically terminate all simulator containers.

### Manual Startup (without jq)

If you don't have `jq` installed (*you should get it, it's useful!*), you can start the simulators manually:

1. Build the simulator image:
   ```bash
   docker build -t masd-simulator:latest ./simulator
   ```
2. Load the environment variables:
   ```bash
   source .env
   ```
3. Start each station manually:
   ```bash
   docker run -d \
     --name "simulator-<station_id>" \
     --network "masd-network" \
     -e SIM_STATION_NAME="<station_name>" \
     -e SIM_STATION_ID="<station_id>" \
     -e SIM_NUM_SENSORS="<num_sensors>" \
     -e SIM_INTERVAL_MEAN_MS="<mean_ms>" \
     -e SIM_INTERVAL_STDDEV_PCT="<stddev_pct>" \
     -e SIM_MALFORMED_PCT="<malformation_pct>" \
     -e KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS \
     -e KAFKA_TOPIC_PREFIX=$KAFKA_TOPIC_PREFIX \
     masd-simulator:latest
   ```
    Replace the values between `<>` with the desired parameters for the station (see [simulator configuration](#%EF%B8%8F-simulator-configuration) for details).

## 📖 Usage Example

For a detailed step-by-step guide on how to verify the data flow (from generation to storage), check the [usage example](docs/usage.md).

## 🌐 Web Interfaces

Monitor the pipeline using these dashboards (if everything started correctly 🤞).

**Standard:**
-   **Hadoop NameNode** on [localhost:9870](http://localhost:9870): HDFS status and file browser.
-   **YARN ResourceManager** on [localhost:8088](http://localhost:8088): Cluster resources and Spark job status.

**Optional** (requires `--profile web-ui`):
-   **Kafka UI** on [localhost:8080](http://localhost:8080) (by [Provectus](https://github.com/provectus/kafka-ui)): Manage topics, view messages, and monitor consumers.
-   **Mongo Express** on [localhost:8081](http://localhost:8081) (by [mongo-express](https://github.com/mongo-express/mongo-express)): Admin interface for MongoDB collections.

## ⚙️ Simulator Configuration

The simulators are configured via the `simulator/config.json` file:

```jsonc
{
    "sensors": {
        "send_interval": {
            "mean_ms": 250,        // Average send interval in milliseconds
            "stddev_pct": 0.2      // Standard deviation of send interval (20%)
        },
        "malformation_pct": 0.05   // Percentage of malformed data (5%)
    },
    "stations": [
        {
            "name": "Perugia",     // Station name
            "id": "perugia",       // Unique ID (used for Kafka topic and MongoDB collection)
            "num_sensors": 3       // Number of sensors for this station
        },
        // ... other stations
    ]
}
```

Each station is started as a separate Docker container and publishes to a dedicated Kafka topic: `sensors.raw.<station_id>`.

## 🏗️ Architecture

The pipeline consists of several components orchestrated by Docker Compose to create a complete data streaming and processing environment.

-   **🤖 Simulator**: Python-based producer simulating IoT sensors.
-   **📬 Kafka + ZooKeeper**: Distributed message broker for data ingestion.
-   **✨ Spark**: Real-time data processing engine running on YARN.
-   **💾 MongoDB**: NoSQL database for storing aggregated results.
-   **🐘 Hadoop (HDFS + YARN)**: Distributed storage and resource management.

For a detailed explanation of the architecture and configuration of each component, please refer to the [architecture documentation](docs/architecture.md).

## 💡 Useful Commands

```bash
# View logs
docker logs -f container_id

# Stop everything
docker compose down

# Stop and remove volumes
docker compose down -v

# (If web UIs were started)
docker compose --profile web-ui down -v
```
