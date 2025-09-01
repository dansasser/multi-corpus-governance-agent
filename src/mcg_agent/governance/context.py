"""Agent Context system for PydanticAI RunContext dependency injection.

This module provides the AgentContext classes that are injected into
PydanticAI RunContext to provide governance, attribution, and security
context to all agent tools and operations.

Implements requirements from:
docs/security/protocols/governance-protocol.md
docs/security/architecture/security-architecture.md
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Union
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from .protocol import AgentRole, AgentPermissions, CorpusType
from ..utils.exceptions import SecurityValidationError


class OutputMode(str, Enum):
    """Output modes for agent processing."""
    CHAT = "chat"
    WRITING = "writing" 
    VOICE = "voice"


class TaskClassification(str, Enum):
    """Task classification levels for security handling."""
    STANDARD = "standard"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class Attribution:
    """Immutable attribution record for content tracking."""
    
    attribution_id: str
    source_type: str  # "corpus", "external", "generated", "user_input"
    source_id: Optional[str]  # ID in source system
    content_hash: str  # Hash of attributed content
    agent_role: AgentRole
    task_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure attribution ID is set."""
        if not self.attribution_id:
            self.attribution_id = str(uuid4())


@dataclass
class VoiceFingerprint:
    """Voice characteristics for tone scoring and preservation."""
    
    fingerprint_id: str
    source_corpus: CorpusType
    tone_characteristics: Dict[str, float]  # Tone scores and patterns
    vocabulary_patterns: Dict[str, Any]     # Word usage patterns
    style_markers: Dict[str, Any]          # Writing style indicators
    confidence_score: float                # Confidence in fingerprint accuracy
    sample_count: int                      # Number of samples used
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextPack:
    """Context pack containing multi-corpus snippets and metadata."""
    
    context_id: str
    task_id: str
    created_at: datetime
    classification: TaskClassification
    
    # Corpus snippets organized by type
    personal_snippets: List[Dict[str, Any]] = field(default_factory=list)
    social_snippets: List[Dict[str, Any]] = field(default_factory=list)
    published_snippets: List[Dict[str, Any]] = field(default_factory=list)
    
    # Voice fingerprints for tone scoring
    voice_fingerprints: Dict[str, VoiceFingerprint] = field(default_factory=dict)
    
    # Coverage and quality metrics
    coverage_score: Optional[float] = None
    diversity_score: Optional[float] = None
    relevance_score: Optional[float] = None
    
    # Attribution tracking
    attributions: List[Attribution] = field(default_factory=list)
    
    def add_snippets(self, snippets: List[Dict[str, Any]], corpus: str) -> None:
        """Add snippets from a specific corpus with attribution."""
        corpus_type = CorpusType(corpus)
        
        # Add to appropriate corpus list
        if corpus_type == CorpusType.PERSONAL:
            self.personal_snippets.extend(snippets)
        elif corpus_type == CorpusType.SOCIAL:
            self.social_snippets.extend(snippets)
        elif corpus_type == CorpusType.PUBLISHED:
            self.published_snippets.extend(snippets)
        
        # Create attributions for each snippet
        for snippet in snippets:
            attribution = Attribution(
                attribution_id=str(uuid4()),
                source_type="corpus",
                source_id=snippet.get('id', snippet.get('snippet_id')),
                content_hash=str(hash(snippet.get('content', ''))),
                agent_role=AgentRole.IDEATOR,  # Default, will be updated by calling agent
                task_id=self.task_id,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "corpus": corpus,
                    "snippet_metadata": snippet.get('metadata', {})
                }
            )
            self.attributions.append(attribution)
    
    def all_snippets(self) -> List[Dict[str, Any]]:
        """Get all snippets across all corpora."""
        return (
            self.personal_snippets + 
            self.social_snippets + 
            self.published_snippets
        )
    
    def snippets_by_corpus(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get snippets organized by corpus type."""
        return {
            "personal": self.personal_snippets,
            "social": self.social_snippets,
            "published": self.published_snippets
        }
    
    def get_corpus_count(self) -> Dict[str, int]:
        """Get count of snippets per corpus."""
        return {
            "personal": len(self.personal_snippets),
            "social": len(self.social_snippets),
            "published": len(self.published_snippets)
        }


class AgentContext(BaseModel):
    """
    Typed context passed to all PydanticAI agents via RunContext.
    
    This context provides governance, attribution, and security information
    to all agent tools and enables complete audit trails and protocol
    enforcement throughout the agent pipeline.
    """
    
    # Core identification
    task_id: str = Field(..., description="Unique task identifier")
    agent_role: str = Field(..., description="Current agent role (ideator, drafter, etc.)")
    
    # Governance state
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Agent permissions from governance protocol")
    api_calls_made: int = Field(default=0, description="Number of API calls made by this agent")
    governance_violations: List[str] = Field(default_factory=list, description="Record of any governance violations")
    
    # Content and context
    context_pack: Optional[Dict[str, Any]] = Field(default=None, description="Context pack with multi-corpus snippets")
    input_content: str = Field(..., description="Input content for this agent")
    pipeline_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata passed through pipeline")
    
    # Attribution chain (immutable)
    attribution_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Complete attribution chain")
    voice_fingerprints: Dict[str, Any] = Field(default_factory=dict, description="Voice fingerprints for tone matching")
    
    # Output configuration
    output_mode: str = Field(default="chat", description="Output mode (chat, writing, voice)")
    target_summary_length: Optional[int] = Field(default=None, description="Target length for summarization")
    
    # Security and tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    security_clearance: str = Field(default="standard", description="Security clearance level")
    classification: str = Field(default="standard", description="Task classification level")
    
    # User and session information
    user_id: Optional[str] = Field(default=None, description="User who initiated this task")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        validate_assignment = True
    
    def add_attribution(self, attribution: Dict[str, Any]) -> None:
        """
        Add attribution to the immutable chain.
        
        Args:
            attribution: Attribution record to add
        """
        self.attribution_chain.append(attribution)
        self.last_updated = datetime.now(timezone.utc)
    
    def increment_api_calls(self) -> None:
        """Increment API call counter for governance tracking."""
        self.api_calls_made += 1
        self.last_updated = datetime.now(timezone.utc)
    
    def add_governance_violation(self, violation: str) -> None:
        """
        Record governance violation for audit trail.
        
        Args:
            violation: Description of the violation
        """
        self.governance_violations.append(violation)
        self.last_updated = datetime.now(timezone.utc)
    
    def get_agent_permissions(self) -> AgentPermissions:
        """
        Get typed agent permissions for current role.
        
        Returns:
            AgentPermissions object for current agent role
        """
        from .protocol import GovernanceProtocol
        
        agent_role = AgentRole(self.agent_role)
        return GovernanceProtocol.AGENT_PERMISSIONS[agent_role]
    
    def can_access_corpus(self, corpus_type: str) -> bool:
        """
        Check if current agent can access specified corpus.
        
        Args:
            corpus_type: Corpus type to check access for
            
        Returns:
            True if access is allowed
        """
        permissions = self.get_agent_permissions()
        return CorpusType(corpus_type) in permissions.corpus_access
    
    def can_use_rag(self) -> bool:
        """
        Check if current agent can use RAG access.
        
        Returns:
            True if RAG access is allowed
        """
        permissions = self.get_agent_permissions()
        return permissions.rag_access
    
    def get_remaining_api_calls(self) -> int:
        """
        Get number of remaining API calls for current agent.
        
        Returns:
            Number of API calls remaining
        """
        permissions = self.get_agent_permissions()
        return max(0, permissions.max_api_calls - self.api_calls_made)
    
    def update_pipeline_metadata(self, key: str, value: Any) -> None:
        """
        Update pipeline metadata with new key-value pair.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.pipeline_metadata[key] = value
        self.last_updated = datetime.now(timezone.utc)
    
    def to_summary(self) -> Dict[str, Any]:
        """
        Create a summary of the agent context for logging.
        
        Returns:
            Summary dictionary suitable for logging
        """
        return {
            "task_id": self.task_id,
            "agent_role": self.agent_role,
            "api_calls_made": self.api_calls_made,
            "governance_violations_count": len(self.governance_violations),
            "attribution_chain_length": len(self.attribution_chain),
            "output_mode": self.output_mode,
            "classification": self.classification,
            "has_context_pack": self.context_pack is not None,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }


class AgentContextBuilder:
    """
    Builder class for constructing AgentContext objects with validation.
    
    Ensures proper initialization and validation of agent contexts
    according to governance protocol requirements.
    """
    
    def __init__(self):
        """Initialize context builder."""
        self.reset()
    
    def reset(self) -> "AgentContextBuilder":
        """Reset builder to initial state."""
        self._task_id: Optional[str] = None
        self._agent_role: Optional[str] = None
        self._input_content: str = ""
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._ip_address: Optional[str] = None
        self._output_mode: str = "chat"
        self._classification: str = "standard"
        self._context_pack: Optional[Dict[str, Any]] = None
        self._initial_metadata: Dict[str, Any] = {}
        return self
    
    def with_task_id(self, task_id: str) -> "AgentContextBuilder":
        """Set task ID."""
        self._task_id = task_id
        return self
    
    def with_agent_role(self, agent_role: Union[str, AgentRole]) -> "AgentContextBuilder":
        """Set agent role."""
        if isinstance(agent_role, AgentRole):
            self._agent_role = agent_role.value
        else:
            # Validate agent role
            AgentRole(agent_role)  # This will raise ValueError if invalid
            self._agent_role = agent_role
        return self
    
    def with_input_content(self, content: str) -> "AgentContextBuilder":
        """Set input content."""
        self._input_content = content
        return self
    
    def with_user_session(self, user_id: str, session_id: str, ip_address: str) -> "AgentContextBuilder":
        """Set user session information."""
        self._user_id = user_id
        self._session_id = session_id
        self._ip_address = ip_address
        return self
    
    def with_output_mode(self, output_mode: Union[str, OutputMode]) -> "AgentContextBuilder":
        """Set output mode."""
        if isinstance(output_mode, OutputMode):
            self._output_mode = output_mode.value
        else:
            OutputMode(output_mode)  # Validate
            self._output_mode = output_mode
        return self
    
    def with_classification(self, classification: Union[str, TaskClassification]) -> "AgentContextBuilder":
        """Set task classification."""
        if isinstance(classification, TaskClassification):
            self._classification = classification.value
        else:
            TaskClassification(classification)  # Validate
            self._classification = classification
        return self
    
    def with_context_pack(self, context_pack: ContextPack) -> "AgentContextBuilder":
        """Set context pack."""
        # Convert to dictionary for AgentContext
        self._context_pack = {
            "context_id": context_pack.context_id,
            "task_id": context_pack.task_id,
            "created_at": context_pack.created_at.isoformat(),
            "classification": context_pack.classification.value,
            "personal_snippets": context_pack.personal_snippets,
            "social_snippets": context_pack.social_snippets,
            "published_snippets": context_pack.published_snippets,
            "voice_fingerprints": {
                k: {
                    "fingerprint_id": v.fingerprint_id,
                    "source_corpus": v.source_corpus.value,
                    "tone_characteristics": v.tone_characteristics,
                    "vocabulary_patterns": v.vocabulary_patterns,
                    "style_markers": v.style_markers,
                    "confidence_score": v.confidence_score,
                    "sample_count": v.sample_count,
                    "created_at": v.created_at.isoformat(),
                    "metadata": v.metadata
                }
                for k, v in context_pack.voice_fingerprints.items()
            },
            "coverage_score": context_pack.coverage_score,
            "diversity_score": context_pack.diversity_score,
            "relevance_score": context_pack.relevance_score,
            "attributions": [
                {
                    "attribution_id": attr.attribution_id,
                    "source_type": attr.source_type,
                    "source_id": attr.source_id,
                    "content_hash": attr.content_hash,
                    "agent_role": attr.agent_role.value,
                    "task_id": attr.task_id,
                    "timestamp": attr.timestamp.isoformat(),
                    "metadata": attr.metadata
                }
                for attr in context_pack.attributions
            ]
        }
        return self
    
    def with_metadata(self, key: str, value: Any) -> "AgentContextBuilder":
        """Add initial metadata."""
        self._initial_metadata[key] = value
        return self
    
    def build(self) -> AgentContext:
        """
        Build and validate AgentContext.
        
        Returns:
            Configured AgentContext instance
            
        Raises:
            SecurityValidationError: If required fields are missing
        """
        # Validate required fields
        if not self._task_id:
            raise SecurityValidationError(
                validation_type="missing_task_id",
                details={"message": "Task ID is required for agent context"}
            )
        
        if not self._agent_role:
            raise SecurityValidationError(
                validation_type="missing_agent_role", 
                details={"message": "Agent role is required for agent context"}
            )
        
        # Get agent permissions for validation
        agent_role = AgentRole(self._agent_role)
        from .protocol import GovernanceProtocol
        permissions = GovernanceProtocol.AGENT_PERMISSIONS[agent_role]
        
        # Build context
        context = AgentContext(
            task_id=self._task_id,
            agent_role=self._agent_role,
            input_content=self._input_content,
            user_id=self._user_id,
            session_id=self._session_id,
            ip_address=self._ip_address,
            output_mode=self._output_mode,
            classification=self._classification,
            context_pack=self._context_pack,
            pipeline_metadata=self._initial_metadata.copy(),
            permissions={
                "max_api_calls": permissions.max_api_calls,
                "corpus_access": [c.value for c in permissions.corpus_access],
                "rag_access": permissions.rag_access,
                "mvlm_access": permissions.mvlm_access,
                "mvlm_preferred": permissions.mvlm_preferred,
                "mvlm_required": permissions.mvlm_required
            }
        )
        
        return context


def create_agent_context(
    task_id: str,
    agent_role: Union[str, AgentRole],
    input_content: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    output_mode: str = "chat",
    classification: str = "standard",
    context_pack: Optional[ContextPack] = None
) -> AgentContext:
    """
    Convenience function to create AgentContext with validation.
    
    Args:
        task_id: Unique task identifier
        agent_role: Agent role (ideator, drafter, etc.)
        input_content: Input content for the agent
        user_id: Optional user identifier
        session_id: Optional session identifier
        ip_address: Optional client IP address
        output_mode: Output mode (chat, writing, voice)
        classification: Task classification level
        context_pack: Optional context pack with corpus data
        
    Returns:
        Configured AgentContext instance
    """
    builder = AgentContextBuilder()
    
    builder.with_task_id(task_id)
    builder.with_agent_role(agent_role)
    builder.with_input_content(input_content)
    
    if user_id and session_id and ip_address:
        builder.with_user_session(user_id, session_id, ip_address)
    
    builder.with_output_mode(output_mode)
    builder.with_classification(classification)
    
    if context_pack:
        builder.with_context_pack(context_pack)
    
    return builder.build()


# Type alias for PydanticAI RunContext
AgentRunContext = AgentContext