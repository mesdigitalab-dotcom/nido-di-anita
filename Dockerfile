FROM python:3.12-slim

# Non bufferizzare stdout/stderr: i log arrivano subito a `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dipendenze di sistema minime (compilazione pacchetti + Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles /app/ics/cache

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
