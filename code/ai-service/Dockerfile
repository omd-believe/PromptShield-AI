FROM python:3.12-slim

WORKDIR /app

# Install system build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt .

# Install dependencies and spaCy language model
RUN pip install --no-cache-dir --default-timeout=1000 --retries=10 -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Copy application source code
COPY . .

# Non-root user for security
RUN useradd -m promptshield && \
    mkdir -p /home/promptshield/.cache/huggingface && \
    chown -R promptshield:promptshield /app /home/promptshield
USER promptshield

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
