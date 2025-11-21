import os
import pathlib
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame # pyright: ignore[reportMissingImports]
from pyspark.sql.functions import ( # pyright: ignore[reportMissingImports]
    col, from_json, window, avg, min, max, count, to_timestamp, sum, when, struct
)
from pyspark.sql.types import ( # pyright: ignore[reportMissingImports]
    StructType, StructField, StringType, LongType
)

# === CONFIGURAZIONE ===
class Config:
    # Metadata
    PROJECT_NAME = "MASD"
    PROJECT_VERSION = "1.0.0"
    PROJECT_AUTHOR = "Omar Criacci"
    PROJECT_EMAIL = "omar.criacci@student.unipg.it"
    PROJECT_GITHUB = "https://github.com/omartrj/MASD"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX")
    
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    MONGO_WRITE_CONCERN = os.getenv("MONGO_WRITE_CONCERN", "majority")
    
    # Spark
    TRIGGER_INTERVAL = os.getenv("SPARK_AGGREGATE_TRIGGER_INTERVAL")
    WINDOW_DURATION = os.getenv("SPARK_AGGREGATE_WINDOW")
    SLIDE_DURATION = os.getenv("SPARK_AGGREGATE_SLIDE")
    WATERMARK_DELAY = os.getenv("SPARK_AGGREGATE_WATERMARK")
    CHECKPOINT_DIR = os.getenv("SPARK_AGGREGATE_CHECKPOINT_DIR")

# === SCHEMA DATI ===
# value: numero (es. "42.5") o stringa (es. "<<bad_data>>")
SENSOR_SCHEMA = StructType([
    StructField("station_name", StringType(), True),
    StructField("station_id", StringType(), True),
    StructField("sensor_id", StringType(), True),
    StructField("timestamp", LongType(), True),
    StructField("value", StringType(), True)
])


# === UTILS ===
def log(level: str, message: str):
    """Stampa messaggio con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def create_spark_session():
    """Inizializza e restituisce la sessione Spark."""
    spark = SparkSession.builder \
        .appName(f"{Config.PROJECT_NAME} - Spark Consumer") \
        .config("spark.mongodb.connection.uri", Config.MONGO_URI) \
        .config("spark.mongodb.write.writeConcern.w", Config.MONGO_WRITE_CONCERN) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def print_startup_banner():
    """Stampa le informazioni di avvio."""
    print("="*70)
    print(f"{Config.PROJECT_NAME} - Spark Consumer")
    print(f"  - Versione: {Config.PROJECT_VERSION}")
    print(f"  - Autore: {Config.PROJECT_AUTHOR} ({Config.PROJECT_EMAIL})")
    print(f"  - Repository: {Config.PROJECT_GITHUB}")
    print("="*70)
    print("CONFIGURAZIONE ATTIVA")
    print(f"  - Kafka: {Config.KAFKA_BOOTSTRAP_SERVERS} (Topic: {Config.KAFKA_TOPIC_PREFIX}.*)")
    print(f"  - MongoDB: {Config.MONGO_URI} ({Config.MONGO_DATABASE})")
    print(f"  - Aggregation Window: {Config.WINDOW_DURATION} (Slide: {Config.SLIDE_DURATION})")
    print(f"  - Watermark: {Config.WATERMARK_DELAY}")
    print("="*70)


def read_kafka_stream(sparkSession):
    """Legge lo stream da Kafka."""
    return sparkSession.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", Config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribePattern", f"{Config.KAFKA_TOPIC_PREFIX}.*") \
        .option("startingOffsets", "latest") \
        .load()


def parse_and_validate_data(df):
    """
    Parsa il JSON e stabilisce la validità del dato.
    - Converte 'value' in double: se riesce è valido, altrimenti è malformato.
    - Aggiunge timestamp e watermark.
    """
    # 1. Parsing JSON
    parsed = df.select(
        from_json(col("value").cast("string"), SENSOR_SCHEMA).alias("data")
    ).select("data.*")

    # 2. Check validità
    validated = parsed.withColumn(
        "value_numeric", 
        col("value").cast("double")
    ).withColumn(
        "is_valid", 
        col("value_numeric").isNotNull()
    )

    # 3. Gestione tempo (timestamp e watermark)
    return validated \
        .withColumn("event_time", to_timestamp(col("timestamp") / 1000)) \
        .withWatermark("event_time", Config.WATERMARK_DELAY)


def compute_aggregations(df):
    """Calcola le metriche aggregate su finestre temporali.
    Usa come chiave di aggregazione:
    - window (finestra temporale)
    - station_id
    - station_name
    - sensor_id
    """
    return df.groupBy(
        window("event_time", Config.WINDOW_DURATION, Config.SLIDE_DURATION),
        "station_id",
        "station_name",
        "sensor_id"
    ).agg(
        count("*").alias("total_count"),
        sum(when(col("is_valid"), 1).otherwise(0)).alias("valid_count"),
        sum(when(col("is_valid"), 0).otherwise(1)).alias("malformed_count"),
        avg(when(col("is_valid"), col("value_numeric"))).alias("avg_val"),
        min(when(col("is_valid"), col("value_numeric"))).alias("min_val"),
        max(when(col("is_valid"), col("value_numeric"))).alias("max_val")
    )


def prepare_output_structure(df):
    """Ristruttura il DataFrame in una forma più leggibile"""
    return df.select(
        struct(
            col("window.start").alias("start"),
            col("window.end").alias("end")
        ).alias("window"),
        struct(
            col("station_id").alias("id"),
            col("station_name").alias("name")
        ).alias("station"),
        struct(
            col("sensor_id").alias("id")
        ).alias("sensor"),
        struct(
            col("min_val").alias("min_value"),
            col("max_val").alias("max_value"),
            col("avg_val").alias("avg_value"),
            struct(
                col("total_count").alias("total"),
                col("malformed_count").alias("malformed"),
            ).alias("count")
        ).alias("metrics")
    )


# === LOGICA DI SCRITTURA ===
def write_to_mongo(batch_df, batch_id: int):
    """
    Scrive il batch su MongoDB.
    Utilizza collezioni separate per ogni stazione.
    """
    if batch_df.isEmpty():
        return
    
    # Prepara la struttura dati
    final_df = prepare_output_structure(batch_df)
    
    # Ottimizzazione: Cache del batch per evitare ricalcoli nel loop
    final_df.cache()
    
    try:
        # Identifica le stazioni presenti in questo batch
        stations = [row["id"] for row in final_df.select(col("station.id").alias("id")).distinct().collect()]
        
        for station_id in stations:
            # Filtra i dati per la stazione corrente
            station_data = final_df.filter(col("station.id") == station_id)
            
            # Scrittura su MongoDB
            collection_name = f"station_{station_id}"
            
            station_data.write \
                .format("mongodb") \
                .mode("append") \
                .option("spark.mongodb.connection.uri", Config.MONGO_URI) \
                .option("spark.mongodb.database", Config.MONGO_DATABASE) \
                .option("spark.mongodb.collection", collection_name) \
                .option("spark.mongodb.write.writeConcern.w", Config.MONGO_WRITE_CONCERN) \
                .save()
            
            log("INFO", f"Batch {batch_id} | Scrittura completata per stazione: {station_id}")
            
    except Exception as e:
        log("ERROR", f"Batch {batch_id}: {str(e)}")
    finally:
        final_df.unpersist()


# === MAIN ===
def main():
    # Inizializza Spark
    spark = create_spark_session()

    print_startup_banner()
    log("INFO", "Avvio applicazione Spark...")
    
    # Pipeline di elaborazione
    # 1. Lettura
    raw_stream = read_kafka_stream(spark)
    
    # 2. Trasformazione
    processed_stream = parse_and_validate_data(raw_stream)
    
    # 3. Aggregazione
    aggregated_stream = compute_aggregations(processed_stream)
    
    # 4. Scrittura
    query = aggregated_stream.writeStream \
        .foreachBatch(write_to_mongo) \
        .option("checkpointLocation", Config.CHECKPOINT_DIR) \
        .trigger(processingTime=Config.TRIGGER_INTERVAL) \
        .start()
    
    # Flag per l'healthcheck
    pathlib.Path("/tmp/spark-ready").touch()
    log("INFO", "Sistema pronto. In attesa di dati...")
    
    query.awaitTermination()


if __name__ == "__main__":
    main()