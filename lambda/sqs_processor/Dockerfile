FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir boto3 python-dotenv

# Copy deployment script
COPY deploy.py .

# Run deployment script
CMD ["python", "deploy.py"]
