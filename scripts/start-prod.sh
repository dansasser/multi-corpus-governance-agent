#!/bin/bash
# Multi-Corpus Governance Agent - Production Server Script
# Starts the production server using Gunicorn with multiple workers

set -e  # Exit on any error

echo "🚀 Production Server"
echo "==================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default production configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_WORKERS="4"
DEFAULT_WORKER_CLASS="uvicorn.workers.UvicornWorker"
DEFAULT_TIMEOUT="120"
DEFAULT_KEEPALIVE="5"
DEFAULT_MAX_REQUESTS="1000"
DEFAULT_MAX_REQUESTS_JITTER="100"

# Configuration variables
HOST=${DEFAULT_HOST}
PORT=${DEFAULT_PORT}
WORKERS=${DEFAULT_WORKERS}
WORKER_CLASS=${DEFAULT_WORKER_CLASS}
TIMEOUT=${DEFAULT_TIMEOUT}
KEEPALIVE=${DEFAULT_KEEPALIVE}
MAX_REQUESTS=${DEFAULT_MAX_REQUESTS}
MAX_REQUESTS_JITTER=${DEFAULT_MAX_REQUESTS_JITTER}
PRELOAD=true
LOG_LEVEL="info"

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        print_success "Environment variables loaded from .env"
        
        # Override defaults with env vars if present
        HOST=${HOST:-$DEFAULT_HOST}
        PORT=${PORT:-$DEFAULT_PORT}
        WORKERS=${WORKERS:-$DEFAULT_WORKERS}
        WORKER_CLASS=${WORKER_CLASS:-$DEFAULT_WORKER_CLASS}
        TIMEOUT=${TIMEOUT:-$DEFAULT_TIMEOUT}
        KEEPALIVE=${KEEPALIVE:-$DEFAULT_KEEPALIVE}
        MAX_REQUESTS=${MAX_REQUESTS:-$DEFAULT_MAX_REQUESTS}
        MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-$DEFAULT_MAX_REQUESTS_JITTER}
    else
        print_error ".env file not found. Production requires proper configuration."
        exit 1
    fi
}

# Validate production environment
validate_production_env() {
    print_status "Validating production environment..."
    
    # Check required environment variables
    REQUIRED_VARS=("JWT_SECRET_KEY" "ENCRYPTION_KEY" "DATABASE_URL")
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check for development values that shouldn't be in production
    if [[ "${JWT_SECRET_KEY}" == *"change-this"* ]] || [[ "${JWT_SECRET_KEY}" == *"your-"* ]]; then
        print_error "JWT_SECRET_KEY appears to be a default value. Use a secure key in production."
        exit 1
    fi
    
    if [[ "${ENCRYPTION_KEY}" == *"change-this"* ]] || [[ "${ENCRYPTION_KEY}" == *"your-"* ]]; then
        print_error "ENCRYPTION_KEY appears to be a default value. Use a secure key in production."
        exit 1
    fi
    
    # Ensure production environment
    export ENVIRONMENT=production
    export DEBUG=false
    
    print_success "Production environment validated"
}

# Check if virtual environment is activated
check_venv() {
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_warning "Virtual environment not detected"
        if [ -d ".venv" ]; then
            print_status "Activating virtual environment..."
            source .venv/bin/activate
            print_success "Virtual environment activated"
        else
            print_error "No virtual environment found. Run ./scripts/setup.sh first"
            exit 1
        fi
    else
        print_success "Virtual environment active: $VIRTUAL_ENV"
    fi
}

# Check if Gunicorn is installed
check_gunicorn() {
    print_status "Checking for Gunicorn..."
    
    if ! command -v gunicorn &> /dev/null; then
        print_error "Gunicorn not found. Installing..."
        pip install gunicorn
        print_success "Gunicorn installed"
    else
        print_success "Gunicorn found"
    fi
}

# Check database connection
check_database() {
    print_status "Checking database connection..."
    
    python -c "
from mcg_agent.db.session import get_session
try:
    with get_session() as session:
        session.execute('SELECT 1')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" || exit 1
    
    print_success "Database connection verified"
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        print_success "Database migrations completed"
    else
        print_warning "Alembic not found, skipping migrations"
    fi
}

# Create Gunicorn configuration
create_gunicorn_config() {
    print_status "Creating Gunicorn configuration..."
    
    cat > gunicorn.conf.py << EOF
# Gunicorn configuration for Multi-Corpus Governance Agent
import multiprocessing
import os

# Server socket
bind = "${HOST}:${PORT}"
backlog = 2048

# Worker processes
workers = ${WORKERS}
worker_class = "${WORKER_CLASS}"
worker_connections = 1000
timeout = ${TIMEOUT}
keepalive = ${KEEPALIVE}

# Restart workers after this many requests, with up to this much jitter
max_requests = ${MAX_REQUESTS}
max_requests_jitter = ${MAX_REQUESTS_JITTER}

# Preload application code before forking worker processes
preload_app = ${PRELOAD}

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "${LOG_LEVEL}"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "mcg-agent"

# Server mechanics
daemon = False
pidfile = "/tmp/mcg-agent.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if certificates are available)
keyfile = os.environ.get("SSL_KEYFILE")
certfile = os.environ.get("SSL_CERTFILE")

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
EOF
    
    print_success "Gunicorn configuration created"
}

# Start the production server
start_server() {
    print_status "Starting production server..."
    print_status "Server will be available at: http://${HOST}:${PORT}"
    print_status "Workers: ${WORKERS}"
    print_status "Press Ctrl+C to stop the server"
    echo
    
    # Start server with Gunicorn
    if command -v mcg-agent &> /dev/null; then
        # Use CLI if available
        mcg-agent serve --workers ${WORKERS} --host ${HOST} --port ${PORT}
    else
        # Fallback to Gunicorn directly
        gunicorn mcg_agent.main:app \
            --config gunicorn.conf.py \
            --bind ${HOST}:${PORT} \
            --workers ${WORKERS} \
            --worker-class ${WORKER_CLASS}
    fi
}

# Health check function
health_check() {
    print_status "Performing health check..."
    
    # Wait for server to start
    sleep 5
    
    # Check if server is responding
    if curl -s -f "http://${HOST}:${PORT}/health" > /dev/null 2>&1; then
        print_success "Server health check passed"
    else
        print_error "Server health check failed"
        return 1
    fi
}

# Cleanup function for graceful shutdown
cleanup() {
    echo
    print_status "Shutting down production server..."
    
    # Kill Gunicorn master process
    if [ -f "/tmp/mcg-agent.pid" ]; then
        PID=$(cat /tmp/mcg-agent.pid)
        if kill -0 $PID 2>/dev/null; then
            print_status "Sending SIGTERM to master process (PID: $PID)..."
            kill -TERM $PID
            
            # Wait for graceful shutdown
            for i in {1..30}; do
                if ! kill -0 $PID 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 $PID 2>/dev/null; then
                print_warning "Forcing shutdown..."
                kill -KILL $PID
            fi
        fi
        rm -f /tmp/mcg-agent.pid
    fi
    
    # Clean up configuration file
    rm -f gunicorn.conf.py
    
    print_success "Production server stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main production server flow
main() {
    echo
    print_status "Starting production environment..."
    
    load_env
    validate_production_env
    check_venv
    check_gunicorn
    check_database
    run_migrations
    create_gunicorn_config
    
    echo
    print_success "Production environment ready!"
    echo "Configuration:"
    echo "  Host: ${HOST}"
    echo "  Port: ${PORT}"
    echo "  Workers: ${WORKERS}"
    echo "  Worker Class: ${WORKER_CLASS}"
    echo "  Timeout: ${TIMEOUT}s"
    echo "  Max Requests: ${MAX_REQUESTS}"
    echo "  Preload: ${PRELOAD}"
    echo
    
    start_server
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Multi-Corpus Governance Agent Production Server"
            echo
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --help, -h              Show this help message"
            echo "  --host HOST             Host to bind to (default: ${DEFAULT_HOST})"
            echo "  --port PORT             Port to bind to (default: ${DEFAULT_PORT})"
            echo "  --workers NUM           Number of worker processes (default: ${DEFAULT_WORKERS})"
            echo "  --timeout SECONDS       Worker timeout (default: ${DEFAULT_TIMEOUT})"
            echo "  --health-check          Run health check after startup"
            echo "  --no-preload            Disable application preloading"
            echo
            echo "Environment variables:"
            echo "  HOST                    Override default host"
            echo "  PORT                    Override default port"
            echo "  WORKERS                 Override default worker count"
            echo "  SSL_KEYFILE             Path to SSL private key"
            echo "  SSL_CERTFILE            Path to SSL certificate"
            echo
            exit 0
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --health-check)
            # Start server in background and run health check
            main &
            SERVER_PID=$!
            sleep 10  # Give more time for production startup
            health_check
            if [ $? -eq 0 ]; then
                print_success "Production server is healthy"
                kill $SERVER_PID
                exit 0
            else
                print_error "Production server health check failed"
                kill $SERVER_PID
                exit 1
            fi
            ;;
        --no-preload)
            PRELOAD=false
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main production server
main
