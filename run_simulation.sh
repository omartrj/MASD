#!/bin/bash

# Avvia simulatori da config.json
# Uso: ./run_simulation.sh -c simulator/config.json

set -e

# === PARSING ARGOMENTI ===
CONFIG_FILE=""
while getopts "c:" opt; do
    case $opt in
        c) CONFIG_FILE="$OPTARG" ;;
        *) echo "Uso: $0 -c <config.json>"; exit 1 ;;
    esac
done

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Errore: File di configurazione non trovato: $CONFIG_FILE"
    echo "Uso: $0 -c <config.json>"
    exit 1
fi

# === CARICA .env ===
if [ ! -f .env ]; then
    echo "Errore: File .env non trovato"
    exit 1
fi

set -a
source .env
set +a

# === ATTENDI SPARK APP HEALTHY ===
echo "Attendo che spark-app sia healthy..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' spark-app 2>/dev/null)" = "healthy" ]; do 
    sleep 2
done
echo "✓ spark-app is healthy"
echo ""

# === BUILD IMMAGINE ===
echo "Build immagine simulator..."
docker build -q -t masd-simulator:latest ./simulator

# === AVVIA SIMULATORI ===
NETWORK="masd-network"
STATION_COUNT=$(jq '.stations | length' "$CONFIG_FILE")
declare -a CONTAINER_IDS=()

cleanup() {
    echo -e "\nArresto simulatori..."
    for id in "${CONTAINER_IDS[@]}"; do
        docker stop "$id" > /dev/null 2>&1 && docker rm "$id" > /dev/null 2>&1
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "Avvio $STATION_COUNT simulatori..."
echo ""

for i in $(seq 0 $((STATION_COUNT - 1))); do
    NAME=$(jq -r ".stations[$i].name" "$CONFIG_FILE")
    ID=$(jq -r ".stations[$i].id" "$CONFIG_FILE")
    NUM_SENSORS=$(jq -r ".stations[$i].num_sensors" "$CONFIG_FILE")
    INTERVAL_MEAN_MS=$(jq -r ".sensors.send_interval.mean_ms" "$CONFIG_FILE")
    INTERVAL_STDDEV_PCT=$(jq -r ".sensors.send_interval.stddev_pct" "$CONFIG_FILE")
    MALFORMED_PCT=$(jq -r ".sensors.malformation_pct" "$CONFIG_FILE")
    
    CONTAINER_ID=$(docker run -d \
        --name "simulator-${ID}" \
        --network "$NETWORK" \
        -e PROJECT_NAME="$PROJECT_NAME" \
        -e PROJECT_VERSION="$VERSION" \
        -e PROJECT_AUTHOR="$AUTHOR" \
        -e PROJECT_EMAIL="$EMAIL" \
        -e PROJECT_GITHUB="$GITHUB_REPO" \
        -e SIM_STATION_NAME="$NAME" \
        -e SIM_STATION_ID="$ID" \
        -e SIM_NUM_SENSORS="$NUM_SENSORS" \
        -e SIM_INTERVAL_MEAN_MS="$INTERVAL_MEAN_MS" \
        -e SIM_INTERVAL_STDDEV_PCT="$INTERVAL_STDDEV_PCT" \
        -e SIM_MALFORMED_PCT="$MALFORMED_PCT" \
        -e KAFKA_BOOTSTRAP_SERVERS="$KAFKA_BOOTSTRAP_SERVERS" \
        -e KAFKA_TOPIC_PREFIX="$KAFKA_TOPIC_PREFIX" \
        masd-simulator:latest)
    
    CONTAINER_IDS+=("$CONTAINER_ID")
    echo "✓ $NAME ($SENSORS sensori) - simulator-${ID}"
done

echo ""
echo "Tutti i simulatori sono attivi!"
echo "Logs: docker logs -f simulator-<id>"
echo ""
echo "=== WEB UI ==="
echo "• Kafka UI:        http://localhost:8080"
echo "• Mongo Express:   http://localhost:8081"
echo "• HDFS NameNode:   http://localhost:9870"
echo "• YARN RM:         http://localhost:8088"
echo "• Spark UI:        http://localhost:4040"
echo ""
echo "Premi CTRL+C per arrestare"
echo ""

# Monitora container
while true; do
    sleep 2
    for id in "${CONTAINER_IDS[@]}"; do
        if ! docker ps -q --filter "id=$id" | grep -q .; then
            NAME=$(docker ps -a --filter "id=$id" --format "{{.Names}}")
            echo "Errore: Container $NAME terminato"
            cleanup
        fi
    done
done
            log_error "Container $CONTAINER_NAME è terminato inaspettatamente"
            log_info "Log del container:"
            docker logs --tail 50 "$container_id"
            cleanup
        fi
    done
done
