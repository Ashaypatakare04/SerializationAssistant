# Production Dockerfile for AI Novel-to-Webtoon Studio Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow and database clients
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application and alembic migrations
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Create storage directory
RUN mkdir -p /app/storage/assets /app/storage/exports /app/storage/references

EXPOSE 8000

ENV PYTHONPATH=/app
ENV APP_ENV=production

# Start FastAPI server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
