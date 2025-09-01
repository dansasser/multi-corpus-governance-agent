"""Governance Protocol Implementation.

This module implements the exact governance rules defined in:
docs/security/protocols/governance-protocol.md

All agent permissions, API call limits, and access controls are enforced
through this protocol system at runtime.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

from ..utils.exceptions import (
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    UnauthorizedRAGAccessError,
    GovernanceViolationError,
    MVLMRequiredError
)


class AgentRole(Enum):
    """Agent roles per governance protocol specification."""
    IDEATOR = "ideator"
    DRAFTER = "drafter"
    CRITIC = "critic"
    REVISOR = "revisor"
    SUMMARIZER = "summarizer"


class CorpusType(Enum):
    """Corpus types with access control."""
    PERSONAL = "personal"
    SOCIAL = "social"
    PUBLISHED = "published"


@dataclass
class AgentPermissions:
    """Agent permission configuration per governance protocol."""
    agent_role: AgentRole
    max_api_calls: int
    corpus_access: List[CorpusType]
    rag_access: bool
    mvlm_access: bool
    mvlm_preferred: bool = False
    mvlm_required: bool = False
    
    def __post_init__(self):
        """Validate permission consistency."""
        if self.mvlm_required and not self.mvlm_access:
            raise ValueError(f"Agent {self.agent_role.value} requires MVLM but doesn't have access")
        
        if self.mvlm_preferred and not self.mvlm_access:
            raise ValueError(f"Agent {self.agent_role.value} prefers MVLM but doesn't have access")


class GovernanceProtocol:
    """
    Core governance protocol implementing exact rules from:
    docs/security/protocols/governance-protocol.md
    
    This class enforces all agent constraints, access controls, and 
    security rules at runtime.
    """
    
    # Agent permission matrix from governance protocol specification
    AGENT_PERMISSIONS: Dict[AgentRole, AgentPermissions] = {
        AgentRole.IDEATOR: AgentPermissions(
            agent_role=AgentRole.IDEATOR,
            max_api_calls=2,
            corpus_access=[CorpusType.PERSONAL, CorpusType.SOCIAL, CorpusType.PUBLISHED],
            rag_access=False,
            mvlm_access=True
        ),
        AgentRole.DRAFTER: AgentPermissions(
            agent_role=AgentRole.DRAFTER,
            max_api_calls=1,
            corpus_access=[CorpusType.SOCIAL, CorpusType.PUBLISHED],  # limited access
            rag_access=False,
            mvlm_access=True
        ),
        AgentRole.CRITIC: AgentPermissions(
            agent_role=AgentRole.CRITIC,
            max_api_calls=2,
            corpus_access=[CorpusType.PERSONAL, CorpusType.SOCIAL, CorpusType.PUBLISHED],
            rag_access=True,  # ONLY agent with RAG access
            mvlm_access=True
        ),
        AgentRole.REVISOR: AgentPermissions(
            agent_role=AgentRole.REVISOR,
            max_api_calls=1,  # fallback only
            corpus_access=[],  # inherited context only
            rag_access=False,
            mvlm_access=True,
            mvlm_preferred=True
        ),
        AgentRole.SUMMARIZER: AgentPermissions(
            agent_role=AgentRole.SUMMARIZER,
            max_api_calls=0,  # emergency fallback only
            corpus_access=[],  # no new queries
            rag_access=False,
            mvlm_access=True,
            mvlm_required=True
        )
    }
    
    def __init__(self):
        """Initialize governance protocol with tracking state."""
        self._api_call_tracker: Dict[str, Dict[str, int]] = {}  # task_id -> agent -> count
        self._violation_tracker: Dict[str, List[Dict[str, Any]]] = {}  # task_id -> violations
        self._task_start_times: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    @classmethod
    def get_agent_permissions(cls, agent_role: AgentRole) -> AgentPermissions:
        """Get permissions for specified agent role."""
        return cls.AGENT_PERMISSIONS[agent_role]
    
    async def validate_agent_permissions(
        self,
        agent_name: str,
        required_permissions: List[str],
        task_id: str
    ) -> bool:
        """Validate agent has required permissions for action."""
        try:
            agent_role = AgentRole(agent_name)
        except ValueError:
            raise GovernanceViolationError(
                violation_type="invalid_agent_role",
                agent_name=agent_name,
                details={"task_id": task_id, "valid_roles": [r.value for r in AgentRole]}
            )
        
        permissions = self.get_agent_permissions(agent_role)
        
        # Check each required permission
        for permission in required_permissions:
            if not self._has_permission(permissions, permission):
                raise GovernanceViolationError(
                    violation_type=f"missing_permission_{permission}",
                    agent_name=agent_name,
                    details={
                        "task_id": task_id,
                        "required_permission": permission,
                        "agent_permissions": self._serialize_permissions(permissions)
                    }
                )
        
        return True
    
    async def validate_corpus_access(
        self,
        agent_name: str,
        corpus: str,
        task_id: str
    ) -> bool:
        """Validate agent can access specified corpus."""
        try:
            agent_role = AgentRole(agent_name)
            corpus_type = CorpusType(corpus)
        except ValueError as e:
            raise GovernanceViolationError(
                violation_type="invalid_corpus_or_agent",
                agent_name=agent_name,
                details={"task_id": task_id, "error": str(e)}
            )
        
        permissions = self.get_agent_permissions(agent_role)
        
        if corpus_type not in permissions.corpus_access:
            await self._record_violation(
                task_id=task_id,
                violation_type="unauthorized_corpus_access",
                agent_name=agent_name,
                details={"corpus": corpus, "authorized_corpora": [c.value for c in permissions.corpus_access]}
            )
            raise UnauthorizedCorpusAccessError(agent_name, corpus, task_id)
        
        return True
    
    async def validate_rag_access(
        self,
        agent_name: str,
        task_id: str
    ) -> bool:
        """Validate agent can access RAG endpoints."""
        try:
            agent_role = AgentRole(agent_name)
        except ValueError:
            raise GovernanceViolationError(
                violation_type="invalid_agent_role",
                agent_name=agent_name,
                details={"task_id": task_id}
            )
        
        permissions = self.get_agent_permissions(agent_role)
        
        if not permissions.rag_access:
            await self._record_violation(
                task_id=task_id,
                violation_type="unauthorized_rag_access",
                agent_name=agent_name,
                details={"authorized_agents": ["critic"]}
            )
            raise UnauthorizedRAGAccessError(agent_name, task_id)
        
        return True
    
    async def validate_api_call(
        self,
        agent_name: str,
        task_id: str
    ) -> bool:
        """Validate agent can make API call within limits."""
        async with self._lock:
            try:
                agent_role = AgentRole(agent_name)
            except ValueError:
                raise GovernanceViolationError(
                    violation_type="invalid_agent_role",
                    agent_name=agent_name,
                    details={"task_id": task_id}
                )
            
            permissions = self.get_agent_permissions(agent_role)
            
            # Initialize tracking if needed
            if task_id not in self._api_call_tracker:
                self._api_call_tracker[task_id] = {}
                self._task_start_times[task_id] = datetime.utcnow()
            
            if agent_name not in self._api_call_tracker[task_id]:
                self._api_call_tracker[task_id][agent_name] = 0
            
            current_calls = self._api_call_tracker[task_id][agent_name]
            
            if current_calls >= permissions.max_api_calls:
                await self._record_violation(
                    task_id=task_id,
                    violation_type="api_call_limit_exceeded",
                    agent_name=agent_name,
                    details={
                        "current_calls": current_calls,
                        "max_calls": permissions.max_api_calls,
                        "attempted_call": current_calls + 1
                    }
                )
                raise APICallLimitExceededError(
                    agent_name, 
                    permissions.max_api_calls, 
                    current_calls + 1, 
                    task_id
                )
            
            # Increment call count
            self._api_call_tracker[task_id][agent_name] += 1
            return True
    
    async def validate_mvlm_preference(
        self,
        agent_name: str,
        task_id: str,
        mvlm_available: bool
    ) -> bool:
        """Validate MVLM preference/requirement compliance."""
        try:
            agent_role = AgentRole(agent_name)
        except ValueError:
            raise GovernanceViolationError(
                violation_type="invalid_agent_role",
                agent_name=agent_name,
                details={"task_id": task_id}
            )
        
        permissions = self.get_agent_permissions(agent_role)
        
        # If MVLM is required and not available, check fallback permission
        if permissions.mvlm_required and not mvlm_available:
            if not await self.can_fallback_to_api(agent_name, task_id):
                raise MVLMRequiredError(
                    agent_name, 
                    task_id, 
                    "MVLM required but unavailable and no API fallback permission"
                )
        
        return True
    
    async def can_fallback_to_api(
        self,
        agent_name: str,
        task_id: str
    ) -> bool:
        """Check if agent can fallback to API when MVLM fails."""
        try:
            agent_role = AgentRole(agent_name)
        except ValueError:
            return False
        
        permissions = self.get_agent_permissions(agent_role)
        
        # Revisor can fallback if MVLM fails
        if agent_role == AgentRole.REVISOR:
            return permissions.max_api_calls > 0
        
        # Summarizer requires emergency authorization
        if agent_role == AgentRole.SUMMARIZER:
            return await self._check_emergency_authorization(task_id)
        
        # Other agents follow normal API limits
        async with self._lock:
            if task_id not in self._api_call_tracker:
                return permissions.max_api_calls > 0
            
            current_calls = self._api_call_tracker[task_id].get(agent_name, 0)
            return current_calls < permissions.max_api_calls
    
    async def get_api_call_count(
        self,
        agent_name: str,
        task_id: str
    ) -> int:
        """Get current API call count for agent in task."""
        async with self._lock:
            if task_id not in self._api_call_tracker:
                return 0
            return self._api_call_tracker[task_id].get(agent_name, 0)
    
    async def get_task_violations(
        self,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """Get all violations recorded for task."""
        return self._violation_tracker.get(task_id, [])
    
    async def cleanup_task_tracking(
        self,
        task_id: str,
        max_age_hours: int = 24
    ) -> None:
        """Clean up tracking data for completed tasks."""
        async with self._lock:
            # Remove old tasks
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            tasks_to_remove = []
            for tid, start_time in self._task_start_times.items():
                if start_time < cutoff_time:
                    tasks_to_remove.append(tid)
            
            for tid in tasks_to_remove:
                self._api_call_tracker.pop(tid, None)
                self._violation_tracker.pop(tid, None)
                self._task_start_times.pop(tid, None)
            
            # Remove specific task if requested
            if task_id in self._api_call_tracker:
                del self._api_call_tracker[task_id]
            if task_id in self._violation_tracker:
                del self._violation_tracker[task_id]
            if task_id in self._task_start_times:
                del self._task_start_times[task_id]
    
    def _has_permission(self, permissions: AgentPermissions, permission: str) -> bool:
        """Check if agent permissions include specified permission."""
        permission_map = {
            "corpus_access": len(permissions.corpus_access) > 0,
            "rag_access": permissions.rag_access,
            "mvlm_access": permissions.mvlm_access,
            "api_access": permissions.max_api_calls > 0,
            "outline_generation": permissions.agent_role == AgentRole.IDEATOR,
            "draft_expansion": permissions.agent_role == AgentRole.DRAFTER,
            "truth_validation": permissions.agent_role == AgentRole.CRITIC,
            "correction_application": permissions.agent_role == AgentRole.REVISOR,
            "content_compression": permissions.agent_role == AgentRole.SUMMARIZER,
            "keyword_extraction": permissions.agent_role == AgentRole.SUMMARIZER,
            "tone_preservation": permissions.agent_role in [AgentRole.REVISOR, AgentRole.DRAFTER]
        }
        
        return permission_map.get(permission, False)
    
    def _serialize_permissions(self, permissions: AgentPermissions) -> Dict[str, Any]:
        """Serialize permissions for logging."""
        return {
            "agent_role": permissions.agent_role.value,
            "max_api_calls": permissions.max_api_calls,
            "corpus_access": [c.value for c in permissions.corpus_access],
            "rag_access": permissions.rag_access,
            "mvlm_access": permissions.mvlm_access,
            "mvlm_preferred": permissions.mvlm_preferred,
            "mvlm_required": permissions.mvlm_required
        }
    
    async def _record_violation(
        self,
        task_id: str,
        violation_type: str,
        agent_name: str,
        details: Dict[str, Any]
    ) -> None:
        """Record governance violation for audit trail."""
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "violation_type": violation_type,
            "agent_name": agent_name,
            "details": details
        }
        
        if task_id not in self._violation_tracker:
            self._violation_tracker[task_id] = []
        
        self._violation_tracker[task_id].append(violation)
    
    async def _check_emergency_authorization(self, task_id: str) -> bool:
        """Check if emergency authorization exists for API fallback."""
        # In production, this would check an authorization service
        # For now, return False to enforce MVLM-only for Summarizer
        return False


# Global governance protocol instance
governance_protocol = GovernanceProtocol()