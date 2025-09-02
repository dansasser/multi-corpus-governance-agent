#!/bin/bash
# Database initialization and migration script

set -e

echo "Initializing MCG Agent Database..."

# Check if we're in the right directory
if [ ! -f "src/mcg_agent/database/__init__.py" ]; then
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

# Set environment
export ENVIRONMENT=${ENVIRONMENT:-development}

# Parse command line arguments
FORCE_RECREATE=false
RUN_SEED=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        --seed)
            RUN_SEED=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --force-recreate  Drop and recreate all tables (DESTRUCTIVE)"
            echo "  --seed           Run seed data after initialization"
            echo "  --verbose        Enable verbose output"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$VERBOSE" = true ]; then
    set -x
fi

# Check database connection
echo "Checking database connection..."
python -c "
from src.mcg_agent.database.connection import check_db_connection
try:
    check_db_connection()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"

if [ "$FORCE_RECREATE" = true ]; then
    echo "⚠️  WARNING: This will DROP ALL EXISTING DATA!"
    read -p "Are you sure you want to recreate the database? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Operation cancelled."
        exit 0
    fi
    
    echo "Dropping existing tables..."
    python -c "
from src.mcg_agent.database.models import drop_all_tables
drop_all_tables()
print('✓ All tables dropped')
    "
fi

# Create/update database schema
echo "Creating/updating database schema..."
python -c "
from src.mcg_agent.database.models import create_all_tables
create_all_tables()
print('✓ Database schema created/updated')
"

# Run migrations
echo "Running database migrations..."
python -c "
from src.mcg_agent.database.migrations import run_migrations
try:
    run_migrations()
    print('✓ Database migrations completed')
except Exception as e:
    print(f'ℹ️  No migrations needed or available: {e}')
"

# Seed database if requested
if [ "$RUN_SEED" = true ]; then
    echo "Seeding database with initial data..."
    python -c "
from src.mcg_agent.database.seed import seed_database
try:
    seed_database()
    print('✓ Database seeded successfully')
except Exception as e:
    print(f'⚠️  Seeding failed: {e}')
    "
fi

# Verify database state
echo "Verifying database state..."
python -c "
from src.mcg_agent.database.models import verify_schema
from src.mcg_agent.database.connection import get_db_info

try:
    verify_schema()
    info = get_db_info()
    print('✓ Database verification successful')
    print(f'  Database: {info.get("database", "unknown")}')
    print(f'  Tables: {info.get("table_count", 0)}')
    print(f'  Version: {info.get("version", "unknown")}')
except Exception as e:
    print(f'⚠️  Database verification issues: {e}')
    exit(1)
"

echo "✅ Database initialization completed successfully!"

if [ "$VERBOSE" = true ]; then
    set +x
fi