"""Custom exceptions for the Multi-Corpus Governance Agent.

This module implements all security and governance exceptions referenced in:
- docs/security/protocols/governance-protocol.md
- docs/security/incident-response/incident-response-playbook.md
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


class MCGBaseException(Exception):
    """Base exception for all Multi-Corpus Governance Agent errors."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium"
    ):
        self.message = message
        self.details = details or {}
        self.severity = severity  # critical, high, medium, low
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class GovernanceViolationError(MCGBaseException):
    """Raised when governance rules are violated.
    
    Severity levels follow docs/security/incident-response/incident-response-playbook.md
    """
    
    def __init__(
        self,
        violation_type: str,
        agent_name: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "high"
    ):
        self.violation_type = violation_type
        self.agent_name = agent_name
        message = f"Governance violation '{violation_type}' by agent '{agent_name}'"
        
        violation_details = {
            "violation_type": violation_type,
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        violation_details.update(details or {})
        
        super().__init__(message, violation_details, severity)


class APICallLimitExceededError(GovernanceViolationError):
    """Raised when an agent exceeds its API call limit.
    
    Per docs/security/protocols/governance-protocol.md:
    - Ideator: 2 calls max
    - Drafter: 1 call max  
    - Critic: 2 calls max
    - Revisor: 1 call max (fallback only)
    - Summarizer: 0 calls (emergency only)
    """
    
    def __init__(self, agent_name: str, limit: int, attempted: int, task_id: str):
        details = {
            "limit": limit,
            "attempted": attempted,
            "task_id": task_id,
            "governance_rule": "api_call_limits"
        }
        super().__init__(
            violation_type="api_call_limit_exceeded",
            agent_name=agent_name,
            details=details,
            severity="high"  # High priority per incident response playbook
        )


class UnauthorizedCorpusAccessError(GovernanceViolationError):
    """Raised when an agent attempts unauthorized corpus access.
    
    Per docs/security/protocols/governance-protocol.md corpus access matrix.
    """
    
    def __init__(self, agent_name: str, corpus: str, task_id: str):
        details = {
            "corpus": corpus,
            "task_id": task_id,
            "governance_rule": "corpus_access_control",
            "authorized_corpora": self._get_authorized_corpora(agent_name)
        }
        super().__init__(
            violation_type="unauthorized_corpus_access",
            agent_name=agent_name,
            details=details,
            severity="critical"  # Critical per security architecture
        )
    
    @staticmethod
    def _get_authorized_corpora(agent_name: str) -> List[str]:
        """Return authorized corpora for agent per governance protocol."""
        corpus_access_matrix = {
            "ideator": ["personal", "social", "published"],
            "drafter": ["social", "published"],  # limited access
            "critic": ["personal", "social", "published"],
            "revisor": [],  # inherited context only
            "summarizer": []  # no new queries
        }
        return corpus_access_matrix.get(agent_name, [])


class UnauthorizedRAGAccessError(GovernanceViolationError):
    """Raised when an agent attempts unauthorized RAG access.
    
    Per docs/security/protocols/governance-protocol.md:
    Only Critic agent is authorized for RAG access.
    """
    
    def __init__(self, agent_name: str, task_id: str):
        details = {
            "task_id": task_id,
            "governance_rule": "rag_access_control",
            "authorized_agents": ["critic"]
        }
        super().__init__(
            violation_type="unauthorized_rag_access",
            agent_name=agent_name,
            details=details,
            severity="critical"
        )


class MVLMRequiredError(GovernanceViolationError):
    """Raised when MVLM is required but unavailable without fallback permission."""
    
    def __init__(self, agent_name: str, task_id: str, reason: str):
        details = {
            "task_id": task_id,
            "reason": reason,
            "governance_rule": "mvlm_preference_enforcement"
        }
        super().__init__(
            violation_type="mvlm_required_unavailable",
            agent_name=agent_name,
            details=details,
            severity="high"
        )


class CriticalFailureError(MCGBaseException):
    """Raised when a critical failure occurs that should stop the pipeline.
    
    Per docs/security/incident-response/incident-response-playbook.md P0 incidents.
    """
    
    def __init__(
        self, 
        agent_name: str, 
        reason: str, 
        task_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.agent_name = agent_name
        self.task_id = task_id
        self.reason = reason
        
        message = f"Critical failure in agent '{agent_name}': {reason}"
        failure_details = {
            "agent_name": agent_name,
            "task_id": task_id,
            "reason": reason,
            "requires_pipeline_termination": True
        }
        failure_details.update(details or {})
        
        super().__init__(message, failure_details, severity="critical")


class SecurityValidationError(MCGBaseException):
    """Raised when security validation fails."""
    
    def __init__(self, validation_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Security validation failed: {validation_type}"
        super().__init__(message, details, severity="high")


class AuthenticationError(MCGBaseException):
    """Raised when authentication fails."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Authentication failed: {reason}"
        super().__init__(message, details, severity="high")


class AuthorizationError(MCGBaseException):
    """Raised when authorization fails."""
    
    def __init__(self, action: str, required_permission: str, details: Optional[Dict[str, Any]] = None):
        message = f"Authorization failed for action '{action}': missing permission '{required_permission}'"
        auth_details = {"action": action, "required_permission": required_permission}
        auth_details.update(details or {})
        super().__init__(message, auth_details, severity="high")


class ContextAssemblyError(MCGBaseException):
    """Raised when context assembly fails."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Context assembly failed: {reason}"
        super().__init__(message, details, severity="medium")


class VoiceFingerprintError(MCGBaseException):
    """Raised when voice fingerprinting fails."""
    
    def __init__(self, corpus: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Voice fingerprinting failed for corpus '{corpus}': {reason}"
        fingerprint_details = {"corpus": corpus, "reason": reason}
        fingerprint_details.update(details or {})
        super().__init__(message, fingerprint_details, severity="medium")


class DatabaseConnectionError(MCGBaseException):
    """Raised when database connection fails."""
    
    def __init__(self, database_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Database connection failed ({database_type}): {reason}"
        db_details = {"database_type": database_type, "reason": reason}
        db_details.update(details or {})
        super().__init__(message, db_details, severity="critical")


class RedisConnectionError(MCGBaseException):
    """Raised when Redis connection fails."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Redis connection failed: {reason}"
        super().__init__(message, details, severity="high")


class ValidationError(MCGBaseException):
    """Raised when input/output validation fails."""
    
    def __init__(self, field: str, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Validation failed for field '{field}': {reason}"
        validation_details = {"field": field, "reason": reason}
        validation_details.update(details or {})
        super().__init__(message, validation_details, severity="medium")


class CompressionFailureError(MCGBaseException):
    """Raised when Summarizer compression fails."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Content compression failed: {reason}"
        super().__init__(message, details, severity="high")


class CompressionViolationError(GovernanceViolationError):
    """Raised when Summarizer introduces unauthorized content during compression."""
    
    def __init__(self, violations: List[str], task_id: str):
        details = {
            "violations": violations,
            "task_id": task_id,
            "governance_rule": "no_new_vocabulary_in_compression"
        }
        super().__init__(
            violation_type="compression_content_violation",
            agent_name="summarizer",
            details=details,
            severity="high"
        )


class MVLMFailure(Exception):
    """Raised when MVLM processing fails and fallback may be needed."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(f"MVLM failure: {reason}")


class MVLMOutputUnacceptableError(Exception):
    """Raised when MVLM output doesn't meet governance requirements."""
    
    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__(f"MVLM output unacceptable: {', '.join(issues)}")


class EmergencyAuthorizationRequired(MCGBaseException):
    """Raised when emergency authorization is required for API fallback."""
    
    def __init__(self, agent_name: str, task_id: str, reason: str):
        message = f"Emergency authorization required for {agent_name} API fallback: {reason}"
        details = {
            "agent_name": agent_name,
            "task_id": task_id,
            "reason": reason,
            "requires_manual_approval": True
        }
        super().__init__(message, details, severity="high")