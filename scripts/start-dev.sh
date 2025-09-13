#!/bin/bash
# Multi-Corpus Governance Agent - Development Server Script
# Starts the development server with hot reloading

set -e  # Exit on any error

echo "🔧 Development Server"
echo "===================="

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

# Default configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_LOG_LEVEL="info"

# Parse command line arguments
HOST=${DEFAULT_HOST}
PORT=${DEFAULT_PORT}
LOG_LEVEL=${DEFAULT_LOG_LEVEL}
RELOAD=true
DEBUG=true

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        print_success "Environment variables loaded from .env"
        
        # Override defaults with env vars if present
        HOST=${HOST:-$DEFAULT_HOST}
        PORT=${PORT:-$DEFAULT_PORT}
        LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}
    else
        print_warning ".env file not found, using defaults"
    fi
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

# Check if dependencies are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! python -c "import mcg_agent" 2>/dev/null; then
        print_error "mcg_agent package not found"
        print_status "Installing package in development mode..."
        pip install -e .
        print_success "Package installed"
    fi
    
    if ! python -c "import uvicorn" 2>/dev/null; then
        print_error "uvicorn not found. Installing dependencies..."
        pip install -r src/requirements.txt
        print_success "Dependencies installed"
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
    print('Run ./scripts/init-db.sh to initialize the database')
    exit(1)
" || exit 1
    
    print_success "Database connection verified"
}

# Start the development server
start_server() {
    print_status "Starting development server..."
    print_status "Server will be available at: http://${HOST}:${PORT}"
    print_status "Press Ctrl+C to stop the server"
    echo
    
    # Set development environment
    export ENVIRONMENT=development
    export DEBUG=true
    
    # Start server with uvicorn
    if command -v mcg-agent &> /dev/null; then
        # Use CLI if available
        mcg-agent serve --reload --host ${HOST} --port ${PORT} --log-level ${LOG_LEVEL}
    else
        # Fallback to uvicorn directly
        uvicorn mcg_agent.main:app \
            --reload \
            --host ${HOST} \
            --port ${PORT} \
            --log-level ${LOG_LEVEL} \
            --reload-dir src/mcg_agent \
            --reload-exclude "*.pyc" \
            --reload-exclude "__pycache__"
    fi
}

# Health check function
health_check() {
    print_status "Performing health check..."
    
    # Wait a moment for server to start
    sleep 2
    
    # Check if server is responding
    if curl -s -f "http://${HOST}:${PORT}/health" > /dev/null 2>&1; then
        print_success "Server health check passed"
    else
        print_warning "Server health check failed (this is normal during startup)"
    fi
}

# Cleanup function for graceful shutdown
cleanup() {
    echo
    print_status "Shutting down development server..."
    # Kill any background processes
    jobs -p | xargs -r kill
    print_success "Development server stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main development server flow
main() {
    echo
    print_status "Starting development environment..."
    
    load_env
    check_venv
    check_dependencies
    check_database
    
    echo
    print_success "Development environment ready!"
    echo "Configuration:"
    echo "  Host: ${HOST}"
    echo "  Port: ${PORT}"
    echo "  Log Level: ${LOG_LEVEL}"
    echo "  Reload: ${RELOAD}"
    echo "  Debug: ${DEBUG}"
    echo
    
    start_server
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Multi-Corpus Governance Agent Development Server"
            echo
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --help, -h              Show this help message"
            echo "  --host HOST             Host to bind to (default: ${DEFAULT_HOST})"
            echo "  --port PORT             Port to bind to (default: ${DEFAULT_PORT})"
            echo "  --log-level LEVEL       Log level (default: ${DEFAULT_LOG_LEVEL})"
            echo "  --no-reload             Disable auto-reload"
            echo "  --health-check          Run health check after startup"
            echo
            echo "Environment variables:"
            echo "  HOST                    Override default host"
            echo "  PORT                    Override default port"
            echo "  LOG_LEVEL               Override default log level"
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
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --no-reload)
            RELOAD=false
            shift
            ;;
        --health-check)
            # Start server in background and run health check
            main &
            SERVER_PID=$!
            health_check
            wait $SERVER_PID
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main development server
main
