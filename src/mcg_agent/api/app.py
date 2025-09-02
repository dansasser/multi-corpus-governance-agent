"""FastAPI application for Multi-Corpus Governance Agent.

This module creates the main FastAPI application with authentication,
agent pipeline endpoints, and comprehensive security monitoring.

Integrates with:
- JWT authentication system (auth.py)
- Governance protocol engine (governance/)
- Redis session management (session_manager.py)
- Database models and operations (database/)
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from .routers import auth, agents, health, monitoring
from ..config import settings
from ..utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    UnauthorizedRAGAccessError,
    MVLMRequiredError,
    SecurityValidationError,
    AuthenticationError,
    AuthorizationError
)
from ..utils.logging import SecurityLogger
from ..database.session import db_manager
from .session_manager import session_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown procedures including:
    - Database connection initialization
    - Redis session manager initialization
    - Security system startup
    - Graceful shutdown procedures
    """
    
    # Startup procedures
    logger.info("🚀 Starting Multi-Corpus Governance Agent API...")
    
    try:
        # Initialize database connection
        logger.info("📊 Initializing database connection...")
        await db_manager.initialize()
        
        # Initialize Redis session manager
        logger.info("🔐 Initializing Redis session manager...")
        await session_manager.initialize()
        
        # Log system startup
        await SecurityLogger.log_system_event(
            event_type="application_startup",
            success=True,
            details={
                "version": "1.0.0",
                "environment": getattr(settings, 'ENVIRONMENT', 'development'),
                "startup_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Multi-Corpus Governance Agent API started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {str(e)}")
        
        await SecurityLogger.log_system_event(
            event_type="application_startup_failed",
            success=False,
            details={"error": str(e)}
        )
        
        raise
    
    finally:
        # Shutdown procedures
        logger.info("🛑 Shutting down Multi-Corpus Governance Agent API...")
        
        try:
            # Close Redis connections
            await session_manager.close()
            
            # Close database connections
            await db_manager.close()
            
            # Log system shutdown
            await SecurityLogger.log_system_event(
                event_type="application_shutdown",
                success=True,
                details={"shutdown_time": datetime.now(timezone.utc).isoformat()}
            )
            
            logger.info("✅ Application shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="Multi-Corpus Governance Agent API",
    description="""
    Multi-Corpus Governance Agent API with protocol-first governance enforcement.
    
    ## Features
    
    * **Protocol-First Governance**: Architectural constraints prevent rule violations
    * **Five-Agent Pipeline**: Ideator → Drafter → Critic → Revisor → Summarizer
    * **Multi-Corpus Integration**: Personal, Social, and Published corpus access
    * **JWT Authentication**: Secure authentication with role-based access control
    * **Redis Session Management**: Scalable session storage with TLS encryption
    * **Comprehensive Security**: Real-time monitoring and incident response
    * **Complete Audit Trail**: Immutable attribution tracking throughout pipeline
    
    ## Security
    
    All endpoints require proper authentication and authorization.
    Governance rules are enforced at the architectural level to ensure compliance.
    """,
    version="1.0.0",
    contact={
        "name": "Multi-Corpus Governance Agent Team",
        "url": "https://gorombo.com",
        "email": "support@gorombo.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    # Security headers
    docs_url="/docs" if getattr(settings, 'ENVIRONMENT', 'development') == 'development' else None,
    redoc_url="/redoc" if getattr(settings, 'ENVIRONMENT', 'development') == 'development' else None,
)


# Security Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, 'ALLOWED_ORIGINS', ["http://localhost:3000"]),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=getattr(settings, 'ALLOWED_HOSTS', ["localhost", "127.0.0.1", "*.gorombo.com"])
)


# Request/Response Middleware for Security Logging
@app.middleware("http")
async def security_logging_middleware(request: Request, call_next):
    """
    Log all requests for security monitoring and audit trails.
    """
    start_time = datetime.now(timezone.utc)
    
    # Extract client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log successful request
        await SecurityLogger.log_system_event(
            event_type="api_request",
            success=True,
            details={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            }
        )
        
        return response
        
    except Exception as e:
        # Log failed request
        await SecurityLogger.log_system_event(
            event_type="api_request_error",
            success=False,
            details={
                "method": request.method,
                "path": str(request.url.path),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "error": str(e),
                "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            }
        )
        
        raise


# Exception Handlers

@app.exception_handler(GovernanceViolationError)
async def governance_violation_handler(request: Request, exc: GovernanceViolationError):
    """Handle governance violations with appropriate security response."""
    
    await SecurityLogger.log_governance_violation(
        violation_type=exc.violation_type,
        agent_name=exc.agent_name,
        task_id=getattr(exc, 'task_id', None),
        severity=exc.severity,
        details={
            "violation_details": exc.details,
            "request_path": str(request.url.path),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=403,
        content={
            "error": "Governance Violation",
            "message": f"Action violates governance protocol: {exc.violation_type}",
            "violation_type": exc.violation_type,
            "severity": exc.severity,
            "reference_id": getattr(exc, 'violation_id', None)
        }
    )


@app.exception_handler(APICallLimitExceededError)
async def api_limit_exceeded_handler(request: Request, exc: APICallLimitExceededError):
    """Handle API call limit violations."""
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "API Call Limit Exceeded",
            "message": f"Agent {exc.agent_name} has exceeded API call limit",
            "agent": exc.agent_name,
            "max_calls": exc.max_calls,
            "current_calls": exc.current_calls
        }
    )


@app.exception_handler(UnauthorizedCorpusAccessError)
async def unauthorized_corpus_handler(request: Request, exc: UnauthorizedCorpusAccessError):
    """Handle unauthorized corpus access attempts."""
    
    return JSONResponse(
        status_code=403,
        content={
            "error": "Unauthorized Corpus Access",
            "message": f"Agent {exc.agent_name} not authorized to access {exc.corpus} corpus",
            "agent": exc.agent_name,
            "requested_corpus": exc.corpus,
            "allowed_corpora": exc.allowed_corpora
        }
    )


@app.exception_handler(UnauthorizedRAGAccessError)
async def unauthorized_rag_handler(request: Request, exc: UnauthorizedRAGAccessError):
    """Handle unauthorized RAG access attempts."""
    
    return JSONResponse(
        status_code=403,
        content={
            "error": "Unauthorized RAG Access",
            "message": f"Agent {exc.agent_name} not authorized for RAG access",
            "agent": exc.agent_name,
            "authorized_agents": exc.authorized_agents
        }
    )


@app.exception_handler(MVLMRequiredError)
async def mvlm_required_handler(request: Request, exc: MVLMRequiredError):
    """Handle MVLM requirement violations."""
    
    return JSONResponse(
        status_code=503,
        content={
            "error": "MVLM Required",
            "message": f"Agent {exc.agent_name} requires MVLM but it's unavailable",
            "agent": exc.agent_name,
            "reason": exc.reason
        }
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    
    return JSONResponse(
        status_code=401,
        content={
            "error": "Authentication Failed",
            "message": exc.reason,
            "details": exc.details
        }
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    
    return JSONResponse(
        status_code=403,
        content={
            "error": "Authorization Failed",
            "message": exc.reason,
            "details": exc.details
        }
    )


@app.exception_handler(SecurityValidationError)
async def security_validation_handler(request: Request, exc: SecurityValidationError):
    """Handle security validation errors."""
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Security Validation Failed",
            "validation_type": exc.validation_type,
            "details": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request Validation Failed",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle general HTTP exceptions."""
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with security logging."""
    
    await SecurityLogger.log_system_event(
        event_type="unexpected_exception",
        success=False,
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_path": str(request.url.path),
            "request_method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. The incident has been logged."
        }
    )


# Include API Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agent Pipeline"])  
app.include_router(health.router, prefix="/api/v1/health", tags=["Health & Monitoring"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Security Monitoring"])


# Root endpoint
@app.get("/", summary="API Root", description="Multi-Corpus Governance Agent API root endpoint")
async def root():
    """
    API root endpoint with system information.
    """
    return {
        "service": "Multi-Corpus Governance Agent API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "governance": "protocol-first",
        "security": "comprehensive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Development server function
def run_development_server():
    """
    Run the development server with hot reload.
    
    This function is used by development startup scripts.
    """
    uvicorn.run(
        "src.mcg_agent.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


# Production server function
def run_production_server():
    """
    Run the production server with optimized settings.
    
    This function is used by production startup scripts.
    """
    uvicorn.run(
        "src.mcg_agent.api.app:app",
        host="0.0.0.0", 
        port=8000,
        workers=4,
        log_level="warning",
        access_log=False,
        server_header=False
    )


if __name__ == "__main__":
    # Default to development server when run directly
    run_development_server()