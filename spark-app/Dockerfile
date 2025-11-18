FROM spark:4.0.1-python3

# Utente root per installare pacchetti
USER root

# Installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia l'applicazione Spark nel container
WORKDIR /opt/spark/work-dir
COPY consumer.py .

# Torna all'utente spark
USER spark

# Pre-scarica JAR dependencies durante il build:
# - Connettore a Kafka
# - Connettore a MongoDB
# Usa il file pi.py come test (|| true per evitare errori)
RUN /opt/spark/bin/spark-submit \
    --conf "spark.driver.extraJavaOptions=-Divy.home=/opt/spark/.ivy2 -Djava.io.tmpdir=/opt/spark/tmp" \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1,org.mongodb.spark:mongo-spark-connector_2.13:10.5.0 \
    /opt/spark/examples/src/main/python/pi.py 2>&1 || true