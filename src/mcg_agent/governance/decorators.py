"""Governance enforcement decorators for PydanticAI tools.

This module provides decorators that enforce governance rules at the tool level,
implementing the protocol enforcement patterns from:
docs/security/protocols/governance-protocol.md
"""

import functools
import asyncio
from typing import List, Optional, Callable, Any, Dict
from datetime import datetime

from pydantic_ai import RunContext

from .protocol import governance_protocol
from ..utils.exceptions import GovernanceViolationError
from ..utils.logging import SecurityLogger


def governance_enforced(
    permissions: List[str],
    max_calls: Optional[int] = None,
    corpus_restrictions: Optional[List[str]] = None,
    requires_mvlm_primary: bool = False,
    requires_rag_access: bool = False
):
    """
    Decorator that enforces governance rules at tool invocation.
    
    This decorator implements runtime governance validation per:
    docs/security/protocols/governance-protocol.md
    
    Args:
        permissions: List of required permissions for this tool
        max_calls: Maximum API calls allowed (overrides agent default)
        corpus_restrictions: List of corpora this tool can access
        requires_mvlm_primary: Tool prefers MVLM over API
        requires_rag_access: Tool requires RAG access
        
    Raises:
        GovernanceViolationError: When governance rules are violated
        APICallLimitExceededError: When API call limits exceeded
        UnauthorizedCorpusAccessError: When corpus access unauthorized
        UnauthorizedRAGAccessError: When RAG access unauthorized
    """
    def decorator(tool_func: Callable) -> Callable:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, *args, **kwargs) -> Any:
            # Extract agent context from RunContext
            agent_context = ctx.deps
            agent_name = agent_context.agent_role
            task_id = agent_context.task_id
            
            validation_start = datetime.utcnow()
            
            try:
                # 1. Validate agent permissions against protocol
                await governance_protocol.validate_agent_permissions(
                    agent_name=agent_name,
                    required_permissions=permissions,
                    task_id=task_id
                )
                
                # 2. Check API call limits if this tool makes API calls
                if 'api_access' in permissions:
                    await governance_protocol.validate_api_call(
                        agent_name=agent_name,
                        task_id=task_id
                    )
                
                # 3. Validate corpus access if applicable
                if corpus_restrictions:
                    for corpus in corpus_restrictions:
                        await governance_protocol.validate_corpus_access(
                            agent_name=agent_name,
                            corpus=corpus,
                            task_id=task_id
                        )
                
                # 4. Validate RAG access if required
                if requires_rag_access:
                    await governance_protocol.validate_rag_access(
                        agent_name=agent_name,
                        task_id=task_id
                    )
                
                # 5. MVLM preference check
                if requires_mvlm_primary:
                    mvlm_available = await _check_mvlm_availability()
                    await governance_protocol.validate_mvlm_preference(
                        agent_name=agent_name,
                        task_id=task_id,
                        mvlm_available=mvlm_available
                    )
                
                # Record successful validation
                validation_time = (datetime.utcnow() - validation_start).total_seconds() * 1000
                await SecurityLogger.log_governance_validation(
                    agent_role=agent_name,
                    tool_name=tool_func.__name__,
                    task_id=task_id,
                    validation_passed=True,
                    validation_time_ms=validation_time,
                    permissions_checked=permissions
                )
                
                # 6. Execute the tool function
                execution_start = datetime.utcnow()
                result = await tool_func(ctx, *args, **kwargs)
                execution_time = (datetime.utcnow() - execution_start).total_seconds() * 1000
                
                # 7. Log successful execution with attribution
                await SecurityLogger.log_tool_execution(
                    agent_role=agent_name,
                    tool_name=tool_func.__name__,
                    task_id=task_id,
                    execution_time_ms=execution_time,
                    input_params=_sanitize_params(kwargs),
                    output_hash=hash(str(result)) if result else None,
                    governance_validation_passed=True
                )
                
                return result
                
            except GovernanceViolationError as e:
                # Log governance violation
                validation_time = (datetime.utcnow() - validation_start).total_seconds() * 1000
                await SecurityLogger.log_governance_violation(
                    agent_role=agent_name,
                    tool_name=tool_func.__name__,
                    task_id=task_id,
                    violation_type=e.violation_type,
                    violation_details=e.details,
                    validation_time_ms=validation_time
                )
                
                # Re-raise to trigger upstream handling
                raise
                
            except Exception as e:
                # Log unexpected errors
                await SecurityLogger.log_tool_error(
                    agent_role=agent_name,
                    tool_name=tool_func.__name__,
                    task_id=task_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
                
        return wrapper
    return decorator


def corpus_access_enforced(allowed_corpora: List[str]):
    """
    Decorator specifically for corpus access validation.
    
    Args:
        allowed_corpora: List of corpus names this tool can access
    """
    def decorator(tool_func: Callable) -> Callable:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, corpus: str, *args, **kwargs) -> Any:
            agent_context = ctx.deps
            
            # Validate the specific corpus being accessed
            await governance_protocol.validate_corpus_access(
                agent_name=agent_context.agent_role,
                corpus=corpus,
                task_id=agent_context.task_id
            )
            
            # Additional check against allowed corpora for this tool
            if corpus not in allowed_corpora:
                raise GovernanceViolationError(
                    violation_type="tool_corpus_restriction_violated",
                    agent_name=agent_context.agent_role,
                    details={
                        "tool": tool_func.__name__,
                        "requested_corpus": corpus,
                        "allowed_corpora": allowed_corpora,
                        "task_id": agent_context.task_id
                    }
                )
            
            return await tool_func(ctx, corpus, *args, **kwargs)
            
        return wrapper
    return decorator


def api_call_tracked(call_type: str = "standard"):
    """
    Decorator to track API calls for governance compliance.
    
    Args:
        call_type: Type of API call ("standard", "fallback", "emergency")
    """
    def decorator(tool_func: Callable) -> Callable:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, *args, **kwargs) -> Any:
            agent_context = ctx.deps
            
            # Validate API call is allowed
            await governance_protocol.validate_api_call(
                agent_name=agent_context.agent_role,
                task_id=agent_context.task_id
            )
            
            # Log API call initiation
            await SecurityLogger.log_api_call_start(
                agent_role=agent_context.agent_role,
                tool_name=tool_func.__name__,
                task_id=agent_context.task_id,
                call_type=call_type,
                current_call_count=await governance_protocol.get_api_call_count(
                    agent_context.agent_role, 
                    agent_context.task_id
                )
            )
            
            try:
                result = await tool_func(ctx, *args, **kwargs)
                
                # Log successful API call
                await SecurityLogger.log_api_call_success(
                    agent_role=agent_context.agent_role,
                    tool_name=tool_func.__name__,
                    task_id=agent_context.task_id,
                    call_type=call_type,
                    result_hash=hash(str(result)) if result else None
                )
                
                return result
                
            except Exception as e:
                # Log API call failure
                await SecurityLogger.log_api_call_failure(
                    agent_role=agent_context.agent_role,
                    tool_name=tool_func.__name__,
                    task_id=agent_context.task_id,
                    call_type=call_type,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
                
        return wrapper
    return decorator


def mvlm_preferred(fallback_allowed: bool = True):
    """
    Decorator for tools that should prefer MVLM over API.
    
    Args:
        fallback_allowed: Whether API fallback is permitted if MVLM fails
    """
    def decorator(tool_func: Callable) -> Callable:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, *args, **kwargs) -> Any:
            agent_context = ctx.deps
            
            # Check MVLM availability first
            mvlm_available = await _check_mvlm_availability()
            
            if not mvlm_available and not fallback_allowed:
                raise GovernanceViolationError(
                    violation_type="mvlm_required_unavailable",
                    agent_name=agent_context.agent_role,
                    details={
                        "tool": tool_func.__name__,
                        "task_id": agent_context.task_id,
                        "fallback_allowed": fallback_allowed
                    }
                )
            
            # Validate MVLM preference compliance
            await governance_protocol.validate_mvlm_preference(
                agent_name=agent_context.agent_role,
                task_id=agent_context.task_id,
                mvlm_available=mvlm_available
            )
            
            return await tool_func(ctx, *args, **kwargs)
            
        return wrapper
    return decorator


def emergency_authorization_required():
    """
    Decorator for tools requiring emergency authorization.
    Used primarily for Summarizer API fallback.
    """
    def decorator(tool_func: Callable) -> Callable:
        @functools.wraps(tool_func)
        async def wrapper(ctx: RunContext, *args, **kwargs) -> Any:
            agent_context = ctx.deps
            
            # Check emergency authorization
            can_proceed = await governance_protocol.can_fallback_to_api(
                agent_name=agent_context.agent_role,
                task_id=agent_context.task_id
            )
            
            if not can_proceed:
                await SecurityLogger.log_emergency_authorization_denied(
                    agent_role=agent_context.agent_role,
                    tool_name=tool_func.__name__,
                    task_id=agent_context.task_id
                )
                
                raise GovernanceViolationError(
                    violation_type="emergency_authorization_required",
                    agent_name=agent_context.agent_role,
                    details={
                        "tool": tool_func.__name__,
                        "task_id": agent_context.task_id,
                        "requires_manual_approval": True
                    }
                )
            
            # Log emergency authorization granted
            await SecurityLogger.log_emergency_authorization_granted(
                agent_role=agent_context.agent_role,
                tool_name=tool_func.__name__,
                task_id=agent_context.task_id
            )
            
            return await tool_func(ctx, *args, **kwargs)
            
        return wrapper
    return decorator


async def _check_mvlm_availability() -> bool:
    """Check if MVLM is available for processing."""
    # In production, this would check MVLM service health
    # For now, assume MVLM is available
    return True


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize parameters for logging (remove sensitive data)."""
    sanitized = {}
    
    for key, value in params.items():
        if key.lower() in ['password', 'token', 'secret', 'key', 'auth']:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 1000:
            sanitized[key] = f"[TRUNCATED:{len(value)} chars]"
        else:
            sanitized[key] = str(value)[:500]  # Limit string length
    
    return sanitized