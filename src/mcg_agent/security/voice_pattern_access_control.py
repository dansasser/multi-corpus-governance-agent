"""
Voice Pattern Access Control Module

Controls access to different aspects of user's voice patterns based on agent roles.
Implements fine-grained permissions for personal voice data protection.
"""

from typing import Dict, List, Set, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from mcg_agent.pydantic_ai.agent_base import AgentRole
from mcg_agent.utils.exceptions import UnauthorizedCorpusAccessError, VoiceAccessDeniedError
from mcg_agent.utils.audit import AuditLogger
from mcg_agent.config import get_settings


class CorpusType(str, Enum):
    """Types of corpora containing voice patterns"""
    PERSONAL = "personal"
    SOCIAL = "social" 
    PUBLISHED = "published"


class VoicePatternType(str, Enum):
    """Types of voice patterns that can be accessed"""
    REASONING_PATTERNS = "reasoning_patterns"
    CONVERSATIONAL_STYLE = "conversational_style"
    PROFESSIONAL_TONE = "professional_tone"
    CASUAL_TONE = "casual_tone"
    COLLOCATIONS = "collocations"
    PHRASE_PREFERENCES = "phrase_preferences"
    ARGUMENTATION_STYLE = "argumentation_style"
    ENGAGEMENT_PATTERNS = "engagement_patterns"


class AccessPermission(BaseModel):
    """Access permission for voice patterns"""
    agent_role: AgentRole
    corpus_type: CorpusType
    voice_pattern_types: Set[VoicePatternType]
    max_patterns_per_request: int = Field(default=100)
    time_window_minutes: int = Field(default=60)
    max_requests_per_window: int = Field(default=10)


class VoiceAccessRequest(BaseModel):
    """Request for voice pattern access"""
    agent_role: AgentRole
    corpus_type: CorpusType
    voice_pattern_types: List[VoicePatternType]
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    justification: str = Field(description="Reason for accessing voice patterns")


class VoiceAccessLog(BaseModel):
    """Log entry for voice pattern access"""
    request: VoiceAccessRequest
    granted: bool
    patterns_accessed: List[str] = Field(default_factory=list)
    access_duration_ms: float
    denial_reason: Optional[str] = None


class VoicePatternAccessControl:
    """
    Control access to different aspects of user's voice patterns.
    
    Implements role-based access control for voice patterns across all corpora:
    - Ideator: All corpora for complete voice analysis
    - Drafter: Personal + Social for natural tone
    - Critic: All corpora for voice validation  
    - Revisor: Provided snippets only (no new corpus access)
    - Summarizer: No new corpus access
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.audit_logger = AuditLogger()
        self._access_logs: List[VoiceAccessLog] = []
        self._permissions = self._initialize_permissions()
        
    def _initialize_permissions(self) -> Dict[AgentRole, List[AccessPermission]]:
        """Initialize role-based access permissions for voice patterns"""
        permissions = {
            # Ideator: Full access to all corpora for complete voice analysis
            AgentRole.IDEATOR: [
                AccessPermission(
                    agent_role=AgentRole.IDEATOR,
                    corpus_type=CorpusType.PERSONAL,
                    voice_pattern_types={
                        VoicePatternType.REASONING_PATTERNS,
                        VoicePatternType.CONVERSATIONAL_STYLE,
                        VoicePatternType.COLLOCATIONS,
                        VoicePatternType.PHRASE_PREFERENCES
                    },
                    max_patterns_per_request=200,
                    max_requests_per_window=15
                ),
                AccessPermission(
                    agent_role=AgentRole.IDEATOR,
                    corpus_type=CorpusType.SOCIAL,
                    voice_pattern_types={
                        VoicePatternType.CASUAL_TONE,
                        VoicePatternType.ENGAGEMENT_PATTERNS,
                        VoicePatternType.COLLOCATIONS
                    },
                    max_patterns_per_request=150,
                    max_requests_per_window=15
                ),
                AccessPermission(
                    agent_role=AgentRole.IDEATOR,
                    corpus_type=CorpusType.PUBLISHED,
                    voice_pattern_types={
                        VoicePatternType.PROFESSIONAL_TONE,
                        VoicePatternType.ARGUMENTATION_STYLE,
                        VoicePatternType.COLLOCATIONS
                    },
                    max_patterns_per_request=150,
                    max_requests_per_window=15
                )
            ],
            
            # Drafter: Personal + Social for natural tone anchoring
            AgentRole.DRAFTER: [
                AccessPermission(
                    agent_role=AgentRole.DRAFTER,
                    corpus_type=CorpusType.PERSONAL,
                    voice_pattern_types={
                        VoicePatternType.CONVERSATIONAL_STYLE,
                        VoicePatternType.PHRASE_PREFERENCES,
                        VoicePatternType.COLLOCATIONS
                    },
                    max_patterns_per_request=100,
                    max_requests_per_window=8
                ),
                AccessPermission(
                    agent_role=AgentRole.DRAFTER,
                    corpus_type=CorpusType.SOCIAL,
                    voice_pattern_types={
                        VoicePatternType.CASUAL_TONE,
                        VoicePatternType.ENGAGEMENT_PATTERNS
                    },
                    max_patterns_per_request=75,
                    max_requests_per_window=8
                )
            ],
            
            # Critic: Full access to all corpora for voice validation
            AgentRole.CRITIC: [
                AccessPermission(
                    agent_role=AgentRole.CRITIC,
                    corpus_type=CorpusType.PERSONAL,
                    voice_pattern_types={
                        VoicePatternType.REASONING_PATTERNS,
                        VoicePatternType.CONVERSATIONAL_STYLE,
                        VoicePatternType.COLLOCATIONS,
                        VoicePatternType.PHRASE_PREFERENCES
                    },
                    max_patterns_per_request=150,
                    max_requests_per_window=12
                ),
                AccessPermission(
                    agent_role=AgentRole.CRITIC,
                    corpus_type=CorpusType.SOCIAL,
                    voice_pattern_types={
                        VoicePatternType.CASUAL_TONE,
                        VoicePatternType.ENGAGEMENT_PATTERNS,
                        VoicePatternType.COLLOCATIONS
                    },
                    max_patterns_per_request=100,
                    max_requests_per_window=12
                ),
                AccessPermission(
                    agent_role=AgentRole.CRITIC,
                    corpus_type=CorpusType.PUBLISHED,
                    voice_pattern_types={
                        VoicePatternType.PROFESSIONAL_TONE,
                        VoicePatternType.ARGUMENTATION_STYLE,
                        VoicePatternType.COLLOCATIONS
                    },
                    max_patterns_per_request=100,
                    max_requests_per_window=12
                )
            ],
            
            # Revisor: No new corpus access (works with provided snippets only)
            AgentRole.REVISOR: [],
            
            # Summarizer: No new corpus access
            AgentRole.SUMMARIZER: []
        }
        
        return permissions
        
    def validate_corpus_access(self, agent_role: AgentRole, corpus_type: CorpusType) -> bool:
        """
        Validate if an agent role has access to a specific corpus type.
        
        Args:
            agent_role: The agent requesting access
            corpus_type: The corpus type being accessed
            
        Returns:
            bool: True if access is allowed, False otherwise
        """
        if agent_role not in self._permissions:
            return False
            
        agent_permissions = self._permissions[agent_role]
        
        for permission in agent_permissions:
            if permission.corpus_type == corpus_type:
                return True
                
        return False
        
    def validate_voice_pattern_access(
        self, 
        request: VoiceAccessRequest
    ) -> bool:
        """
        Validate if an agent can access specific voice pattern types.
        
        Args:
            request: Voice access request
            
        Returns:
            bool: True if access is allowed, False otherwise
        """
        if request.agent_role not in self._permissions:
            return False
            
        agent_permissions = self._permissions[request.agent_role]
        
        # Find matching permission for corpus type
        matching_permission = None
        for permission in agent_permissions:
            if permission.corpus_type == request.corpus_type:
                matching_permission = permission
                break
                
        if not matching_permission:
            return False
            
        # Check if all requested voice pattern types are allowed
        requested_patterns = set(request.voice_pattern_types)
        allowed_patterns = matching_permission.voice_pattern_types
        
        if not requested_patterns.issubset(allowed_patterns):
            return False
            
        # Check rate limiting
        if not self._check_rate_limits(request, matching_permission):
            return False
            
        return True
        
    def _check_rate_limits(
        self, 
        request: VoiceAccessRequest, 
        permission: AccessPermission
    ) -> bool:
        """Check if request is within rate limits"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=permission.time_window_minutes)
        
        # Count recent requests from this agent for this corpus
        recent_requests = [
            log for log in self._access_logs
            if (log.request.agent_role == request.agent_role and
                log.request.corpus_type == request.corpus_type and
                log.request.timestamp >= window_start and
                log.granted)
        ]
        
        if len(recent_requests) >= permission.max_requests_per_window:
            return False
            
        # Check pattern count limits
        if len(request.voice_pattern_types) > permission.max_patterns_per_request:
            return False
            
        return True
        
    def request_voice_access(
        self, 
        request: VoiceAccessRequest
    ) -> VoiceAccessLog:
        """
        Process a voice pattern access request.
        
        Args:
            request: Voice access request
            
        Returns:
            VoiceAccessLog: Log of the access attempt
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate access
            if not self.validate_voice_pattern_access(request):
                access_log = VoiceAccessLog(
                    request=request,
                    granted=False,
                    access_duration_ms=0,
                    denial_reason="Access denied: insufficient permissions or rate limit exceeded"
                )
                
                self._access_logs.append(access_log)
                
                self.audit_logger.log_security_event(
                    event_type="voice_access_denied",
                    details={
                        "agent_role": request.agent_role,
                        "corpus_type": request.corpus_type,
                        "voice_pattern_types": request.voice_pattern_types,
                        "task_id": request.task_id,
                        "denial_reason": access_log.denial_reason
                    }
                )
                
                return access_log
                
            # Grant access and log patterns accessed
            patterns_accessed = [f"{request.corpus_type}:{pattern}" for pattern in request.voice_pattern_types]
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            access_log = VoiceAccessLog(
                request=request,
                granted=True,
                patterns_accessed=patterns_accessed,
                access_duration_ms=duration_ms
            )
            
            self._access_logs.append(access_log)
            
            self.audit_logger.log_security_event(
                event_type="voice_access_granted",
                details={
                    "agent_role": request.agent_role,
                    "corpus_type": request.corpus_type,
                    "voice_pattern_types": request.voice_pattern_types,
                    "patterns_accessed": patterns_accessed,
                    "task_id": request.task_id,
                    "access_duration_ms": duration_ms
                }
            )
            
            return access_log
            
        except Exception as e:
            access_log = VoiceAccessLog(
                request=request,
                granted=False,
                access_duration_ms=0,
                denial_reason=f"Access error: {str(e)}"
            )
            
            self._access_logs.append(access_log)
            
            self.audit_logger.log_security_event(
                event_type="voice_access_error",
                details={
                    "agent_role": request.agent_role,
                    "corpus_type": request.corpus_type,
                    "task_id": request.task_id,
                    "error": str(e)
                }
            )
            
            return access_log
            
    def get_agent_permissions(self, agent_role: AgentRole) -> List[AccessPermission]:
        """
        Get all permissions for a specific agent role.
        
        Args:
            agent_role: The agent role
            
        Returns:
            List[AccessPermission]: List of permissions for the agent
        """
        return self._permissions.get(agent_role, [])
        
    def get_access_summary(self, agent_role: Optional[AgentRole] = None) -> Dict[str, Any]:
        """
        Get summary of voice pattern access activity.
        
        Args:
            agent_role: Optional agent role to filter by
            
        Returns:
            Dict[str, Any]: Access summary statistics
        """
        logs = self._access_logs
        if agent_role:
            logs = [log for log in logs if log.request.agent_role == agent_role]
            
        total_requests = len(logs)
        granted_requests = len([log for log in logs if log.granted])
        denied_requests = total_requests - granted_requests
        
        if total_requests > 0:
            avg_duration = sum(log.access_duration_ms for log in logs if log.granted) / max(granted_requests, 1)
        else:
            avg_duration = 0
            
        return {
            "total_requests": total_requests,
            "granted_requests": granted_requests,
            "denied_requests": denied_requests,
            "success_rate": granted_requests / max(total_requests, 1),
            "average_access_duration_ms": avg_duration,
            "agent_role": agent_role
        }
        
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Clean up old access logs.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            int: Number of logs removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        old_logs = [log for log in self._access_logs if log.request.timestamp < cutoff_date]
        self._access_logs = [log for log in self._access_logs if log.request.timestamp >= cutoff_date]
        
        removed_count = len(old_logs)
        
        if removed_count > 0:
            self.audit_logger.log_security_event(
                event_type="voice_access_logs_cleaned",
                details={
                    "logs_removed": removed_count,
                    "cutoff_date": cutoff_date.isoformat()
                }
            )
            
        return removed_count


__all__ = [
    "VoicePatternAccessControl",
    "VoiceAccessRequest",
    "VoiceAccessLog",
    "AccessPermission",
    "CorpusType",
    "VoicePatternType"
]
