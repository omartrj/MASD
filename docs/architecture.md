# Architecture

The pipeline consists of several components orchestrated by Docker Compose to create a complete data streaming and processing environment.

## 🤖 Simulator

A Python-based producer that simulates multiple IoT sensors from different stations. It is highly configurable through the `simulator/config.json` file, which defines:

-   `send_interval`: Controls the rate of message production, with `mean_ms` for the average interval and `stddev_pct` for variability.
-   `malformation_pct`: The percentage of intentionally malformed JSON messages, used to test the resilience of the consumer.
-   `stations`: A list of simulated stations, each with its own `name`, `id`, and `num_sensors`. Each station runs in a separate Docker container, allowing for parallel and isolated data generation.

The simulators connect to Kafka using the `KAFKA_BOOTSTRAP_SERVERS` variable from the `.env` file and publish to topics created with the `KAFKA_TOPIC_PREFIX`.

## 📬 Kafka + ZooKeeper

The core of the data ingestion layer, configured for high availability and fault tolerance.

-   **Kafka**: A cluster of 3 brokers (`kafka1`, `kafka2`, `kafka3`) acts as a distributed message broker. It receives data streams from the simulators and is configured with the following parameters from the `.env` file:
    -   `KAFKA_NUM_PARTITIONS=3`: Each topic is split into 3 partitions, allowing for parallel consumption by Spark.
    -   `KAFKA_DEFAULT_REPLICATION_FACTOR=3`: Each partition is replicated across all 3 brokers, ensuring data is not lost if a broker fails.
    -   `KAFKA_MIN_INSYNC_REPLICAS=2`: A write is considered successful only when it has been confirmed by at least 2 of the 3 replicas. This guarantees strong consistency and durability even in the event of a broker failure.
-   **ZooKeeper**: Used by Kafka for cluster coordination, managing broker metadata, and maintaining consumer state.

## ✨ Spark

A powerful data processing engine that consumes data from Kafka in real-time. The Spark Structured Streaming application runs on a Hadoop YARN cluster and is configured for windowed aggregations with the following parameters:

-   `SPARK_AGGREGATE_WINDOW="1 minute"`: Data is grouped into 1-minute tumbling (non-overlapping) windows based on the event timestamp.
-   `SPARK_AGGREGATE_SLIDE="1 minute"`: The window slides every minute, matching the window duration to ensure no overlaps.
-   `SPARK_AGGREGATE_TRIGGER_INTERVAL="1 minute"`: The aggregation is triggered every minute, processing the data collected in the preceding window.
-   `SPARK_AGGREGATE_WATERMARK="5 seconds"`: The application tolerates data arriving up to 5 seconds late. Any data older than that is dropped to avoid delaying the stream.
-   `SPARK_AGGREGATE_CHECKPOINT_DIR`: Specifies a directory in HDFS for storing checkpointing information, which ensures fault tolerance by allowing the streaming query to recover from failures and continue from where it left off.

The application performs the following tasks:

1.  **Reads data streams** from Kafka topics.
2.  **Validates and cleans** the incoming JSON data, filtering out malformed records.
3.  **Parses the data** and applies a schema to structure it.
4.  **Performs real-time aggregations** within the defined windows to calculate statistics like average, standard deviation, minimum, and maximum sensor values.
5.  **Writes the aggregated results** to MongoDB for persistence and further analysis.

## 💾 MongoDB

A NoSQL database used to store the aggregated results from the Spark processing job. It is configured as a 3-node replica set (`mongodb-primary`, `mongodb-secondary1`, `mongodb-secondary2`) to ensure high availability and data redundancy. The configuration is defined by these variables:

-   `MONGO_URI`: Specifies the connection string for the replica set, ensuring that the application can connect to the primary node even if a failover occurs.
-   `MONGO_WRITE_CONCERN=majority`: A write operation is only acknowledged after it has been committed to the primary and a majority (i.e., at least one other secondary) of the replicas. This prevents data loss in case the primary node goes down.
-   `MONGO_READ_PREFERENCE=primaryPreferred`: Read operations are directed to the primary node by default, but if it is unavailable, they are routed to secondary nodes. This ensures that reads are always possible while preferring the most up-to-date data.

## 🐘 Hadoop (HDFS + YARN)

Provides the distributed computing backbone for Spark. The cluster consists of a `namenode` and `resourcemanager`, and is designed to be scalable. You can add more `datanode` and `nodemanager` containers to expand the cluster's storage and processing capacity.

-   **HDFS (Hadoop Distributed File System)**: Offers distributed storage. In this project, it is primarily used by Spark for checkpointing (as defined by `SPARK_AGGREGATE_CHECKPOINT_DIR`) and for shuffling data between distributed stages of the Spark job.
-   **YARN (Yet Another Resource Negotiator)**: The cluster resource manager. It is responsible for scheduling the Spark application and allocating cluster resources (CPU, memory) to it, enabling distributed execution across multiple nodes.
-   `HADOOP_HOME`: This environment variable is set in the Docker containers to specify the path to the Hadoop installation, which is essential for the services to run correctly.
