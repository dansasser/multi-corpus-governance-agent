"""Security validation tests for governance protocol enforcement.

This module tests that all governance rules are properly enforced
at the architectural level, validating implementation against:
docs/security/protocols/governance-protocol.md
docs/security/compliance/deployment-security.md

These tests ensure that governance violations are impossible
through architectural constraints, not just prompt engineering.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from src.mcg_agent.governance.protocol import (
    GovernanceProtocol,
    AgentRole,
    CorpusType,
    ViolationSeverity,
    TaskGovernanceState
)
from src.mcg_agent.governance.decorators import (
    governance_enforced,
    ideator_tool,
    drafter_tool,
    critic_tool,
    revisor_tool,
    summarizer_tool,
    GovernanceValidationContext
)
from src.mcg_agent.governance.context import (
    AgentContext,
    AgentContextBuilder,
    create_agent_context
)
from src.mcg_agent.utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    UnauthorizedRAGAccessError,
    MVLMRequiredError,
    SecurityValidationError
)


@pytest.fixture
def governance_protocol():
    """Create a fresh governance protocol instance for testing."""
    return GovernanceProtocol()


@pytest.fixture  
def sample_task_id():
    """Generate a sample task ID."""
    return str(uuid4())


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return str(uuid4())


class TestGovernanceProtocol:
    """Test core governance protocol enforcement."""
    
    @pytest.mark.asyncio
    async def test_agent_permission_matrix_completeness(self, governance_protocol):
        """Test that all agent roles have defined permissions."""
        
        # Verify all agent roles are defined
        expected_roles = {
            AgentRole.IDEATOR,
            AgentRole.DRAFTER,
            AgentRole.CRITIC,
            AgentRole.REVISOR,
            AgentRole.SUMMARIZER
        }
        
        actual_roles = set(governance_protocol.AGENT_PERMISSIONS.keys())
        assert actual_roles == expected_roles, f"Missing agent roles: {expected_roles - actual_roles}"
        
        # Verify each role has proper permission structure
        for role, permissions in governance_protocol.AGENT_PERMISSIONS.items():
            assert permissions.agent_role == role
            assert isinstance(permissions.max_api_calls, int)
            assert permissions.max_api_calls >= 0
            assert isinstance(permissions.corpus_access, list)
            assert isinstance(permissions.rag_access, bool)
            assert isinstance(permissions.mvlm_access, bool)
    
    @pytest.mark.asyncio
    async def test_task_governance_initialization(self, governance_protocol, sample_task_id, sample_user_id):
        """Test task governance state initialization."""
        
        task_state = await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id,
            classification="standard"
        )
        
        assert task_state.task_id == sample_task_id
        assert task_state.user_id == sample_user_id
        assert task_state.classification == "standard"
        assert task_state.created_at is not None
        assert len(task_state.violations) == 0
        assert sample_task_id in governance_protocol.active_tasks
    
    @pytest.mark.asyncio
    async def test_ideator_api_call_limits(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that Ideator cannot exceed 2 API calls per task."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # First call should succeed
        assert await governance_protocol.validate_api_call(
            agent_role=AgentRole.IDEATOR,
            task_id=sample_task_id
        )
        
        # Second call should succeed
        assert await governance_protocol.validate_api_call(
            agent_role=AgentRole.IDEATOR,
            task_id=sample_task_id
        )
        
        # Third call should raise APICallLimitExceededError
        with pytest.raises(APICallLimitExceededError) as exc_info:
            await governance_protocol.validate_api_call(
                agent_role=AgentRole.IDEATOR,
                task_id=sample_task_id
            )
        
        assert exc_info.value.agent_name == "ideator"
        assert exc_info.value.max_calls == 2
        assert exc_info.value.current_calls == 3
    
    @pytest.mark.asyncio
    async def test_drafter_corpus_access_restrictions(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that Drafter cannot access Personal corpus."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # Social corpus access should be allowed
        assert await governance_protocol.validate_corpus_access(
            agent_role=AgentRole.DRAFTER,
            corpus_type=CorpusType.SOCIAL,
            task_id=sample_task_id
        )
        
        # Published corpus access should be allowed
        assert await governance_protocol.validate_corpus_access(
            agent_role=AgentRole.DRAFTER,
            corpus_type=CorpusType.PUBLISHED,
            task_id=sample_task_id
        )
        
        # Personal corpus access should be denied
        with pytest.raises(UnauthorizedCorpusAccessError) as exc_info:
            await governance_protocol.validate_corpus_access(
                agent_role=AgentRole.DRAFTER,
                corpus_type=CorpusType.PERSONAL,
                task_id=sample_task_id
            )
        
        assert exc_info.value.agent_name == "drafter"
        assert exc_info.value.corpus == "personal"
        assert "social" in exc_info.value.allowed_corpora
        assert "published" in exc_info.value.allowed_corpora
    
    @pytest.mark.asyncio
    async def test_non_critic_rag_access_blocked(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that only Critic can access RAG endpoints."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # Critic should have RAG access
        assert await governance_protocol.validate_rag_access(
            agent_role=AgentRole.CRITIC,
            task_id=sample_task_id
        )
        
        # All other agents should be denied RAG access
        non_critic_agents = [
            AgentRole.IDEATOR,
            AgentRole.DRAFTER,
            AgentRole.REVISOR,
            AgentRole.SUMMARIZER
        ]
        
        for agent_role in non_critic_agents:
            with pytest.raises(UnauthorizedRAGAccessError) as exc_info:
                await governance_protocol.validate_rag_access(
                    agent_role=agent_role,
                    task_id=sample_task_id
                )
            
            assert exc_info.value.agent_name == agent_role.value
            assert "critic" in exc_info.value.authorized_agents
    
    @pytest.mark.asyncio
    async def test_summarizer_mvlm_requirements(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that Summarizer requires MVLM and cannot use API without emergency auth."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # With MVLM available, should work normally
        mvlm_decision = await governance_protocol.validate_mvlm_requirements(
            agent_role=AgentRole.SUMMARIZER,
            task_id=sample_task_id,
            mvlm_available=True
        )
        
        assert mvlm_decision["use_mvlm"] is True
        assert mvlm_decision["processing_method"] == "mvlm"
        
        # Without MVLM available, should raise MVLMRequiredError
        with pytest.raises(MVLMRequiredError) as exc_info:
            await governance_protocol.validate_mvlm_requirements(
                agent_role=AgentRole.SUMMARIZER,
                task_id=sample_task_id,
                mvlm_available=False
            )
        
        assert exc_info.value.agent_name == "summarizer"
        assert "MVLM required but unavailable" in exc_info.value.reason
    
    @pytest.mark.asyncio
    async def test_revisor_mvlm_preference_with_fallback(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that Revisor prefers MVLM but can fall back to API."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # With MVLM available, should prefer MVLM
        mvlm_decision = await governance_protocol.validate_mvlm_requirements(
            agent_role=AgentRole.REVISOR,
            task_id=sample_task_id,
            mvlm_available=True
        )
        
        assert mvlm_decision["use_mvlm"] is True
        assert mvlm_decision["can_fallback_to_api"] is True
        assert mvlm_decision["processing_method"] == "mvlm_primary"
        
        # Without MVLM available, should allow API fallback
        mvlm_decision = await governance_protocol.validate_mvlm_requirements(
            agent_role=AgentRole.REVISOR,
            task_id=sample_task_id,
            mvlm_available=False
        )
        
        assert mvlm_decision["can_fallback_to_api"] is True
        assert mvlm_decision["processing_method"] == "api_fallback"
    
    @pytest.mark.asyncio
    async def test_corpus_rate_limiting(self, governance_protocol, sample_task_id, sample_user_id):
        """Test corpus access rate limiting enforcement."""
        
        # Initialize task
        task_state = await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # Personal corpus has rate limit of 10 queries per minute
        # Simulate 10 queries within rate limit
        for i in range(10):
            assert await governance_protocol.validate_corpus_access(
                agent_role=AgentRole.IDEATOR,
                corpus_type=CorpusType.PERSONAL,
                task_id=sample_task_id
            )
        
        # 11th query should trigger rate limiting
        with pytest.raises(GovernanceViolationError) as exc_info:
            await governance_protocol.validate_corpus_access(
                agent_role=AgentRole.IDEATOR,
                corpus_type=CorpusType.PERSONAL,
                task_id=sample_task_id
            )
        
        assert exc_info.value.violation_type == "corpus_rate_limit_exceeded"
        assert "personal" in str(exc_info.value.details)


class TestGovernanceDecorators:
    """Test governance enforcement decorators for PydanticAI tools."""
    
    @pytest.mark.asyncio
    async def test_governance_enforced_decorator_permission_validation(self):
        """Test that governance_enforced decorator validates permissions."""
        
        @governance_enforced(
            permissions=["corpus_access"],
            max_calls=1
        )
        async def test_tool(ctx, query: str):
            return f"Processed: {query}"
        
        # Mock RunContext with agent context
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.agent_role = "ideator"
        mock_ctx.deps.task_id = str(uuid4())
        
        # Mock governance protocol validation
        with patch('src.mcg_agent.governance.decorators.governance_protocol') as mock_protocol:
            mock_protocol.validate_agent_permissions = AsyncMock(return_value=True)
            mock_protocol.validate_api_call = AsyncMock(return_value=True)
            
            with patch('src.mcg_agent.governance.decorators._log_tool_execution_start') as mock_log_start:
                mock_log_start.return_value = None
                
                with patch('src.mcg_agent.governance.decorators._log_tool_execution_success') as mock_log_success:
                    mock_log_success.return_value = None
                    
                    result = await test_tool(mock_ctx, "test query")
                    assert result == "Processed: test query"
                    
                    # Verify governance validation was called
                    mock_protocol.validate_agent_permissions.assert_called_once()
                    mock_protocol.validate_api_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ideator_tool_decorator_enforces_constraints(self):
        """Test that ideator_tool decorator enforces Ideator-specific constraints."""
        
        @ideator_tool(
            permissions=["outline_generation"],
            max_api_calls=2
        )
        async def ideator_outline_tool(ctx, prompt: str):
            return {"outline": "Generated outline", "status": "success"}
        
        # Mock RunContext
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.agent_role = "ideator"
        mock_ctx.deps.task_id = str(uuid4())
        
        # Mock all validation functions
        with patch('src.mcg_agent.governance.decorators._validate_agent_permissions') as mock_validate_perms:
            mock_validate_perms.return_value = None
            
            with patch('src.mcg_agent.governance.decorators._validate_api_call_limits') as mock_validate_calls:
                mock_validate_calls.return_value = None
                
                with patch('src.mcg_agent.governance.decorators._validate_corpus_access') as mock_validate_corpus:
                    mock_validate_corpus.return_value = None
                    
                    with patch('src.mcg_agent.governance.decorators._log_tool_execution_start') as mock_log_start:
                        mock_log_start.return_value = None
                        
                        with patch('src.mcg_agent.governance.decorators._log_tool_execution_success') as mock_log_success:
                            mock_log_success.return_value = None
                            
                            with patch('src.mcg_agent.governance.decorators._validate_tool_output') as mock_validate_output:
                                mock_validate_output.return_value = None
                                
                                result = await ideator_outline_tool(mock_ctx, "Generate outline for...")
                                
                                assert result["status"] == "success"
                                assert "outline" in result
                                
                                # Verify Ideator-specific validations were called
                                mock_validate_perms.assert_called_once()
                                mock_validate_calls.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_critic_tool_rag_access_validation(self):
        """Test that critic_tool validates RAG access permissions."""
        
        @critic_tool(
            permissions=["truth_validation"],
            rag_access=True
        )
        async def critic_rag_tool(ctx, claim: str):
            return {"validation": "verified", "sources": ["source1", "source2"]}
        
        # Mock RunContext
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.agent_role = "critic"
        mock_ctx.deps.task_id = str(uuid4())
        
        # Mock validation functions
        with patch('src.mcg_agent.governance.decorators._validate_agent_permissions') as mock_validate_perms:
            mock_validate_perms.return_value = None
            
            with patch('src.mcg_agent.governance.decorators._validate_rag_access') as mock_validate_rag:
                mock_validate_rag.return_value = None
                
                with patch('src.mcg_agent.governance.decorators._log_tool_execution_start') as mock_log_start:
                    mock_log_start.return_value = None
                    
                    with patch('src.mcg_agent.governance.decorators._log_tool_execution_success') as mock_log_success:
                        mock_log_success.return_value = None
                        
                        with patch('src.mcg_agent.governance.decorators._validate_tool_output') as mock_validate_output:
                            mock_validate_output.return_value = None
                            
                            result = await critic_rag_tool(mock_ctx, "Claim to validate")
                            
                            assert result["validation"] == "verified"
                            
                            # Verify RAG access validation was called
                            mock_validate_rag.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarizer_tool_mvlm_requirement_enforcement(self):
        """Test that summarizer_tool enforces MVLM-only requirement."""
        
        @summarizer_tool(
            permissions=["content_compression"],
            mvlm_required=True
        )
        async def summarizer_compress_tool(ctx, content: str):
            return {"compressed": "Summary...", "keywords": ["key1", "key2"]}
        
        # Mock RunContext
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.agent_role = "summarizer"
        mock_ctx.deps.task_id = str(uuid4())
        
        # Mock validation functions
        with patch('src.mcg_agent.governance.decorators._validate_agent_permissions') as mock_validate_perms:
            mock_validate_perms.return_value = None
            
            with patch('src.mcg_agent.governance.decorators._validate_mvlm_requirements') as mock_validate_mvlm:
                mock_validate_mvlm.return_value = None
                
                with patch('src.mcg_agent.governance.decorators._log_tool_execution_start') as mock_log_start:
                    mock_log_start.return_value = None
                    
                    with patch('src.mcg_agent.governance.decorators._log_tool_execution_success') as mock_log_success:
                        mock_log_success.return_value = None
                        
                        with patch('src.mcg_agent.governance.decorators._validate_tool_output') as mock_validate_output:
                            mock_validate_output.return_value = None
                            
                            result = await summarizer_compress_tool(mock_ctx, "Long content to compress...")
                            
                            assert "compressed" in result
                            assert "keywords" in result
                            
                            # Verify MVLM requirement validation was called
                            mock_validate_mvlm.assert_called_once()


class TestAgentContext:
    """Test AgentContext system for PydanticAI integration."""
    
    def test_agent_context_creation_with_builder(self):
        """Test AgentContext creation using builder pattern."""
        
        task_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        builder = AgentContextBuilder()
        context = (builder
                   .with_task_id(task_id)
                   .with_agent_role(AgentRole.IDEATOR)
                   .with_input_content("Test input content")
                   .with_user_session(user_id, session_id, "192.168.1.1")
                   .with_output_mode("chat")
                   .with_classification("standard")
                   .build())
        
        assert context.task_id == task_id
        assert context.agent_role == "ideator"
        assert context.input_content == "Test input content"
        assert context.user_id == user_id
        assert context.session_id == session_id
        assert context.ip_address == "192.168.1.1"
        assert context.output_mode == "chat"
        assert context.classification == "standard"
    
    def test_agent_context_permission_validation(self):
        """Test that AgentContext validates permissions correctly."""
        
        context = create_agent_context(
            task_id=str(uuid4()),
            agent_role=AgentRole.DRAFTER,
            input_content="Test content"
        )
        
        # Drafter should have limited corpus access
        assert context.can_access_corpus("social") is True
        assert context.can_access_corpus("published") is True
        assert context.can_access_corpus("personal") is False
        
        # Drafter should not have RAG access
        assert context.can_use_rag() is False
    
    def test_agent_context_api_call_tracking(self):
        """Test API call tracking in AgentContext."""
        
        context = create_agent_context(
            task_id=str(uuid4()),
            agent_role=AgentRole.IDEATOR,
            input_content="Test content"
        )
        
        # Initially no API calls made
        assert context.api_calls_made == 0
        assert context.get_remaining_api_calls() == 2  # Ideator max is 2
        
        # Increment API calls
        context.increment_api_calls()
        assert context.api_calls_made == 1
        assert context.get_remaining_api_calls() == 1
        
        context.increment_api_calls()
        assert context.api_calls_made == 2
        assert context.get_remaining_api_calls() == 0
    
    def test_agent_context_governance_violation_tracking(self):
        """Test governance violation tracking in AgentContext."""
        
        context = create_agent_context(
            task_id=str(uuid4()),
            agent_role=AgentRole.CRITIC,
            input_content="Test content"
        )
        
        # Initially no violations
        assert len(context.governance_violations) == 0
        
        # Add violation
        context.add_governance_violation("Attempted unauthorized corpus access")
        assert len(context.governance_violations) == 1
        assert "unauthorized corpus access" in context.governance_violations[0]
    
    def test_agent_context_attribution_chain(self):
        """Test attribution chain management in AgentContext."""
        
        context = create_agent_context(
            task_id=str(uuid4()),
            agent_role=AgentRole.IDEATOR,
            input_content="Test content"
        )
        
        # Initially empty attribution chain
        assert len(context.attribution_chain) == 0
        
        # Add attribution
        attribution = {
            "attribution_id": str(uuid4()),
            "source_type": "corpus",
            "source_id": "msg_123",
            "content_hash": "abc123",
            "agent_role": "ideator",
            "task_id": context.task_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        context.add_attribution(attribution)
        assert len(context.attribution_chain) == 1
        assert context.attribution_chain[0]["source_type"] == "corpus"
    
    def test_agent_context_summary_generation(self):
        """Test AgentContext summary generation for logging."""
        
        context = create_agent_context(
            task_id=str(uuid4()),
            agent_role=AgentRole.REVISOR,
            input_content="Test content",
            output_mode="writing",
            classification="sensitive"
        )
        
        # Add some state
        context.increment_api_calls()
        context.add_governance_violation("Test violation")
        
        summary = context.to_summary()
        
        assert summary["task_id"] == context.task_id
        assert summary["agent_role"] == "revisor"
        assert summary["api_calls_made"] == 1
        assert summary["governance_violations_count"] == 1
        assert summary["output_mode"] == "writing"
        assert summary["classification"] == "sensitive"
        assert "created_at" in summary
        assert "last_updated" in summary


class TestSecurityValidation:
    """Test overall security validation requirements."""
    
    @pytest.mark.asyncio
    async def test_complete_governance_workflow(self, governance_protocol, sample_task_id, sample_user_id):
        """Test complete governance workflow from task init to finalization."""
        
        # Initialize task
        task_state = await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id,
            classification="standard"
        )
        
        # Simulate Ideator stage (2 API calls, corpus access)
        await governance_protocol.validate_agent_permissions(
            agent_role=AgentRole.IDEATOR,
            task_id=sample_task_id,
            required_permissions=["corpus_access", "outline_generation"]
        )
        
        await governance_protocol.validate_corpus_access(
            agent_role=AgentRole.IDEATOR,
            corpus_type=CorpusType.PERSONAL,
            task_id=sample_task_id
        )
        
        await governance_protocol.validate_api_call(
            agent_role=AgentRole.IDEATOR,
            task_id=sample_task_id
        )
        
        # Simulate Critic stage (RAG access)
        await governance_protocol.validate_rag_access(
            agent_role=AgentRole.CRITIC,
            task_id=sample_task_id
        )
        
        # Finalize task
        summary = await governance_protocol.finalize_task_governance(sample_task_id)
        
        assert summary["task_id"] == sample_task_id
        assert summary["api_calls_by_agent"][AgentRole.IDEATOR] == 1
        assert summary["corpus_accesses"] == 1
        assert summary["rag_queries"] == 0  # Didn't actually increment in this test
        assert summary["governance_violations"] == 0
        assert summary["completed_successfully"] is True
    
    @pytest.mark.asyncio
    async def test_security_violation_detection_and_logging(self, governance_protocol, sample_task_id, sample_user_id):
        """Test that security violations are properly detected and logged."""
        
        # Initialize task
        await governance_protocol.initialize_task_governance(
            task_id=sample_task_id,
            user_id=sample_user_id
        )
        
        # Attempt unauthorized RAG access (should fail)
        with pytest.raises(UnauthorizedRAGAccessError):
            await governance_protocol.validate_rag_access(
                agent_role=AgentRole.IDEATOR,  # Not authorized for RAG
                task_id=sample_task_id
            )
        
        # Verify violation was recorded
        task_state = governance_protocol.active_tasks[sample_task_id]
        assert len(task_state.violations) > 0
        
        # Finalize task to see violation in summary
        summary = await governance_protocol.finalize_task_governance(sample_task_id)
        assert summary["governance_violations"] > 0
        assert summary["completed_successfully"] is False
    
    def test_agent_role_validation(self):
        """Test that only valid agent roles are accepted."""
        
        # Valid roles should work
        for role in ["ideator", "drafter", "critic", "revisor", "summarizer"]:
            agent_role = AgentRole(role)
            assert agent_role.value == role
        
        # Invalid role should raise ValueError
        with pytest.raises(ValueError):
            AgentRole("invalid_role")
    
    def test_corpus_type_validation(self):
        """Test that only valid corpus types are accepted."""
        
        # Valid corpus types should work
        for corpus in ["personal", "social", "published"]:
            corpus_type = CorpusType(corpus)
            assert corpus_type.value == corpus
        
        # Invalid corpus should raise ValueError
        with pytest.raises(ValueError):
            CorpusType("invalid_corpus")


# Integration test markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.security,
    pytest.mark.governance
]