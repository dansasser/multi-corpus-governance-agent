"""Core Governance Protocol Engine for Multi-Corpus Governance Agent.

This module implements the exact governance rules specified in:
docs/security/protocols/governance-protocol.md

The governance engine enforces agent constraints at the architectural level,
making rule violations impossible through runtime validation and tool-level
security enforcement.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    UnauthorizedRAGAccessError,
    MVLMRequiredError,
    SecurityValidationError
)
from ..utils.logging import SecurityLogger


class AgentRole(str, Enum):
    """Enumeration of agent roles in the governance system."""
    IDEATOR = "ideator"
    DRAFTER = "drafter" 
    CRITIC = "critic"
    REVISOR = "revisor"
    SUMMARIZER = "summarizer"


class CorpusType(str, Enum):
    """Enumeration of corpus types with access controls."""
    PERSONAL = "personal"
    SOCIAL = "social"
    PUBLISHED = "published"


class ViolationSeverity(str, Enum):
    """Severity levels for governance violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AgentPermissions:
    """Agent permissions as defined in governance protocol specification."""
    
    agent_role: AgentRole
    max_api_calls: int
    corpus_access: List[CorpusType]
    rag_access: bool
    mvlm_access: bool
    mvlm_preferred: bool = False
    mvlm_required: bool = False
    
    # Derived properties for validation
    can_access_personal: bool = False
    can_access_social: bool = False
    can_access_published: bool = False
    
    def __post_init__(self):
        """Set corpus access flags based on corpus_access list."""
        self.can_access_personal = CorpusType.PERSONAL in self.corpus_access
        self.can_access_social = CorpusType.SOCIAL in self.corpus_access
        self.can_access_published = CorpusType.PUBLISHED in self.corpus_access


class GovernanceProtocol:
    """
    Core governance protocol implementing exact rules from security documentation.
    
    Enforces agent permission matrix with runtime validation and prevents
    all governance rule violations through architectural constraints.
    """
    
    # Agent Permission Matrix - Exact implementation of governance protocol spec
    AGENT_PERMISSIONS: Dict[AgentRole, AgentPermissions] = {
        
        AgentRole.IDEATOR: AgentPermissions(
            agent_role=AgentRole.IDEATOR,
            max_api_calls=2,
            corpus_access=[CorpusType.PERSONAL, CorpusType.SOCIAL, CorpusType.PUBLISHED],
            rag_access=False,
            mvlm_access=True,
            mvlm_preferred=False,
            mvlm_required=False
        ),
        
        AgentRole.DRAFTER: AgentPermissions(
            agent_role=AgentRole.DRAFTER,
            max_api_calls=1,
            corpus_access=[CorpusType.SOCIAL, CorpusType.PUBLISHED],  # Limited access
            rag_access=False,
            mvlm_access=True,
            mvlm_preferred=False,
            mvlm_required=False
        ),
        
        AgentRole.CRITIC: AgentPermissions(
            agent_role=AgentRole.CRITIC,
            max_api_calls=2,
            corpus_access=[CorpusType.PERSONAL, CorpusType.SOCIAL, CorpusType.PUBLISHED],
            rag_access=True,  # ONLY agent with RAG access
            mvlm_access=True,
            mvlm_preferred=False,
            mvlm_required=False
        ),
        
        AgentRole.REVISOR: AgentPermissions(
            agent_role=AgentRole.REVISOR,
            max_api_calls=1,  # Fallback only when MVLM fails
            corpus_access=[],  # Inherited context only, no new queries
            rag_access=False,
            mvlm_access=True,
            mvlm_preferred=True,  # MVLM is primary processing method
            mvlm_required=False
        ),
        
        AgentRole.SUMMARIZER: AgentPermissions(
            agent_role=AgentRole.SUMMARIZER,
            max_api_calls=0,  # Emergency fallback only with authorization
            corpus_access=[],  # No new corpus queries allowed
            rag_access=False,
            mvlm_access=True,
            mvlm_preferred=True,
            mvlm_required=True  # MVLM ONLY, API fallback requires emergency auth
        )
    }
    
    # Rate limiting configuration
    CORPUS_QUERY_RATE_LIMITS = {
        CorpusType.PERSONAL: 10,  # 10 queries per minute
        CorpusType.SOCIAL: 15,    # 15 queries per minute  
        CorpusType.PUBLISHED: 20  # 20 queries per minute
    }
    
    # RAG access configuration (Critic only)
    RAG_CONFIG = {
        "max_queries_per_task": 3,
        "timeout_seconds": 30,
        "authorized_agents": [AgentRole.CRITIC]
    }
    
    def __init__(self):
        """Initialize governance protocol engine."""
        self.active_tasks: Dict[str, "TaskGovernanceState"] = {}
        self.violation_history: List["GovernanceViolation"] = []
        
    async def initialize_task_governance(
        self, 
        task_id: str,
        user_id: str,
        classification: str = "standard"
    ) -> "TaskGovernanceState":
        """
        Initialize governance tracking for a new task.
        
        Args:
            task_id: Unique task identifier
            user_id: User who initiated the task
            classification: Task classification (standard, sensitive, etc.)
            
        Returns:
            Task governance state for tracking
        """
        task_state = TaskGovernanceState(
            task_id=task_id,
            user_id=user_id,
            classification=classification,
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_tasks[task_id] = task_state
        
        await SecurityLogger.log_governance_event(
            event_type="task_governance_initialized",
            task_id=task_id,
            user_id=user_id,
            success=True,
            details={"classification": classification}
        )
        
        return task_state
    
    async def validate_agent_permissions(
        self,
        agent_role: AgentRole,
        task_id: str,
        required_permissions: List[str]
    ) -> bool:
        """
        Validate that agent has required permissions for operation.
        
        Args:
            agent_role: Agent requesting permission
            task_id: Current task identifier
            required_permissions: List of required permission types
            
        Returns:
            True if all permissions validated
            
        Raises:
            GovernanceViolationError: If permissions insufficient
        """
        if task_id not in self.active_tasks:
            raise GovernanceViolationError(
                violation_type="task_not_initialized",
                agent_name=agent_role.value,
                details={"task_id": task_id},
                severity="critical"
            )
        
        task_state = self.active_tasks[task_id]
        agent_permissions = self.AGENT_PERMISSIONS[agent_role]
        
        # Validate each required permission
        for permission in required_permissions:
            if not await self._validate_specific_permission(
                agent_role, agent_permissions, permission, task_state
            ):
                await self._log_permission_violation(
                    agent_role, task_id, permission, task_state
                )
                raise GovernanceViolationError(
                    violation_type="insufficient_permissions",
                    agent_name=agent_role.value,
                    details={
                        "required_permission": permission,
                        "task_id": task_id
                    },
                    severity="high"
                )
        
        return True
    
    async def validate_api_call(
        self,
        agent_role: AgentRole,
        task_id: str
    ) -> bool:
        """
        Validate agent API call against limits.
        
        Args:
            agent_role: Agent making the API call
            task_id: Current task identifier
            
        Returns:
            True if call allowed
            
        Raises:
            APICallLimitExceededError: If limit exceeded
        """
        if task_id not in self.active_tasks:
            raise GovernanceViolationError(
                violation_type="task_not_initialized",
                agent_name=agent_role.value,
                details={"task_id": task_id},
                severity="critical"
            )
        
        task_state = self.active_tasks[task_id]
        agent_permissions = self.AGENT_PERMISSIONS[agent_role]
        
        # Get current API call count for this agent in this task
        current_calls = task_state.get_api_call_count(agent_role)
        max_calls = agent_permissions.max_api_calls
        
        if current_calls >= max_calls:
            # Log violation before raising exception
            await SecurityLogger.log_governance_violation(
                violation_type="api_call_limit_exceeded",
                agent_name=agent_role.value,
                task_id=task_id,
                severity="high",
                details={
                    "current_calls": current_calls,
                    "max_calls": max_calls,
                    "attempted_call": current_calls + 1
                }
            )
            
            raise APICallLimitExceededError(
                agent_name=agent_role.value,
                max_calls=max_calls,
                current_calls=current_calls + 1,
                task_id=task_id
            )
        
        # Increment API call count
        task_state.increment_api_calls(agent_role)
        
        await SecurityLogger.log_governance_event(
            event_type="api_call_validated",
            task_id=task_id,
            agent_name=agent_role.value,
            success=True,
            details={
                "call_number": current_calls + 1,
                "max_calls": max_calls
            }
        )
        
        return True
    
    async def validate_corpus_access(
        self,
        agent_role: AgentRole,
        corpus_type: CorpusType,
        task_id: str
    ) -> bool:
        """
        Validate agent access to specific corpus.
        
        Args:
            agent_role: Agent requesting access
            corpus_type: Corpus being accessed
            task_id: Current task identifier
            
        Returns:
            True if access allowed
            
        Raises:
            UnauthorizedCorpusAccessError: If access denied
        """
        agent_permissions = self.AGENT_PERMISSIONS[agent_role]
        
        if corpus_type not in agent_permissions.corpus_access:
            # Log violation
            await SecurityLogger.log_governance_violation(
                violation_type="unauthorized_corpus_access",
                agent_name=agent_role.value,
                task_id=task_id,
                severity="critical",
                details={
                    "requested_corpus": corpus_type.value,
                    "allowed_corpora": [c.value for c in agent_permissions.corpus_access]
                }
            )
            
            raise UnauthorizedCorpusAccessError(
                agent_name=agent_role.value,
                corpus=corpus_type.value,
                allowed_corpora=[c.value for c in agent_permissions.corpus_access],
                task_id=task_id
            )
        
        # Validate rate limiting
        if task_id in self.active_tasks:
            task_state = self.active_tasks[task_id]
            rate_limit = self.CORPUS_QUERY_RATE_LIMITS[corpus_type]
            
            if not task_state.check_corpus_rate_limit(corpus_type, rate_limit):
                await SecurityLogger.log_governance_violation(
                    violation_type="corpus_rate_limit_exceeded",
                    agent_name=agent_role.value,
                    task_id=task_id,
                    severity="medium",
                    details={
                        "corpus": corpus_type.value,
                        "rate_limit": rate_limit
                    }
                )
                
                raise GovernanceViolationError(
                    violation_type="corpus_rate_limit_exceeded",
                    agent_name=agent_role.value,
                    details={
                        "corpus": corpus_type.value,
                        "rate_limit": rate_limit,
                        "task_id": task_id
                    },
                    severity="medium"
                )
            
            # Record corpus access
            task_state.record_corpus_access(agent_role, corpus_type)
        
        return True
    
    async def validate_rag_access(
        self,
        agent_role: AgentRole,
        task_id: str
    ) -> bool:
        """
        Validate RAG access (Critic only).
        
        Args:
            agent_role: Agent requesting RAG access
            task_id: Current task identifier
            
        Returns:
            True if RAG access allowed
            
        Raises:
            UnauthorizedRAGAccessError: If access denied
        """
        if agent_role not in self.RAG_CONFIG["authorized_agents"]:
            await SecurityLogger.log_governance_violation(
                violation_type="unauthorized_rag_access",
                agent_name=agent_role.value,
                task_id=task_id,
                severity="critical",
                details={
                    "authorized_agents": [a.value for a in self.RAG_CONFIG["authorized_agents"]]
                }
            )
            
            raise UnauthorizedRAGAccessError(
                agent_name=agent_role.value,
                authorized_agents=[a.value for a in self.RAG_CONFIG["authorized_agents"]],
                task_id=task_id
            )
        
        # Check RAG query limits
        if task_id in self.active_tasks:
            task_state = self.active_tasks[task_id]
            max_rag_queries = self.RAG_CONFIG["max_queries_per_task"]
            current_queries = task_state.get_rag_query_count()
            
            if current_queries >= max_rag_queries:
                await SecurityLogger.log_governance_violation(
                    violation_type="rag_query_limit_exceeded",
                    agent_name=agent_role.value,
                    task_id=task_id,
                    severity="high",
                    details={
                        "current_queries": current_queries,
                        "max_queries": max_rag_queries
                    }
                )
                
                raise GovernanceViolationError(
                    violation_type="rag_query_limit_exceeded",
                    agent_name=agent_role.value,
                    details={
                        "current_queries": current_queries,
                        "max_queries": max_rag_queries,
                        "task_id": task_id
                    },
                    severity="high"
                )
            
            # Record RAG query
            task_state.increment_rag_queries()
        
        return True
    
    async def validate_mvlm_requirements(
        self,
        agent_role: AgentRole,
        task_id: str,
        mvlm_available: bool = True
    ) -> Dict[str, Any]:
        """
        Validate MVLM usage requirements for agent.
        
        Args:
            agent_role: Agent requesting MVLM validation
            task_id: Current task identifier
            mvlm_available: Whether MVLM is currently available
            
        Returns:
            MVLM usage decision and fallback permissions
            
        Raises:
            MVLMRequiredError: If MVLM required but unavailable
        """
        agent_permissions = self.AGENT_PERMISSIONS[agent_role]
        
        decision = {
            "use_mvlm": mvlm_available and agent_permissions.mvlm_access,
            "can_fallback_to_api": False,
            "requires_emergency_auth": False,
            "processing_method": "api"  # default
        }
        
        if agent_permissions.mvlm_required and not mvlm_available:
            # Summarizer requires MVLM - no fallback without emergency auth
            if agent_role == AgentRole.SUMMARIZER:
                await SecurityLogger.log_governance_violation(
                    violation_type="mvlm_required_unavailable",
                    agent_name=agent_role.value,
                    task_id=task_id,
                    severity="high",
                    details={"agent_requires_mvlm": True}
                )
                
                decision["requires_emergency_auth"] = True
                decision["processing_method"] = "emergency_api_fallback"
                
                raise MVLMRequiredError(
                    agent_name=agent_role.value,
                    reason="MVLM required but unavailable",
                    task_id=task_id
                )
            else:
                # Other agents can fallback if allowed
                decision["can_fallback_to_api"] = True
                decision["processing_method"] = "api_fallback"
        
        elif agent_permissions.mvlm_preferred and mvlm_available:
            # Revisor prefers MVLM, can fallback to API
            decision["use_mvlm"] = True
            decision["can_fallback_to_api"] = True
            decision["processing_method"] = "mvlm_primary"
            
        elif mvlm_available and agent_permissions.mvlm_access:
            # Normal MVLM usage
            decision["use_mvlm"] = True
            decision["processing_method"] = "mvlm"
            
        return decision
    
    async def finalize_task_governance(self, task_id: str) -> Dict[str, Any]:
        """
        Finalize governance tracking for completed task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task governance summary
        """
        if task_id not in self.active_tasks:
            return {"error": "Task not found"}
        
        task_state = self.active_tasks[task_id]
        task_state.completed_at = datetime.now(timezone.utc)
        
        # Generate summary
        summary = {
            "task_id": task_id,
            "duration_seconds": (task_state.completed_at - task_state.created_at).total_seconds(),
            "api_calls_by_agent": task_state.api_calls_by_agent,
            "corpus_accesses": len(task_state.corpus_access_log),
            "rag_queries": task_state.rag_query_count,
            "governance_violations": len(task_state.violations),
            "completed_successfully": len(task_state.violations) == 0
        }
        
        await SecurityLogger.log_governance_event(
            event_type="task_governance_finalized",
            task_id=task_id,
            success=True,
            details=summary
        )
        
        # Archive task state
        del self.active_tasks[task_id]
        
        return summary
    
    # Private helper methods
    
    async def _validate_specific_permission(
        self,
        agent_role: AgentRole,
        agent_permissions: AgentPermissions, 
        permission: str,
        task_state: "TaskGovernanceState"
    ) -> bool:
        """Validate a specific permission type."""
        
        permission_validators = {
            "corpus_access": lambda: len(agent_permissions.corpus_access) > 0,
            "rag_access": lambda: agent_permissions.rag_access,
            "mvlm_access": lambda: agent_permissions.mvlm_access,
            "outline_generation": lambda: agent_role == AgentRole.IDEATOR,
            "draft_expansion": lambda: agent_role == AgentRole.DRAFTER,
            "truth_validation": lambda: agent_role == AgentRole.CRITIC,
            "correction_application": lambda: agent_role == AgentRole.REVISOR,
            "content_compression": lambda: agent_role == AgentRole.SUMMARIZER,
        }
        
        validator = permission_validators.get(permission)
        if validator:
            return validator()
        
        # Default: unknown permissions are denied
        return False
    
    async def _log_permission_violation(
        self,
        agent_role: AgentRole,
        task_id: str,
        permission: str,
        task_state: "TaskGovernanceState"
    ) -> None:
        """Log a permission violation."""
        
        violation = GovernanceViolation(
            violation_type="insufficient_permissions",
            agent_role=agent_role,
            task_id=task_id,
            details={"required_permission": permission},
            severity=ViolationSeverity.HIGH,
            timestamp=datetime.now(timezone.utc)
        )
        
        task_state.violations.append(violation)
        self.violation_history.append(violation)
        
        await SecurityLogger.log_governance_violation(
            violation_type=violation.violation_type,
            agent_name=agent_role.value,
            task_id=task_id,
            severity=violation.severity.value,
            details=violation.details
        )


@dataclass
class TaskGovernanceState:
    """Tracks governance state for a single task execution."""
    
    task_id: str
    user_id: str
    classification: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    # API call tracking
    api_calls_by_agent: Dict[AgentRole, int] = None
    
    # Corpus access tracking
    corpus_access_log: List[Dict[str, Any]] = None
    corpus_access_times: Dict[CorpusType, List[datetime]] = None
    
    # RAG query tracking
    rag_query_count: int = 0
    rag_queries: List[Dict[str, Any]] = None
    
    # Violation tracking
    violations: List["GovernanceViolation"] = None
    
    def __post_init__(self):
        """Initialize tracking dictionaries."""
        if self.api_calls_by_agent is None:
            self.api_calls_by_agent = {}
        if self.corpus_access_log is None:
            self.corpus_access_log = []
        if self.corpus_access_times is None:
            self.corpus_access_times = {}
        if self.rag_queries is None:
            self.rag_queries = []
        if self.violations is None:
            self.violations = []
    
    def get_api_call_count(self, agent_role: AgentRole) -> int:
        """Get current API call count for agent."""
        return self.api_calls_by_agent.get(agent_role, 0)
    
    def increment_api_calls(self, agent_role: AgentRole) -> None:
        """Increment API call count for agent."""
        self.api_calls_by_agent[agent_role] = self.get_api_call_count(agent_role) + 1
    
    def record_corpus_access(self, agent_role: AgentRole, corpus_type: CorpusType) -> None:
        """Record corpus access event."""
        access_time = datetime.now(timezone.utc)
        
        self.corpus_access_log.append({
            "agent_role": agent_role.value,
            "corpus_type": corpus_type.value,
            "timestamp": access_time,
            "access_id": str(uuid4())
        })
        
        if corpus_type not in self.corpus_access_times:
            self.corpus_access_times[corpus_type] = []
        self.corpus_access_times[corpus_type].append(access_time)
    
    def check_corpus_rate_limit(self, corpus_type: CorpusType, rate_limit: int) -> bool:
        """Check if corpus access is within rate limits (queries per minute)."""
        if corpus_type not in self.corpus_access_times:
            return True
        
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_accesses = [
            access_time for access_time in self.corpus_access_times[corpus_type]
            if access_time > one_minute_ago
        ]
        
        return len(recent_accesses) < rate_limit
    
    def get_rag_query_count(self) -> int:
        """Get current RAG query count."""
        return self.rag_query_count
    
    def increment_rag_queries(self) -> None:
        """Increment RAG query count."""
        self.rag_query_count += 1
        self.rag_queries.append({
            "query_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc)
        })


@dataclass  
class GovernanceViolation:
    """Records a governance rule violation."""
    
    violation_type: str
    agent_role: AgentRole
    task_id: str
    details: Dict[str, Any]
    severity: ViolationSeverity
    timestamp: datetime
    violation_id: str = None
    
    def __post_init__(self):
        """Generate violation ID."""
        if self.violation_id is None:
            self.violation_id = str(uuid4())


# Global governance protocol instance
governance_protocol = GovernanceProtocol()