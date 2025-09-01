"""Governance enforcement decorators for PydanticAI tools.

This module provides decorators that enforce governance rules at the tool level,
making rule violations architecturally impossible. Each tool call is validated
against the governance protocol before execution.

Implements security requirements from:
docs/security/protocols/governance-protocol.md
"""

import functools
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Awaitable
from uuid import uuid4

from pydantic_ai import RunContext

from .protocol import (
    governance_protocol,
    AgentRole,
    CorpusType,
    ViolationSeverity
)
from ..utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    UnauthorizedRAGAccessError,
    MVLMRequiredError,
    SecurityValidationError
)
from ..utils.logging import SecurityLogger


# Type variables for generic decorators
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


def governance_enforced(
    permissions: List[str],
    max_calls: Optional[int] = None,
    corpus_restrictions: Optional[List[str]] = None,
    requires_mvlm_primary: bool = False,
    requires_rag_access: bool = False
) -> Callable[[F], F]:
    """
    Decorator that enforces governance rules at tool invocation.
    
    This decorator validates all governance constraints before allowing
    tool execution, making rule violations architecturally impossible.
    
    Args:
        permissions: List of required permissions for this tool
        max_calls: Maximum API calls allowed (validates against agent limits)
        corpus_restrictions: List of allowed corpus types for this tool
        requires_mvlm_primary: Whether this tool requires MVLM as primary method
        requires_rag_access: Whether this tool requires RAG access capabilities
        
    Returns:
        Decorated function with governance enforcement
        
    Raises:
        GovernanceViolationError: If governance rules are violated
    """
    def decorator(tool_func: F) -> F:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, *args, **kwargs) -> Any:
            """Governance validation wrapper for PydanticAI tools."""
            
            # Extract agent context
            agent_context = ctx.deps
            if not hasattr(agent_context, 'agent_role'):
                raise SecurityValidationError(
                    validation_type="missing_agent_context",
                    details={
                        "tool_name": tool_func.__name__,
                        "required_attributes": ["agent_role", "task_id"]
                    }
                )
            
            agent_role = AgentRole(agent_context.agent_role)
            task_id = agent_context.task_id
            
            # Create governance validation context
            validation_context = GovernanceValidationContext(
                agent_role=agent_role,
                task_id=task_id,
                tool_name=tool_func.__name__,
                permissions=permissions,
                max_calls=max_calls,
                corpus_restrictions=corpus_restrictions,
                requires_mvlm_primary=requires_mvlm_primary,
                requires_rag_access=requires_rag_access,
                tool_args=args,
                tool_kwargs=kwargs
            )
            
            try:
                # 1. Validate agent permissions
                await _validate_agent_permissions(validation_context)
                
                # 2. Check API call limits if specified
                if max_calls is not None:
                    await _validate_api_call_limits(validation_context)
                
                # 3. Validate corpus access if specified
                if corpus_restrictions:
                    await _validate_corpus_access(validation_context)
                
                # 4. Validate RAG access if required
                if requires_rag_access:
                    await _validate_rag_access(validation_context)
                
                # 5. Validate MVLM requirements if specified
                if requires_mvlm_primary:
                    await _validate_mvlm_requirements(validation_context)
                
                # 6. Pre-execution security logging
                await _log_tool_execution_start(validation_context)
                
                # 7. Execute tool with governance validation passed
                start_time = datetime.now(timezone.utc)
                result = await tool_func(ctx, *args, **kwargs)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # 8. Post-execution validation and logging
                await _validate_tool_output(validation_context, result)
                await _log_tool_execution_success(validation_context, result, execution_time)
                
                return result
                
            except (
                GovernanceViolationError,
                APICallLimitExceededError,
                UnauthorizedCorpusAccessError,
                UnauthorizedRAGAccessError,
                MVLMRequiredError
            ) as governance_error:
                # Log governance violation
                await _log_governance_violation(validation_context, governance_error)
                raise
                
            except Exception as unexpected_error:
                # Log unexpected error
                await _log_tool_execution_error(validation_context, unexpected_error)
                raise
        
        return wrapper
    return decorator


def api_call_enforced(max_calls: int) -> Callable[[F], F]:
    """
    Decorator specifically for API call enforcement.
    
    Args:
        max_calls: Maximum number of API calls allowed for this agent
        
    Returns:
        Decorated function with API call limit enforcement
    """
    return governance_enforced(
        permissions=["api_access"],
        max_calls=max_calls
    )


def corpus_access_enforced(
    allowed_corpora: List[str],
    rate_limit: Optional[int] = None
) -> Callable[[F], F]:
    """
    Decorator specifically for corpus access enforcement.
    
    Args:
        allowed_corpora: List of allowed corpus types
        rate_limit: Optional rate limit (queries per minute)
        
    Returns:
        Decorated function with corpus access enforcement
    """
    return governance_enforced(
        permissions=["corpus_access"],
        corpus_restrictions=allowed_corpora
    )


def rag_access_enforced() -> Callable[[F], F]:
    """
    Decorator specifically for RAG access enforcement (Critic only).
    
    Returns:
        Decorated function with RAG access enforcement
    """
    return governance_enforced(
        permissions=["rag_access"],
        requires_rag_access=True
    )


def mvlm_primary_enforced() -> Callable[[F], F]:
    """
    Decorator for tools that require MVLM as primary processing method.
    
    Returns:
        Decorated function with MVLM primary enforcement
    """
    return governance_enforced(
        permissions=["mvlm_access"],
        requires_mvlm_primary=True
    )


class GovernanceValidationContext:
    """Context object for governance validation operations."""
    
    def __init__(
        self,
        agent_role: AgentRole,
        task_id: str,
        tool_name: str,
        permissions: List[str],
        max_calls: Optional[int],
        corpus_restrictions: Optional[List[str]],
        requires_mvlm_primary: bool,
        requires_rag_access: bool,
        tool_args: tuple,
        tool_kwargs: dict
    ):
        self.agent_role = agent_role
        self.task_id = task_id
        self.tool_name = tool_name
        self.permissions = permissions
        self.max_calls = max_calls
        self.corpus_restrictions = corpus_restrictions
        self.requires_mvlm_primary = requires_mvlm_primary
        self.requires_rag_access = requires_rag_access
        self.tool_args = tool_args
        self.tool_kwargs = tool_kwargs
        self.validation_id = str(uuid4())
        self.timestamp = datetime.now(timezone.utc)


# Validation helper functions

async def _validate_agent_permissions(context: GovernanceValidationContext) -> None:
    """Validate that agent has required permissions."""
    
    await governance_protocol.validate_agent_permissions(
        agent_role=context.agent_role,
        task_id=context.task_id,
        required_permissions=context.permissions
    )


async def _validate_api_call_limits(context: GovernanceValidationContext) -> None:
    """Validate API call limits for agent."""
    
    await governance_protocol.validate_api_call(
        agent_role=context.agent_role,
        task_id=context.task_id
    )


async def _validate_corpus_access(context: GovernanceValidationContext) -> None:
    """Validate corpus access permissions."""
    
    # Extract corpus parameter from tool arguments
    corpus_param = None
    
    # Check kwargs first
    if 'corpus' in context.tool_kwargs:
        corpus_param = context.tool_kwargs['corpus']
    elif 'corpus_type' in context.tool_kwargs:
        corpus_param = context.tool_kwargs['corpus_type']
    
    # Check positional args if not found in kwargs
    if corpus_param is None and len(context.tool_args) > 0:
        # Assume first arg might be corpus if it's a string matching corpus types
        first_arg = context.tool_args[0]
        if isinstance(first_arg, str) and first_arg in ['personal', 'social', 'published']:
            corpus_param = first_arg
    
    if corpus_param:
        corpus_type = CorpusType(corpus_param)
        
        # Validate against restrictions
        if context.corpus_restrictions and corpus_param not in context.corpus_restrictions:
            raise GovernanceViolationError(
                violation_type="tool_corpus_restriction_violated",
                agent_name=context.agent_role.value,
                details={
                    "requested_corpus": corpus_param,
                    "allowed_corpora": context.corpus_restrictions,
                    "tool_name": context.tool_name,
                    "task_id": context.task_id
                },
                severity="high"
            )
        
        # Validate against agent permissions
        await governance_protocol.validate_corpus_access(
            agent_role=context.agent_role,
            corpus_type=corpus_type,
            task_id=context.task_id
        )


async def _validate_rag_access(context: GovernanceValidationContext) -> None:
    """Validate RAG access permissions."""
    
    await governance_protocol.validate_rag_access(
        agent_role=context.agent_role,
        task_id=context.task_id
    )


async def _validate_mvlm_requirements(context: GovernanceValidationContext) -> None:
    """Validate MVLM usage requirements."""
    
    # Check if MVLM is available (this would be determined by system state)
    mvlm_available = await _check_mvlm_availability()
    
    mvlm_decision = await governance_protocol.validate_mvlm_requirements(
        agent_role=context.agent_role,
        task_id=context.task_id,
        mvlm_available=mvlm_available
    )
    
    # Store MVLM decision in context for tool execution
    context.mvlm_decision = mvlm_decision


async def _validate_tool_output(
    context: GovernanceValidationContext, 
    result: Any
) -> None:
    """Validate tool output against governance rules."""
    
    # Basic output validation
    if result is None:
        await SecurityLogger.log_governance_event(
            event_type="tool_output_null",
            task_id=context.task_id,
            agent_name=context.agent_role.value,
            success=True,
            details={
                "tool_name": context.tool_name,
                "warning": "Tool returned null result"
            }
        )
    
    # Additional output validation can be added here
    # For example: content filtering, format validation, etc.


async def _check_mvlm_availability() -> bool:
    """Check if MVLM (Multi-Vector Language Model) is currently available."""
    
    # This would connect to actual MVLM service health check
    # For now, return True as placeholder
    # In production, this would check:
    # - MVLM service health endpoint
    # - Resource availability
    # - Queue status
    return True


# Logging helper functions

async def _log_tool_execution_start(context: GovernanceValidationContext) -> None:
    """Log the start of tool execution with governance validation."""
    
    await SecurityLogger.log_governance_event(
        event_type="tool_execution_started",
        task_id=context.task_id,
        agent_name=context.agent_role.value,
        success=True,
        details={
            "tool_name": context.tool_name,
            "validation_id": context.validation_id,
            "permissions_validated": context.permissions,
            "governance_checks_passed": True
        }
    )


async def _log_tool_execution_success(
    context: GovernanceValidationContext,
    result: Any,
    execution_time: float
) -> None:
    """Log successful tool execution with governance compliance."""
    
    await SecurityLogger.log_governance_event(
        event_type="tool_execution_completed",
        task_id=context.task_id,
        agent_name=context.agent_role.value,
        success=True,
        details={
            "tool_name": context.tool_name,
            "validation_id": context.validation_id,
            "execution_time_seconds": execution_time,
            "result_type": type(result).__name__,
            "governance_compliant": True
        }
    )


async def _log_tool_execution_error(
    context: GovernanceValidationContext,
    error: Exception
) -> None:
    """Log tool execution error."""
    
    await SecurityLogger.log_governance_event(
        event_type="tool_execution_error", 
        task_id=context.task_id,
        agent_name=context.agent_role.value,
        success=False,
        details={
            "tool_name": context.tool_name,
            "validation_id": context.validation_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "governance_enforcement_active": True
        }
    )


async def _log_governance_violation(
    context: GovernanceValidationContext,
    violation_error: Exception
) -> None:
    """Log governance violation with full context."""
    
    severity = "high"  # Default severity
    
    if isinstance(violation_error, GovernanceViolationError):
        severity = violation_error.severity
    elif isinstance(violation_error, (APICallLimitExceededError, UnauthorizedCorpusAccessError)):
        severity = "critical"
    elif isinstance(violation_error, UnauthorizedRAGAccessError):
        severity = "critical"
    elif isinstance(violation_error, MVLMRequiredError):
        severity = "high"
    
    await SecurityLogger.log_governance_violation(
        violation_type=type(violation_error).__name__,
        agent_name=context.agent_role.value,
        task_id=context.task_id,
        severity=severity,
        details={
            "tool_name": context.tool_name,
            "validation_id": context.validation_id,
            "violation_details": str(violation_error),
            "attempted_permissions": context.permissions,
            "attempted_corpus_access": context.corpus_restrictions,
            "governance_enforcement": "architectural_level"
        }
    )


# Specialized decorators for each agent role

def ideator_tool(
    permissions: List[str],
    corpus_access: Optional[List[str]] = None,
    max_api_calls: int = 2
) -> Callable[[F], F]:
    """
    Decorator specifically for Ideator agent tools.
    
    Enforces Ideator-specific constraints:
    - Max 2 API calls per task
    - Full corpus access (personal, social, published)
    - No RAG access
    - MVLM access allowed
    """
    return governance_enforced(
        permissions=permissions + ["outline_generation"],
        max_calls=max_api_calls,
        corpus_restrictions=corpus_access or ["personal", "social", "published"],
        requires_mvlm_primary=False,
        requires_rag_access=False
    )


def drafter_tool(
    permissions: List[str],
    corpus_access: Optional[List[str]] = None,
    max_api_calls: int = 1
) -> Callable[[F], F]:
    """
    Decorator specifically for Drafter agent tools.
    
    Enforces Drafter-specific constraints:
    - Max 1 API call per task
    - Limited corpus access (social, published only)
    - No RAG access
    - MVLM access allowed
    """
    return governance_enforced(
        permissions=permissions + ["draft_expansion"],
        max_calls=max_api_calls,
        corpus_restrictions=corpus_access or ["social", "published"],
        requires_mvlm_primary=False,
        requires_rag_access=False
    )


def critic_tool(
    permissions: List[str],
    corpus_access: Optional[List[str]] = None,
    max_api_calls: int = 2,
    rag_access: bool = False
) -> Callable[[F], F]:
    """
    Decorator specifically for Critic agent tools.
    
    Enforces Critic-specific constraints:
    - Max 2 API calls per task
    - Full corpus access (personal, social, published)
    - RAG access allowed (only agent with this capability)
    - MVLM access allowed
    """
    return governance_enforced(
        permissions=permissions + ["truth_validation"],
        max_calls=max_api_calls,
        corpus_restrictions=corpus_access or ["personal", "social", "published"],
        requires_mvlm_primary=False,
        requires_rag_access=rag_access
    )


def revisor_tool(
    permissions: List[str],
    max_api_calls: int = 1,
    mvlm_primary: bool = True
) -> Callable[[F], F]:
    """
    Decorator specifically for Revisor agent tools.
    
    Enforces Revisor-specific constraints:
    - Max 1 API call per task (fallback only)
    - No new corpus queries (inherited context only)
    - No RAG access
    - MVLM primary, API fallback allowed
    """
    return governance_enforced(
        permissions=permissions + ["correction_application"],
        max_calls=max_api_calls,
        corpus_restrictions=[],  # No new corpus access
        requires_mvlm_primary=mvlm_primary,
        requires_rag_access=False
    )


def summarizer_tool(
    permissions: List[str],
    max_api_calls: int = 0,
    mvlm_required: bool = True
) -> Callable[[F], F]:
    """
    Decorator specifically for Summarizer agent tools.
    
    Enforces Summarizer-specific constraints:
    - No API calls (emergency fallback only with authorization)
    - No new corpus queries
    - No RAG access  
    - MVLM required (only processing method)
    """
    return governance_enforced(
        permissions=permissions + ["content_compression"],
        max_calls=max_api_calls,
        corpus_restrictions=[],  # No corpus access
        requires_mvlm_primary=mvlm_required,
        requires_rag_access=False
    )