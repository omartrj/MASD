# MASD — Monitoring & Analytics of Streaming Data

![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E35A16?style=flat&logo=apachespark&logoColor=white) ![Apache Hadoop](https://img.shields.io/badge/Apache%20Hadoop-66CCFF?style=flat&logo=apachehadoop&logoColor=black) ![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-000000?style=flat&logo=apachekafka&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)

Progetto per l'esame di **Data Intensive Application & Big Data**, Università degli Studi di Perugia.

Pipeline di streaming data che simula sensori IoT, invia i dati a Kafka, li processa con Spark su un cluster Hadoop ed infine li salva su MongoDB. Ambiente completamente containerizzato con Docker Compose.

**Autore**: Omar Criacci (omar.criacci@student.unipg.it)  
**Versione**: 1.0.0

## Indice
- [Architettura](#architettura)
- [Prerequisiti](#prerequisiti)
- [Quick Start](#quickstart)
    - [Automatico (Consigliato)](#automatico-consigliato)
    - [Manuale](#avvio-manuale)
- [Configurazione Simulatori](#configurazione-simulatori)
- [Struttura](#struttura)
- [Comandi Utili](#comandi-utili)

## Architettura

La pipeline si compone di diversi componenti:
- **Simulatore**: producer Python che genera dati sensori e li pubblica su Kafka
- **Kafka + ZooKeeper**: message broker per lo streaming dei dati
- **Spark**: consumer che aggrega i dati in real-time su un cluster Hadoop
- **MongoDB**: database per la persistenza dei risultati
- **Hadoop (HDFS + YARN)**: cluster per l'esecuzione distribuita

## Prerequisiti

- Docker e Docker Compose
- jq (opzionale, per lo script di simulazione)
- Almeno 8 GB di RAM

## Quickstart

### Automatico (Consigliato)

1. Clona il repository:
   ```bash
   git clone https://github.com/omarcriacci/MASD.git
   cd MASD
   ```

2. Avvia l'intero stack (Kafka, MongoDB, Hadoop, Spark):
   ```bash
   docker compose up -d --build
   ```

   Per avviare anche le interfacce web per Kafka e MongoDB (opzionali):
   ```bash
   docker compose --profile web-ui up -d --build
   ```

   Inoltre è possibile scalare il cluster Hadoop aggiungendo nodi (opzionale):
   ```bash
   docker compose up -d --build --scale hdfs-datanode=2 --scale yarn-nodemanager=2
   ```

3. Avvia i simulatori:
   ```bash
   ./run_simulation.sh -c simulator/config.json
   ```

   **Nota**: Per fermare i simulatori, premi `CTRL+C`. Lo script terminerà automaticamente tutti i container.

### Manuale (senza jq)

Se non hai `jq` installato (scaricalo, è utile!), puoi avviare i simulatori manualmente:

1. Builda l'immagine del simulatore:
   ```bash
   docker build -t masd-simulator:latest ./simulator
   ```
2. Carica le variabili d'ambiente:
   ```bash
   source .env
   ```
3. Avvia ogni stazione manualmente:
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
    Sostituisci i valori tra `<>` con i parametri desiderati per la stazione (vedi `simulator/config.json`).

## Configurazione Simulatori

I simulatori sono configurati tramite il file `simulator/config.json`:

```jsonc
{
    "sensors": {
        "send_interval": {
            "mean_ms": 250,        // Intervallo medio di invio in millisecondi
            "stddev_pct": 0.2      // Deviazione standard (20%)
        },
        "malformation_pct": 0.05   // Percentuale di dati malformati (5%)
    },
    "stations": [
        {
            "name": "Perugia",     // Nome stazione
            "id": "perugia",       // ID univoco (usato per topic Kafka e collezione MongoDB)
            "num_sensors": 3       // Numero di sensori per questa stazione
        },
        // ... altre stazioni
    ]
}
```

Ogni stazione viene avviata come container Docker separato e pubblica su un topic Kafka dedicato: `sensors.raw.<station_id>`.

## Struttura

```text
.
├── .env                        # Variabili d'ambiente
├── docker-compose.yml          # Orchestrazione principale
├── compose/                    
│   ├── kafka.yml               # Cluster Kafka (Zookeeper, 3 brokers, UI)
│   ├── mongodb.yml             # Replica Set MongoDB (3 nodi, UI)
│   ├── hadoop.yml              # Cluster Hadoop (HDFS + YARN)
│   └── spark.yml               # Applicazione Spark
├── hadoop.config               # Configurazione Hadoop
├── run_simulation.sh           # Script per avviare i simulatori
├── README.md                   
├── simulator/                  # Simulatore (Producer)
│   ├── producer.py
│   ├── config.json             # Configurazione simulazione   
│   ├── requirements.txt
│   └── Dockerfile
└── spark-app/                  # Spark Application (Consumer)
    ├── consumer.py
    ├── requirements.txt
    └── Dockerfile
```

## Comandi Utili

```bash
# Visualizzare log
docker logs -f container_id

# Fermare tutto
docker compose down

# Rimuovere anche i volumi
docker compose down -v

# (Se sono state avviate le UI web)
docker compose --profile web-ui down -v
```
