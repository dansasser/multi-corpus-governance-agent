#!/bin/bash

# Multi-Corpus Governance Agent - Initial Setup Script
# This script sets up the development environment and dependencies

set -e  # Exit on any error

echo "🚀 Setting up Multi-Corpus Governance Agent..."

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

# Check if Python 3.11+ is installed
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )[0-9]+\.[0-9]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python $python_version is installed"
else
    print_error "Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

# Check if pip is installed
print_status "Checking pip..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip3 first."
    exit 1
else
    print_success "pip3 is available"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip, setuptools, and wheel
print_status "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Create .env file from template if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cat > .env << 'EOF'
# Database Configuration
POSTGRES_USER=mcg_agent
POSTGRES_PASSWORD=secure_password_change_this
POSTGRES_DB=mcg_agent_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PASSWORD=redis_password_change_this
REDIS_HOST=localhost
REDIS_PORT=6379

# Security Configuration
JWT_SECRET_KEY=your_very_long_and_secure_jwt_secret_key_here_change_this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=development
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1", "*.gorombo.com"]

# Logging Configuration
LOG_LEVEL=INFO
EOF
    print_success ".env file created"
    print_warning "IMPORTANT: Update the passwords and secret keys in .env file!"
else
    print_warning ".env file already exists"
fi

# Check if PostgreSQL is running
print_status "Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        print_success "PostgreSQL is running"
    else
        print_warning "PostgreSQL is not running. Please start PostgreSQL service."
        print_status "On Ubuntu/Debian: sudo systemctl start postgresql"
        print_status "On macOS with Homebrew: brew services start postgresql"
    fi
else
    print_warning "PostgreSQL tools not found. Please install PostgreSQL."
fi

# Check if Redis is running  
print_status "Checking Redis connection..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_success "Redis is running"
    else
        print_warning "Redis is not running. Please start Redis service."
        print_status "On Ubuntu/Debian: sudo systemctl start redis-server"
        print_status "On macOS with Homebrew: brew services start redis"
    fi
else
    print_warning "Redis tools not found. Please install Redis."
fi

# Create log directories
print_status "Creating log directories..."
mkdir -p logs
mkdir -p logs/security
mkdir -p logs/governance
mkdir -p logs/api
print_success "Log directories created"

# Set up database (if PostgreSQL is running)
if pg_isready -h localhost -p 5432 &> /dev/null; then
    print_status "Setting up database..."
    
    # Check if database exists
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB" 2>/dev/null; then
        print_warning "Database already exists"
    else
        print_status "Creating database..."
        # This would create the database in production
        print_status "Database setup completed (manual setup required)"
    fi
fi

# Install pre-commit hooks (optional)
if command -v pre-commit &> /dev/null; then
    print_status "Installing pre-commit hooks..."
    pre-commit install
    print_success "Pre-commit hooks installed"
fi

print_success "Setup completed successfully!"
echo ""
print_status "Next steps:"
echo "1. Update passwords and secrets in .env file"
echo "2. Ensure PostgreSQL and Redis are running"
echo "3. Run database migrations: ./scripts/init-db.sh"
echo "4. Start development server: ./scripts/start-dev.sh"
echo ""
print_status "For more information, see README.md"