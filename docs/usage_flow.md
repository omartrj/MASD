# Usage Flow

This document describes the end-to-end flow of data in the MASD pipeline, from generation to storage, including how to verify each step.

## 1. 📡 Data Generation (Simulator)

The **Simulator** (`simulator/producer.py`) acts as an IoT gateway. It generates synthetic sensor data and publishes it to Kafka.

### Data Format
The simulator generates JSON messages. The validity of the message is determined by the `value` field:

**1. Valid Data**
`value` is a number.
```json
{
  "station_name": "Perugia",
  "station_id": "perugia",
  "sensor_id": 1,
  "timestamp": 1700000000000,
  "value": 42.5
}
```

**2. Malformed Data**
`value` is a string (e.g., `"<<bad_data>>"`). Injected intentionally based on `malformation_pct` in `config.json` to test Spark's error handling.
```json
{
  "station_name": "Perugia",
  "station_id": "perugia",
  "sensor_id": 1,
  "timestamp": 1700000000000,
  "value": "<<bad_data>>"
}
```

### Configuration
The simulation is controlled by `simulator/config.json`, where you can define stations, sensor counts, and generation intervals.

---

## 2. 📬 Ingestion (Kafka)

Data is published to Kafka topics named `sensors.raw.<station_id>` (e.g., `sensors.raw.perugia`).

### Verification

To verify that data is being published correctly, you can use either the command line or the Kafka UI.

**Option A: Command Line (Interactive)**

1.  **Access the container shell:**
    ```bash
    docker exec -it kafka1 bash
    ```

2.  **List all topics:**
    Verify that topics have been created for each station.
    ```bash
    kafka-topics --bootstrap-server localhost:9092 --list
    ```
    ![Screenshot: Kafka Topics List](placeholder_kafka_topics.png)

3.  **Describe a specific topic:**
    Check partition count and replication details.
    ```bash
    kafka-topics --bootstrap-server localhost:9092 --describe --topic sensors.raw.perugia
    ```
    ![Screenshot: Kafka Topic Describe](placeholder_kafka_describe.png)

4.  **Consume messages:**
    Read the actual data flowing into the topic.
    ```bash
    kafka-console-consumer --bootstrap-server localhost:9092 --topic sensors.raw.perugia --from-beginning --max-messages 5
    ```
    ![Screenshot: Kafka Console Consumer](placeholder_kafka_consumer.png)

**Option B: Kafka UI**

1.  Open [http://localhost:8080](http://localhost:8080).
2.  Navigate to **Topics**.
3.  Select a topic (e.g., `sensors.raw.perugia`).
4.  Go to the **Messages** tab to see real-time data.

![Screenshot: Kafka UI Messages](placeholder_kafka_ui.png)

---

## 3. ✨ Processing (Spark)

The **Spark Application** (`spark-app/consumer.py`) consumes data from Kafka, validates it, and performs windowed aggregations.

### Logic
1.  **Ingest**: Reads from all `sensors.raw.*` topics.
2.  **Parse & Validate**: Converts JSON to a structured schema. Infers validity by checking if `value` is numeric.
3.  **Aggregate**: Groups data into **1-minute tumbling windows**.
    -   Calculates: `min_val`, `max_val`, `avg_val`, `total_count`, and `malformed_count`.

### Verification

**Check Logs**
View the logs of the Spark application to see batch processing status:
```bash
docker logs -f spark-app
```
*Look for messages like: `Batch 5 | perugia: 120 aggregati scritti`.*

![Screenshot: Spark App Logs](placeholder_spark_logs.png)

**YARN ResourceManager**
Open [http://localhost:8088](http://localhost:8088) to see the running Spark application (`MASD`) and its resource usage.

![Screenshot: YARN ResourceManager](placeholder_yarn_ui.png)

---

## 4. 💾 Storage (MongoDB)

Aggregated results are saved to MongoDB in the `masd_sensors` database. Each station has its own collection named `station_<station_id>` (e.g., `station_perugia`).

### Data Format
The stored documents contain the statistics for each window in a nested structure:
```json
{
  "window": {
    "start": "2023-11-20T10:00:00.000Z",
    "end": "2023-11-20T10:01:00.000Z"
  },
  "station": {
    "id": "perugia",
    "name": "Perugia"
  },
  "sensor": {
    "id": "1"
  },
  "metrics": {
    "min_value": 40.1,
    "max_value": 45.2,
    "avg_value": 42.5,
    "count": {
      "total": 60,
      "malformed": 3
    }
  }
}
```

### Verification

**Option A: Command Line (Mongosh)**

Use the MongoDB Shell (`mongosh`) to interactively explore the data.

1.  **Access the MongoDB Shell:**
    ```bash
    docker exec -it mongodb-primary mongosh
    ```

2.  **Show Databases:**
    Verify that `masd_sensors` exists.
    ```javascript
    show dbs
    ```
    ![Screenshot: Mongo Show DBs](placeholder_mongo_dbs.png)

3.  **Switch to the database:**
    ```javascript
    use masd_sensors
    ```

4.  **Show Collections:**
    You should see one collection per station (e.g., `station_perugia`).
    ```javascript
    show collections
    ```
    ![Screenshot: Mongo Show Collections](placeholder_mongo_collections.png)

5.  **Query Aggregated Data:**
    Retrieve the most recent aggregations for a station.
    ```javascript
    db.station_perugia.find().sort({"window.start": -1}).limit(3)
    ```
    ![Screenshot: Mongo Query Result](placeholder_mongo_query.png)

**Option B: Mongo Express**

1.  Open [http://localhost:8081](http://localhost:8081).
2.  Click on the `masd_sensors` database.
3.  Select a collection (e.g., `station_perugia`) to view the documents.

![Screenshot: Mongo Express UI](placeholder_mongo_express.png)
