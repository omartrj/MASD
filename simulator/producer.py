import asyncio
import os
import json
import time
import random
from kafka import KafkaProducer # pyright: ignore[reportMissingImports]

# === VARIABILI D'AMBIENTE ===
PROJECT_NAME = os.getenv("PROJECT_NAME")
PROJECT_VERSION = os.getenv("PROJECT_VERSION")
PROJECT_AUTHOR = os.getenv("PROJECT_AUTHOR")
PROJECT_EMAIL = os.getenv("PROJECT_EMAIL")
PROJECT_GITHUB = os.getenv("PROJECT_GITHUB")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX")
SIM_STATION_NAME = os.getenv("SIM_STATION_NAME")
SIM_STATION_ID = os.getenv("SIM_STATION_ID")
SIM_NUM_SENSORS = int(os.getenv("SIM_NUM_SENSORS"))
SIM_INTERVAL_MEAN_MS = int(os.getenv("SIM_INTERVAL_MEAN_MS"))
SIM_INTERVAL_STDDEV_PCT = float(os.getenv("SIM_INTERVAL_STDDEV_PCT"))
SIM_MALFORMED_PCT = float(os.getenv("SIM_MALFORMED_PCT"))


SIM_INTERVAL_STD_DEV = SIM_INTERVAL_MEAN_MS * SIM_INTERVAL_STDDEV_PCT

# Prendi l'ID della stazione dal nome host del container
#STATION_ID = os.getenv("HOSTNAME")
TOPIC = f"{KAFKA_TOPIC_PREFIX}.{SIM_STATION_ID}"


# === CONNESSIONE KAFKA ===
def connect_to_kafka():
    """Connette al cluster Kafka con retry automatico."""
    print(f"Connessione a Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                linger_ms=10,
                acks="all",
            )
            print(f"Connesso a Kafka")
            return producer
        except Exception as e:
            print(f"Errore connessione Kafka: {e}. Riprovo tra 2 secondi...")
            time.sleep(2)


producer = connect_to_kafka()


# === GENERAZIONE DATI ===
def make_payload(sensor_id):
    """
    Genera un payload sensore.
    - type="SIMPLE", value=numero per dati validi
    - type="MALFORMED", value="<<bad_data>>" per dati corrotti
    """
    timestamp = int(time.time() * 1000)
    
    # Genera dato malformato con probabilità SIM_MALFORMED_PCT
    if random.random() < SIM_MALFORMED_PCT:
        return {
            "station_name": SIM_STATION_NAME,
            "station_id": SIM_STATION_ID,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "type": "MALFORMED",
            "value": "<<bad_data>>",
        }
    
    # Dato valido
    return {
        "station_name": SIM_STATION_NAME,
        "station_id": SIM_STATION_ID,
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "type": "SIMPLE",
        "value": round(random.uniform(0.0, 100.0), 3),
    }


# === TASK SENSORE ===
async def sensor_task(sensor_id):
    """Task asincrono che simula un sensore che pubblica dati a intervalli regolari."""
    # Offset iniziale per distribuire le pubblicazioni nel tempo
    await asyncio.sleep(sensor_id * (SIM_INTERVAL_MEAN_MS / 1000) / SIM_NUM_SENSORS)
    
    while True:
        payload = make_payload(sensor_id)
        producer.send(TOPIC, key=sensor_id, value=payload)
        #print(f"[SENSOR_{sensor_id}] {payload['type']}: {payload['value']}")
        print(f"[SENSOR_{sensor_id}] SENT: {payload}")
        
        # Genera intervallo con distribuzione gaussiana
        # max(0, ...) per evitare valori negativi
        interval_seconds = max(0, random.gauss(SIM_INTERVAL_MEAN_MS, SIM_INTERVAL_STD_DEV) / 1000)
        #print(f"[SENSOR_{sensor_id}] Next in {interval_seconds*1000:.2f} ms")
        await asyncio.sleep(interval_seconds)


# === MAIN ===
async def main():
    print("="*70)
    print(f"{PROJECT_NAME} - Simulatore di Sensori")
    print(f"  - Versione: {PROJECT_VERSION}")
    print(f"  - Autore: {PROJECT_AUTHOR} ({PROJECT_EMAIL})")
    print(f"  - Repository: {PROJECT_GITHUB}")
    print("="*70)
    print(f"AVVIO SIMULATORE STAZIONE - {SIM_STATION_NAME} (ID: {SIM_STATION_ID})")
    print(f"  - # Sensori: {SIM_NUM_SENSORS}")
    print(f"  - Intervallo medio d'invio: {SIM_INTERVAL_MEAN_MS}ms")
    print(f"  - Deviazione standard intervallo: {SIM_INTERVAL_STDDEV_PCT*100}%")
    print(f"  - Pacchetti malformati: {SIM_MALFORMED_PCT*100}%")
    print(f"  - Invio pacchetti a {KAFKA_BOOTSTRAP_SERVERS} | Topic: {TOPIC}")
    print("="*70)
    
    # Avvia tutti i task dei sensori in parallelo
    tasks = [asyncio.create_task(sensor_task(i)) for i in range(SIM_NUM_SENSORS)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nChiusura in corso...")
        producer.flush()
        producer.close()
        print("Simulatore terminato.")
        print("Stopped.")
