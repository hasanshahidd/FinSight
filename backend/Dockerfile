FROM python:3.11-slim

WORKDIR /app

# System deps for chromadb / embeddings
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini ./

# Generated at runtime by entrypoint:
RUN mkdir -p /app/data /app/chroma_db

EXPOSE 8000

# Entrypoint: seed DB + ingest docs (idempotent), then serve
CMD ["sh", "-c", "python scripts/generate_demo_data.py && python scripts/ingest_docs.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
