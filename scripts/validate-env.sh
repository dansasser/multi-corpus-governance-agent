#!/bin/bash
# Multi-Corpus Governance Agent - Environment Validation Script
# Validates environment configuration and provides setup guidance

set -e  # Exit on any error

echo "🔍 Environment Validation"
echo "========================"

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

# Validation results
VALIDATION_PASSED=true
ISSUES_FOUND=()
WARNINGS_FOUND=()

# Check if .env file exists
check_env_file() {
    print_status "Checking for .env file..."
    
    if [ -f ".env" ]; then
        print_success ".env file found"
        
        # Check if it's not just the example file
        if grep -q "your-.*-change-this" .env; then
            print_warning ".env file contains example values that should be changed"
            WARNINGS_FOUND+=("Example values found in .env file")
        fi
    else
        print_error ".env file not found"
        ISSUES_FOUND+=(".env file missing")
        VALIDATION_PASSED=false
        
        if [ -f ".env.example" ]; then
            print_status "Creating .env from .env.example..."
            cp .env.example .env
            print_success ".env file created from example"
            print_warning "Please edit .env file with your actual configuration values"
        fi
    fi
}

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs) 2>/dev/null || true
        print_success "Environment variables loaded"
    fi
}

# Check required environment variables
check_required_vars() {
    print_status "Checking required environment variables..."
    
    # Define required variables by category
    REQUIRED_VARS=(
        "POSTGRES_USER:Database username"
        "POSTGRES_PASSWORD:Database password"
        "POSTGRES_DB:Database name"
        "JWT_SECRET_KEY:JWT secret key"
        "ENCRYPTION_KEY:Encryption key"
    )
    
    for var_info in "${REQUIRED_VARS[@]}"; do
        IFS=':' read -ra PARTS <<< "$var_info"
        var_name="${PARTS[0]}"
        var_desc="${PARTS[1]}"
        
        if [[ -z "${!var_name}" ]]; then
            print_error "$var_desc ($var_name) is not set"
            ISSUES_FOUND+=("$var_name is required but not set")
            VALIDATION_PASSED=false
        else
            print_success "$var_desc is configured"
        fi
    done
}

# Check API keys
check_api_keys() {
    print_status "Checking API keys..."
    
    api_keys_found=0
    
    if [[ -n "${OPENAI_API_KEY}" ]]; then
        print_success "OpenAI API key is configured"
        api_keys_found=$((api_keys_found + 1))
    fi
    
    if [[ -n "${ANTHROPIC_API_KEY}" ]]; then
        print_success "Anthropic API key is configured"
        api_keys_found=$((api_keys_found + 1))
    fi
    
    if [ $api_keys_found -eq 0 ]; then
        print_error "No AI service API keys configured"
        ISSUES_FOUND+=("At least one AI service API key is required")
        VALIDATION_PASSED=false
    fi
}

# Check security configuration
check_security() {
    print_status "Checking security configuration..."
    
    # Check JWT secret key
    if [[ "${JWT_SECRET_KEY}" == *"change-this"* ]] || [[ "${JWT_SECRET_KEY}" == *"your-"* ]]; then
        if [[ "${ENVIRONMENT}" == "production" ]]; then
            print_error "JWT_SECRET_KEY contains default value in production"
            ISSUES_FOUND+=("JWT_SECRET_KEY must be changed in production")
            VALIDATION_PASSED=false
        else
            print_warning "JWT_SECRET_KEY appears to be a default value"
            WARNINGS_FOUND+=("JWT_SECRET_KEY should be changed for security")
        fi
    else
        print_success "JWT_SECRET_KEY appears to be customized"
    fi
    
    # Check encryption key
    if [[ "${ENCRYPTION_KEY}" == *"change-this"* ]] || [[ "${ENCRYPTION_KEY}" == *"your-"* ]]; then
        if [[ "${ENVIRONMENT}" == "production" ]]; then
            print_error "ENCRYPTION_KEY contains default value in production"
            ISSUES_FOUND+=("ENCRYPTION_KEY must be changed in production")
            VALIDATION_PASSED=false
        else
            print_warning "ENCRYPTION_KEY appears to be a default value"
            WARNINGS_FOUND+=("ENCRYPTION_KEY should be changed for security")
        fi
    else
        print_success "ENCRYPTION_KEY appears to be customized"
    fi
}

# Check database configuration
check_database() {
    print_status "Checking database configuration..."
    
    # Check if using SQLite in production
    if [[ "${ENVIRONMENT}" == "production" ]] && [[ "${DATABASE_URL}" == *"sqlite"* ]]; then
        print_error "SQLite should not be used in production"
        ISSUES_FOUND+=("Use PostgreSQL for production deployment")
        VALIDATION_PASSED=false
    fi
    
    # Test database connection if possible
    if command -v python3 &> /dev/null; then
        print_status "Testing database connection..."
        
        python3 -c "
import os
import sys
sys.path.insert(0, 'src')

try:
    from mcg_agent.config import settings
    print(f'Database URL configured: {settings.database.postgres_url[:20]}...')
    print('Database configuration appears valid')
except Exception as e:
    print(f'Database configuration error: {e}')
    sys.exit(1)
" 2>/dev/null && print_success "Database configuration valid" || {
            print_warning "Could not validate database configuration"
            WARNINGS_FOUND+=("Database connection could not be tested")
        }
    fi
}

# Check Python environment
check_python_env() {
    print_status "Checking Python environment..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python $python_version found"
        
        # Check if version is 3.11+
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
            print_success "Python version is 3.11 or higher"
        else
            print_warning "Python 3.11+ recommended, found $python_version"
            WARNINGS_FOUND+=("Python 3.11+ recommended for best compatibility")
        fi
    else
        print_error "Python 3 not found"
        ISSUES_FOUND+=("Python 3.11+ is required")
        VALIDATION_PASSED=false
    fi
    
    # Check virtual environment
    if [[ -n "${VIRTUAL_ENV}" ]]; then
        print_success "Virtual environment active: $(basename $VIRTUAL_ENV)"
    else
        print_warning "Virtual environment not detected"
        WARNINGS_FOUND+=("Virtual environment recommended for development")
    fi
    
    # Check if package is installed
    if python3 -c "import mcg_agent" 2>/dev/null; then
        print_success "MCG Agent package is installed"
    else
        print_warning "MCG Agent package not installed"
        WARNINGS_FOUND+=("Run 'pip install -e .' to install the package")
    fi
}

# Check file permissions
check_permissions() {
    print_status "Checking file permissions..."
    
    # Check script permissions
    scripts_dir="scripts"
    if [ -d "$scripts_dir" ]; then
        for script in "$scripts_dir"/*.sh; do
            if [ -f "$script" ]; then
                if [ -x "$script" ]; then
                    print_success "$(basename $script) is executable"
                else
                    print_warning "$(basename $script) is not executable"
                    chmod +x "$script"
                    print_success "Made $(basename $script) executable"
                fi
            fi
        done
    fi
}

# Generate secure secrets
generate_secrets() {
    print_status "Generating secure secrets..."
    
    echo "You can use these secure values in your .env file:"
    echo
    echo "# JWT Secret Key (copy this to JWT_SECRET_KEY)"
    python3 -c "import secrets; print(f'JWT_SECRET_KEY={secrets.token_urlsafe(32)}')"
    echo
    echo "# Encryption Key (copy this to ENCRYPTION_KEY)"
    python3 -c "import secrets; print(f'ENCRYPTION_KEY={secrets.token_urlsafe(32)}')"
    echo
    echo "# Redis Password (copy this to REDIS_PASSWORD)"
    python3 -c "import secrets; print(f'REDIS_PASSWORD={secrets.token_urlsafe(16)}')"
    echo
}

# Display validation summary
display_summary() {
    echo
    echo "======================================"
    echo "VALIDATION SUMMARY"
    echo "======================================"
    
    if [ "$VALIDATION_PASSED" = true ]; then
        print_success "Environment validation PASSED"
    else
        print_error "Environment validation FAILED"
    fi
    
    echo
    echo "Issues found: ${#ISSUES_FOUND[@]}"
    for issue in "${ISSUES_FOUND[@]}"; do
        print_error "• $issue"
    done
    
    echo
    echo "Warnings: ${#WARNINGS_FOUND[@]}"
    for warning in "${WARNINGS_FOUND[@]}"; do
        print_warning "• $warning"
    done
    
    echo
    if [ "$VALIDATION_PASSED" = false ]; then
        echo "Next steps to fix issues:"
        echo "1. Edit .env file with proper configuration values"
        echo "2. Generate secure secrets with: $0 --generate-secrets"
        echo "3. Install required dependencies: pip install -r src/requirements.txt"
        echo "4. Run validation again: $0"
    else
        echo "Environment is properly configured!"
        echo "You can now run:"
        echo "• ./scripts/setup.sh - Complete setup"
        echo "• ./scripts/init-db.sh - Initialize database"
        echo "• ./scripts/start-dev.sh - Start development server"
    fi
    echo
}

# Main validation flow
main() {
    echo
    print_status "Starting environment validation..."
    
    check_env_file
    load_env
    check_required_vars
    check_api_keys
    check_security
    check_database
    check_python_env
    check_permissions
    
    display_summary
    
    # Exit with appropriate code
    if [ "$VALIDATION_PASSED" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Multi-Corpus Governance Agent Environment Validation"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h              Show this help message"
        echo "  --generate-secrets      Generate secure secrets for .env file"
        echo "  --fix-permissions       Fix script permissions"
        echo
        exit 0
        ;;
    --generate-secrets)
        generate_secrets
        exit 0
        ;;
    --fix-permissions)
        check_permissions
        exit 0
        ;;
esac

# Run main validation
main
