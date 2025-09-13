#!/bin/bash
# Multi-Corpus Governance Agent - Test Execution Script
# Runs comprehensive test suite with various options

set -e  # Exit on any error

echo "🧪 Test Suite"
echo "============="

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
DEFAULT_TEST_DIR="tests"
DEFAULT_COV_MIN="80"
DEFAULT_TIMEOUT="300"

# Configuration variables
TEST_DIR=${DEFAULT_TEST_DIR}
COV_MIN=${DEFAULT_COV_MIN}
TIMEOUT=${DEFAULT_TIMEOUT}
VERBOSE=false
COVERAGE=true
UNIT_TESTS=true
INTEGRATION_TESTS=true
API_TESTS=true
FAST_MODE=false
PARALLEL=false
WATCH_MODE=false

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs) 2>/dev/null || true
        print_success "Environment variables loaded from .env"
    else
        print_warning ".env file not found, using defaults"
    fi
    
    # Set test environment
    export ENVIRONMENT=test
    export DEBUG=false
    export DATABASE_URL=${TEST_DATABASE_URL:-"sqlite:///./test_mcg_agent.db"}
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

# Check if pytest is installed
check_pytest() {
    print_status "Checking for pytest..."
    
    if ! python -c "import pytest" 2>/dev/null; then
        print_error "pytest not found. Installing test dependencies..."
        pip install pytest pytest-asyncio pytest-cov httpx
        print_success "Test dependencies installed"
    else
        print_success "pytest found"
    fi
}

# Setup test database
setup_test_db() {
    print_status "Setting up test database..."
    
    # Remove existing test database
    if [ -f "test_mcg_agent.db" ]; then
        rm test_mcg_agent.db
        print_status "Removed existing test database"
    fi
    
    # Create test database
    python -c "
from mcg_agent.db.base import Base
from mcg_agent.db.session import engine
Base.metadata.create_all(bind=engine)
print('Test database created')
" || {
        print_error "Failed to create test database"
        exit 1
    }
    
    print_success "Test database setup completed"
}

# Run code quality checks
run_quality_checks() {
    print_status "Running code quality checks..."
    
    # Check if quality tools are installed
    QUALITY_TOOLS=("black" "isort" "flake8" "mypy")
    for tool in "${QUALITY_TOOLS[@]}"; do
        if ! command -v $tool &> /dev/null; then
            print_warning "$tool not found, installing..."
            pip install $tool
        fi
    done
    
    # Run black formatting check
    print_status "Checking code formatting with black..."
    if black --check src/ tests/ 2>/dev/null; then
        print_success "Code formatting check passed"
    else
        print_error "Code formatting check failed. Run: black src/ tests/"
        return 1
    fi
    
    # Run import sorting check
    print_status "Checking import sorting with isort..."
    if isort --check-only src/ tests/ 2>/dev/null; then
        print_success "Import sorting check passed"
    else
        print_error "Import sorting check failed. Run: isort src/ tests/"
        return 1
    fi
    
    # Run linting
    print_status "Running linting with flake8..."
    if flake8 src/ tests/ 2>/dev/null; then
        print_success "Linting check passed"
    else
        print_error "Linting check failed"
        return 1
    fi
    
    # Run type checking
    print_status "Running type checking with mypy..."
    if mypy src/ 2>/dev/null; then
        print_success "Type checking passed"
    else
        print_warning "Type checking found issues (non-blocking)"
    fi
    
    print_success "Code quality checks completed"
}

# Build pytest command
build_pytest_cmd() {
    local cmd="pytest"
    
    # Add verbosity
    if [ "$VERBOSE" = true ]; then
        cmd="$cmd -v"
    else
        cmd="$cmd -q"
    fi
    
    # Add coverage
    if [ "$COVERAGE" = true ]; then
        cmd="$cmd --cov=src/mcg_agent --cov-report=term-missing --cov-report=html --cov-fail-under=${COV_MIN}"
    fi
    
    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        cmd="$cmd -n auto"
    fi
    
    # Add timeout
    cmd="$cmd --timeout=${TIMEOUT}"
    
    # Add test selection
    local test_paths=()
    
    if [ "$UNIT_TESTS" = true ]; then
        test_paths+=("${TEST_DIR}/unit")
    fi
    
    if [ "$INTEGRATION_TESTS" = true ]; then
        test_paths+=("${TEST_DIR}/integration")
    fi
    
    if [ "$API_TESTS" = true ]; then
        test_paths+=("${TEST_DIR}/api")
    fi
    
    # If no specific test types selected, run all
    if [ ${#test_paths[@]} -eq 0 ]; then
        test_paths+=("${TEST_DIR}")
    fi
    
    # Add test paths to command
    for path in "${test_paths[@]}"; do
        if [ -d "$path" ]; then
            cmd="$cmd $path"
        fi
    done
    
    # If no test directories exist, just run tests directory
    if [ ${#test_paths[@]} -eq 0 ] || [ ! -d "${test_paths[0]}" ]; then
        cmd="$cmd ${TEST_DIR}"
    fi
    
    echo "$cmd"
}

# Run tests
run_tests() {
    print_status "Running test suite..."
    
    local pytest_cmd=$(build_pytest_cmd)
    print_status "Command: $pytest_cmd"
    
    if [ "$FAST_MODE" = true ]; then
        print_status "Fast mode: Skipping slow tests"
        pytest_cmd="$pytest_cmd -m 'not slow'"
    fi
    
    # Run the tests
    if eval $pytest_cmd; then
        print_success "All tests passed!"
        return 0
    else
        print_error "Some tests failed"
        return 1
    fi
}

# Watch mode for continuous testing
run_watch_mode() {
    print_status "Starting watch mode..."
    print_status "Tests will re-run when files change. Press Ctrl+C to stop."
    
    if ! command -v pytest-watch &> /dev/null; then
        print_status "Installing pytest-watch..."
        pip install pytest-watch
    fi
    
    local pytest_cmd=$(build_pytest_cmd)
    ptw --runner "$pytest_cmd"
}

# Generate test report
generate_report() {
    print_status "Generating test report..."
    
    if [ -d "htmlcov" ]; then
        print_success "Coverage report available at: htmlcov/index.html"
    fi
    
    if [ -f "pytest-report.html" ]; then
        print_success "Test report available at: pytest-report.html"
    fi
}

# Cleanup test artifacts
cleanup() {
    print_status "Cleaning up test artifacts..."
    
    # Remove test database
    if [ -f "test_mcg_agent.db" ]; then
        rm test_mcg_agent.db
        print_status "Removed test database"
    fi
    
    # Remove pytest cache
    if [ -d ".pytest_cache" ]; then
        rm -rf .pytest_cache
        print_status "Removed pytest cache"
    fi
    
    print_success "Cleanup completed"
}

# Main test execution flow
main() {
    echo
    print_status "Starting test execution..."
    
    load_env
    check_venv
    check_pytest
    setup_test_db
    
    # Run quality checks unless in fast mode
    if [ "$FAST_MODE" != true ]; then
        run_quality_checks || {
            print_error "Code quality checks failed"
            exit 1
        }
    fi
    
    # Run tests
    if [ "$WATCH_MODE" = true ]; then
        run_watch_mode
    else
        run_tests || {
            print_error "Tests failed"
            cleanup
            exit 1
        }
    fi
    
    generate_report
    cleanup
    
    echo
    print_success "Test execution completed successfully!"
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Multi-Corpus Governance Agent Test Runner"
            echo
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --help, -h              Show this help message"
            echo "  --unit                  Run only unit tests"
            echo "  --integration           Run only integration tests"
            echo "  --api                   Run only API tests"
            echo "  --fast                  Fast mode (skip slow tests and quality checks)"
            echo "  --coverage              Enable coverage reporting (default: true)"
            echo "  --no-coverage           Disable coverage reporting"
            echo "  --parallel              Run tests in parallel"
            echo "  --watch                 Watch mode (re-run on file changes)"
            echo "  --verbose, -v           Verbose output"
            echo "  --timeout SECONDS       Test timeout (default: ${DEFAULT_TIMEOUT})"
            echo "  --cov-min PERCENT       Minimum coverage percentage (default: ${DEFAULT_COV_MIN})"
            echo
            echo "Environment variables:"
            echo "  TEST_DATABASE_URL       Test database URL"
            echo "  COV_MIN                 Minimum coverage percentage"
            echo
            exit 0
            ;;
        --unit)
            UNIT_TESTS=true
            INTEGRATION_TESTS=false
            API_TESTS=false
            shift
            ;;
        --integration)
            UNIT_TESTS=false
            INTEGRATION_TESTS=true
            API_TESTS=false
            shift
            ;;
        --api)
            UNIT_TESTS=false
            INTEGRATION_TESTS=false
            API_TESTS=true
            shift
            ;;
        --fast)
            FAST_MODE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --cov-min)
            COV_MIN="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set up signal handler for cleanup
trap cleanup SIGINT SIGTERM

# Run main test execution
main
