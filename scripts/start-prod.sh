#!/bin/bash
# Production server startup script

set -e

echo "Starting MCG Agent FastAPI Production Server..."

# Check if we're in the right directory
if [ ! -f "src/mcg_agent/api/app.py" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    source .env
else
    echo "Error: .env file required for production"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
else
    echo "Error: Virtual environment not found"
    exit 1
fi

# Set production environment variables
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}

# Validate required environment variables
required_vars=("DATABASE_URL" "REDIS_URL" "JWT_SECRET_KEY" "ENCRYPTION_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required environment variable $var is not set"
        exit 1
    fi
done

# Check database connection
echo "Verifying database connection..."
python -c "from src.mcg_agent.database.connection import check_db_connection; check_db_connection()" || {
    echo "Error: Database connection failed"
    exit 1
}

# Check Redis connection
echo "Verifying Redis connection..."
python -c "from src.mcg_agent.auth.redis_client import check_redis_connection; check_redis_connection()" || {
    echo "Error: Redis connection failed"
    exit 1
}

# Run database migrations if needed
echo "Running database migrations..."
python -c "from src.mcg_agent.database.migrations import run_migrations; run_migrations()" || {
    echo "Warning: Database migrations failed or not needed"
}

# Pre-flight health check
echo "Running pre-flight health check..."
python -c "
import asyncio
from src.mcg_agent.api.routers.health import comprehensive_health_check
result = asyncio.run(comprehensive_health_check())
if not result['healthy']:
    print('Health check failed:', result['details'])
    exit(1)
print('All systems healthy')
" || {
    echo "Error: Pre-flight health check failed"
    exit 1
}

# Start the production server with Gunicorn
echo "Starting FastAPI production server on http://${HOST}:${PORT} with ${WORKERS} workers"
echo "Process ID: $$"
echo "To stop: kill $$"

exec gunicorn src.mcg_agent.api.app:app \
    --bind "${HOST}:${PORT}" \
    --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload \
    --timeout 30 \
    --keep-alive 2 \
    --log-level "$LOG_LEVEL" \
    --access-logfile - \
    --error-logfile - \
    --capture-output