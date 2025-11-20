# 📊 MASD — Monitoring & Analytics of Streaming Data

![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E35A16?style=flat&logo=apachespark&logoColor=white) ![Apache Hadoop](https://img.shields.io/badge/Apache%20Hadoop-66CCFF?style=flat&logo=apachehadoop&logoColor=black) ![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-000000?style=flat&logo=apachekafka&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)

Project for the **Data Intensive Application & Big Data** exam, University of Perugia.

A data streaming pipeline that simulates IoT sensors, sends data to Kafka, processes it with Spark on a Hadoop cluster, and finally saves it to MongoDB. The entire environment is containerized with Docker Compose.

**Author**: Omar Criacci (omar.criacci@student.unipg.it)  
**Version**: 1.0.0

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Quick Start](#-quickstart)
    - [Automatic (Recommended)](#automatic-recommended)
    - [Manual Startup (without jq)](#manual-startup-without-jq)
- [Simulator Configuration](#️-simulator-configuration)
- [Architecture](#-architecture)
- [Structure](#-structure)
- [Useful Commands](#-useful-commands)

## ✅ Prerequisites

- Docker and Docker Compose
- jq (optional, for the simulation script)
- At least 8 GB of RAM

## 🚀 Quickstart

### Automatic (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/omarcriacci/MASD.git
   cd MASD
   ```

2. Start the entire stack (Kafka, MongoDB, Hadoop, Spark):
   ```bash
   docker compose up -d --build
   ```

   To also start the web UIs for Kafka and MongoDB (optional):
   ```bash
   docker compose --profile web-ui up -d --build
   ```

   You can also scale the Hadoop cluster by adding more nodes (optional):
   ```bash
   docker compose up -d --build --scale hdfs-datanode=2 --scale yarn-nodemanager=2
   ```

3. Start the simulators:
   ```bash
   ./run_simulation.sh -c simulator/config.json
   ```

   **Note**: To stop the simulators, press `CTRL+C`. The script will automatically terminate all simulator containers.

### Manual Startup (without jq)

If you don't have `jq` installed (you should get it, it's useful!), you can start the simulators manually:

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
     -e KAFKA_BOOTSTRAP_SERVERS="$KAFKA_BOOTSTRAP_SERVERS" \
     -e KAFKA_TOPIC_PREFIX="$KAFKA_TOPIC_PREFIX" \
     masd-simulator:latest
   ```
    Replace the values between `<>` with the desired parameters for the station (see `simulator/config.json`).

## ⚙️ Simulator Configuration

The simulators are configured via the `simulator/config.json` file:

```jsonc
{
    "sensors": {
        "send_interval": {
            "mean_ms": 250,        // Average send interval in milliseconds
            "stddev_pct": 0.2      // Standard deviation (20%)
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

-   **🤖 Simulator**: A Python-based producer that simulates multiple IoT sensors from different stations. It generates sensor data with configurable intervals and error rates, then publishes these messages to specific Kafka topics. Each station runs in its own Docker container, allowing for parallel and isolated data generation.

-   **📬 Kafka + ZooKeeper**: The core of the data ingestion layer.
    -   **Kafka** acts as a distributed message broker, receiving streams of sensor data from the simulators. It provides a scalable and fault-tolerant way to handle high-throughput data streams.
    -   **ZooKeeper** is used by Kafka for cluster coordination, managing broker metadata, and maintaining consumer state.

-   **✨ Spark**: A powerful data processing engine that consumes data from Kafka in real-time. The Spark application runs on a Hadoop YARN cluster and performs the following tasks:
    1.  **Reads data streams** from Kafka topics.
    2.  **Validates and cleans** the incoming JSON data, filtering out malformed records.
    3.  **Parses the data** and applies a schema to structure it.
    4.  **Performs real-time aggregations** to calculate statistics like average, standard deviation, minimum, and maximum sensor values for each station.
    5.  **Writes the aggregated results** to MongoDB for persistence and further analysis.

-   **💾 MongoDB**: A NoSQL database used to store the aggregated results from the Spark processing job. It is configured as a replica set to ensure high availability and data redundancy. The results are stored in collections named after each station's ID.

-   **🐘 Hadoop (HDFS + YARN)**: Provides the distributed computing backbone for Spark.
    -   **HDFS (Hadoop Distributed File System)** offers distributed storage, although it's primarily used by YARN and Spark for job coordination and shuffling data between stages, not for final data persistence in this project.
    -   **YARN (Yet Another Resource Negotiator)** is the cluster resource manager, responsible for scheduling and managing the distributed execution of the Spark application across multiple nodes.

## 📂 Structure

```text
.
├── .env                        # Environment variables
├── docker-compose.yml          # Main orchestration file
├── compose/                    
│   ├── kafka.yml               # Kafka Cluster (Zookeeper, 3 brokers, UI)
│   ├── mongodb.yml             # MongoDB Replica Set (3 nodes, UI)
│   ├── hadoop.yml              # Hadoop Cluster (HDFS + YARN)
│   └── spark.yml               # Spark Application
├── hadoop.config               # Hadoop configuration
├── run_simulation.sh           # Script to start simulators
├── README.md                   
├── simulator/                  # Simulator (Producer)
│   ├── producer.py
│   ├── config.json             # Simulation configuration   
│   ├── requirements.txt
│   └── Dockerfile
└── spark-app/                  # Spark Application (Consumer)
    ├── consumer.py
    ├── requirements.txt
    └── Dockerfile
```

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
