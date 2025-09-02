#!/bin/bash
# Health check script for monitoring and deployment

set -e

# Configuration
HOST=${HOST:-localhost}
PORT=${PORT:-8000}
TIMEOUT=${TIMEOUT:-30}
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-5}
VERBOSE=${VERBOSE:-false}
OUTPUT_FORMAT=${OUTPUT_FORMAT:-human}  # human, json, prometheus

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        --retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --delay)
            RETRY_DELAY="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --host HOST        Target host (default: localhost)"
            echo "  --port PORT        Target port (default: 8000)"
            echo "  --timeout SECONDS  Request timeout (default: 30)"
            echo "  --retries COUNT    Max retry attempts (default: 3)"
            echo "  --delay SECONDS    Retry delay (default: 5)"
            echo "  --verbose          Enable verbose output"
            echo "  --format FORMAT    Output format: human, json, prometheus"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for human output
if [ "$OUTPUT_FORMAT" = "human" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if [ "$VERBOSE" = true ] || [ "$level" != "DEBUG" ]; then
        case $OUTPUT_FORMAT in
            "json")
                echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"message\":\"$message\"}"
                ;;
            "human")
                case $level in
                    "ERROR") echo -e "${RED}[ERROR]${NC} $message" >&2 ;;
                    "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" >&2 ;;
                    "INFO")  echo -e "${GREEN}[INFO]${NC} $message" ;;
                    "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" ;;
                esac
                ;;
        esac
    fi
}

# Health check function
check_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local url="http://${HOST}:${PORT}${endpoint}"
    
    log "DEBUG" "Checking endpoint: $url"
    
    local response
    local http_code
    local response_time
    
    # Make request and capture response, status code, and timing
    response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
                   --max-time "$TIMEOUT" \
                   --connect-timeout 10 \
                   "$url" 2>/dev/null) || {
        log "ERROR" "Failed to connect to $url"
        return 1
    }
    
    # Parse response
    local body=$(echo "$response" | sed -n '1,/^[0-9]*$/p' | sed '$d')
    http_code=$(echo "$response" | tail -n 2 | head -n 1)
    response_time=$(echo "$response" | tail -n 1)
    
    log "DEBUG" "HTTP $http_code in ${response_time}s"
    
    # Check status code
    if [ "$http_code" -ne "$expected_status" ]; then
        log "ERROR" "Unexpected status code $http_code (expected $expected_status)"
        return 1
    fi
    
    # Store results for later use
    export LAST_HTTP_CODE="$http_code"
    export LAST_RESPONSE_TIME="$response_time"
    export LAST_RESPONSE_BODY="$body"
    
    return 0
}

# Main health check function
run_health_check() {
    local start_time=$(date +%s.%N)
    local overall_status="healthy"
    local checks_passed=0
    local checks_total=0
    
    log "INFO" "Starting health check for ${HOST}:${PORT}"
    
    # Basic connectivity check
    log "INFO" "Checking basic connectivity..."
    ((checks_total++))
    if check_endpoint "/health/ping" 200; then
        log "INFO" "✓ Basic connectivity: OK"
        ((checks_passed++))
    else
        log "ERROR" "❌ Basic connectivity: FAILED"
        overall_status="unhealthy"
    fi
    
    # Readiness check
    log "INFO" "Checking application readiness..."
    ((checks_total++))
    if check_endpoint "/health/ready" 200; then
        log "INFO" "✓ Application readiness: OK"
        ((checks_passed++))
    else
        log "WARN" "⚠️  Application readiness: NOT READY"
        overall_status="degraded"
    fi
    
    # Liveness check
    log "INFO" "Checking application liveness..."
    ((checks_total++))
    if check_endpoint "/health/live" 200; then
        log "INFO" "✓ Application liveness: OK"
        ((checks_passed++))
    else
        log "ERROR" "❌ Application liveness: FAILED"
        overall_status="unhealthy"
    fi
    
    # Comprehensive health check
    log "INFO" "Running comprehensive health check..."
    ((checks_total++))
    if check_endpoint "/health" 200; then
        log "INFO" "✓ Comprehensive health: OK"
        ((checks_passed++))
        
        # Parse health response if JSON
        if command -v jq >/dev/null 2>&1; then
            local db_status=$(echo "$LAST_RESPONSE_BODY" | jq -r '.details.database.status // "unknown"' 2>/dev/null)
            local redis_status=$(echo "$LAST_RESPONSE_BODY" | jq -r '.details.redis.status // "unknown"' 2>/dev/null)
            
            log "DEBUG" "Database status: $db_status"
            log "DEBUG" "Redis status: $redis_status"
        fi
    else
        log "ERROR" "❌ Comprehensive health: FAILED"
        overall_status="unhealthy"
    fi
    
    local end_time=$(date +%s.%N)
    local total_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
    
    # Output results based on format
    case $OUTPUT_FORMAT in
        "json")
            cat << EOF
{
  "status": "$overall_status",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "checks_passed": $checks_passed,
  "checks_total": $checks_total,
  "response_time": "${total_time}s",
  "endpoint": "${HOST}:${PORT}"
}
EOF
            ;;
        "prometheus")
            echo "# HELP mcg_agent_health_status Health status of MCG Agent API"
            echo "# TYPE mcg_agent_health_status gauge"
            local status_code=0
            case $overall_status in
                "healthy") status_code=1 ;;
                "degraded") status_code=0.5 ;;
                "unhealthy") status_code=0 ;;
            esac
            echo "mcg_agent_health_status{host=\"$HOST\",port=\"$PORT\"} $status_code"
            echo "# HELP mcg_agent_health_checks_total Total number of health checks"
            echo "# TYPE mcg_agent_health_checks_total counter"
            echo "mcg_agent_health_checks_total{host=\"$HOST\",port=\"$PORT\"} $checks_total"
            echo "# HELP mcg_agent_health_checks_passed Number of passed health checks"
            echo "# TYPE mcg_agent_health_checks_passed counter"
            echo "mcg_agent_health_checks_passed{host=\"$HOST\",port=\"$PORT\"} $checks_passed"
            ;;
        *)
            log "INFO" "Health check completed"
            log "INFO" "Status: $overall_status"
            log "INFO" "Checks: $checks_passed/$checks_total passed"
            log "INFO" "Total time: ${total_time}s"
            ;;
    esac
    
    # Return appropriate exit code
    case $overall_status in
        "healthy") return 0 ;;
        "degraded") return 1 ;;
        "unhealthy") return 2 ;;
    esac
}

# Retry logic
for attempt in $(seq 1 $MAX_RETRIES); do
    log "DEBUG" "Attempt $attempt of $MAX_RETRIES"
    
    if run_health_check; then
        exit 0
    else
        exit_code=$?
        if [ $attempt -lt $MAX_RETRIES ]; then
            log "WARN" "Health check failed, retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        else
            log "ERROR" "Health check failed after $MAX_RETRIES attempts"
            exit $exit_code
        fi
    fi
done