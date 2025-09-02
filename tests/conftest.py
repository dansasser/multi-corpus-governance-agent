"""
Pytest configuration and fixtures for MCG Agent testing.

This module provides comprehensive testing infrastructure including:
- Database fixtures for isolated testing
- Authentication mocking and user fixtures  
- Agent testing utilities with governance validation
- API client fixtures for endpoint testing
- Logging capture and validation fixtures
- Mock external service responses
"""

import pytest
import pytest_asyncio
import asyncio
from typing import Dict, Any, List, AsyncGenerator, Generator
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
import tempfile
import os

# FastAPI testing
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Database testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Application imports
from src.mcg_agent.api.app import app
from src.mcg_agent.database.connection import get_database
from src.mcg_agent.database.models import Base, User
from src.mcg_agent.auth.jwt_handler import create_access_token
from src.mcg_agent.auth.redis_client import get_redis
from src.mcg_agent.governance.protocol import governance_protocol, AgentRole
from src.mcg_agent.governance.context import create_agent_context
from src.mcg_agent.utils.logging import SecurityLogger


# ================================
# Test Configuration
# ================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings."""
    return {
        "database_url": "sqlite:///./test_mcg.db",
        "redis_url": "redis://localhost:6379/15",  # Use different DB for testing
        "jwt_secret": "test-secret-key-for-testing-only",
        "environment": "testing",
        "debug": True,
        "log_level": "DEBUG"
    }


# ================================
# Database Fixtures
# ================================

@pytest.fixture
async def test_db_engine(test_config):
    """Create test database engine."""
    engine = create_async_engine(
        test_config["database_url"],
        echo=False,  # Set to True for SQL debugging
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def clean_db(test_db_session):
    """Clean database between tests."""
    yield test_db_session
    
    # Rollback any uncommitted changes
    await test_db_session.rollback()
    
    # Clean all tables
    for table in reversed(Base.metadata.sorted_tables):
        await test_db_session.execute(table.delete())
    await test_db_session.commit()


# ================================
# Redis Fixtures  
# ================================

@pytest.fixture
async def test_redis(test_config):
    """Create test Redis connection."""
    import redis.asyncio as redis
    
    redis_client = redis.from_url(
        test_config["redis_url"],
        decode_responses=True
    )
    
    yield redis_client
    
    # Cleanup test data
    await redis_client.flushdb()
    await redis_client.close()


# ================================
# Authentication Fixtures
# ================================

@pytest.fixture
async def test_user(clean_db):
    """Create test user."""
    from src.mcg_agent.auth.password import hash_password
    
    user_data = {
        "user_id": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com", 
        "hashed_password": hash_password("testpassword"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    user = User(**user_data)
    clean_db.add(user)
    await clean_db.commit()
    await clean_db.refresh(user)
    
    return user


@pytest.fixture
def test_user_token(test_user, test_config):
    """Create JWT token for test user."""
    token_data = {
        "sub": test_user.user_id,
        "username": test_user.username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    return create_access_token(
        data=token_data,
        secret_key=test_config["jwt_secret"]
    )


@pytest.fixture
def auth_headers(test_user_token):
    """Create authentication headers for requests."""
    return {"Authorization": f"Bearer {test_user_token}"}


# ================================
# API Client Fixtures
# ================================

@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def authenticated_client(test_client, auth_headers):
    """Create authenticated test client."""
    test_client.headers.update(auth_headers)
    return test_client


@pytest.fixture
async def authenticated_async_client(async_client, auth_headers):
    """Create authenticated async client."""
    async_client.headers.update(auth_headers)
    return async_client


# ================================
# Agent Testing Fixtures
# ================================

@pytest.fixture
def mock_agent_context():
    """Create mock agent context for testing."""
    return {
        "task_id": str(uuid4()),
        "agent_role": AgentRole.IDEATOR,
        "user_id": str(uuid4()),
        "input_content": "Test prompt for agent testing",
        "output_mode": "chat",
        "max_api_calls": 2,
        "max_corpus_queries": 3,
        "governance_state": "active"
    }


@pytest.fixture
async def test_governance_context(mock_agent_context, test_user):
    """Create test governance context."""
    return await create_agent_context(
        task_id=mock_agent_context["task_id"],
        agent_role=mock_agent_context["agent_role"],
        input_content=mock_agent_context["input_content"],
        user_id=test_user.user_id,
        output_mode=mock_agent_context["output_mode"]
    )


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Test AI response content for testing purposes."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 50,
            "total_tokens": 75
        }
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Test Anthropic response for agent testing."
            }
        ],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 25,
            "output_tokens": 45
        }
    }


# ================================
# Logging and Monitoring Fixtures
# ================================

@pytest.fixture
def capture_logs():
    """Capture security logs for testing."""
    logged_events = []
    
    original_write_log = SecurityLogger._write_security_log
    
    async def mock_write_log(event):
        logged_events.append(event)
        await original_write_log(event)
    
    with patch.object(SecurityLogger, '_write_security_log', mock_write_log):
        yield logged_events


@pytest.fixture
def mock_security_alerts():
    """Mock security alert system."""
    alerts = []
    
    async def mock_alert(event):
        alerts.append(event)
    
    with patch.object(SecurityLogger, '_trigger_security_alert', mock_alert):
        with patch.object(SecurityLogger, '_trigger_critical_alert', mock_alert):
            yield alerts


# ================================
# External Service Mocks
# ================================

@pytest.fixture
def mock_external_apis():
    """Mock all external API calls."""
    mocks = {}
    
    # Mock OpenAI
    with patch('openai.AsyncClient') as mock_openai:
        mock_openai_instance = AsyncMock()
        mock_openai.return_value = mock_openai_instance
        mocks['openai'] = mock_openai_instance
        
        # Mock Anthropic
        with patch('anthropic.AsyncClient') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance  
            mocks['anthropic'] = mock_anthropic_instance
            
            yield mocks


@pytest.fixture
def mock_corpus_search():
    """Mock corpus search functionality."""
    search_results = {
        "personal": [
            {
                "id": "personal_1",
                "content": "Personal content for testing",
                "source": "notes",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "social": [
            {
                "id": "social_1", 
                "content": "Social media content for testing",
                "source": "twitter",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "published": [
            {
                "id": "published_1",
                "content": "Published article content for testing",
                "source": "blog",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }
    
    return search_results


# ================================
# Performance Testing Fixtures
# ================================

@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    timers = {}
    
    def start_timer(name: str):
        timers[name] = time.perf_counter()
    
    def stop_timer(name: str) -> float:
        if name not in timers:
            return 0.0
        elapsed = time.perf_counter() - timers[name]
        del timers[name]
        return elapsed
    
    return {"start": start_timer, "stop": stop_timer}


# ================================
# Utility Functions  
# ================================

@pytest.fixture
def assert_governance_compliance():
    """Utility to assert governance compliance in tests."""
    def _assert_compliance(logged_events, agent_role, expected_calls=None):
        """Assert that agent behavior complies with governance rules."""
        
        # Check no governance violations occurred
        violations = [e for e in logged_events if e.get("event_type") == "governance_violation"]
        assert len(violations) == 0, f"Governance violations found: {violations}"
        
        # Check API call limits if specified
        if expected_calls is not None:
            api_calls = [e for e in logged_events if e.get("event_type") == "api_call"]
            assert len(api_calls) <= expected_calls, f"Too many API calls: {len(api_calls)} > {expected_calls}"
        
        # Check agent-specific rules
        if agent_role == AgentRole.REVISOR:
            # Revisor should use MVLM primarily
            mvlm_calls = [e for e in logged_events if "mvlm" in e.get("tool_name", "").lower()]
            api_calls = [e for e in logged_events if e.get("event_type") == "api_call"]
            assert len(mvlm_calls) >= len(api_calls), "Revisor should prefer MVLM over API calls"
        
        elif agent_role == AgentRole.CRITIC:
            # Critic is the only one allowed RAG access
            rag_calls = [e for e in logged_events if e.get("event_type") == "rag_access"]
            # RAG access should be logged if used
            
        return True
    
    return _assert_compliance


@pytest.fixture  
def generate_test_data():
    """Generate test data for various scenarios."""
    def _generate(data_type: str, count: int = 1):
        if data_type == "prompts":
            return [f"Test prompt {i+1} for agent testing" for i in range(count)]
        elif data_type == "contexts":
            return [
                {
                    "task_id": str(uuid4()),
                    "prompt": f"Context prompt {i+1}",
                    "sources": ["personal", "social"] if i % 2 == 0 else ["published"]
                }
                for i in range(count)
            ]
        elif data_type == "users":
            return [
                {
                    "username": f"testuser{i+1}",
                    "email": f"test{i+1}@example.com",
                    "password": f"testpass{i+1}"
                }
                for i in range(count)
            ]
        return []
    
    return _generate


# ================================
# Cleanup Fixtures
# ================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    
    # Clean up any hanging async tasks
    tasks = [t for t in asyncio.all_tasks() if not t.done()]
    if tasks:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)