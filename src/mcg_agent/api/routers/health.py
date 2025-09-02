"""Health check and system monitoring endpoints.

This module provides comprehensive health monitoring for all system components:
- Database connectivity and performance
- Redis session manager health
- System resource monitoring
- Service dependency status
- Security system health
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import asyncio
import psutil
import platform

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import get_current_user, require_permissions
from ..session_manager import session_manager
from ...database.session import db_manager
from ...utils.logging import SecurityLogger

# Create router
router = APIRouter()


# Pydantic models

class HealthStatus(BaseModel):
    """Health status model."""
    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    message: str = Field(..., description="Status description")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class ComponentHealth(BaseModel):
    """Individual component health model."""
    component: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = Field(None, description="Component-specific details")


class SystemHealth(BaseModel):
    """Complete system health model."""
    overall_status: str = Field(..., description="Overall system health")
    components: List[ComponentHealth] = Field(..., description="Individual component health")
    system_info: Dict[str, Any] = Field(..., description="System information")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SystemMetrics(BaseModel):
    """System performance metrics model."""
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_percent: float = Field(..., description="Memory usage percentage") 
    disk_usage_percent: float = Field(..., description="Disk usage percentage")
    active_connections: int = Field(..., description="Active network connections")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    load_average: Optional[List[float]] = Field(None, description="System load average")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Health check endpoints

@router.get(
    "/",
    response_model=HealthStatus,
    summary="Basic Health Check",
    description="Basic health check endpoint for load balancers and monitoring"
)
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint.
    
    Returns overall system health status for external monitoring systems.
    This endpoint is lightweight and suitable for frequent polling.
    """
    
    try:
        # Quick database connectivity check
        db_healthy = await _quick_database_check()
        
        # Quick Redis connectivity check  
        redis_healthy = await _quick_redis_check()
        
        if db_healthy and redis_healthy:
            status_value = "healthy"
            message = "All core systems operational"
        elif db_healthy or redis_healthy:
            status_value = "degraded"
            message = "Some systems experiencing issues"
        else:
            status_value = "unhealthy"
            message = "Critical systems unavailable"
        
        return HealthStatus(
            status=status_value,
            message=message,
            details={
                "database": "healthy" if db_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy"
            }
        )
        
    except Exception as e:
        return HealthStatus(
            status="unhealthy",
            message=f"Health check failed: {str(e)}"
        )


@router.get(
    "/detailed",
    response_model=SystemHealth,
    summary="Detailed Health Check",
    description="Comprehensive health check with component details"
)
async def detailed_health_check(
    current_user: Dict[str, Any] = Depends(require_permissions(["system_monitoring"]))
) -> SystemHealth:
    """
    Comprehensive health check with detailed component status.
    
    Requires system monitoring permissions. Returns detailed information
    about all system components and their current health status.
    """
    
    components = []
    
    try:
        # Database health check
        db_component = await _detailed_database_check()
        components.append(db_component)
        
        # Redis health check
        redis_component = await _detailed_redis_check()
        components.append(redis_component)
        
        # Security system health check
        security_component = await _security_system_check()
        components.append(security_component)
        
        # Governance system health check
        governance_component = await _governance_system_check()
        components.append(governance_component)
        
        # Determine overall status
        component_statuses = [comp.status for comp in components]
        if all(status == "healthy" for status in component_statuses):
            overall_status = "healthy"
        elif any(status == "healthy" for status in component_statuses):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        # Collect system information
        system_info = await _get_system_info()
        
        return SystemHealth(
            overall_status=overall_status,
            components=components,
            system_info=system_info
        )
        
    except Exception as e:
        # Return error component if detailed check fails
        error_component = ComponentHealth(
            component="system",
            status="unhealthy",
            details={"error": str(e)}
        )
        
        return SystemHealth(
            overall_status="unhealthy",
            components=[error_component],
            system_info={"error": "Failed to collect system information"}
        )


@router.get(
    "/metrics", 
    response_model=SystemMetrics,
    summary="System Metrics",
    description="System performance metrics and resource usage"
)
async def system_metrics(
    current_user: Dict[str, Any] = Depends(require_permissions(["system_monitoring"]))
) -> SystemMetrics:
    """
    Get current system performance metrics.
    
    Returns CPU, memory, disk usage and other system metrics.
    Requires system monitoring permissions.
    """
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage (root filesystem)
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Network connections
        connections = len(psutil.net_connections())
        
        # System uptime
        boot_time = psutil.boot_time()
        uptime = datetime.now().timestamp() - boot_time
        
        # Load average (Unix-like systems)
        load_avg = None
        try:
            load_avg = list(psutil.getloadavg())
        except AttributeError:
            # Windows doesn't have load average
            pass
        
        return SystemMetrics(
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory_percent,
            disk_usage_percent=disk_percent,
            active_connections=connections,
            uptime_seconds=uptime,
            load_average=load_avg
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect system metrics: {str(e)}"
        )


@router.get(
    "/readiness",
    response_model=HealthStatus,
    summary="Readiness Check",
    description="Check if system is ready to accept traffic"
)
async def readiness_check() -> HealthStatus:
    """
    Readiness check for Kubernetes and container orchestration.
    
    Verifies that all required services are available and the system
    is ready to handle requests.
    """
    
    try:
        # Check database readiness
        db_ready = await _database_readiness_check()
        
        # Check Redis readiness
        redis_ready = await _redis_readiness_check()
        
        # Check governance system readiness
        governance_ready = await _governance_readiness_check()
        
        if db_ready and redis_ready and governance_ready:
            return HealthStatus(
                status="ready",
                message="System is ready to accept traffic",
                details={
                    "database": "ready",
                    "redis": "ready", 
                    "governance": "ready"
                }
            )
        else:
            return HealthStatus(
                status="not_ready",
                message="System is not ready to accept traffic",
                details={
                    "database": "ready" if db_ready else "not_ready",
                    "redis": "ready" if redis_ready else "not_ready",
                    "governance": "ready" if governance_ready else "not_ready"
                }
            )
            
    except Exception as e:
        return HealthStatus(
            status="not_ready",
            message=f"Readiness check failed: {str(e)}"
        )


@router.get(
    "/liveness", 
    response_model=HealthStatus,
    summary="Liveness Check",
    description="Check if system is alive and responsive"
)
async def liveness_check() -> HealthStatus:
    """
    Liveness check for Kubernetes and container orchestration.
    
    Simple check to verify the application is running and responsive.
    If this fails, the container should be restarted.
    """
    
    try:
        # Basic application liveness check
        current_time = datetime.now(timezone.utc)
        
        return HealthStatus(
            status="alive",
            message="System is alive and responsive",
            timestamp=current_time,
            details={"process_id": psutil.Process().pid}
        )
        
    except Exception as e:
        return HealthStatus(
            status="dead",
            message=f"Liveness check failed: {str(e)}"
        )


# Helper functions for health checks

async def _quick_database_check() -> bool:
    """Quick database connectivity check."""
    try:
        async with db_manager.get_session() as session:
            # Simple query to test connectivity
            result = await session.execute("SELECT 1")
            return result is not None
    except Exception:
        return False


async def _quick_redis_check() -> bool:
    """Quick Redis connectivity check."""
    try:
        health_info = await session_manager.health_check()
        return health_info["status"] == "healthy"
    except Exception:
        return False


async def _detailed_database_check() -> ComponentHealth:
    """Detailed database health check."""
    try:
        start_time = datetime.now(timezone.utc)
        
        async with db_manager.get_session() as session:
            # Test query
            await session.execute("SELECT 1")
            
            # Get database info
            db_info = await session.execute("""
                SELECT 
                    version() as version,
                    current_database() as database,
                    current_user as user
            """)
            result = db_info.fetchone()
            
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return ComponentHealth(
            component="database",
            status="healthy",
            response_time_ms=response_time,
            details={
                "version": result[0] if result else "unknown",
                "database": result[1] if result else "unknown",
                "user": result[2] if result else "unknown"
            }
        )
        
    except Exception as e:
        return ComponentHealth(
            component="database",
            status="unhealthy",
            details={"error": str(e)}
        )


async def _detailed_redis_check() -> ComponentHealth:
    """Detailed Redis health check."""
    try:
        start_time = datetime.now(timezone.utc)
        health_info = await session_manager.health_check()
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        if health_info["status"] == "healthy":
            return ComponentHealth(
                component="redis",
                status="healthy",
                response_time_ms=response_time,
                details=health_info
            )
        else:
            return ComponentHealth(
                component="redis",
                status="unhealthy",
                details=health_info
            )
            
    except Exception as e:
        return ComponentHealth(
            component="redis",
            status="unhealthy",
            details={"error": str(e)}
        )


async def _security_system_check() -> ComponentHealth:
    """Security system health check."""
    try:
        # Test security logging system
        start_time = datetime.now(timezone.utc)
        
        await SecurityLogger.log_system_event(
            event_type="health_check",
            success=True,
            details={"check_type": "security_system"}
        )
        
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return ComponentHealth(
            component="security",
            status="healthy",
            response_time_ms=response_time,
            details={"logging": "operational"}
        )
        
    except Exception as e:
        return ComponentHealth(
            component="security",
            status="unhealthy",
            details={"error": str(e)}
        )


async def _governance_system_check() -> ComponentHealth:
    """Governance system health check."""
    try:
        from ...governance.protocol import governance_protocol
        
        start_time = datetime.now(timezone.utc)
        
        # Test governance protocol
        test_task_id = "health_check_task"
        task_state = await governance_protocol.initialize_task_governance(
            task_id=test_task_id,
            user_id="health_check_user",
            classification="test"
        )
        
        # Clean up test task
        await governance_protocol.finalize_task_governance(test_task_id)
        
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return ComponentHealth(
            component="governance",
            status="healthy",
            response_time_ms=response_time,
            details={"protocol": "operational"}
        )
        
    except Exception as e:
        return ComponentHealth(
            component="governance",
            status="unhealthy",
            details={"error": str(e)}
        )


async def _get_system_info() -> Dict[str, Any]:
    """Collect system information."""
    try:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "hostname": platform.node(),
            "process_id": psutil.Process().pid,
            "process_threads": psutil.Process().num_threads(),
            "system_time": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to collect system info: {str(e)}"}


async def _database_readiness_check() -> bool:
    """Check if database is ready for operations."""
    try:
        async with db_manager.get_session() as session:
            # Test basic operations
            await session.execute("SELECT 1")
            
            # Check if required tables exist
            tables_check = await session.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('users', 'security_events')
            """)
            
            table_count = tables_check.scalar()
            return table_count >= 2  # At least users and security_events tables
            
    except Exception:
        return False


async def _redis_readiness_check() -> bool:
    """Check if Redis is ready for session management."""
    try:
        # Test Redis operations
        test_key = "readiness_check"
        test_value = "ready"
        
        # This would need to be implemented in session_manager
        # For now, use the health check
        health_info = await session_manager.health_check()
        return health_info["status"] == "healthy"
        
    except Exception:
        return False


async def _governance_readiness_check() -> bool:
    """Check if governance system is ready."""
    try:
        from ...governance.protocol import GovernanceProtocol
        
        # Verify governance protocol is properly initialized
        protocol = GovernanceProtocol()
        
        # Check that all agent roles have permissions defined
        required_roles = ["ideator", "drafter", "critic", "revisor", "summarizer"]
        
        for role_name in required_roles:
            from ...governance.protocol import AgentRole
            role = AgentRole(role_name)
            if role not in protocol.AGENT_PERMISSIONS:
                return False
        
        return True
        
    except Exception:
        return False