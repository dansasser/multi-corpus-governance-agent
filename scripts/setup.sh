#!/bin/bash
# Multi-Corpus Governance Agent - Setup Script
# Automated environment setup for development and production

set -e  # Exit on any error

echo "🚀 Multi-Corpus Governance Agent Setup"
echo "======================================"

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

# Check if Python 3.11+ is available
check_python() {
    print_status "Checking Python version..."
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
            PYTHON_CMD="python3"
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3.11+ not found"
        exit 1
    fi
    print_success "Python found: $($PYTHON_CMD --version)"
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    if [ ! -d ".venv" ]; then
        $PYTHON_CMD -m venv .venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source .venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    pip install --upgrade pip
    pip install -r src/requirements.txt
    print_success "Dependencies installed"
}

# Install package in development mode
install_package() {
    print_status "Installing package in development mode..."
    if [ -f "pyproject.toml" ]; then
        pip install -e .[dev]
        print_success "Package installed in development mode"
    else
        print_warning "pyproject.toml not found, skipping package installation"
    fi
}

# Create .env file if it doesn't exist
create_env_file() {
    print_status "Setting up environment configuration..."
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "Please edit .env file with your actual configuration values"
        else
            print_warning ".env.example not found, creating basic .env file"
            cat > .env << EOF
# Database Configuration
DATABASE_URL=sqlite:///./mcg_agent.db

# Redis Configuration (session management)
REDIS_URL=redis://localhost:6379/0

# Security Keys (CHANGE THESE IN PRODUCTION!)
JWT_SECRET_KEY=your-jwt-secret-key-here-change-this
ENCRYPTION_KEY=your-32-byte-encryption-key-change-this

# API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
EOF
            print_success "Created basic .env file"
            print_warning "Please edit .env file with your actual API keys and configuration"
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Initialize database
init_database() {
    print_status "Initializing database..."
    if command -v ./scripts/init-db.sh &> /dev/null; then
        ./scripts/init-db.sh
    else
        print_warning "Database initialization script not found, skipping"
    fi
}

# Run tests to verify setup
run_tests() {
    print_status "Running tests to verify setup..."
    if command -v ./scripts/run-tests.sh &> /dev/null; then
        ./scripts/run-tests.sh --fast
    else
        print_warning "Test script not found, skipping tests"
    fi
}

# Main setup flow
main() {
    echo
    print_status "Starting setup process..."
    
    check_python
    create_venv
    activate_venv
    install_dependencies
    install_package
    create_env_file
    init_database
    run_tests
    
    echo
    print_success "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Edit .env file with your API keys and configuration"
    echo "2. Run: source .venv/bin/activate"
    echo "3. Run: ./scripts/start-dev.sh"
    echo
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Multi-Corpus Governance Agent Setup Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-tests     Skip running tests during setup"
        echo "  --no-db        Skip database initialization"
        echo
        exit 0
        ;;
    --no-tests)
        run_tests() { print_status "Skipping tests (--no-tests flag)"; }
        ;;
    --no-db)
        init_database() { print_status "Skipping database initialization (--no-db flag)"; }
        ;;
esac

# Run main setup
main
