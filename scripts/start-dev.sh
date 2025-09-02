#!/bin/bash
# Development server startup script

set -e

echo "Starting MCG Agent FastAPI Development Server..."

# Check if we're in the right directory
if [ ! -f "src/mcg_agent/api/app.py" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    source .env
else
    echo "Warning: .env file not found. Using defaults."
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Set development environment variables
export ENVIRONMENT=development
export DEBUG=true
export LOG_LEVEL=DEBUG
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}

# Check database connection
echo "Checking database connection..."
python -c "from src.mcg_agent.database.connection import check_db_connection; check_db_connection()" || {
    echo "Warning: Database connection failed. Starting anyway for development."
}

# Check Redis connection
echo "Checking Redis connection..."
python -c "from src.mcg_agent.auth.redis_client import check_redis_connection; check_redis_connection()" || {
    echo "Warning: Redis connection failed. Starting anyway for development."
}

# Install/update dependencies
echo "Installing development dependencies..."
pip install -e .[dev]

# Start the development server with hot reload
echo "Starting FastAPI development server on http://${HOST}:${PORT}"
echo "Press Ctrl+C to stop the server"

exec uvicorn src.mcg_agent.api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --log-level debug \
    --access-log \
    --use-colors