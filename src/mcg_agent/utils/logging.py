"""Security and audit logging for Multi-Corpus Governance Agent.

This module provides comprehensive logging capabilities for security events,
governance violations, and audit trails as required by:
- docs/security/architecture/security-architecture.md
- docs/security/incident-response/incident-response-playbook.md
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import structlog
from pathlib import Path

from ..utils.exceptions import MCGBaseException


class LogLevel(Enum):
    """Log severity levels aligned with incident response playbook."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Security event types for monitoring and alerting."""
    GOVERNANCE_VALIDATION = "governance_validation"
    GOVERNANCE_VIOLATION = "governance_violation"
    TOOL_EXECUTION = "tool_execution"
    API_CALL = "api_call"
    CORPUS_ACCESS = "corpus_access"
    RAG_ACCESS = "rag_access"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SESSION_MANAGEMENT = "session_management"
    EMERGENCY_AUTHORIZATION = "emergency_authorization"
    SYSTEM_ERROR = "system_error"


class SecurityLogger:
    """
    Centralized security logging system providing immutable audit trails
    and real-time monitoring capabilities.
    """
    
    def __init__(self):
        """Initialize structured logging with security configuration."""
        # Configure structlog for security logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self._logger = structlog.get_logger("mcg_security")
        self._violation_count = 0
        self._lock = asyncio.Lock()
    
    async def log_governance_validation(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        validation_passed: bool,
        validation_time_ms: float,
        permissions_checked: List[str],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log governance validation attempt and result."""
        
        event = {
            "event_type": SecurityEventType.GOVERNANCE_VALIDATION.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "validation_passed": validation_passed,
            "validation_time_ms": validation_time_ms,
            "permissions_checked": permissions_checked,
            "log_level": LogLevel.INFO.value if validation_passed else LogLevel.WARNING.value
        }
        
        if additional_context:
            event["additional_context"] = additional_context
        
        await self._write_security_log(event)
    
    async def log_governance_violation(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        violation_type: str,
        violation_details: Dict[str, Any],
        validation_time_ms: float
    ) -> None:
        """Log governance rule violation with full context."""
        
        async with self._lock:
            self._violation_count += 1
            violation_id = f"VIOL-{datetime.utcnow().strftime('%Y%m%d')}-{self._violation_count:06d}"
        
        event = {
            "event_type": SecurityEventType.GOVERNANCE_VIOLATION.value,
            "violation_id": violation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "violation_type": violation_type,
            "violation_details": violation_details,
            "validation_time_ms": validation_time_ms,
            "log_level": LogLevel.ERROR.value,
            "requires_investigation": True
        }
        
        await self._write_security_log(event)
        
        # Trigger real-time monitoring alert for violations
        await self._trigger_security_alert(event)
    
    async def log_tool_execution(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        execution_time_ms: float,
        input_params: Dict[str, Any],
        output_hash: Optional[int],
        governance_validation_passed: bool,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log successful tool execution with attribution."""
        
        event = {
            "event_type": SecurityEventType.TOOL_EXECUTION.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "execution_time_ms": execution_time_ms,
            "input_params": input_params,
            "output_hash": output_hash,
            "governance_validation_passed": governance_validation_passed,
            "log_level": LogLevel.INFO.value
        }
        
        if additional_metadata:
            event["metadata"] = additional_metadata
        
        await self._write_security_log(event)
    
    async def log_api_call_start(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        call_type: str,
        current_call_count: int
    ) -> None:
        """Log API call initiation for governance tracking."""
        
        event = {
            "event_type": SecurityEventType.API_CALL.value,
            "event_subtype": "api_call_start",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "call_type": call_type,
            "current_call_count": current_call_count,
            "log_level": LogLevel.INFO.value
        }
        
        await self._write_security_log(event)
    
    async def log_api_call_success(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        call_type: str,
        result_hash: Optional[int]
    ) -> None:
        """Log successful API call completion."""
        
        event = {
            "event_type": SecurityEventType.API_CALL.value,
            "event_subtype": "api_call_success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "call_type": call_type,
            "result_hash": result_hash,
            "log_level": LogLevel.INFO.value
        }
        
        await self._write_security_log(event)
    
    async def log_api_call_failure(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        call_type: str,
        error_type: str,
        error_message: str
    ) -> None:
        """Log API call failure for investigation."""
        
        event = {
            "event_type": SecurityEventType.API_CALL.value,
            "event_subtype": "api_call_failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "call_type": call_type,
            "error_type": error_type,
            "error_message": error_message,
            "log_level": LogLevel.ERROR.value,
            "requires_investigation": True
        }
        
        await self._write_security_log(event)
    
    async def log_corpus_access(
        self,
        agent_role: str,
        corpus: str,
        task_id: str,
        query_hash: str,
        result_count: int,
        attribution_sources: List[Dict[str, Any]]
    ) -> None:
        """Log corpus access with attribution tracking."""
        
        event = {
            "event_type": SecurityEventType.CORPUS_ACCESS.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "corpus": corpus,
            "query_hash": query_hash,
            "result_count": result_count,
            "attribution_sources": attribution_sources,
            "log_level": LogLevel.INFO.value
        }
        
        await self._write_security_log(event)
    
    async def log_rag_access(
        self,
        agent_role: str,
        task_id: str,
        external_domains: List[str],
        query_hash: str,
        result_count: int
    ) -> None:
        """Log RAG/external search access (Critic only)."""
        
        event = {
            "event_type": SecurityEventType.RAG_ACCESS.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "external_domains": external_domains,
            "query_hash": query_hash,
            "result_count": result_count,
            "log_level": LogLevel.INFO.value
        }
        
        await self._write_security_log(event)
    
    async def log_authentication_event(
        self,
        event_subtype: str,
        user_id: Optional[str],
        ip_address: str,
        success: bool,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log authentication events."""
        
        event = {
            "event_type": SecurityEventType.AUTHENTICATION.value,
            "event_subtype": event_subtype,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
            "failure_reason": failure_reason,
            "log_level": LogLevel.INFO.value if success else LogLevel.WARNING.value
        }
        
        await self._write_security_log(event)
        
        # Alert on authentication failures
        if not success:
            await self._trigger_security_alert(event)
    
    async def log_emergency_authorization_granted(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        authorization_reason: Optional[str] = None
    ) -> None:
        """Log emergency authorization granted (high priority event)."""
        
        event = {
            "event_type": SecurityEventType.EMERGENCY_AUTHORIZATION.value,
            "event_subtype": "authorization_granted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "authorization_reason": authorization_reason,
            "log_level": LogLevel.WARNING.value,
            "requires_review": True
        }
        
        await self._write_security_log(event)
        await self._trigger_security_alert(event)
    
    async def log_emergency_authorization_denied(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str
    ) -> None:
        """Log emergency authorization denied."""
        
        event = {
            "event_type": SecurityEventType.EMERGENCY_AUTHORIZATION.value,
            "event_subtype": "authorization_denied",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "log_level": LogLevel.INFO.value
        }
        
        await self._write_security_log(event)
    
    async def log_tool_error(
        self,
        agent_role: str,
        tool_name: str,
        task_id: str,
        error_type: str,
        error_message: str
    ) -> None:
        """Log unexpected tool errors."""
        
        event = {
            "event_type": SecurityEventType.SYSTEM_ERROR.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "error_type": error_type,
            "error_message": error_message,
            "log_level": LogLevel.ERROR.value,
            "requires_investigation": True
        }
        
        await self._write_security_log(event)
    
    async def log_critical_failure(
        self,
        agent: str,
        task_id: str,
        failure_reasons: List[str],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log critical failures that terminate the pipeline."""
        
        event = {
            "event_type": SecurityEventType.SYSTEM_ERROR.value,
            "event_subtype": "critical_failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "agent": agent,
            "failure_reasons": failure_reasons,
            "pipeline_terminated": True,
            "log_level": LogLevel.CRITICAL.value,
            "requires_immediate_attention": True
        }
        
        if additional_context:
            event["additional_context"] = additional_context
        
        await self._write_security_log(event)
        await self._trigger_critical_alert(event)
    
    async def _write_security_log(self, event: Dict[str, Any]) -> None:
        """Write security event to structured log with immutable formatting."""
        
        # Add consistent metadata
        event.update({
            "log_version": "1.0",
            "system": "mcg-agent",
            "environment": "production",  # Should come from config
            "log_hash": hash(json.dumps(event, sort_keys=True))
        })
        
        # Write to structured logger
        log_level = event.get("log_level", LogLevel.INFO.value)
        
        if log_level == LogLevel.CRITICAL.value:
            self._logger.critical("Security Event", **event)
        elif log_level == LogLevel.ERROR.value:
            self._logger.error("Security Event", **event)
        elif log_level == LogLevel.WARNING.value:
            self._logger.warning("Security Event", **event)
        else:
            self._logger.info("Security Event", **event)
    
    async def _trigger_security_alert(self, event: Dict[str, Any]) -> None:
        """Trigger real-time security alert for monitoring systems."""
        # In production, this would integrate with alerting systems
        # (PagerDuty, Slack, email, etc.)
        
        if event.get("log_level") in [LogLevel.ERROR.value, LogLevel.CRITICAL.value]:
            # High priority alert
            print(f"🚨 SECURITY ALERT: {event.get('event_type')} - {event.get('violation_type', 'Unknown')}")
        elif event.get("log_level") == LogLevel.WARNING.value:
            # Medium priority alert  
            print(f"⚠️ Security Warning: {event.get('event_type')} - {event.get('event_subtype', 'Unknown')}")
    
    async def _trigger_critical_alert(self, event: Dict[str, Any]) -> None:
        """Trigger critical alert requiring immediate response."""
        # In production, this would trigger P0 incident response
        print(f"🔴 CRITICAL SECURITY INCIDENT: {event.get('event_subtype')} in task {event.get('task_id')}")
        print(f"Failure reasons: {event.get('failure_reasons')}")
        
        # Would also:
        # - Create incident ticket
        # - Page on-call team
        # - Trigger automated containment
    
    @classmethod
    async def get_violation_summary(
        cls,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary of violations in time window for monitoring."""
        # In production, this would query the log aggregation system
        return {
            "time_window_hours": time_window_hours,
            "total_violations": 0,  # Would be populated from actual logs
            "violation_types": {},
            "affected_agents": {},
            "trends": "stable"  # Would include trend analysis
        }


# Global security logger instance
SecurityLogger = SecurityLogger()