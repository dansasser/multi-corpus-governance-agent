"""Database models for Multi-Corpus Governance Agent.

This module implements the complete database schema for all three corpora
as specified in the implementation plan and security documentation.

Database design follows:
- docs/security/architecture/security-architecture.md (data protection)
- IMPLEMENTATION_PLAN.md database schema specifications
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Boolean, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# PERSONAL CORPUS MODELS
# =============================================================================

class Message(Base, TimestampMixin):
    """
    Personal corpus message storage.
    
    Stores chat history, notes, and personal communications with
    full-text search and attribution tracking.
    """
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.thread_id'), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), nullable=False)  # app name, platform
    channel = Column(String(100), nullable=True)  # specific channel/room
    meta = Column(JSON, nullable=True)  # additional metadata
    
    # Full-text search support
    search_vector = Column(TSVECTOR)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_messages_thread_id', 'thread_id'),
        Index('ix_messages_timestamp', 'timestamp'),
        Index('ix_messages_role', 'role'),
        Index('ix_messages_source', 'source'),
        Index('ix_messages_search_vector', 'search_vector', postgresql_using='gin'),
        CheckConstraint("role IN ('user', 'assistant', 'system')", name='valid_role'),
        CheckConstraint("length(content) > 0", name='non_empty_content')
    )


class Thread(Base, TimestampMixin):
    """
    Personal corpus thread/conversation groupings.
    
    Groups related messages together with metadata and tags.
    """
    __tablename__ = 'threads'
    
    thread_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=True)
    participants = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_threads_started_at', 'started_at'),
        Index('ix_threads_tags', 'tags', postgresql_using='gin'),
        Index('ix_threads_participants', 'participants', postgresql_using='gin'),
    )


class Attachment(Base, TimestampMixin):
    """
    File attachments associated with messages.
    """
    __tablename__ = 'attachments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False)
    kind = Column(String(50), nullable=False)  # file, image, document, etc.
    url = Column(String(1000), nullable=True)
    filename = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    meta = Column(JSON, nullable=True)
    
    # Relationships
    message = relationship("Message", back_populates="attachments")
    
    # Indexes
    __table_args__ = (
        Index('ix_attachments_message_id', 'message_id'),
        Index('ix_attachments_kind', 'kind'),
    )


# =============================================================================
# SOCIAL CORPUS MODELS
# =============================================================================

class SocialPost(Base, TimestampMixin):
    """
    Social corpus post storage.
    
    Stores social media posts, engagement data, and metadata
    with privacy controls and attribution.
    """
    __tablename__ = 'social_posts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(50), nullable=False)  # linkedin, twitter, facebook, etc.
    post_id = Column(String(200), nullable=False)  # platform-specific ID
    content = Column(Text, nullable=False)
    author = Column(String(200), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    engagement_metrics = Column(JSON, nullable=True)  # likes, shares, comments
    hashtags = Column(ARRAY(String), nullable=True)
    mentions = Column(ARRAY(String), nullable=True)
    url = Column(String(1000), nullable=True)
    meta = Column(JSON, nullable=True)
    
    # Privacy and access control
    visibility = Column(String(20), nullable=False, default='public')  # public, private, restricted
    access_level = Column(String(20), nullable=False, default='standard')  # standard, limited, full
    
    # Full-text search support
    search_vector = Column(TSVECTOR)
    
    # Relationships
    reactions = relationship("SocialReaction", back_populates="post", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('platform', 'post_id', name='unique_platform_post'),
        Index('ix_social_posts_platform', 'platform'),
        Index('ix_social_posts_timestamp', 'timestamp'),
        Index('ix_social_posts_author', 'author'),
        Index('ix_social_posts_hashtags', 'hashtags', postgresql_using='gin'),
        Index('ix_social_posts_search_vector', 'search_vector', postgresql_using='gin'),
        Index('ix_social_posts_visibility', 'visibility'),
        CheckConstraint("visibility IN ('public', 'private', 'restricted')", name='valid_visibility'),
        CheckConstraint("access_level IN ('standard', 'limited', 'full')", name='valid_access_level'),
    )


class SocialReaction(Base, TimestampMixin):
    """
    Social post reactions and engagement tracking.
    """
    __tablename__ = 'social_reactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('social_posts.id'), nullable=False)
    reaction_type = Column(String(50), nullable=False)  # like, share, comment, etc.
    user_handle = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)  # for comments
    timestamp = Column(DateTime(timezone=True), nullable=False)
    meta = Column(JSON, nullable=True)
    
    # Relationships
    post = relationship("SocialPost", back_populates="reactions")
    
    # Indexes
    __table_args__ = (
        Index('ix_social_reactions_post_id', 'post_id'),
        Index('ix_social_reactions_type', 'reaction_type'),
        Index('ix_social_reactions_timestamp', 'timestamp'),
    )


# =============================================================================
# PUBLISHED CORPUS MODELS
# =============================================================================

class PublishedContent(Base, TimestampMixin):
    """
    Published corpus content storage.
    
    Stores articles, blogs, research papers, and other published content
    with SEO metadata and citation tracking.
    """
    __tablename__ = 'published_content'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    author = Column(String(200), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    content_type = Column(String(50), nullable=False)  # article, blog, research, book, etc.
    
    # SEO and categorization
    seo_keywords = Column(ARRAY(String), nullable=True)
    categories = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Publishing metadata
    publisher = Column(String(200), nullable=True)
    publication = Column(String(200), nullable=True)  # journal, blog name, etc.
    doi = Column(String(200), nullable=True)  # Digital Object Identifier
    isbn = Column(String(20), nullable=True)
    
    # Content metrics
    word_count = Column(Integer, nullable=True)
    reading_time_minutes = Column(Integer, nullable=True)
    
    # Full-text search support
    search_vector = Column(TSVECTOR)
    
    meta = Column(JSON, nullable=True)
    
    # Relationships
    citations = relationship("Citation", back_populates="content", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index('ix_published_content_published_at', 'published_at'),
        Index('ix_published_content_author', 'author'),
        Index('ix_published_content_content_type', 'content_type'),
        Index('ix_published_content_categories', 'categories', postgresql_using='gin'),
        Index('ix_published_content_seo_keywords', 'seo_keywords', postgresql_using='gin'),
        Index('ix_published_content_search_vector', 'search_vector', postgresql_using='gin'),
        Index('ix_published_content_url', 'url'),
        CheckConstraint("length(title) > 0", name='non_empty_title'),
        CheckConstraint("length(content) > 0", name='non_empty_content'),
    )


class Citation(Base, TimestampMixin):
    """
    Citation tracking for published content.
    """
    __tablename__ = 'citations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey('published_content.id'), nullable=False)
    cited_work_title = Column(String(500), nullable=False)
    cited_work_author = Column(String(200), nullable=True)
    cited_work_url = Column(String(1000), nullable=True)
    cited_work_doi = Column(String(200), nullable=True)
    citation_context = Column(Text, nullable=True)  # surrounding text
    page_number = Column(Integer, nullable=True)
    meta = Column(JSON, nullable=True)
    
    # Relationships
    content = relationship("PublishedContent", back_populates="citations")
    
    # Indexes
    __table_args__ = (
        Index('ix_citations_content_id', 'content_id'),
        Index('ix_citations_author', 'cited_work_author'),
        Index('ix_citations_title', 'cited_work_title'),
    )


# =============================================================================
# VOICE FINGERPRINTING MODELS
# =============================================================================

class VoiceFingerprint(Base, TimestampMixin):
    """
    Voice fingerprints for tone analysis and matching.
    
    Stores n-gram patterns, collocations, and style markers
    for each corpus to enable tone scoring.
    """
    __tablename__ = 'voice_fingerprints'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_type = Column(String(20), nullable=False)  # personal, social, published
    
    # Linguistic patterns
    collocations = Column(JSON, nullable=False)  # word pair frequencies
    cadence_markers = Column(JSON, nullable=False)  # sentence patterns, punctuation
    frequency_counts = Column(JSON, nullable=False)  # word/phrase frequencies
    n_grams = Column(JSON, nullable=True)  # 2-gram, 3-gram patterns
    
    # Metadata
    sample_size = Column(Integer, nullable=False)  # number of texts analyzed
    confidence_score = Column(Integer, nullable=False, default=0)  # 0-100
    
    # Versioning and updates
    version = Column(String(20), nullable=False, default='1.0')
    
    # Indexes
    __table_args__ = (
        Index('ix_voice_fingerprints_corpus_type', 'corpus_type'),
        Index('ix_voice_fingerprints_version', 'version'),
        CheckConstraint("corpus_type IN ('personal', 'social', 'published')", name='valid_corpus_type'),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name='valid_confidence'),
    )


# =============================================================================
# TASK EXECUTION AND AUDIT MODELS
# =============================================================================

class TaskLog(Base, TimestampMixin):
    """
    Complete audit trail for task execution.
    
    Tracks all agent actions, decisions, and outputs for
    security auditing and governance compliance.
    """
    __tablename__ = 'task_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False)
    agent_role = Column(String(20), nullable=False)
    
    # Execution details
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=False)
    
    # Performance tracking
    execution_time_ms = Column(Integer, nullable=True)
    api_calls_made = Column(Integer, nullable=False, default=0)
    corpus_queries_made = Column(Integer, nullable=False, default=0)
    
    # Governance tracking
    governance_violations = Column(JSON, nullable=True)  # any violations detected
    security_flags = Column(ARRAY(String), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False)  # success, failure, terminated
    error_message = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_task_logs_task_id', 'task_id'),
        Index('ix_task_logs_agent_role', 'agent_role'),
        Index('ix_task_logs_created_at', 'created_at'),
        Index('ix_task_logs_status', 'status'),
        CheckConstraint("agent_role IN ('ideator', 'drafter', 'critic', 'revisor', 'summarizer')", name='valid_agent_role'),
        CheckConstraint("status IN ('success', 'failure', 'terminated')", name='valid_status'),
    )


class AttributionRecord(Base, TimestampMixin):
    """
    Immutable attribution tracking for all content sources.
    
    Maintains complete provenance chain for all generated content.
    """
    __tablename__ = 'attribution_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Source information
    source_type = Column(String(20), nullable=False)  # personal, social, published, external
    source_id = Column(String(200), nullable=True)  # ID in source system
    source_url = Column(String(1000), nullable=True)
    source_author = Column(String(200), nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Content details
    content_snippet = Column(Text, nullable=False)  # actual content used
    usage_context = Column(Text, nullable=True)  # how it was used
    
    # Attribution metadata
    attribution_confidence = Column(Integer, nullable=False, default=100)  # 0-100
    human_verified = Column(Boolean, nullable=False, default=False)
    
    # Indexes
    __table_args__ = (
        Index('ix_attribution_records_task_id', 'task_id'),
        Index('ix_attribution_records_source_type', 'source_type'),
        Index('ix_attribution_records_source_id', 'source_id'),
        CheckConstraint("source_type IN ('personal', 'social', 'published', 'external')", name='valid_source_type'),
        CheckConstraint("attribution_confidence >= 0 AND attribution_confidence <= 100", name='valid_confidence'),
    )


# =============================================================================
# USER AND SESSION MODELS
# =============================================================================

class User(Base, TimestampMixin):
    """
    User accounts with role-based access control.
    """
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    # Authorization
    roles = Column(ARRAY(String), nullable=False, default=lambda: ['user'])
    permissions = Column(JSON, nullable=True)
    
    # Profile
    full_name = Column(String(200), nullable=True)
    timezone = Column(String(50), nullable=True, default='UTC')
    
    # Security tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_users_username', 'username'),
        Index('ix_users_email', 'email'),
        Index('ix_users_is_active', 'is_active'),
        Index('ix_users_roles', 'roles', postgresql_using='gin'),
    )


class UserSession(Base, TimestampMixin):
    """
    User session tracking for security and audit.
    """
    __tablename__ = 'user_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Session details
    session_token = Column(String(255), nullable=False, unique=True)
    ip_address = Column(String(45), nullable=False)  # supports IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Security
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('ix_user_sessions_user_id', 'user_id'),
        Index('ix_user_sessions_session_token', 'session_token'),
        Index('ix_user_sessions_expires_at', 'expires_at'),
        Index('ix_user_sessions_is_active', 'is_active'),
        Index('ix_user_sessions_ip_address', 'ip_address'),
    )


# =============================================================================
# SECURITY AND AUDIT LOGGING MODELS
# =============================================================================

class SecurityEvent(Base, TimestampMixin):
    """
    Security event logging for comprehensive audit trail.
    
    Captures all security-relevant events including authentication,
    authorization, governance violations, and system events.
    """
    __tablename__ = 'security_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event classification
    event_type = Column(String(50), nullable=False)  # authentication, authorization, governance, system
    event_subtype = Column(String(100), nullable=False)  # login, violation, api_call, etc.
    severity = Column(String(20), nullable=False, default='info')  # critical, high, medium, low, info
    
    # Context information
    user_id = Column(UUID(as_uuid=True), nullable=True)  # May be null for system events
    task_id = Column(UUID(as_uuid=True), nullable=True)  # May be null for non-task events
    agent_name = Column(String(20), nullable=True)  # ideator, drafter, critic, revisor, summarizer
    session_id = Column(String(255), nullable=True)
    
    # Network information
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    
    # Event details
    success = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Additional event-specific data
    
    # Response and impact
    response_actions = Column(ARRAY(String), nullable=True)  # Actions taken in response
    containment_applied = Column(Boolean, nullable=False, default=False)
    
    # Indexes for security monitoring
    __table_args__ = (
        Index('ix_security_events_event_type', 'event_type'),
        Index('ix_security_events_severity', 'severity'),
        Index('ix_security_events_created_at', 'created_at'),
        Index('ix_security_events_user_id', 'user_id'),
        Index('ix_security_events_task_id', 'task_id'),
        Index('ix_security_events_agent_name', 'agent_name'),
        Index('ix_security_events_ip_address', 'ip_address'),
        Index('ix_security_events_success', 'success'),
        CheckConstraint("event_type IN ('authentication', 'authorization', 'governance', 'system', 'tool_execution')", name='valid_event_type'),
        CheckConstraint("severity IN ('critical', 'high', 'medium', 'low', 'info')", name='valid_severity'),
    )


class GovernanceViolationLog(Base, TimestampMixin):
    """
    Detailed governance violation tracking.
    
    Maintains comprehensive records of all governance rule violations
    for security analysis and compliance reporting.
    """
    __tablename__ = 'governance_violation_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Violation identification
    violation_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    violation_type = Column(String(100), nullable=False)  # api_limit_exceeded, unauthorized_access, etc.
    severity = Column(String(20), nullable=False)
    
    # Context
    task_id = Column(UUID(as_uuid=True), nullable=False)
    agent_role = Column(String(20), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Violation details
    rule_violated = Column(String(200), nullable=False)  # Specific rule from governance protocol
    attempted_action = Column(Text, nullable=False)  # What the agent tried to do
    current_state = Column(JSON, nullable=False)  # Agent state when violation occurred
    violation_context = Column(JSON, nullable=False)  # Tool call, parameters, etc.
    
    # Enforcement actions
    enforcement_action = Column(String(50), nullable=False)  # blocked, terminated, logged
    containment_actions = Column(ARRAY(String), nullable=True)
    
    # Investigation and resolution
    investigation_status = Column(String(20), nullable=False, default='pending')  # pending, reviewed, resolved
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    
    # Indexes for compliance reporting
    __table_args__ = (
        Index('ix_governance_violations_violation_type', 'violation_type'),
        Index('ix_governance_violations_severity', 'severity'),
        Index('ix_governance_violations_task_id', 'task_id'),
        Index('ix_governance_violations_agent_role', 'agent_role'),
        Index('ix_governance_violations_created_at', 'created_at'),
        Index('ix_governance_violations_investigation_status', 'investigation_status'),
        CheckConstraint("agent_role IN ('ideator', 'drafter', 'critic', 'revisor', 'summarizer')", name='valid_agent_role'),
        CheckConstraint("severity IN ('critical', 'high', 'medium', 'low')", name='valid_severity'),
        CheckConstraint("enforcement_action IN ('blocked', 'terminated', 'logged', 'quarantined')", name='valid_enforcement'),
        CheckConstraint("investigation_status IN ('pending', 'reviewing', 'reviewed', 'resolved', 'dismissed')", name='valid_status'),
    )


class APICallLog(Base, TimestampMixin):
    """
    API call tracking for governance and performance monitoring.
    
    Tracks all API calls made by agents for limit enforcement
    and usage analysis.
    """
    __tablename__ = 'api_call_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Call identification
    call_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False)
    agent_role = Column(String(20), nullable=False)
    
    # API details
    endpoint = Column(String(200), nullable=False)  # Which API endpoint was called
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    request_data = Column(JSON, nullable=True)  # Request parameters (sanitized)
    response_status = Column(Integer, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)  # For LLM API calls
    cost_estimate = Column(Integer, nullable=True)  # Cost in cents
    
    # Governance tracking
    call_sequence = Column(Integer, nullable=False)  # 1st, 2nd call etc. for this agent/task
    governance_approved = Column(Boolean, nullable=False, default=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Indexes for performance monitoring
    __table_args__ = (
        Index('ix_api_call_logs_task_id', 'task_id'),
        Index('ix_api_call_logs_agent_role', 'agent_role'),
        Index('ix_api_call_logs_created_at', 'created_at'),
        Index('ix_api_call_logs_endpoint', 'endpoint'),
        Index('ix_api_call_logs_response_status', 'response_status'),
        Index('ix_api_call_logs_call_sequence', 'call_sequence'),
        CheckConstraint("agent_role IN ('ideator', 'drafter', 'critic', 'revisor', 'summarizer')", name='valid_agent_role'),
        CheckConstraint("method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')", name='valid_method'),
        CheckConstraint("response_status >= 100 AND response_status < 600", name='valid_status'),
    )


class CorpusAccessLog(Base, TimestampMixin):
    """
    Corpus access tracking for governance and audit.
    
    Monitors all corpus queries for permission validation
    and usage analytics.
    """
    __tablename__ = 'corpus_access_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Access identification
    access_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), nullable=False)
    agent_role = Column(String(20), nullable=False)
    
    # Corpus details
    corpus_type = Column(String(20), nullable=False)  # personal, social, published
    query_text = Column(Text, nullable=False)
    query_parameters = Column(JSON, nullable=True)
    
    # Results
    results_count = Column(Integer, nullable=False, default=0)
    results_returned = Column(Integer, nullable=False, default=0)  # May be limited
    
    # Performance
    query_time_ms = Column(Integer, nullable=True)
    
    # Governance
    access_granted = Column(Boolean, nullable=False)
    denial_reason = Column(String(200), nullable=True)
    rate_limit_applied = Column(Boolean, nullable=False, default=False)
    
    # Attribution tracking
    attribution_records_created = Column(Integer, nullable=False, default=0)
    
    # Indexes for governance monitoring
    __table_args__ = (
        Index('ix_corpus_access_logs_task_id', 'task_id'),
        Index('ix_corpus_access_logs_agent_role', 'agent_role'),
        Index('ix_corpus_access_logs_corpus_type', 'corpus_type'),
        Index('ix_corpus_access_logs_created_at', 'created_at'),
        Index('ix_corpus_access_logs_access_granted', 'access_granted'),
        CheckConstraint("agent_role IN ('ideator', 'drafter', 'critic', 'revisor', 'summarizer')", name='valid_agent_role'),
        CheckConstraint("corpus_type IN ('personal', 'social', 'published')", name='valid_corpus_type'),
    )


class IncidentLog(Base, TimestampMixin):
    """
    Security incident tracking and management.
    
    Manages security incidents from detection through resolution
    following incident response procedures.
    """
    __tablename__ = 'incident_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Incident identification
    incident_id = Column(String(50), nullable=False, unique=True)  # Human-readable ID (INC-2024-001)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Classification
    incident_type = Column(String(50), nullable=False)  # governance_violation, security_breach, etc.
    severity = Column(String(20), nullable=False)  # P0, P1, P2, P3
    priority = Column(String(20), nullable=False, default='medium')  # critical, high, medium, low
    
    # Context
    affected_systems = Column(ARRAY(String), nullable=True)
    affected_users = Column(ARRAY(String), nullable=True)
    related_tasks = Column(ARRAY(String), nullable=True)  # Task IDs
    
    # Response
    status = Column(String(20), nullable=False, default='open')  # open, investigating, resolved, closed
    assigned_to = Column(String(100), nullable=True)
    response_team = Column(ARRAY(String), nullable=True)
    
    # Timeline
    detected_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Response metrics
    time_to_acknowledge_minutes = Column(Integer, nullable=True)
    time_to_resolve_minutes = Column(Integer, nullable=True)
    
    # Impact assessment
    impact_description = Column(Text, nullable=True)
    data_affected = Column(Boolean, nullable=False, default=False)
    service_disrupted = Column(Boolean, nullable=False, default=False)
    
    # Resolution
    root_cause = Column(Text, nullable=True)
    remediation_actions = Column(JSON, nullable=True)  # List of actions taken
    preventive_measures = Column(JSON, nullable=True)  # Future prevention steps
    
    # Post-incident
    lessons_learned = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, nullable=False, default=False)
    
    # Indexes for incident management
    __table_args__ = (
        Index('ix_incident_logs_incident_id', 'incident_id'),
        Index('ix_incident_logs_severity', 'severity'),
        Index('ix_incident_logs_status', 'status'),
        Index('ix_incident_logs_detected_at', 'detected_at'),
        Index('ix_incident_logs_incident_type', 'incident_type'),
        Index('ix_incident_logs_assigned_to', 'assigned_to'),
        CheckConstraint("severity IN ('P0', 'P1', 'P2', 'P3')", name='valid_severity'),
        CheckConstraint("priority IN ('critical', 'high', 'medium', 'low')", name='valid_priority'),
        CheckConstraint("status IN ('open', 'investigating', 'contained', 'resolved', 'closed')", name='valid_status'),
    )


class ComplianceReport(Base, TimestampMixin):
    """
    Compliance reporting and validation tracking.
    
    Maintains records of compliance checks and validation
    results for audit and regulatory requirements.
    """
    __tablename__ = 'compliance_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report identification
    report_id = Column(String(50), nullable=False, unique=True)  # COMP-2024-001
    report_type = Column(String(50), nullable=False)  # governance, security, privacy, etc.
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Generation metadata
    generated_by = Column(String(100), nullable=False)  # User or system
    generation_method = Column(String(20), nullable=False)  # automatic, manual
    
    # Report content
    summary = Column(Text, nullable=False)
    findings = Column(JSON, nullable=False)  # Detailed findings
    metrics = Column(JSON, nullable=False)  # Compliance metrics
    
    # Validation
    validation_status = Column(String(20), nullable=False, default='pending')  # pending, validated, rejected
    validated_by = Column(String(100), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    # Follow-up actions
    action_items = Column(JSON, nullable=True)  # Required actions
    next_review_date = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for compliance tracking
    __table_args__ = (
        Index('ix_compliance_reports_report_type', 'report_type'),
        Index('ix_compliance_reports_period_start', 'period_start'),
        Index('ix_compliance_reports_validation_status', 'validation_status'),
        Index('ix_compliance_reports_generated_by', 'generated_by'),
        CheckConstraint("generation_method IN ('automatic', 'manual')", name='valid_generation_method'),
        CheckConstraint("validation_status IN ('pending', 'validated', 'rejected', 'expired')", name='valid_validation_status'),
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_search_vector_trigger():
    """
    SQL function and trigger to automatically update search vectors.
    This should be run after table creation.
    """
    return """
    -- Function to update search vector
    CREATE OR REPLACE FUNCTION update_search_vector() RETURNS TRIGGER AS $$
    BEGIN
        IF TG_TABLE_NAME = 'messages' THEN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
        ELSIF TG_TABLE_NAME = 'social_posts' THEN
            NEW.search_vector := to_tsvector('english', 
                COALESCE(NEW.content, '') || ' ' || 
                COALESCE(array_to_string(NEW.hashtags, ' '), '')
            );
        ELSIF TG_TABLE_NAME = 'published_content' THEN
            NEW.search_vector := to_tsvector('english', 
                COALESCE(NEW.title, '') || ' ' || 
                COALESCE(NEW.content, '') || ' ' ||
                COALESCE(NEW.summary, '') || ' ' ||
                COALESCE(array_to_string(NEW.seo_keywords, ' '), '')
            );
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Triggers for each table
    CREATE TRIGGER update_messages_search_vector
        BEFORE INSERT OR UPDATE ON messages
        FOR EACH ROW EXECUTE FUNCTION update_search_vector();
        
    CREATE TRIGGER update_social_posts_search_vector
        BEFORE INSERT OR UPDATE ON social_posts
        FOR EACH ROW EXECUTE FUNCTION update_search_vector();
        
    CREATE TRIGGER update_published_content_search_vector
        BEFORE INSERT OR UPDATE ON published_content
        FOR EACH ROW EXECUTE FUNCTION update_search_vector();
    """


def create_security_audit_functions():
    """
    SQL functions for automated security audit and compliance tracking.
    These functions support incident response and compliance reporting.
    """
    return """
    -- Function to automatically calculate incident response times
    CREATE OR REPLACE FUNCTION update_incident_response_times() RETURNS TRIGGER AS $$
    BEGIN
        -- Calculate time to acknowledge
        IF NEW.acknowledged_at IS NOT NULL AND OLD.acknowledged_at IS NULL THEN
            NEW.time_to_acknowledge_minutes := EXTRACT(EPOCH FROM (NEW.acknowledged_at - NEW.detected_at)) / 60;
        END IF;
        
        -- Calculate time to resolve
        IF NEW.resolved_at IS NOT NULL AND OLD.resolved_at IS NULL THEN
            NEW.time_to_resolve_minutes := EXTRACT(EPOCH FROM (NEW.resolved_at - NEW.detected_at)) / 60;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Trigger for incident response time calculation
    CREATE TRIGGER update_incident_response_times_trigger
        BEFORE UPDATE ON incident_logs
        FOR EACH ROW EXECUTE FUNCTION update_incident_response_times();
    
    -- Function to generate incident IDs
    CREATE OR REPLACE FUNCTION generate_incident_id() RETURNS TRIGGER AS $$
    DECLARE
        year_suffix TEXT;
        sequence_num INTEGER;
    BEGIN
        -- Get current year suffix
        year_suffix := EXTRACT(YEAR FROM NOW())::TEXT;
        
        -- Get next sequence number for this year
        SELECT COALESCE(MAX(CAST(SUBSTRING(incident_id FROM 'INC-' || year_suffix || '-(.*)') AS INTEGER)), 0) + 1
        INTO sequence_num
        FROM incident_logs
        WHERE incident_id LIKE 'INC-' || year_suffix || '-%';
        
        -- Generate incident ID
        NEW.incident_id := 'INC-' || year_suffix || '-' || LPAD(sequence_num::TEXT, 3, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Trigger for incident ID generation
    CREATE TRIGGER generate_incident_id_trigger
        BEFORE INSERT ON incident_logs
        FOR EACH ROW EXECUTE FUNCTION generate_incident_id();
    
    -- Function to auto-generate compliance report IDs
    CREATE OR REPLACE FUNCTION generate_compliance_report_id() RETURNS TRIGGER AS $$
    DECLARE
        year_suffix TEXT;
        sequence_num INTEGER;
        type_prefix TEXT;
    BEGIN
        -- Get current year suffix
        year_suffix := EXTRACT(YEAR FROM NOW())::TEXT;
        
        -- Create type prefix
        type_prefix := UPPER(LEFT(NEW.report_type, 3));
        
        -- Get next sequence number
        SELECT COALESCE(MAX(CAST(SUBSTRING(report_id FROM type_prefix || '-' || year_suffix || '-(.*)') AS INTEGER)), 0) + 1
        INTO sequence_num
        FROM compliance_reports
        WHERE report_id LIKE type_prefix || '-' || year_suffix || '-%';
        
        -- Generate report ID
        NEW.report_id := type_prefix || '-' || year_suffix || '-' || LPAD(sequence_num::TEXT, 3, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Trigger for compliance report ID generation
    CREATE TRIGGER generate_compliance_report_id_trigger
        BEFORE INSERT ON compliance_reports
        FOR EACH ROW EXECUTE FUNCTION generate_compliance_report_id();
    """


def create_governance_monitoring_views():
    """
    SQL views for governance and security monitoring dashboards.
    These views support real-time monitoring and compliance reporting.
    """
    return """
    -- View for governance violation monitoring
    CREATE OR REPLACE VIEW governance_violation_summary AS
    SELECT 
        DATE(created_at) as violation_date,
        agent_role,
        violation_type,
        severity,
        COUNT(*) as violation_count,
        COUNT(CASE WHEN investigation_status = 'resolved' THEN 1 END) as resolved_count,
        AVG(CASE WHEN resolved_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600 
            END) as avg_resolution_hours
    FROM governance_violation_logs
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY DATE(created_at), agent_role, violation_type, severity
    ORDER BY violation_date DESC, violation_count DESC;
    
    -- View for API call monitoring
    CREATE OR REPLACE VIEW api_call_monitoring AS
    SELECT 
        DATE(created_at) as call_date,
        agent_role,
        endpoint,
        COUNT(*) as call_count,
        AVG(latency_ms) as avg_latency_ms,
        COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count,
        SUM(COALESCE(tokens_used, 0)) as total_tokens,
        SUM(COALESCE(cost_estimate, 0)) as total_cost_cents
    FROM api_call_logs
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY DATE(created_at), agent_role, endpoint
    ORDER BY call_date DESC, call_count DESC;
    
    -- View for security event monitoring
    CREATE OR REPLACE VIEW security_event_dashboard AS
    SELECT 
        DATE(created_at) as event_date,
        event_type,
        event_subtype,
        severity,
        COUNT(*) as event_count,
        COUNT(CASE WHEN success = true THEN 1 END) as success_count,
        COUNT(CASE WHEN success = false THEN 1 END) as failure_count,
        COUNT(DISTINCT user_id) as unique_users_affected,
        COUNT(DISTINCT ip_address) as unique_ips
    FROM security_events
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY DATE(created_at), event_type, event_subtype, severity
    ORDER BY event_date DESC, event_count DESC;
    
    -- View for compliance metrics
    CREATE OR REPLACE VIEW compliance_metrics AS
    SELECT 
        'governance_violations' as metric_type,
        COUNT(*) as total_count,
        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_count,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as last_24h_count
    FROM governance_violation_logs
    UNION ALL
    SELECT 
        'security_incidents' as metric_type,
        COUNT(*) as total_count,
        COUNT(CASE WHEN severity = 'P0' THEN 1 END) as critical_count,
        COUNT(CASE WHEN detected_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as last_24h_count
    FROM incident_logs
    UNION ALL
    SELECT 
        'failed_logins' as metric_type,
        COUNT(*) as total_count,
        COUNT(CASE WHEN details->>'failure_reason' LIKE '%password%' THEN 1 END) as critical_count,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as last_24h_count
    FROM security_events
    WHERE event_type = 'authentication' AND success = false;
    """