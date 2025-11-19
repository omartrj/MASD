import os
from datetime import datetime
from pyspark.sql import SparkSession # pyright: ignore[reportMissingImports]
from pyspark.sql.functions import ( # pyright: ignore[reportMissingImports]
    col, from_json, window, avg, min, max, count, to_timestamp, sum, when
)
from pyspark.sql.types import ( # pyright: ignore[reportMissingImports]
    StructType, StructField, StringType, LongType, DoubleType
)

# === VARIABILI D'AMBIENTE ===
PROJECT_NAME = os.getenv("PROJECT_NAME")
PROJECT_VERSION = os.getenv("PROJECT_VERSION")
PROJECT_AUTHOR = os.getenv("PROJECT_AUTHOR")
PROJECT_EMAIL = os.getenv("PROJECT_EMAIL")
PROJECT_GITHUB = os.getenv("PROJECT_GITHUB")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")
MONGO_WRITE_CONCERN = os.getenv("MONGO_WRITE_CONCERN", "majority")
SPARK_AGGREGATE_TRIGGER_INTERVAL = os.getenv("SPARK_AGGREGATE_TRIGGER_INTERVAL")
SPARK_AGGREGATE_WINDOW = os.getenv("SPARK_AGGREGATE_WINDOW")
SPARK_AGGREGATE_SLIDE = os.getenv("SPARK_AGGREGATE_SLIDE")
SPARK_AGGREGATE_WATERMARK = os.getenv("SPARK_AGGREGATE_WATERMARK")
SPARK_AGGREGATE_CHECKPOINT_DIR= os.getenv("SPARK_AGGREGATE_CHECKPOINT_DIR")

# === SCHEMA DATI ===
# type: "SIMPLE" per dati validi, "MALFORMED" per dati corrotti
# value: numero (es. "42.5") o stringa (es. "<<bad_data>>")
sensor_schema = StructType([
    StructField("station_id", StringType(), True),
    StructField("sensor_id", StringType(), True),
    StructField("timestamp", LongType(), True),
    StructField("type", StringType(), True),
    StructField("value", StringType(), True)
])


# === FUNZIONI DI SCRITTURA ===
def log(message):
    """Stampa messaggio con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")


def write_aggregates(batch_df, batch_id):
    """Scrive statistiche aggregate su MongoDB: un database con collezione per stazione."""
    if batch_df.isEmpty():
        log(f"Batch {batch_id}: nessuna statistica da scrivere")
        return
    
    # Appiattisci la struttura window per MongoDB
    flat_df = batch_df.select(
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        "station_id", "sensor_id", "count", "malformed_count", "avg", "min", "max"
    )
    
    # Raggruppa per stazione e scrivi in collezioni separate
    stations = [row["station_id"] for row in flat_df.select("station_id").distinct().collect()]
    
    for station_id in stations:
        station_stats = flat_df.filter(col("station_id") == station_id)
        stat_count = station_stats.count()
        
        # Ottieni la finestra per il log
        window_info = station_stats.select("window_start", "window_end").first()
        window_start = window_info["window_start"]
        window_end = window_info["window_end"]
        
        station_stats.write \
            .format("mongodb") \
            .mode("append") \
            .option("spark.mongodb.connection.uri", MONGO_URI) \
            .option("spark.mongodb.database", MONGO_DATABASE) \
            .option("spark.mongodb.collection", station_id) \
            .option("spark.mongodb.write.writeConcern.w", MONGO_WRITE_CONCERN) \
            .save()
        
        log(f"Batch {batch_id} | {station_id}: {stat_count} aggregati scritti | Finestra: [{window_start} → {window_end}]")




# === MAIN ===
def main():
    
    # Crea Spark Session
    spark = SparkSession.builder \
        .appName(PROJECT_NAME) \
        .config("spark.mongodb.connection.uri", MONGO_URI) \
        .config("spark.mongodb.write.writeConcern.w", MONGO_WRITE_CONCERN) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")

    print("="*70)
    print(f"{PROJECT_NAME} - Consumer Spark Streaming")
    print(f"  - Versione: {PROJECT_VERSION}")
    print(f"  - Autore: {PROJECT_AUTHOR} ({PROJECT_EMAIL})")
    print(f"  - Repository: {PROJECT_GITHUB}")
    print("="*70)
    print("AVVIO CONSUMER SPARK STREAMING")
    print(f"  - Connessione a Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  - Topic Kafka: {KAFKA_TOPIC_PREFIX}.*")
    print(f"  - Scrittura su MongoDB: {MONGO_URI}")
    print(f"  - Database MongoDB: {MONGO_DATABASE}")
    print("="*70)    
    
    # === LETTURA DA KAFKA ===
    kafka_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribePattern", f"{KAFKA_TOPIC_PREFIX}.*") \
        .option("startingOffsets", "latest") \
        .load()
    
    # === PARSING JSON ===
    parsed_stream = kafka_stream.select(
        from_json(col("value").cast("string"), sensor_schema).alias("data")
    ).select("data.*")
    
    # === STREAM AGGREGAZIONI ===
    # Converti value in numerico solo per pacchetti validi (type == "SIMPLE")
    # I pacchetti malformati avranno value_numeric = null e saranno ignorati nelle aggregazioni
    numeric_stream = parsed_stream.withColumn(
        "value_numeric",
        when(col("type") == "SIMPLE", col("value").cast("double")).otherwise(None)
    )
    
    # Aggiungi timestamp e watermark per le finestre temporali
    timestamped_stream = numeric_stream \
        .withColumn("event_time", to_timestamp(col("timestamp") / 1000)) \
        .withWatermark("event_time", SPARK_AGGREGATE_WATERMARK)
    
    # Calcola aggregazioni su finestre temporali
    aggregated_stream = timestamped_stream.groupBy(
        window("event_time", SPARK_AGGREGATE_WINDOW, SPARK_AGGREGATE_SLIDE),
        "station_id",
        "sensor_id"
    ).agg(
        count("*").alias("count"),
        sum(when(col("type") == "MALFORMED", 1).otherwise(0)).alias("malformed_count"),
        avg("value_numeric").alias("avg"),
        min("value_numeric").alias("min"),
        max("value_numeric").alias("max")
    )
    
    stats_query = aggregated_stream.writeStream \
        .foreachBatch(write_aggregates) \
        .option("checkpointLocation", SPARK_AGGREGATE_CHECKPOINT_DIR) \
        .trigger(processingTime=SPARK_AGGREGATE_TRIGGER_INTERVAL) \
        .start()
    
    print(f"Stream AGGREGATES avviato")
    print(f"  - Trigger: {SPARK_AGGREGATE_TRIGGER_INTERVAL}")
    print(f"  - Finestra: {SPARK_AGGREGATE_WINDOW}")
    print(f"  - Slide: {SPARK_AGGREGATE_SLIDE}")
    print(f"  - Watermark: {SPARK_AGGREGATE_WATERMARK}")
    print("="*70)
    
    # Crea file di ready quando Spark è completamente avviato
    # Serve per l'healthcheck del container
    import pathlib
    pathlib.Path("/tmp/spark-ready").touch()
    log("Spark App pronta, in attesa di dati da Kafka...")
    
    # Attendi la terminazione dello stream
    stats_query.awaitTermination()


if __name__ == "__main__":
    main()