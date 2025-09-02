#!/bin/bash
# Comprehensive test runner script

set -e

echo "Running MCG Agent Test Suite..."

# Check if we're in the right directory
if [ ! -f "src/mcg_agent/__init__.py" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Load environment variables
if [ -f ".env.test" ]; then
    source .env.test
    echo "Loaded test environment variables"
elif [ -f ".env" ]; then
    source .env
    echo "Loaded default environment variables"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Set test environment
export ENVIRONMENT=test
export DEBUG=false
export LOG_LEVEL=ERROR

# Parse command line arguments
TEST_TYPE="all"
VERBOSE=false
COVERAGE=true
PARALLEL=true
FAST=false
KEEP_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --api)
            TEST_TYPE="api"
            shift
            ;;
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --no-parallel)
            PARALLEL=false
            shift
            ;;
        --fast)
            FAST=true
            COVERAGE=false
            PARALLEL=true
            shift
            ;;
        --keep-db)
            KEEP_DB=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --unit           Run only unit tests"
            echo "  --integration    Run only integration tests"
            echo "  --api           Run only API tests"
            echo "  --e2e           Run only end-to-end tests"
            echo "  --verbose       Enable verbose output"
            echo "  --no-coverage   Skip coverage reporting"
            echo "  --no-parallel   Run tests sequentially"
            echo "  --fast          Fast mode (no coverage, parallel)"
            echo "  --keep-db       Don't cleanup test database"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Install test dependencies
echo "Installing test dependencies..."
pip install -e .[test] > /dev/null

# Setup test database if needed
if [ "$KEEP_DB" = false ]; then
    echo "Setting up test database..."
    python -c "
from src.mcg_agent.database.test_utils import setup_test_db, cleanup_test_db
cleanup_test_db()  # Clean any previous test data
setup_test_db()
print('✓ Test database ready')
    " || {
        echo "Warning: Test database setup failed, continuing anyway"
    }
fi

# Build pytest arguments
PYTEST_ARGS=()

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
else
    PYTEST_ARGS+=("-q")
fi

if [ "$PARALLEL" = true ] && [ "$TEST_TYPE" != "e2e" ]; then
    PYTEST_ARGS+=("-n" "auto")
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS+=("--cov=src/mcg_agent" "--cov-report=term-missing" "--cov-report=html:htmlcov")
fi

# Set test paths based on type
case $TEST_TYPE in
    "unit")
        TEST_PATHS=("tests/unit")
        echo "Running unit tests..."
        ;;
    "integration")
        TEST_PATHS=("tests/integration")
        echo "Running integration tests..."
        ;;
    "api")
        TEST_PATHS=("tests/api")
        echo "Running API tests..."
        ;;
    "e2e")
        TEST_PATHS=("tests/e2e")
        echo "Running end-to-end tests..."
        PYTEST_ARGS=("${PYTEST_ARGS[@]//-n/}" "${PYTEST_ARGS[@]//auto/}")  # Remove parallel for e2e
        ;;
    "all")
        TEST_PATHS=("tests/")
        echo "Running all tests..."
        ;;
esac

# Add test paths to pytest args
PYTEST_ARGS+=("${TEST_PATHS[@]}")

# Run linting first (unless in fast mode)
if [ "$FAST" = false ]; then
    echo "Running code quality checks..."
    
    echo "  • Checking code formatting with black..."
    black --check src/ tests/ || {
        echo "    ⚠️  Code formatting issues found. Run 'black src/ tests/' to fix."
    }
    
    echo "  • Checking imports with isort..."
    isort --check-only src/ tests/ || {
        echo "    ⚠️  Import sorting issues found. Run 'isort src/ tests/' to fix."
    }
    
    echo "  • Running flake8 linting..."
    flake8 src/ tests/ || {
        echo "    ⚠️  Linting issues found."
    }
    
    echo "  • Running mypy type checking..."
    mypy src/ || {
        echo "    ⚠️  Type checking issues found."
    }
fi

# Run the tests
echo "Executing tests with: pytest ${PYTEST_ARGS[*]}"
START_TIME=$(date +%s)

pytest "${PYTEST_ARGS[@]}" || {
    TEST_EXIT_CODE=$?
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
    
    # Cleanup on failure
    if [ "$KEEP_DB" = false ]; then
        python -c "from src.mcg_agent.database.test_utils import cleanup_test_db; cleanup_test_db()" 2>/dev/null || true
    fi
    
    exit $TEST_EXIT_CODE
}

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "✅ All tests passed in ${DURATION}s!"

# Show coverage report if enabled
if [ "$COVERAGE" = true ]; then
    echo "
Coverage report saved to htmlcov/index.html"
fi

# Cleanup test database
if [ "$KEEP_DB" = false ]; then
    echo "Cleaning up test database..."
    python -c "from src.mcg_agent.database.test_utils import cleanup_test_db; cleanup_test_db()" 2>/dev/null || {
        echo "Warning: Test database cleanup failed"
    }
fi

echo "✨ Test suite completed successfully!"