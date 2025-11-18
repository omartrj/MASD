FROM python:slim

WORKDIR /app

# Installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia l'applicazione nel container
COPY producer.py .

# Imposta variabili d'ambiente e comando di avvio
ENV PYTHONUNBUFFERED=1
CMD ["python", "producer.py"]