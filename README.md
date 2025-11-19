# MASD — Monitoring & Analytics of Streaming Data

Progetto per l'esame di **Data Intensive Application & Big Data**, Università degli Studi di Perugia.

Pipeline di streaming data che simula sensori IoT, invia i dati a Kafka, li processa con Spark ed infine li salva su MongoDB. Ambiente completamente containerizzato con Docker Compose.

## Architettura

- **Simulatore**: producer Python che genera dati sensori e li pubblica su Kafka
- **Kafka + ZooKeeper**: message broker per lo streaming dei dati
- **Spark**: consumer che aggrega i dati in real-time (attualmente in modalità local)
- **MongoDB**: database per la persistenza dei risultati
- **Hadoop (HDFS + YARN)**: cluster per l'esecuzione distribuita

## Prerequisiti

- Docker e Docker Compose
- jq (opzionale, per lo script di simulazione)
- Almeno 8 GB di RAM

## Quick Start

1. Avvia lo stack completo:

```bash
docker compose up -d --build
```

2. (Opzionale) Avvia le UI web:

```bash
docker compose --profile kafka-ui --profile mongo-ui up -d
```

3. Avvia i simulatori:

```bash
./run_simulation.sh -c simulator/config.json
```

Premi `CTRL+C` per fermare i simulatori.

## Struttura

```text
.
├── .env                        # Variabili d'ambiente
├── docker-compose.yml          # Stack completo
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
docker compose --profile kafka-ui --profile mongo-ui down -v
```

## Sviluppi Futuri

- **Spark su YARN**: migrare l'esecuzione di Spark da `--master local[*]` a `--master yarn` per sfruttare il cluster Hadoop distribuito già presente nel docker-compose
