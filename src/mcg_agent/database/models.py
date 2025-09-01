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