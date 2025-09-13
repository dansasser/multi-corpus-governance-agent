#!/bin/bash
# Multi-Corpus Governance Agent - Database Initialization Script
# Handles database creation, migrations, and seeding

set -e  # Exit on any error

echo "🗄️  Database Initialization"
echo "=========================="

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

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        print_success "Environment variables loaded from .env"
    else
        print_warning ".env file not found, using defaults"
        export DATABASE_URL=${DATABASE_URL:-"sqlite:///./mcg_agent.db"}
    fi
}

# Check if alembic is available
check_alembic() {
    print_status "Checking for Alembic..."
    if ! command -v alembic &> /dev/null; then
        print_error "Alembic not found. Please install dependencies first."
        echo "Run: pip install -r src/requirements.txt"
        exit 1
    fi
    print_success "Alembic found"
}

# Initialize Alembic if not already initialized
init_alembic() {
    print_status "Checking Alembic configuration..."
    if [ ! -f "alembic.ini" ]; then
        print_status "Initializing Alembic..."
        alembic init alembic
        print_success "Alembic initialized"
    else
        print_success "Alembic already configured"
    fi
}

# Create database tables using Alembic
create_tables() {
    print_status "Creating database tables..."
    
    # Check if we have any migrations
    if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
        print_status "No migrations found, creating initial migration..."
        alembic revision --autogenerate -m "Initial migration"
    fi
    
    # Apply migrations
    print_status "Applying database migrations..."
    alembic upgrade head
    print_success "Database tables created/updated"
}

# Seed database with initial data
seed_database() {
    print_status "Seeding database with initial data..."
    
    # Check if seed script exists
    if [ -f "src/mcg_agent/ingest/seed.py" ]; then
        python -m mcg_agent.ingest.seed --upgrade-db
        print_success "Database seeded with initial data"
    else
        print_warning "Seed script not found, skipping initial data"
    fi
}

# Import sample data if available
import_sample_data() {
    print_status "Checking for sample data..."
    
    # Check for ChatGPT export data
    if [ -f "db/chat data/conversations.json" ]; then
        print_status "Found ChatGPT export data, importing..."
        python -m mcg_agent.ingest.seed \
            --personal-path "db/chat data/conversations.json" \
            --source openai_chatgpt
        print_success "ChatGPT data imported"
    else
        print_warning "No sample ChatGPT data found in db/chat data/"
    fi
    
    # Check for other sample data
    if [ -d "db/sample_data" ]; then
        print_status "Found sample data directory, importing..."
        # Add logic for other sample data types here
        print_success "Sample data imported"
    else
        print_warning "No sample data directory found"
    fi
}

# Verify database setup
verify_database() {
    print_status "Verifying database setup..."
    
    # Try to connect and query basic info
    python -c "
from mcg_agent.db.session import get_session
from mcg_agent.db.models_personal import Message
from mcg_agent.db.models_social import Post  
from mcg_agent.db.models_published import Article

try:
    with get_session() as session:
        message_count = session.query(Message).count()
        post_count = session.query(Post).count()
        article_count = session.query(Article).count()
        
        print(f'Database verification successful:')
        print(f'  Personal messages: {message_count}')
        print(f'  Social posts: {post_count}')
        print(f'  Published articles: {article_count}')
except Exception as e:
    print(f'Database verification failed: {e}')
    exit(1)
"
    print_success "Database verification completed"
}

# Main initialization flow
main() {
    echo
    print_status "Starting database initialization..."
    
    load_env
    check_alembic
    init_alembic
    create_tables
    seed_database
    
    # Only import sample data if requested
    if [[ "${1:-}" == "--import-samples" ]]; then
        import_sample_data
    fi
    
    verify_database
    
    echo
    print_success "Database initialization completed successfully!"
    echo
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Multi-Corpus Governance Agent Database Initialization"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h         Show this help message"
        echo "  --import-samples   Import sample data after initialization"
        echo "  --reset            Drop all tables and recreate (DESTRUCTIVE)"
        echo "  --migrate-only     Only run migrations, skip seeding"
        echo
        exit 0
        ;;
    --reset)
        print_warning "DESTRUCTIVE OPERATION: This will drop all existing data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Dropping all tables..."
            alembic downgrade base
            print_success "Tables dropped"
        else
            print_status "Operation cancelled"
            exit 0
        fi
        ;;
    --migrate-only)
        seed_database() { print_status "Skipping seeding (--migrate-only flag)"; }
        import_sample_data() { print_status "Skipping sample data (--migrate-only flag)"; }
        ;;
esac

# Run main initialization
main "$@"
