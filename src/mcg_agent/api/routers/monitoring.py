"""Security monitoring and governance dashboard endpoints.

This module provides comprehensive monitoring capabilities for:
- Governance violation tracking and analysis
- Security event monitoring and alerting
- API call usage and performance metrics
- Real-time system security status
- Compliance reporting and audit trails

All endpoints require appropriate security monitoring permissions.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..auth import get_current_user, require_permissions, require_roles
from ...utils.logging import SecurityLogger
from ...database.session import db_manager
from ...governance.protocol import governance_protocol

# Create router
router = APIRouter()


# Pydantic models

class ViolationSeverity(str, Enum):
    """Governance violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"


class TimeRange(str, Enum):
    """Time range options for monitoring queries."""
    LAST_HOUR = "1h"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"


class GovernanceViolationSummary(BaseModel):
    """Governance violation summary model."""
    
    violation_type: str = Field(..., description="Type of governance violation")
    agent_role: str = Field(..., description="Agent role that caused violation")
    count: int = Field(..., description="Number of violations")
    severity: str = Field(..., description="Violation severity")
    last_occurrence: datetime = Field(..., description="Last occurrence timestamp")
    trend: str = Field(..., description="Violation trend (increasing, stable, decreasing)")


class SecurityEventSummary(BaseModel):
    """Security event summary model."""
    
    event_type: str = Field(..., description="Security event type")
    event_subtype: str = Field(..., description="Security event subtype")
    success_count: int = Field(..., description="Successful events")
    failure_count: int = Field(..., description="Failed events")
    unique_users: int = Field(..., description="Number of unique users involved")
    unique_ips: int = Field(..., description="Number of unique IP addresses")
    last_event: datetime = Field(..., description="Last event timestamp")


class APIUsageMetrics(BaseModel):
    """API usage metrics model."""
    
    agent_role: str = Field(..., description="Agent role")
    total_calls: int = Field(..., description="Total API calls")
    successful_calls: int = Field(..., description="Successful API calls")
    failed_calls: int = Field(..., description="Failed API calls")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost_cents: int = Field(..., description="Total estimated cost in cents")


class SystemSecurityStatus(BaseModel):
    """Overall system security status model."""
    
    overall_status: str = Field(..., description="Overall security status")
    active_incidents: int = Field(..., description="Number of active security incidents")
    recent_violations: int = Field(..., description="Governance violations in last 24h")
    failed_authentications: int = Field(..., description="Failed authentication attempts in last hour")
    suspicious_activities: int = Field(..., description="Suspicious activities detected")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Detailed breakdowns
    violation_breakdown: Dict[str, int] = Field(default_factory=dict, description="Violations by type")
    agent_violations: Dict[str, int] = Field(default_factory=dict, description="Violations by agent")
    security_alerts: List[str] = Field(default_factory=list, description="Active security alerts")


class ComplianceReport(BaseModel):
    """Compliance report model."""
    
    report_period: str = Field(..., description="Reporting period")
    governance_compliance_score: float = Field(..., ge=0, le=100, description="Governance compliance score")
    security_score: float = Field(..., ge=0, le=100, description="Security score")
    
    # Metrics
    total_tasks_executed: int = Field(..., description="Total tasks executed")
    compliant_tasks: int = Field(..., description="Fully compliant tasks")
    violation_rate: float = Field(..., description="Violation rate percentage")
    
    # Detailed findings
    agent_compliance: Dict[str, float] = Field(..., description="Compliance score by agent")
    violation_trends: Dict[str, List[int]] = Field(..., description="Violation trends over time")
    recommendations: List[str] = Field(..., description="Compliance improvement recommendations")


# Monitoring endpoints

@router.get(
    "/status",
    response_model=SystemSecurityStatus,
    summary="System Security Status",
    description="Get overall system security status and recent activity"
)
async def get_security_status(
    current_user: Dict[str, Any] = Depends(require_permissions(["security_monitoring"]))
) -> SystemSecurityStatus:
    """
    Get comprehensive system security status.
    
    Returns overall security posture including recent violations,
    incidents, and suspicious activities.
    """
    
    try:
        # Calculate time windows
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_1h = now - timedelta(hours=1)
        
        # Get governance violations in last 24h
        recent_violations = 0
        violation_breakdown = {}
        agent_violations = {}
        
        # Get security events
        failed_authentications = 0
        suspicious_activities = 0
        
        # This would query the actual database in production
        # For now, return mock data structure
        
        # Determine overall status
        overall_status = "healthy"
        security_alerts = []
        
        if recent_violations > 10:
            overall_status = "degraded"
            security_alerts.append("High number of governance violations detected")
        
        if failed_authentications > 50:
            overall_status = "degraded"
            security_alerts.append("Elevated authentication failures")
        
        if suspicious_activities > 5:
            overall_status = "critical"
            security_alerts.append("Suspicious activities require investigation")
        
        return SystemSecurityStatus(
            overall_status=overall_status,
            active_incidents=0,  # Would query incident_logs table
            recent_violations=recent_violations,
            failed_authentications=failed_authentications,
            suspicious_activities=suspicious_activities,
            violation_breakdown=violation_breakdown,
            agent_violations=agent_violations,
            security_alerts=security_alerts
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security status: {str(e)}"
        )


@router.get(
    "/violations",
    response_model=List[GovernanceViolationSummary],
    summary="Governance Violations",
    description="Get governance violation summary and trends"
)
async def get_governance_violations(
    time_range: TimeRange = Query(default=TimeRange.LAST_24H, description="Time range for violations"),
    severity: Optional[ViolationSeverity] = Query(default=None, description="Filter by violation severity"),
    agent_role: Optional[str] = Query(default=None, description="Filter by agent role"),
    current_user: Dict[str, Any] = Depends(require_permissions(["security_monitoring"]))
) -> List[GovernanceViolationSummary]:
    """
    Get governance violation summary with filtering options.
    
    Returns violations grouped by type with trend analysis.
    """
    
    try:
        # Calculate time window
        now = datetime.now(timezone.utc)
        time_deltas = {
            TimeRange.LAST_HOUR: timedelta(hours=1),
            TimeRange.LAST_24H: timedelta(hours=24),
            TimeRange.LAST_7D: timedelta(days=7),
            TimeRange.LAST_30D: timedelta(days=30)
        }
        
        since_time = now - time_deltas[time_range]
        
        # This would query governance_violation_logs table in production
        # For now, return mock data
        
        violations = [
            GovernanceViolationSummary(
                violation_type="api_call_limit_exceeded",
                agent_role="ideator",
                count=5,
                severity="high",
                last_occurrence=now - timedelta(hours=2),
                trend="stable"
            ),
            GovernanceViolationSummary(
                violation_type="unauthorized_corpus_access",
                agent_role="drafter",
                count=2,
                severity="critical", 
                last_occurrence=now - timedelta(hours=6),
                trend="decreasing"
            )
        ]
        
        # Apply filters
        if severity:
            violations = [v for v in violations if v.severity == severity.value]
        
        if agent_role:
            violations = [v for v in violations if v.agent_role == agent_role]
        
        return violations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get governance violations: {str(e)}"
        )


@router.get(
    "/security-events", 
    response_model=List[SecurityEventSummary],
    summary="Security Events",
    description="Get security event summary and analysis"
)
async def get_security_events(
    time_range: TimeRange = Query(default=TimeRange.LAST_24H, description="Time range for events"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    current_user: Dict[str, Any] = Depends(require_permissions(["security_monitoring"]))
) -> List[SecurityEventSummary]:
    """
    Get security event summary with filtering options.
    
    Returns security events grouped by type with success/failure counts.
    """
    
    try:
        # This would query security_events table in production
        # For now, return mock data
        
        events = [
            SecurityEventSummary(
                event_type="authentication",
                event_subtype="login_attempt", 
                success_count=145,
                failure_count=12,
                unique_users=45,
                unique_ips=38,
                last_event=datetime.now(timezone.utc) - timedelta(minutes=5)
            ),
            SecurityEventSummary(
                event_type="governance",
                event_subtype="tool_execution",
                success_count=238,
                failure_count=7,
                unique_users=12,
                unique_ips=8,
                last_event=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
        ]
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security events: {str(e)}"
        )


@router.get(
    "/api-usage",
    response_model=List[APIUsageMetrics], 
    summary="API Usage Metrics",
    description="Get API usage metrics by agent role"
)
async def get_api_usage_metrics(
    time_range: TimeRange = Query(default=TimeRange.LAST_24H, description="Time range for metrics"),
    current_user: Dict[str, Any] = Depends(require_permissions(["usage_monitoring"]))
) -> List[APIUsageMetrics]:
    """
    Get API usage metrics broken down by agent role.
    
    Returns call counts, latency, token usage, and cost estimates.
    """
    
    try:
        # This would query api_call_logs table in production
        # For now, return mock data
        
        usage_metrics = [
            APIUsageMetrics(
                agent_role="ideator",
                total_calls=156,
                successful_calls=152,
                failed_calls=4,
                avg_latency_ms=1250.5,
                total_tokens=45000,
                total_cost_cents=892
            ),
            APIUsageMetrics(
                agent_role="drafter", 
                total_calls=78,
                successful_calls=76,
                failed_calls=2,
                avg_latency_ms=980.3,
                total_tokens=23500,
                total_cost_cents=465
            ),
            APIUsageMetrics(
                agent_role="critic",
                total_calls=134,
                successful_calls=131,
                failed_calls=3,
                avg_latency_ms=1450.2,
                total_tokens=38900,
                total_cost_cents=723
            ),
            APIUsageMetrics(
                agent_role="revisor",
                total_calls=23,  # Mostly uses MVLM
                successful_calls=22,
                failed_calls=1,
                avg_latency_ms=850.1,
                total_tokens=5600,
                total_cost_cents=98
            ),
            APIUsageMetrics(
                agent_role="summarizer",
                total_calls=2,  # Emergency fallback only
                successful_calls=2,
                failed_calls=0,
                avg_latency_ms=720.5,
                total_tokens=450,
                total_cost_cents=8
            )
        ]
        
        return usage_metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API usage metrics: {str(e)}"
        )


@router.get(
    "/compliance",
    response_model=ComplianceReport,
    summary="Compliance Report",
    description="Generate compliance report for specified period"
)
async def get_compliance_report(
    time_range: TimeRange = Query(default=TimeRange.LAST_7D, description="Reporting period"),
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "compliance_officer"]))
) -> ComplianceReport:
    """
    Generate comprehensive compliance report.
    
    **Requires admin or compliance officer role.**
    
    Returns governance compliance metrics, violation analysis,
    and recommendations for improvement.
    """
    
    try:
        # This would perform comprehensive analysis in production
        # For now, return mock compliance report
        
        # Calculate compliance scores
        governance_compliance_score = 92.5
        security_score = 88.3
        
        # Task metrics
        total_tasks = 156
        compliant_tasks = 144
        violation_rate = ((total_tasks - compliant_tasks) / total_tasks) * 100
        
        # Agent compliance scores
        agent_compliance = {
            "ideator": 95.2,
            "drafter": 89.7,
            "critic": 96.8,
            "revisor": 91.3,
            "summarizer": 98.1
        }
        
        # Violation trends (last 7 days)
        violation_trends = {
            "api_limit_exceeded": [2, 1, 3, 0, 1, 2, 1],
            "unauthorized_access": [0, 1, 0, 0, 1, 0, 0],
            "rate_limit_exceeded": [1, 2, 1, 3, 2, 1, 2]
        }
        
        # Generate recommendations
        recommendations = []
        
        if governance_compliance_score < 95:
            recommendations.append("Review agent training for governance compliance")
        
        if violation_rate > 5:
            recommendations.append("Implement stricter pre-validation checks")
        
        if agent_compliance["drafter"] < 90:
            recommendations.append("Review Drafter agent corpus access patterns")
        
        return ComplianceReport(
            report_period=time_range.value,
            governance_compliance_score=governance_compliance_score,
            security_score=security_score,
            total_tasks_executed=total_tasks,
            compliant_tasks=compliant_tasks,
            violation_rate=violation_rate,
            agent_compliance=agent_compliance,
            violation_trends=violation_trends,
            recommendations=recommendations
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


# Real-time monitoring endpoints

@router.get(
    "/live/violations",
    summary="Live Violation Stream",
    description="Get recent governance violations (last 10 violations)"
)
async def get_live_violations(
    current_user: Dict[str, Any] = Depends(require_permissions(["security_monitoring"]))
) -> List[Dict[str, Any]]:
    """
    Get live stream of recent governance violations.
    
    Returns the most recent governance violations for real-time monitoring.
    """
    
    try:
        # This would query recent violations from governance_violation_logs
        # For now, return mock data
        
        recent_violations = [
            {
                "violation_id": "viol_001",
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "violation_type": "api_call_limit_exceeded",
                "agent_role": "ideator",
                "severity": "high",
                "task_id": "task_123",
                "user_id": "user_456"
            },
            {
                "violation_id": "viol_002", 
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
                "violation_type": "unauthorized_corpus_access",
                "agent_role": "drafter",
                "severity": "critical",
                "task_id": "task_124",
                "user_id": "user_789"
            }
        ]
        
        return recent_violations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live violations: {str(e)}"
        )


@router.get(
    "/live/metrics",
    summary="Live System Metrics",
    description="Get real-time system performance metrics"
)
async def get_live_metrics(
    current_user: Dict[str, Any] = Depends(require_permissions(["system_monitoring"]))
) -> Dict[str, Any]:
    """
    Get real-time system performance metrics.
    
    Returns current system load, active tasks, and performance indicators.
    """
    
    try:
        # Get current active tasks from governance protocol
        active_tasks_count = len(governance_protocol.active_tasks)
        
        # Mock additional metrics (would be real in production)
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_tasks": active_tasks_count,
            "tasks_per_minute": 4.2,
            "avg_response_time_ms": 1250.5,
            "error_rate_percent": 1.2,
            "governance_violations_per_hour": 0.8,
            "active_sessions": 23,
            "database_connections": 12,
            "redis_connections": 8
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live metrics: {str(e)}"
        )


# Alert management endpoints

@router.post(
    "/alerts/acknowledge/{alert_id}",
    summary="Acknowledge Security Alert",
    description="Acknowledge a security alert or incident"
)
async def acknowledge_alert(
    alert_id: str,
    current_user: Dict[str, Any] = Depends(require_permissions(["incident_response"]))
) -> Dict[str, str]:
    """
    Acknowledge a security alert or incident.
    
    Records acknowledgment and updates incident status.
    """
    
    try:
        # This would update the incident_logs table in production
        
        await SecurityLogger.log_system_event(
            event_type="alert_acknowledged",
            success=True,
            details={
                "alert_id": alert_id,
                "acknowledged_by": current_user["user_id"],
                "acknowledged_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "message": f"Alert {alert_id} acknowledged successfully",
            "acknowledged_by": current_user["username"],
            "acknowledged_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.get(
    "/dashboard",
    summary="Security Dashboard Data",
    description="Get comprehensive security dashboard data"
)
async def get_dashboard_data(
    current_user: Dict[str, Any] = Depends(require_permissions(["security_monitoring"]))
) -> Dict[str, Any]:
    """
    Get comprehensive security dashboard data.
    
    Returns all data needed for security monitoring dashboard.
    """
    
    try:
        # Combine multiple monitoring endpoints for dashboard
        
        security_status = await get_security_status(current_user)
        violations = await get_governance_violations(TimeRange.LAST_24H, None, None, current_user)
        api_usage = await get_api_usage_metrics(TimeRange.LAST_24H, current_user)
        live_metrics = await get_live_metrics(current_user)
        
        dashboard_data = {
            "security_status": security_status.dict(),
            "recent_violations": [v.dict() for v in violations[:5]],  # Top 5 violations
            "api_usage_summary": [usage.dict() for usage in api_usage],
            "live_metrics": live_metrics,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )