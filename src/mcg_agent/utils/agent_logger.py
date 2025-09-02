"""
Agent-specific logging system for Multi-Corpus Governance Agent.

This module extends the security logging system with agent-specific logging
capabilities for detailed debugging, performance monitoring, and compliance
tracking during agent execution.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from contextlib import asynccontextmanager
import structlog

from .logging import SecurityLogger, LogLevel
from .exceptions import MCGBaseException


class AgentLogLevel(Enum):
    """Agent-specific log levels for detailed debugging."""
    TRACE = "trace"          # Ultra-detailed execution tracing
    DEBUG = "debug"          # Debug information
    INFO = "info"            # General information
    PERFORMANCE = "performance"  # Performance metrics
    GOVERNANCE = "governance"    # Governance-related events
    WARNING = "warning"      # Warning conditions
    ERROR = "error"          # Error conditions
    CRITICAL = "critical"    # Critical failures


class AgentEventType(Enum):
    """Agent execution event types."""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    
    TOOL_EXECUTION_STARTED = "tool_execution_started"
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    
    API_CALL_INITIATED = "api_call_initiated"
    API_CALL_COMPLETED = "api_call_completed"
    API_CALL_FAILED = "api_call_failed"
    
    CORPUS_QUERY_STARTED = "corpus_query_started"
    CORPUS_QUERY_COMPLETED = "corpus_query_completed"
    
    GOVERNANCE_CHECK = "governance_check"
    GOVERNANCE_VIOLATION = "governance_violation"
    
    PERFORMANCE_METRIC = "performance_metric"
    STATE_TRANSITION = "state_transition"
    
    INPUT_VALIDATION = "input_validation"
    OUTPUT_GENERATION = "output_generation"
    
    CONTEXT_ASSEMBLY = "context_assembly"
    ATTRIBUTION_TRACKING = "attribution_tracking"


class AgentLogger:
    """
    Comprehensive logging system for agent execution with performance monitoring,
    governance tracking, and detailed debugging capabilities.
    """
    
    def __init__(self, agent_name: str, task_id: str, user_id: str):
        """Initialize agent logger."""
        self.agent_name = agent_name
        self.task_id = task_id
        self.user_id = user_id
        self.session_id = str(uuid4())
        
        # Initialize structured logger
        self._logger = structlog.get_logger(f"mcg_agent.{agent_name.lower()}")
        
        # Performance tracking
        self._start_time = None
        self._timers = {}
        self._metrics = {}
        self._checkpoints = []
        
        # State tracking
        self._current_stage = None
        self._api_call_count = 0
        self._corpus_query_count = 0
        self._governance_checks = 0
        
        # Event buffer for batch logging
        self._event_buffer = []
        self._buffer_lock = asyncio.Lock()
        
    async def start_agent_execution(
        self,
        input_data: Dict[str, Any],
        configuration: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log agent execution start."""
        self._start_time = time.perf_counter()
        
        event = {
            "event_type": AgentEventType.AGENT_STARTED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "input_data_size": len(str(input_data)),
            "configuration": configuration or {},
            "log_level": AgentLogLevel.INFO.value
        }
        
        await self._log_agent_event(event)
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_started",
            task_id=self.task_id,
            user_id=self.user_id,
            success=True,
            details={"agent_name": self.agent_name, "session_id": self.session_id}
        )
    
    async def complete_agent_execution(
        self,
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log successful agent execution completion."""
        execution_time = (time.perf_counter() - self._start_time) * 1000 if self._start_time else 0
        
        event = {
            "event_type": AgentEventType.AGENT_COMPLETED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "execution_time_ms": execution_time,
            "output_data_size": len(str(output_data)),
            "api_calls_made": self._api_call_count,
            "corpus_queries_made": self._corpus_query_count,
            "governance_checks": self._governance_checks,
            "checkpoints_hit": len(self._checkpoints),
            "metadata": metadata or {},
            "performance_summary": self._get_performance_summary(),
            "log_level": AgentLogLevel.INFO.value
        }
        
        await self._log_agent_event(event)
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_completed",
            task_id=self.task_id,
            user_id=self.user_id,
            success=True,
            details={
                "agent_name": self.agent_name,
                "execution_time_ms": execution_time,
                "session_id": self.session_id
            }
        )
    
    async def fail_agent_execution(
        self,
        error: Exception,
        failure_stage: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log agent execution failure."""
        execution_time = (time.perf_counter() - self._start_time) * 1000 if self._start_time else 0
        
        event = {
            "event_type": AgentEventType.AGENT_FAILED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "execution_time_ms": execution_time,
            "failure_stage": failure_stage,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "api_calls_made": self._api_call_count,
            "corpus_queries_made": self._corpus_query_count,
            "governance_checks": self._governance_checks,
            "additional_context": additional_context or {},
            "log_level": AgentLogLevel.ERROR.value,
            "requires_investigation": True
        }
        
        await self._log_agent_event(event)
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_failed",
            task_id=self.task_id,
            user_id=self.user_id,
            success=False,
            details={
                "agent_name": self.agent_name,
                "error_type": type(error).__name__,
                "failure_stage": failure_stage,
                "session_id": self.session_id
            }
        )
    
    @asynccontextmanager
    async def log_tool_execution(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        expected_output_type: str = "unknown"
    ):
        """Context manager for logging tool execution."""
        start_time = time.perf_counter()
        tool_session_id = str(uuid4())
        
        # Log tool start
        await self._log_agent_event({
            "event_type": AgentEventType.TOOL_EXECUTION_STARTED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "tool_name": tool_name,
            "tool_session_id": tool_session_id,
            "input_params": input_params,
            "expected_output_type": expected_output_type,
            "log_level": AgentLogLevel.DEBUG.value
        })
        
        try:
            yield tool_session_id
            
            # Log successful completion
            execution_time = (time.perf_counter() - start_time) * 1000
            await self._log_agent_event({
                "event_type": AgentEventType.TOOL_EXECUTION_COMPLETED.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_name": self.agent_name,
                "task_id": self.task_id,
                "tool_name": tool_name,
                "tool_session_id": tool_session_id,
                "execution_time_ms": execution_time,
                "log_level": AgentLogLevel.DEBUG.value
            })
            
        except Exception as e:
            # Log failure
            execution_time = (time.perf_counter() - start_time) * 1000
            await self._log_agent_event({
                "event_type": AgentEventType.TOOL_EXECUTION_FAILED.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_name": self.agent_name,
                "task_id": self.task_id,
                "tool_name": tool_name,
                "tool_session_id": tool_session_id,
                "execution_time_ms": execution_time,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "log_level": AgentLogLevel.ERROR.value
            })
            raise
    
    async def log_api_call(
        self,
        provider: str,
        model: str,
        call_type: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost_estimate: Optional[float] = None
    ) -> None:
        """Log API call details."""
        self._api_call_count += 1
        
        event = {
            "event_type": AgentEventType.API_CALL_COMPLETED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "call_number": self._api_call_count,
            "provider": provider,
            "model": model,
            "call_type": call_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (input_tokens or 0) + (output_tokens or 0),
            "cost_estimate": cost_estimate,
            "log_level": AgentLogLevel.INFO.value
        }
        
        await self._log_agent_event(event)
    
    async def log_corpus_query(
        self,
        corpus_type: str,
        query: str,
        result_count: int,
        execution_time_ms: float,
        sources: List[str]
    ) -> None:
        """Log corpus query execution."""
        self._corpus_query_count += 1
        
        event = {
            "event_type": AgentEventType.CORPUS_QUERY_COMPLETED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "query_number": self._corpus_query_count,
            "corpus_type": corpus_type,
            "query_hash": hash(query),
            "result_count": result_count,
            "execution_time_ms": execution_time_ms,
            "sources": sources,
            "log_level": AgentLogLevel.DEBUG.value
        }
        
        await self._log_agent_event(event)
    
    async def log_governance_check(
        self,
        check_type: str,
        passed: bool,
        details: Dict[str, Any],
        validation_time_ms: float
    ) -> None:
        """Log governance validation check."""
        self._governance_checks += 1
        
        event = {
            "event_type": AgentEventType.GOVERNANCE_CHECK.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "check_number": self._governance_checks,
            "check_type": check_type,
            "validation_passed": passed,
            "validation_details": details,
            "validation_time_ms": validation_time_ms,
            "log_level": AgentLogLevel.GOVERNANCE.value if passed else AgentLogLevel.WARNING.value
        }
        
        await self._log_agent_event(event)
    
    async def log_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log performance metric."""
        event = {
            "event_type": AgentEventType.PERFORMANCE_METRIC.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "context": context or {},
            "log_level": AgentLogLevel.PERFORMANCE.value
        }
        
        self._metrics[metric_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._log_agent_event(event)
    
    async def log_checkpoint(
        self,
        checkpoint_name: str,
        state_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log execution checkpoint."""
        checkpoint_time = time.perf_counter()
        
        checkpoint = {
            "name": checkpoint_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_time_ms": (checkpoint_time - self._start_time) * 1000 if self._start_time else 0,
            "state_data": state_data or {}
        }
        
        self._checkpoints.append(checkpoint)
        
        event = {
            "event_type": AgentEventType.STATE_TRANSITION.value,
            "timestamp": checkpoint["timestamp"],
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "checkpoint_name": checkpoint_name,
            "elapsed_time_ms": checkpoint["elapsed_time_ms"],
            "checkpoint_number": len(self._checkpoints),
            "state_data": state_data or {},
            "log_level": AgentLogLevel.TRACE.value
        }
        
        await self._log_agent_event(event)
    
    def start_timer(self, timer_name: str) -> None:
        """Start a named timer."""
        self._timers[timer_name] = time.perf_counter()
    
    def stop_timer(self, timer_name: str) -> float:
        """Stop a named timer and return elapsed time in ms."""
        if timer_name not in self._timers:
            return 0.0
        
        elapsed = (time.perf_counter() - self._timers[timer_name]) * 1000
        del self._timers[timer_name]
        return elapsed
    
    async def trace(self, message: str, **kwargs) -> None:
        """Log trace-level message."""
        await self._log_message(AgentLogLevel.TRACE, message, **kwargs)
    
    async def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        await self._log_message(AgentLogLevel.DEBUG, message, **kwargs)
    
    async def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        await self._log_message(AgentLogLevel.INFO, message, **kwargs)
    
    async def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        await self._log_message(AgentLogLevel.WARNING, message, **kwargs)
    
    async def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        await self._log_message(AgentLogLevel.ERROR, message, **kwargs)
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            "execution_time_ms": (time.perf_counter() - self._start_time) * 1000 if self._start_time else 0,
            "api_calls": self._api_call_count,
            "corpus_queries": self._corpus_query_count,
            "governance_checks": self._governance_checks,
            "checkpoints": len(self._checkpoints),
            "metrics": self._metrics
        }
    
    async def _log_message(
        self,
        level: AgentLogLevel,
        message: str,
        **kwargs
    ) -> None:
        """Log a general message with agent context."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "message": message,
            "log_level": level.value,
            **kwargs
        }
        
        await self._log_agent_event(event)
    
    async def _log_agent_event(self, event: Dict[str, Any]) -> None:
        """Write agent event to structured log."""
        # Add consistent metadata
        event.update({
            "log_version": "1.0",
            "system": "mcg-agent",
            "subsystem": "agent_execution",
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "session_id": self.session_id
        })
        
        # Buffer events for performance
        async with self._buffer_lock:
            self._event_buffer.append(event)
            
            # Flush buffer if it gets too large or for high-priority events
            if (len(self._event_buffer) >= 10 or 
                event.get("log_level") in [AgentLogLevel.ERROR.value, AgentLogLevel.CRITICAL.value]):
                await self._flush_event_buffer()
    
    async def _flush_event_buffer(self) -> None:
        """Flush buffered events to log."""
        if not self._event_buffer:
            return
        
        events_to_log = self._event_buffer.copy()
        self._event_buffer.clear()
        
        for event in events_to_log:
            log_level = event.get("log_level", AgentLogLevel.INFO.value)
            
            if log_level == AgentLogLevel.CRITICAL.value:
                self._logger.critical("Agent Event", **event)
            elif log_level == AgentLogLevel.ERROR.value:
                self._logger.error("Agent Event", **event)
            elif log_level == AgentLogLevel.WARNING.value:
                self._logger.warning("Agent Event", **event)
            elif log_level in [AgentLogLevel.PERFORMANCE.value, AgentLogLevel.GOVERNANCE.value]:
                self._logger.info("Agent Event", **event)
            elif log_level == AgentLogLevel.TRACE.value:
                self._logger.debug("Agent Event", **event)
            else:
                self._logger.info("Agent Event", **event)
    
    async def flush_logs(self) -> None:
        """Manually flush any buffered logs."""
        async with self._buffer_lock:
            await self._flush_event_buffer()


def create_agent_logger(agent_name: str, task_id: str, user_id: str) -> AgentLogger:
    """Factory function to create agent logger."""
    return AgentLogger(agent_name, task_id, user_id)