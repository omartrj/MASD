import asyncio
import enum
import os
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer # pyright: ignore[reportMissingImports]

# === CONFIGURAZIONE ===
class Config:
    # Metadata
    PROJECT_NAME = "MASD"
    PROJECT_VERSION = "1.0.0"
    PROJECT_AUTHOR = "Omar Criacci"
    PROJECT_EMAIL = "omar.criacci@student.unipg.it"
    PROJECT_GITHUB = "https://github.com/omartrj/MASD"

    # Simulazione Sensori
    SIM_STATION_NAME = os.getenv("SIM_STATION_NAME")
    SIM_STATION_ID = os.getenv("SIM_STATION_ID")
    SIM_NUM_SENSORS = int(os.getenv("SIM_NUM_SENSORS"))
    SIM_INTERVAL_MEAN_MS = int(os.getenv("SIM_INTERVAL_MEAN_MS"))
    SIM_INTERVAL_STDDEV_PCT = float(os.getenv("SIM_INTERVAL_STDDEV_PCT"))
    SIM_MALFORMED_PCT = float(os.getenv("SIM_MALFORMED_PCT"))
    SIM_INTERVAL_STD_DEV = SIM_INTERVAL_MEAN_MS * SIM_INTERVAL_STDDEV_PCT

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX")
    KAFKA_TOPIC = f"{KAFKA_TOPIC_PREFIX}.{SIM_STATION_ID}"

    VERBOSE_LOGGING = False

# === UTILS ===
def log(level: str, message: str):
    """Stampa messaggio con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# === CONNESSIONE KAFKA ===
def connect_to_kafka():
    """Connette al cluster Kafka con retry automatico."""
    #print(f"Connessione a Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    log("INFO", f"Connessione a Kafka: {Config.KAFKA_BOOTSTRAP_SERVERS}")
    
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                linger_ms=10,
                acks="all",
            )
            log("INFO", "Connesso a Kafka")
            return producer
        except Exception as e:
            log("WARN", f"Errore connessione Kafka: {e}. Riprovo tra 2 secondi...")
            time.sleep(2)


producer = connect_to_kafka()


# === GENERAZIONE DATI ===
def make_payload(sensor_id, mean_value):
    """
    Genera un payload sensore.
    - value=numero per dati validi
    - value="<<bad_data>>" per dati corrotti
    """
    timestamp = int(time.time() * 1000)

    value = "<<bad_data>>"
    if random.random() > Config.SIM_MALFORMED_PCT:
        value = max(0, round(random.gauss(mean_value, mean_value / 10), 3))

    return {
        "station_name": Config.SIM_STATION_NAME,
        "station_id": Config.SIM_STATION_ID,
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "value": value,
    }


# === TASK SENSORE ===
async def sensor_task(sensor_id):
    """Task asincrono che simula un sensore che pubblica dati a intervalli regolari."""
    # Offset iniziale per distribuire le pubblicazioni nel tempo
    await asyncio.sleep(sensor_id * (Config.SIM_INTERVAL_MEAN_MS / 1000) / Config.SIM_NUM_SENSORS)
    
    while True:
        mean_value = max(30, random.gauss(70.0, 20.0))
        payload = make_payload(sensor_id, mean_value)
        producer.send(Config.KAFKA_TOPIC, key=sensor_id, value=payload)
        
        if Config.VERBOSE_LOGGING:
            log(f"SENSOR_{sensor_id}", f"SENT: {payload}")
        
        # Genera intervallo con distribuzione gaussiana
        # max(0, ...) per evitare valori negativi
        interval_seconds = max(0, random.gauss(Config.SIM_INTERVAL_MEAN_MS, Config.SIM_INTERVAL_STD_DEV) / 1000)
        #print(f"[SENSOR_{sensor_id}] Next in {interval_seconds*1000:.2f} ms")
        await asyncio.sleep(interval_seconds)


# === MAIN ===
async def main():
    print("="*70)
    print(f"{Config.PROJECT_NAME} - Sensors Simulator")
    print(f"  - version: {Config.PROJECT_VERSION}")
    print(f"  - author: {Config.PROJECT_AUTHOR} ({Config.PROJECT_EMAIL})")
    print(f"  - repository: {Config.PROJECT_GITHUB}")
    print("="*70)
    print(f"STARTING STATION SIMULATOR - {Config.SIM_STATION_NAME} (ID: {Config.SIM_STATION_ID})")
    print(f"  - # sensors: {Config.SIM_NUM_SENSORS}")
    print(f"  - average send interval: {Config.SIM_INTERVAL_MEAN_MS}ms")
    print(f"  - interval standard deviation: {Config.SIM_INTERVAL_STDDEV_PCT*100}%")
    print(f"  - malformed packets: {Config.SIM_MALFORMED_PCT*100}%")
    print(f"  - sending packets to {Config.KAFKA_BOOTSTRAP_SERVERS} | topic: {Config.KAFKA_TOPIC}")
    print("="*70)
    
    # Avvia tutti i task dei sensori in parallelo
    tasks = [asyncio.create_task(sensor_task(i)) for i in range(Config.SIM_NUM_SENSORS)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("WARN", "Chiusura in corso...")
        producer.flush()
        producer.close()
        log("INFO", "Simulatore terminato.")
        log("INFO", "Stopped.")