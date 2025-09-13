#!/bin/bash
# Multi-Corpus Governance Agent - Health Check Script
# Monitors application health for containers and load balancers

set -e  # Exit on any error

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
DEFAULT_HOST="localhost"
DEFAULT_PORT="8000"
DEFAULT_TIMEOUT="10"
DEFAULT_FORMAT="text"

# Configuration variables
HOST=${HOST:-$DEFAULT_HOST}
PORT=${PORT:-$DEFAULT_PORT}
TIMEOUT=${TIMEOUT:-$DEFAULT_TIMEOUT}
FORMAT=${FORMAT:-$DEFAULT_FORMAT}
VERBOSE=false
QUIET=false

# Health check results
HEALTH_STATUS="unknown"
HEALTH_DETAILS=()
EXIT_CODE=0

# Load environment variables if available
load_env() {
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs) 2>/dev/null || true
        HOST=${HOST:-$DEFAULT_HOST}
        PORT=${PORT:-$DEFAULT_PORT}
    fi
}

# Check if curl is available
check_curl() {
    if ! command -v curl &> /dev/null; then
        print_error "curl is required for health checks"
        exit 1
    fi
}

# Basic connectivity check
check_connectivity() {
    if [ "$VERBOSE" = true ]; then
        print_status "Checking connectivity to ${HOST}:${PORT}..."
    fi
    
    if curl -s --connect-timeout ${TIMEOUT} "http://${HOST}:${PORT}" > /dev/null 2>&1; then
        HEALTH_DETAILS+=("connectivity:ok")
        if [ "$VERBOSE" = true ]; then
            print_success "Connectivity check passed"
        fi
    else
        HEALTH_DETAILS+=("connectivity:failed")
        HEALTH_STATUS="unhealthy"
        EXIT_CODE=1
        if [ "$VERBOSE" = true ]; then
            print_error "Connectivity check failed"
        fi
    fi
}

# Application health endpoint check
check_health_endpoint() {
    if [ "$VERBOSE" = true ]; then
        print_status "Checking health endpoint..."
    fi
    
    RESPONSE=$(curl -s --connect-timeout ${TIMEOUT} --max-time ${TIMEOUT} \
        -w "%{http_code}" \
        "http://${HOST}:${PORT}/health" 2>/dev/null || echo "000")
    
    HTTP_CODE="${RESPONSE: -3}"
    RESPONSE_BODY="${RESPONSE%???}"
    
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_DETAILS+=("health_endpoint:ok")
        if [ "$VERBOSE" = true ]; then
            print_success "Health endpoint check passed"
        fi
    else
        HEALTH_DETAILS+=("health_endpoint:failed:${HTTP_CODE}")
        HEALTH_STATUS="unhealthy"
        EXIT_CODE=1
        if [ "$VERBOSE" = true ]; then
            print_error "Health endpoint check failed (HTTP ${HTTP_CODE})"
        fi
    fi
}

# Database connectivity check
check_database() {
    if [ "$VERBOSE" = true ]; then
        print_status "Checking database connectivity..."
    fi
    
    RESPONSE=$(curl -s --connect-timeout ${TIMEOUT} --max-time ${TIMEOUT} \
        -w "%{http_code}" \
        "http://${HOST}:${PORT}/health/db" 2>/dev/null || echo "000")
    
    HTTP_CODE="${RESPONSE: -3}"
    
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_DETAILS+=("database:ok")
        if [ "$VERBOSE" = true ]; then
            print_success "Database check passed"
        fi
    else
        HEALTH_DETAILS+=("database:failed:${HTTP_CODE}")
        HEALTH_STATUS="unhealthy"
        EXIT_CODE=1
        if [ "$VERBOSE" = true ]; then
            print_error "Database check failed (HTTP ${HTTP_CODE})"
        fi
    fi
}

# Redis connectivity check
check_redis() {
    if [ "$VERBOSE" = true ]; then
        print_status "Checking Redis connectivity..."
    fi
    
    RESPONSE=$(curl -s --connect-timeout ${TIMEOUT} --max-time ${TIMEOUT} \
        -w "%{http_code}" \
        "http://${HOST}:${PORT}/health/redis" 2>/dev/null || echo "000")
    
    HTTP_CODE="${RESPONSE: -3}"
    
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_DETAILS+=("redis:ok")
        if [ "$VERBOSE" = true ]; then
            print_success "Redis check passed"
        fi
    else
        HEALTH_DETAILS+=("redis:failed:${HTTP_CODE}")
        HEALTH_STATUS="unhealthy"
        EXIT_CODE=1
        if [ "$VERBOSE" = true ]; then
            print_error "Redis check failed (HTTP ${HTTP_CODE})"
        fi
    fi
}

# API functionality check
check_api() {
    if [ "$VERBOSE" = true ]; then
        print_status "Checking API functionality..."
    fi
    
    # Test a simple API endpoint
    RESPONSE=$(curl -s --connect-timeout ${TIMEOUT} --max-time ${TIMEOUT} \
        -w "%{http_code}" \
        -H "Content-Type: application/json" \
        "http://${HOST}:${PORT}/api/v1/status" 2>/dev/null || echo "000")
    
    HTTP_CODE="${RESPONSE: -3}"
    
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_DETAILS+=("api:ok")
        if [ "$VERBOSE" = true ]; then
            print_success "API check passed"
        fi
    else
        HEALTH_DETAILS+=("api:failed:${HTTP_CODE}")
        HEALTH_STATUS="unhealthy"
        EXIT_CODE=1
        if [ "$VERBOSE" = true ]; then
            print_error "API check failed (HTTP ${HTTP_CODE})"
        fi
    fi
}

# Output results in different formats
output_results() {
    if [ "$HEALTH_STATUS" = "unknown" ]; then
        HEALTH_STATUS="healthy"
    fi
    
    case $FORMAT in
        json)
            echo "{"
            echo "  \"status\": \"${HEALTH_STATUS}\","
            echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
            echo "  \"checks\": ["
            for i in "${!HEALTH_DETAILS[@]}"; do
                IFS=':' read -ra PARTS <<< "${HEALTH_DETAILS[$i]}"
                CHECK_NAME="${PARTS[0]}"
                CHECK_STATUS="${PARTS[1]}"
                CHECK_CODE="${PARTS[2]:-}"
                
                echo -n "    {\"name\": \"${CHECK_NAME}\", \"status\": \"${CHECK_STATUS}\""
                if [ -n "$CHECK_CODE" ]; then
                    echo -n ", \"code\": \"${CHECK_CODE}\""
                fi
                echo -n "}"
                if [ $i -lt $((${#HEALTH_DETAILS[@]} - 1)) ]; then
                    echo ","
                else
                    echo
                fi
            done
            echo "  ]"
            echo "}"
            ;;
        prometheus)
            echo "# HELP mcg_agent_health_status Health status of the MCG Agent"
            echo "# TYPE mcg_agent_health_status gauge"
            if [ "$HEALTH_STATUS" = "healthy" ]; then
                echo "mcg_agent_health_status 1"
            else
                echo "mcg_agent_health_status 0"
            fi
            
            echo "# HELP mcg_agent_health_check_status Individual health check statuses"
            echo "# TYPE mcg_agent_health_check_status gauge"
            for detail in "${HEALTH_DETAILS[@]}"; do
                IFS=':' read -ra PARTS <<< "$detail"
                CHECK_NAME="${PARTS[0]}"
                CHECK_STATUS="${PARTS[1]}"
                
                if [ "$CHECK_STATUS" = "ok" ]; then
                    echo "mcg_agent_health_check_status{check=\"${CHECK_NAME}\"} 1"
                else
                    echo "mcg_agent_health_check_status{check=\"${CHECK_NAME}\"} 0"
                fi
            done
            ;;
        text|*)
            if [ "$QUIET" != true ]; then
                echo "Health Status: ${HEALTH_STATUS}"
                echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
                echo "Checks:"
                for detail in "${HEALTH_DETAILS[@]}"; do
                    IFS=':' read -ra PARTS <<< "$detail"
                    CHECK_NAME="${PARTS[0]}"
                    CHECK_STATUS="${PARTS[1]}"
                    CHECK_CODE="${PARTS[2]:-}"
                    
                    printf "  %-15s: %s" "$CHECK_NAME" "$CHECK_STATUS"
                    if [ -n "$CHECK_CODE" ]; then
                        printf " (%s)" "$CHECK_CODE"
                    fi
                    echo
                done
            else
                # Quiet mode - just output status
                echo "$HEALTH_STATUS"
            fi
            ;;
    esac
}

# Main health check flow
main() {
    load_env
    check_curl
    
    # Run health checks
    check_connectivity
    check_health_endpoint
    check_database
    check_redis
    check_api
    
    # Output results
    output_results
    
    # Exit with appropriate code
    exit $EXIT_CODE
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Multi-Corpus Governance Agent Health Check"
            echo
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --help, -h              Show this help message"
            echo "  --host HOST             Host to check (default: ${DEFAULT_HOST})"
            echo "  --port PORT             Port to check (default: ${DEFAULT_PORT})"
            echo "  --timeout SECONDS       Request timeout (default: ${DEFAULT_TIMEOUT})"
            echo "  --format FORMAT         Output format: text, json, prometheus (default: ${DEFAULT_FORMAT})"
            echo "  --verbose, -v           Verbose output"
            echo "  --quiet, -q             Quiet output (status only)"
            echo
            echo "Environment variables:"
            echo "  HOST                    Override default host"
            echo "  PORT                    Override default port"
            echo "  TIMEOUT                 Override default timeout"
            echo "  FORMAT                  Override default format"
            echo
            echo "Exit codes:"
            echo "  0                       All checks passed"
            echo "  1                       One or more checks failed"
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
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --quiet|-q)
            QUIET=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main health check
main
