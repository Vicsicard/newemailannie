#!/bin/bash
# Production startup script for AI Email Agent for Salesforce

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Make sure all environment variables are set manually"
fi

# Set default values if not provided in environment
PORT=${PORT:-8000}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-INFO}

echo "Starting AI Email Agent for Salesforce in production mode"
echo "Port: $PORT, Workers: $WORKERS, Log Level: $LOG_LEVEL"

# Run with Uvicorn for production
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    --proxy-headers \
    --forwarded-allow-ips '*'
