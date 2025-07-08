FROM python:3.13-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app

# Main app stage
FROM base AS app

# Expose ports
EXPOSE 8000

# Command to run the application with auto-reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]

# Worker stage
FROM base AS worker

# Set non-root user
USER appuser

# Command to run the worker
CMD ["python", "script/sqs_worker.py"]
