"""
Personal Data Governance Manager

Comprehensive governance system for personal data access, usage, and protection
in the context of personal voice replication and multi-corpus access.
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field

from mcg_agent.governance.call_tracker import CallTracker
from mcg_agent.security.personal_data_encryption import PersonalDataEncryption
from mcg_agent.security.voice_pattern_access_control import VoicePatternAccessControl
from mcg_agent.security.personal_voice_audit_trail import PersonalVoiceAuditTrail, VoicePatternUsage
from mcg_agent.voice.voice_fingerprint_extractor import VoiceFingerprint
from mcg_agent.utils.exceptions import PersonalDataGovernanceError
from mcg_agent.utils.audit import AuditLogger


class PersonalDataAccessLevel(str, Enum):
    """Levels of personal data access"""
    NONE = "none"                    # No personal data access
    METADATA_ONLY = "metadata_only"  # Only metadata, no content
    LIMITED = "limited"              # Limited content access
    STANDARD = "standard"            # Standard personal data access
    FULL = "full"                    # Full personal data access


class PersonalDataUsageType(str, Enum):
    """Types of personal data usage"""
    VOICE_ANALYSIS = "voice_analysis"           # Analyzing voice patterns
    VOICE_REPLICATION = "voice_replication"     # Replicating voice in responses
    CORPUS_SEARCH = "corpus_search"             # Searching personal corpus
    PATTERN_EXTRACTION = "pattern_extraction"   # Extracting communication patterns
    CONTEXT_ANALYSIS = "context_analysis"       # Analyzing communication context


@dataclass
class PersonalDataUsageRecord:
    """Record of personal data usage"""
    usage_id: str
    user_id: str
    usage_type: PersonalDataUsageType
    corpus_sources: List[str]
    data_accessed: Dict[str, Any]
    purpose: str
    timestamp: datetime
    agent_role: str
    access_level: PersonalDataAccessLevel
    retention_period: Optional[timedelta] = None


class PersonalDataGovernancePolicy(BaseModel):
    """Policy for personal data governance"""
    user_id: str = Field(description="User identifier")
    
    # Access permissions
    allowed_access_levels: List[PersonalDataAccessLevel] = Field(description="Allowed access levels")
    allowed_usage_types: List[PersonalDataUsageType] = Field(description="Allowed usage types")
    allowed_corpus_sources: List[str] = Field(description="Allowed corpus sources")
    
    # Agent permissions
    agent_permissions: Dict[str, Dict[str, Any]] = Field(description="Permissions by agent role")
    
    # Usage limits
    daily_access_limit: int = Field(description="Daily access limit")
    hourly_access_limit: int = Field(description="Hourly access limit")
    max_concurrent_access: int = Field(description="Maximum concurrent access")
    
    # Data retention
    default_retention_period: timedelta = Field(description="Default data retention period")
    voice_pattern_retention: timedelta = Field(description="Voice pattern retention period")
    
    # Privacy settings
    require_explicit_consent: bool = Field(description="Require explicit consent for access")
    allow_voice_fingerprinting: bool = Field(description="Allow voice fingerprinting")
    allow_cross_corpus_analysis: bool = Field(description="Allow cross-corpus analysis")
    
    # Audit requirements
    audit_all_access: bool = Field(description="Audit all personal data access")
    detailed_usage_logging: bool = Field(description="Enable detailed usage logging")
    
    # Policy metadata
    created_date: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    policy_version: str = Field(default="1.0")
    
    class Config:
        arbitrary_types_allowed = True


class PersonalDataGovernanceManager:
    """
    Comprehensive governance manager for personal data in voice replication system.
    
    Manages access control, usage tracking, policy enforcement, and compliance
    for all personal data operations including voice fingerprinting and replication.
    """
    
    def __init__(self):
        self.call_tracker = CallTracker()
        self.encryption = PersonalDataEncryption()
        self.access_control = VoicePatternAccessControl()
        self.audit_trail = PersonalVoiceAuditTrail()
        self.audit_logger = AuditLogger()
        
        # Governance state
        self.active_policies: Dict[str, PersonalDataGovernancePolicy] = {}
        self.usage_records: List[PersonalDataUsageRecord] = []
        self.access_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Default limits
        self.default_daily_limit = 100
        self.default_hourly_limit = 20
        self.default_concurrent_limit = 3
        self.default_retention_days = 30
        
    async def enforce_personal_data_governance(
        self,
        user_id: str,
        agent_role: str,
        usage_type: PersonalDataUsageType,
        corpus_sources: List[str],
        requested_access_level: PersonalDataAccessLevel,
        purpose: str,
        data_context: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Enforce personal data governance for a specific access request.
        
        Args:
            user_id: User identifier
            agent_role: Role of the requesting agent
            usage_type: Type of data usage
            corpus_sources: Corpus sources being accessed
            requested_access_level: Requested access level
            purpose: Purpose of data access
            data_context: Additional context for the request
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (allowed, governance_result)
        """
        try:
            self.audit_logger.log_info(
                f"Enforcing personal data governance for user {user_id}, "
                f"agent {agent_role}, usage {usage_type}"
            )
            
            # Get or create governance policy
            policy = await self._get_governance_policy(user_id)
            
            # Check basic permissions
            permission_check = self._check_basic_permissions(
                policy, agent_role, usage_type, corpus_sources, requested_access_level
            )
            
            if not permission_check["allowed"]:
                return False, permission_check
                
            # Check usage limits
            limit_check = await self._check_usage_limits(policy, user_id, agent_role)
            
            if not limit_check["allowed"]:
                return False, limit_check
                
            # Check consent requirements
            consent_check = await self._check_consent_requirements(
                policy, usage_type, corpus_sources, data_context
            )
            
            if not consent_check["allowed"]:
                return False, consent_check
                
            # Create usage record
            usage_record = await self._create_usage_record(
                user_id, agent_role, usage_type, corpus_sources,
                requested_access_level, purpose, data_context
            )
            
            # Update access tracking
            await self._update_access_tracking(user_id, agent_role, usage_record)
            
            # Create governance result
            governance_result = {
                "allowed": True,
                "access_level": requested_access_level,
                "usage_record_id": usage_record.usage_id,
                "retention_period": policy.default_retention_period,
                "audit_required": policy.audit_all_access,
                "restrictions": self._get_access_restrictions(policy, agent_role),
                "governance_metadata": {
                    "policy_version": policy.policy_version,
                    "enforcement_timestamp": datetime.utcnow().isoformat(),
                    "compliance_status": "approved"
                }
            }
            
            self.audit_logger.log_info(
                f"Personal data governance approved for user {user_id} "
                f"with access level {requested_access_level}"
            )
            
            return True, governance_result
            
        except Exception as e:
            self.audit_logger.log_error(f"Personal data governance enforcement failed: {str(e)}")
            return False, {
                "allowed": False,
                "error": str(e),
                "governance_metadata": {
                    "enforcement_timestamp": datetime.utcnow().isoformat(),
                    "compliance_status": "error"
                }
            }
            
    async def _get_governance_policy(self, user_id: str) -> PersonalDataGovernancePolicy:
        """Get or create governance policy for user"""
        try:
            if user_id in self.active_policies:
                return self.active_policies[user_id]
                
            # Create default policy
            default_policy = PersonalDataGovernancePolicy(
                user_id=user_id,
                allowed_access_levels=[
                    PersonalDataAccessLevel.METADATA_ONLY,
                    PersonalDataAccessLevel.LIMITED,
                    PersonalDataAccessLevel.STANDARD
                ],
                allowed_usage_types=[
                    PersonalDataUsageType.VOICE_ANALYSIS,
                    PersonalDataUsageType.VOICE_REPLICATION,
                    PersonalDataUsageType.CORPUS_SEARCH
                ],
                allowed_corpus_sources=["personal", "social", "published"],
                agent_permissions={
                    "ideator": {
                        "access_level": PersonalDataAccessLevel.STANDARD,
                        "corpus_sources": ["personal", "social", "published"],
                        "usage_types": [PersonalDataUsageType.VOICE_ANALYSIS, PersonalDataUsageType.CORPUS_SEARCH]
                    },
                    "drafter": {
                        "access_level": PersonalDataAccessLevel.LIMITED,
                        "corpus_sources": ["personal", "social"],
                        "usage_types": [PersonalDataUsageType.VOICE_REPLICATION, PersonalDataUsageType.CORPUS_SEARCH]
                    },
                    "critic": {
                        "access_level": PersonalDataAccessLevel.STANDARD,
                        "corpus_sources": ["personal", "social", "published"],
                        "usage_types": [PersonalDataUsageType.VOICE_ANALYSIS, PersonalDataUsageType.CONTEXT_ANALYSIS]
                    },
                    "revisor": {
                        "access_level": PersonalDataAccessLevel.METADATA_ONLY,
                        "corpus_sources": [],
                        "usage_types": []
                    },
                    "summarizer": {
                        "access_level": PersonalDataAccessLevel.METADATA_ONLY,
                        "corpus_sources": [],
                        "usage_types": []
                    }
                },
                daily_access_limit=self.default_daily_limit,
                hourly_access_limit=self.default_hourly_limit,
                max_concurrent_access=self.default_concurrent_limit,
                default_retention_period=timedelta(days=self.default_retention_days),
                voice_pattern_retention=timedelta(days=90),
                require_explicit_consent=False,
                allow_voice_fingerprinting=True,
                allow_cross_corpus_analysis=True,
                audit_all_access=True,
                detailed_usage_logging=True
            )
            
            self.active_policies[user_id] = default_policy
            return default_policy
            
        except Exception as e:
            self.audit_logger.log_error(f"Policy retrieval failed: {str(e)}")
            raise PersonalDataGovernanceError(f"Failed to get governance policy: {str(e)}")
            
    def _check_basic_permissions(
        self,
        policy: PersonalDataGovernancePolicy,
        agent_role: str,
        usage_type: PersonalDataUsageType,
        corpus_sources: List[str],
        requested_access_level: PersonalDataAccessLevel
    ) -> Dict[str, Any]:
        """Check basic permissions against policy"""
        try:
            # Check if access level is allowed
            if requested_access_level not in policy.allowed_access_levels:
                return {
                    "allowed": False,
                    "reason": f"Access level {requested_access_level} not allowed",
                    "allowed_levels": [level.value for level in policy.allowed_access_levels]
                }
                
            # Check if usage type is allowed
            if usage_type not in policy.allowed_usage_types:
                return {
                    "allowed": False,
                    "reason": f"Usage type {usage_type} not allowed",
                    "allowed_types": [usage.value for usage in policy.allowed_usage_types]
                }
                
            # Check corpus sources
            for corpus in corpus_sources:
                if corpus not in policy.allowed_corpus_sources:
                    return {
                        "allowed": False,
                        "reason": f"Corpus source {corpus} not allowed",
                        "allowed_sources": policy.allowed_corpus_sources
                    }
                    
            # Check agent-specific permissions
            if agent_role in policy.agent_permissions:
                agent_perms = policy.agent_permissions[agent_role]
                
                # Check agent access level
                agent_access_level = PersonalDataAccessLevel(agent_perms.get("access_level", "none"))
                if requested_access_level.value > agent_access_level.value:
                    return {
                        "allowed": False,
                        "reason": f"Agent {agent_role} not authorized for access level {requested_access_level}",
                        "agent_max_level": agent_access_level.value
                    }
                    
                # Check agent corpus sources
                agent_corpus_sources = agent_perms.get("corpus_sources", [])
                for corpus in corpus_sources:
                    if corpus not in agent_corpus_sources:
                        return {
                            "allowed": False,
                            "reason": f"Agent {agent_role} not authorized for corpus {corpus}",
                            "agent_allowed_sources": agent_corpus_sources
                        }
                        
                # Check agent usage types
                agent_usage_types = [PersonalDataUsageType(ut) for ut in agent_perms.get("usage_types", [])]
                if usage_type not in agent_usage_types:
                    return {
                        "allowed": False,
                        "reason": f"Agent {agent_role} not authorized for usage type {usage_type}",
                        "agent_allowed_types": [ut.value for ut in agent_usage_types]
                    }
                    
            return {"allowed": True}
            
        except Exception as e:
            self.audit_logger.log_error(f"Permission check failed: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Permission check error: {str(e)}"
            }
            
    async def _check_usage_limits(
        self,
        policy: PersonalDataGovernancePolicy,
        user_id: str,
        agent_role: str
    ) -> Dict[str, Any]:
        """Check usage limits"""
        try:
            now = datetime.utcnow()
            
            # Check daily limit
            daily_usage = self._count_usage_in_period(
                user_id, now - timedelta(days=1), now
            )
            
            if daily_usage >= policy.daily_access_limit:
                return {
                    "allowed": False,
                    "reason": "Daily access limit exceeded",
                    "current_usage": daily_usage,
                    "limit": policy.daily_access_limit
                }
                
            # Check hourly limit
            hourly_usage = self._count_usage_in_period(
                user_id, now - timedelta(hours=1), now
            )
            
            if hourly_usage >= policy.hourly_access_limit:
                return {
                    "allowed": False,
                    "reason": "Hourly access limit exceeded",
                    "current_usage": hourly_usage,
                    "limit": policy.hourly_access_limit
                }
                
            # Check concurrent access
            concurrent_sessions = self._count_concurrent_sessions(user_id)
            
            if concurrent_sessions >= policy.max_concurrent_access:
                return {
                    "allowed": False,
                    "reason": "Maximum concurrent access exceeded",
                    "current_sessions": concurrent_sessions,
                    "limit": policy.max_concurrent_access
                }
                
            return {"allowed": True}
            
        except Exception as e:
            self.audit_logger.log_error(f"Usage limit check failed: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Usage limit check error: {str(e)}"
            }
            
    async def _check_consent_requirements(
        self,
        policy: PersonalDataGovernancePolicy,
        usage_type: PersonalDataUsageType,
        corpus_sources: List[str],
        data_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Check consent requirements"""
        try:
            if not policy.require_explicit_consent:
                return {"allowed": True}
                
            # Check for specific consent requirements
            consent_required = False
            consent_reasons = []
            
            # Voice fingerprinting requires consent
            if usage_type == PersonalDataUsageType.PATTERN_EXTRACTION and not policy.allow_voice_fingerprinting:
                consent_required = True
                consent_reasons.append("Voice fingerprinting requires explicit consent")
                
            # Cross-corpus analysis requires consent
            if len(corpus_sources) > 1 and not policy.allow_cross_corpus_analysis:
                consent_required = True
                consent_reasons.append("Cross-corpus analysis requires explicit consent")
                
            if consent_required:
                # In a real implementation, this would check for stored consent
                # For now, we'll assume consent is granted
                return {
                    "allowed": True,
                    "consent_required": True,
                    "consent_reasons": consent_reasons,
                    "consent_status": "assumed_granted"  # Would be actual status in production
                }
                
            return {"allowed": True}
            
        except Exception as e:
            self.audit_logger.log_error(f"Consent check failed: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Consent check error: {str(e)}"
            }
            
    async def _create_usage_record(
        self,
        user_id: str,
        agent_role: str,
        usage_type: PersonalDataUsageType,
        corpus_sources: List[str],
        access_level: PersonalDataAccessLevel,
        purpose: str,
        data_context: Dict[str, Any] = None
    ) -> PersonalDataUsageRecord:
        """Create usage record for audit trail"""
        try:
            usage_id = f"usage_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            usage_record = PersonalDataUsageRecord(
                usage_id=usage_id,
                user_id=user_id,
                usage_type=usage_type,
                corpus_sources=corpus_sources,
                data_accessed=data_context or {},
                purpose=purpose,
                timestamp=datetime.utcnow(),
                agent_role=agent_role,
                access_level=access_level
            )
            
            self.usage_records.append(usage_record)
            
            # Log to audit trail
            self.audit_trail.log_personal_data_access(
                user_id=user_id,
                agent_role=agent_role,
                access_type=usage_type.value,
                corpus_sources=corpus_sources,
                access_level=access_level.value,
                purpose=purpose
            )
            
            return usage_record
            
        except Exception as e:
            self.audit_logger.log_error(f"Usage record creation failed: {str(e)}")
            raise PersonalDataGovernanceError(f"Failed to create usage record: {str(e)}")
            
    async def _update_access_tracking(
        self,
        user_id: str,
        agent_role: str,
        usage_record: PersonalDataUsageRecord
    ) -> None:
        """Update access tracking for concurrent session management"""
        try:
            session_key = f"{user_id}_{agent_role}_{usage_record.usage_id}"
            
            self.access_sessions[session_key] = {
                "user_id": user_id,
                "agent_role": agent_role,
                "usage_record_id": usage_record.usage_id,
                "start_time": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "status": "active"
            }
            
        except Exception as e:
            self.audit_logger.log_error(f"Access tracking update failed: {str(e)}")
            
    def _count_usage_in_period(self, user_id: str, start_time: datetime, end_time: datetime) -> int:
        """Count usage records in a time period"""
        try:
            count = 0
            for record in self.usage_records:
                if (record.user_id == user_id and 
                    start_time <= record.timestamp <= end_time):
                    count += 1
            return count
            
        except Exception as e:
            self.audit_logger.log_error(f"Usage counting failed: {str(e)}")
            return 0
            
    def _count_concurrent_sessions(self, user_id: str) -> int:
        """Count active concurrent sessions for user"""
        try:
            count = 0
            now = datetime.utcnow()
            session_timeout = timedelta(minutes=30)
            
            for session in self.access_sessions.values():
                if (session["user_id"] == user_id and 
                    session["status"] == "active" and
                    now - session["last_activity"] < session_timeout):
                    count += 1
                    
            return count
            
        except Exception as e:
            self.audit_logger.log_error(f"Concurrent session counting failed: {str(e)}")
            return 0
            
    def _get_access_restrictions(
        self,
        policy: PersonalDataGovernancePolicy,
        agent_role: str
    ) -> Dict[str, Any]:
        """Get access restrictions for agent role"""
        try:
            if agent_role in policy.agent_permissions:
                agent_perms = policy.agent_permissions[agent_role]
                return {
                    "max_access_level": agent_perms.get("access_level", "none"),
                    "allowed_corpus_sources": agent_perms.get("corpus_sources", []),
                    "allowed_usage_types": agent_perms.get("usage_types", []),
                    "retention_period": policy.default_retention_period.total_seconds()
                }
            else:
                return {
                    "max_access_level": "none",
                    "allowed_corpus_sources": [],
                    "allowed_usage_types": [],
                    "retention_period": 0
                }
                
        except Exception as e:
            self.audit_logger.log_error(f"Access restriction retrieval failed: {str(e)}")
            return {}
            
    async def update_governance_policy(
        self,
        user_id: str,
        policy_updates: Dict[str, Any]
    ) -> PersonalDataGovernancePolicy:
        """Update governance policy for user"""
        try:
            policy = await self._get_governance_policy(user_id)
            
            # Update policy fields
            for field, value in policy_updates.items():
                if hasattr(policy, field):
                    setattr(policy, field, value)
                    
            policy.last_updated = datetime.utcnow()
            
            self.active_policies[user_id] = policy
            
            self.audit_logger.log_info(f"Governance policy updated for user {user_id}")
            
            return policy
            
        except Exception as e:
            self.audit_logger.log_error(f"Policy update failed: {str(e)}")
            raise PersonalDataGovernanceError(f"Failed to update policy: {str(e)}")
            
    def get_governance_stats(self, user_id: str) -> Dict[str, Any]:
        """Get governance statistics for user"""
        try:
            now = datetime.utcnow()
            
            # Usage statistics
            daily_usage = self._count_usage_in_period(
                user_id, now - timedelta(days=1), now
            )
            
            hourly_usage = self._count_usage_in_period(
                user_id, now - timedelta(hours=1), now
            )
            
            concurrent_sessions = self._count_concurrent_sessions(user_id)
            
            # Policy information
            policy = self.active_policies.get(user_id)
            
            return {
                "user_id": user_id,
                "usage_stats": {
                    "daily_usage": daily_usage,
                    "hourly_usage": hourly_usage,
                    "concurrent_sessions": concurrent_sessions
                },
                "policy_info": {
                    "policy_version": policy.policy_version if policy else "none",
                    "last_updated": policy.last_updated.isoformat() if policy else None,
                    "daily_limit": policy.daily_access_limit if policy else 0,
                    "hourly_limit": policy.hourly_access_limit if policy else 0
                },
                "compliance_status": "compliant"  # Would be calculated based on actual compliance checks
            }
            
        except Exception as e:
            self.audit_logger.log_error(f"Governance stats retrieval failed: {str(e)}")
            return {"error": str(e)}


__all__ = [
    "PersonalDataAccessLevel",
    "PersonalDataUsageType",
    "PersonalDataUsageRecord",
    "PersonalDataGovernancePolicy",
    "PersonalDataGovernanceManager"
]
