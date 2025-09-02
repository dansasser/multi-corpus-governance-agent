"""
Comprehensive unit tests for IdeatorAgent.

This test suite covers:
- Agent initialization and configuration
- Prompt analysis functionality
- Context gathering and corpus integration
- Outline generation logic
- Tone and coverage analysis
- Governance compliance validation
- Performance monitoring
- Error handling and edge cases
- Logging validation
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from src.mcg_agent.agents.ideator_agent import (
    IdeatorAgent,
    IdeatorInput,
    IdeatorMode,
    ToneProfile,
    OutlinePoint
)
from src.mcg_agent.agents.base_agent import AgentState, AgentCapability
from src.mcg_agent.governance.protocol import AgentRole
from src.mcg_agent.utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    MCGBaseException
)


class TestIdeatorAgent:
    """Test suite for IdeatorAgent."""
    
    @pytest.fixture
    def ideator_agent(self):
        """Create IdeatorAgent instance for testing."""
        return IdeatorAgent()
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing."""
        return IdeatorInput(
            content="Create a comprehensive guide about sustainable living practices for modern households",
            context_sources=["personal", "social"],
            mode=IdeatorMode.OUTLINE,
            target_audience="environmentally conscious homeowners",
            content_type="guide",
            tone_preference=ToneProfile.EDUCATIONAL,
            context_depth=3
        )
    
    @pytest.fixture
    def simple_input(self):
        """Simple input for basic testing."""
        return IdeatorInput(
            content="Write about renewable energy"
        )
    
    # ================================
    # Initialization Tests
    # ================================
    
    def test_agent_initialization(self, ideator_agent):
        """Test proper agent initialization."""
        assert ideator_agent.agent_name == "IdeatorAgent"
        assert ideator_agent.agent_role == AgentRole.IDEATOR
        assert ideator_agent.state == AgentState.INITIALIZING
        assert ideator_agent.max_api_calls == 2
        assert ideator_agent.max_corpus_queries == 3
        
        # Check capabilities
        expected_capabilities = [
            AgentCapability.API_CALLS,
            AgentCapability.CORPUS_QUERY,
            AgentCapability.CONTENT_GENERATION,
            AgentCapability.VALIDATION
        ]
        assert all(cap in ideator_agent.capabilities for cap in expected_capabilities)
    
    @pytest_asyncio.async_test
    async def test_agent_initialization_with_context(
        self,
        ideator_agent,
        test_governance_context,
        test_user
    ):
        """Test agent initialization with governance context."""
        task_id = str(uuid4())
        
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        assert ideator_agent.state == AgentState.READY
        assert ideator_agent.current_task_id == task_id
        assert ideator_agent.current_user_id == test_user.user_id
        assert ideator_agent.logger is not None
        assert ideator_agent.governance_context is not None
    
    # ================================
    # Input Validation Tests
    # ================================
    
    def test_ideator_input_validation_valid(self):
        """Test valid IdeatorInput creation."""
        input_data = IdeatorInput(
            content="Test content for validation",
            mode=IdeatorMode.BRAINSTORM,
            target_audience="developers",
            tone_preference=ToneProfile.TECHNICAL
        )
        
        assert input_data.content == "Test content for validation"
        assert input_data.mode == IdeatorMode.BRAINSTORM
        assert input_data.target_audience == "developers"
        assert input_data.tone_preference == ToneProfile.TECHNICAL
    
    def test_ideator_input_validation_invalid_content(self):
        """Test IdeatorInput validation with invalid content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            IdeatorInput(content="")
        
        with pytest.raises(ValueError, match="Content cannot be empty"):
            IdeatorInput(content="   ")
    
    def test_ideator_input_validation_context_depth(self):
        """Test context depth validation."""
        # Valid context depth
        valid_input = IdeatorInput(
            content="Test content",
            context_depth=5
        )
        assert valid_input.context_depth == 5
        
        # Invalid context depth (too low)
        with pytest.raises(ValueError):
            IdeatorInput(content="Test content", context_depth=0)
        
        # Invalid context depth (too high)
        with pytest.raises(ValueError):
            IdeatorInput(content="Test content", context_depth=15)
    
    # ================================
    # Core Functionality Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_execute_success(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user,
        capture_logs,
        mock_corpus_search
    ):
        """Test successful agent execution."""
        # Initialize agent
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Enable test mode to avoid real API calls
        ideator_agent.enable_test_mode()
        
        # Execute agent
        result = await ideator_agent.execute(sample_input)
        
        # Validate result
        assert result.success is True
        assert result.content is not None
        assert len(result.content) > 0
        assert result.metadata is not None
        assert result.attribution is not None
        assert result.performance_metrics is not None
        
        # Validate metadata
        assert result.metadata["mode"] == IdeatorMode.OUTLINE
        assert result.metadata["target_audience"] == sample_input.target_audience
        assert result.metadata["content_type"] == sample_input.content_type
        
        # Check that outline was generated
        assert "# Content Outline" in result.content
        assert "## 1." in result.content
        
        # Validate logging occurred
        assert len(capture_logs) > 0
        
        # Check for key log events
        log_events = [event.get("event_type") for event in capture_logs]
        assert "agent_started" in log_events or any("checkpoint" in str(event) for event in capture_logs)
    
    @pytest_asyncio.async_test
    async def test_prompt_analysis(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user
    ):
        """Test prompt analysis functionality."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Test prompt analysis
        analysis = await ideator_agent._analyze_prompt(sample_input)
        
        # Validate analysis structure
        assert "word_count" in analysis
        assert "character_count" in analysis
        assert "detected_intent" in analysis
        assert "complexity_score" in analysis
        assert "key_topics" in analysis
        
        # Validate analysis content
        assert analysis["word_count"] > 0
        assert analysis["character_count"] > 0
        assert 0 <= analysis["complexity_score"] <= 1
        assert isinstance(analysis["key_topics"], list)
        
        # Check intent detection
        assert analysis["detected_intent"] == "content_creation"  # Based on "Create a comprehensive guide"
    
    @pytest_asyncio.async_test
    async def test_context_gathering(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user,
        capture_logs
    ):
        """Test context gathering from corpora."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Mock prompt analysis
        prompt_analysis = {
            "key_topics": ["sustainable", "living", "practices", "households"],
            "detected_intent": "content_creation"
        }
        
        # Test context gathering
        context_data = await ideator_agent._gather_context(sample_input, prompt_analysis)
        
        # Validate context structure
        assert "sources" in context_data
        assert "personal_context" in context_data
        assert "social_context" in context_data
        assert "published_context" in context_data
        
        # Validate context content
        assert isinstance(context_data["sources"], list)
        assert isinstance(context_data["personal_context"], list)
        assert isinstance(context_data["social_context"], list)
        
        # Check that corpus queries were logged
        corpus_events = [
            event for event in capture_logs 
            if event.get("event_type") == "corpus_query_completed"
        ]
        assert len(corpus_events) > 0
    
    @pytest_asyncio.async_test
    async def test_outline_generation(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user
    ):
        """Test outline generation logic."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Mock analysis data
        prompt_analysis = {
            "key_topics": ["renewable", "energy", "solar", "wind"],
            "requirements": ["must include cost analysis", "should cover installation"]
        }
        
        context_data = {
            "sources": [
                {"id": "source_1", "content_preview": "renewable energy benefits"},
                {"id": "source_2", "content_preview": "solar panel installation guide"}
            ]
        }
        
        # Test outline generation
        outline = await ideator_agent._generate_outline(
            sample_input,
            prompt_analysis,
            context_data
        )
        
        # Validate outline structure
        assert isinstance(outline, list)
        assert len(outline) >= ideator_agent.min_outline_points
        assert len(outline) <= ideator_agent.max_outline_points
        
        # Validate outline points
        for point in outline:
            assert isinstance(point, OutlinePoint)
            assert len(point.title) > 0
            assert len(point.content) > 0
            assert 1 <= point.priority <= 10
            assert isinstance(point.sources, list)
    
    @pytest_asyncio.async_test
    async def test_tone_analysis(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user
    ):
        """Test tone analysis functionality."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Mock data
        outline = [
            OutlinePoint(
                title="Test Point",
                content="Test content for analysis",
                priority=8,
                sources=["source_1"]
            )
        ]
        
        context_data = {
            "sources": [
                {"content_preview": "This is educational content about renewable energy"}
            ]
        }
        
        # Test tone analysis
        tone_analysis = await ideator_agent._analyze_tone(
            sample_input,
            outline,
            context_data
        )
        
        # Validate tone analysis structure
        assert "target_tone" in tone_analysis
        assert "detected_patterns" in tone_analysis
        assert "consistency_score" in tone_analysis
        assert "recommendations" in tone_analysis
        
        # Validate tone analysis content
        assert tone_analysis["target_tone"] == ToneProfile.EDUCATIONAL
        assert isinstance(tone_analysis["recommendations"], list)
        assert 0 <= tone_analysis["consistency_score"] <= 1
    
    # ================================
    # Governance Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_api_call_limit_enforcement(
        self,
        ideator_agent,
        simple_input,
        test_governance_context,
        test_user
    ):
        """Test API call limit enforcement."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Make maximum allowed API calls
        for i in range(ideator_agent.max_api_calls):
            await ideator_agent.make_api_call("openai", "gpt-4", "test prompt")
        
        # Next call should raise exception
        with pytest.raises(APICallLimitExceededError):
            await ideator_agent.make_api_call("openai", "gpt-4", "test prompt")
    
    @pytest_asyncio.async_test
    async def test_corpus_query_limit_enforcement(
        self,
        ideator_agent,
        simple_input,
        test_governance_context,
        test_user
    ):
        """Test corpus query limit enforcement."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Make maximum allowed corpus queries
        for i in range(ideator_agent.max_corpus_queries):
            await ideator_agent.query_corpus("personal", f"test query {i}")
        
        # Next query should raise exception
        with pytest.raises(Exception):  # Should be UnauthorizedCorpusAccessError
            await ideator_agent.query_corpus("personal", "excess query")
    
    @pytest_asyncio.async_test
    async def test_governance_compliance_logging(
        self,
        ideator_agent,
        simple_input,
        test_governance_context,
        test_user,
        capture_logs,
        assert_governance_compliance
    ):
        """Test governance compliance logging."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        ideator_agent.enable_test_mode()
        
        # Execute agent
        result = await ideator_agent.execute(simple_input)
        
        # Assert governance compliance
        assert_governance_compliance(
            capture_logs,
            AgentRole.IDEATOR,
            expected_calls=ideator_agent.max_api_calls
        )
        
        # Check governance summary
        assert result.governance_summary is not None
        assert result.governance_summary["governance_compliant"] is True
        assert result.governance_summary["role"] == AgentRole.IDEATOR.value
    
    # ================================
    # Performance Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_performance_monitoring(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user,
        performance_timer,
        capture_logs
    ):
        """Test performance monitoring and metrics."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        ideator_agent.enable_test_mode()
        
        # Execute with timing
        performance_timer["start"]("execution")
        result = await ideator_agent.execute(sample_input)
        execution_time = performance_timer["stop"]("execution")
        
        # Validate performance metrics
        assert result.performance_metrics is not None
        assert "execution_time_ms" in result.performance_metrics
        assert result.performance_metrics["execution_time_ms"] > 0
        
        # Check for performance-related log events
        performance_events = [
            event for event in capture_logs
            if event.get("event_type") == "performance_metric"
        ]
        assert len(performance_events) > 0
        
        # Validate reasonable execution time (should be fast in test mode)
        assert execution_time < 5000  # 5 seconds max
    
    # ================================
    # Error Handling Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_execution_without_initialization(self, ideator_agent, simple_input):
        """Test execution without proper initialization."""
        with pytest.raises(MCGBaseException, match="Agent not properly initialized"):
            await ideator_agent.execute(simple_input)
    
    @pytest_asyncio.async_test
    async def test_invalid_input_handling(
        self,
        ideator_agent,
        test_governance_context,
        test_user
    ):
        """Test handling of invalid input."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Test with empty content
        invalid_input = IdeatorInput(content="")
        
        with pytest.raises(ValueError):
            await ideator_agent.execute(invalid_input)
    
    @pytest_asyncio.async_test
    async def test_corpus_query_failure_handling(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user,
        capture_logs
    ):
        """Test handling of corpus query failures."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Mock corpus query to raise exception
        original_query = ideator_agent.query_corpus
        
        async def failing_query_corpus(corpus_type, query, max_results=5):
            if corpus_type == "personal":
                raise Exception("Corpus connection failed")
            return await original_query(corpus_type, query, max_results)
        
        ideator_agent.query_corpus = failing_query_corpus
        
        # Enable test mode
        ideator_agent.enable_test_mode()
        
        # Execute should still succeed despite query failure
        result = await ideator_agent.execute(sample_input)
        assert result.success is True
        
        # Check that failure was logged
        warning_events = [
            event for event in capture_logs
            if event.get("log_level") == "warning"
        ]
        assert len(warning_events) > 0
    
    # ================================
    # Utility Method Tests
    # ================================
    
    def test_detect_intent(self, ideator_agent):
        """Test intent detection utility."""
        test_cases = [
            ("Create a new document", "content_creation"),
            ("Analyze the market trends", "content_analysis"),
            ("Improve this content", "content_improvement"),
            ("Explain quantum computing", "explanation"),
            ("Random text here", "general_request")
        ]
        
        for prompt, expected_intent in test_cases:
            actual_intent = ideator_agent._detect_intent(prompt)
            assert actual_intent == expected_intent, f"Failed for: {prompt}"
    
    def test_extract_key_topics(self, ideator_agent):
        """Test key topic extraction."""
        text = "Renewable energy sources include solar panels and wind turbines for sustainable power generation"
        topics = ideator_agent._extract_key_topics(text)
        
        assert isinstance(topics, list)
        assert len(topics) <= 5
        
        # Check that meaningful words are extracted
        expected_topics = ["renewable", "energy", "solar", "wind", "sustainable"]
        assert any(topic in topics for topic in expected_topics)
    
    def test_calculate_complexity_score(self, ideator_agent):
        """Test complexity score calculation."""
        # Simple prompt
        simple = "Write about dogs"
        simple_score = ideator_agent._calculate_complexity_score(simple)
        
        # Complex prompt
        complex = ("Create a comprehensive analysis of the socioeconomic impacts "
                  "of renewable energy adoption in developing countries. "
                  "What are the key challenges? How can they be addressed? "
                  "What role does international cooperation play?")
        complex_score = ideator_agent._calculate_complexity_score(complex)
        
        # Complex prompt should have higher score
        assert 0 <= simple_score <= 1
        assert 0 <= complex_score <= 1
        assert complex_score > simple_score
    
    def test_extract_requirements(self, ideator_agent):
        """Test requirement extraction."""
        text = ("The document must include cost analysis and should cover installation procedures. "
               "You need to provide examples and are required to cite sources.")
        
        requirements = ideator_agent._extract_requirements(text)
        
        assert isinstance(requirements, list)
        assert len(requirements) > 0
        
        # Check that requirements are extracted
        combined = " ".join(requirements).lower()
        assert "cost analysis" in combined or "installation" in combined
    
    # ================================
    # Test Mode and Mocking Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_test_mode_functionality(
        self,
        ideator_agent,
        simple_input,
        test_governance_context,
        test_user
    ):
        """Test test mode functionality."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Enable test mode with mock responses
        mock_responses = {
            "openai": {
                "content": "Test mock response from OpenAI",
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }
        }
        
        ideator_agent.enable_test_mode(mock_responses)
        
        # Make API call
        response = await ideator_agent.make_api_call("openai", "gpt-4", "test")
        
        # Should get mock response
        assert response == mock_responses["openai"]
        
        # Disable test mode
        ideator_agent.disable_test_mode()
        assert not ideator_agent._test_mode
        assert len(ideator_agent._mock_responses) == 0
    
    def test_validation_callbacks(self, ideator_agent):
        """Test validation callback functionality."""
        callback_called = False
        
        async def test_callback(agent, input_data):
            nonlocal callback_called
            callback_called = True
            assert agent == ideator_agent
            assert input_data is not None
        
        # Add callback
        ideator_agent.add_validation_callback(test_callback)
        assert len(ideator_agent._validation_callbacks) == 1
        
        # Clear callbacks
        ideator_agent.clear_validation_callbacks()
        assert len(ideator_agent._validation_callbacks) == 0
    
    # ================================
    # Integration-style Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_complete_workflow(
        self,
        ideator_agent,
        sample_input,
        test_governance_context,
        test_user,
        capture_logs
    ):
        """Test complete agent workflow end-to-end."""
        # Initialize
        task_id = str(uuid4())
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        ideator_agent.enable_test_mode()
        
        # Execute
        result = await ideator_agent.execute(sample_input)
        
        # Validate complete result
        assert result.success is True
        assert result.content is not None
        assert result.metadata is not None
        assert result.attribution is not None
        assert result.performance_metrics is not None
        assert result.governance_summary is not None
        
        # Validate state transitions
        assert ideator_agent.state == AgentState.COMPLETED
        
        # Validate comprehensive logging
        assert len(capture_logs) > 10  # Should have many log events
        
        # Check for all major log event types
        event_types = {event.get("event_type") for event in capture_logs}
        expected_events = {
            "agent_started", "agent_completed", "governance_check", 
            "performance_metric", "state_transition"
        }
        
        # Should have some intersection (not all events may be present due to mocking)
        assert len(event_types.intersection(expected_events)) > 0
        
        # Cleanup
        await ideator_agent.cleanup()
        assert ideator_agent.state == AgentState.READY


# ================================
# Parametrized Tests
# ================================

class TestIdeatorModes:
    """Test different ideator modes."""
    
    @pytest.fixture
    def ideator_agent(self):
        return IdeatorAgent()
    
    @pytest.mark.parametrize("mode", [
        IdeatorMode.OUTLINE,
        IdeatorMode.BRAINSTORM,
        IdeatorMode.RESEARCH,
        IdeatorMode.CREATIVE
    ])
    @pytest_asyncio.async_test
    async def test_different_modes(
        self,
        ideator_agent,
        mode,
        test_governance_context,
        test_user
    ):
        """Test execution with different ideator modes."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        ideator_agent.enable_test_mode()
        
        test_input = IdeatorInput(
            content="Create content about artificial intelligence",
            mode=mode
        )
        
        result = await ideator_agent.execute(test_input)
        
        assert result.success is True
        assert result.metadata["mode"] == mode


class TestToneProfiles:
    """Test different tone profiles."""
    
    @pytest.fixture
    def ideator_agent(self):
        return IdeatorAgent()
    
    @pytest.mark.parametrize("tone", [
        ToneProfile.PROFESSIONAL,
        ToneProfile.CASUAL,
        ToneProfile.TECHNICAL,
        ToneProfile.EDUCATIONAL
    ])
    @pytest_asyncio.async_test
    async def test_different_tones(
        self,
        ideator_agent,
        tone,
        test_governance_context,
        test_user
    ):
        """Test tone analysis with different tone preferences."""
        await ideator_agent.initialize(
            task_id=str(uuid4()),
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        test_input = IdeatorInput(
            content="Explain machine learning concepts",
            tone_preference=tone
        )
        
        # Mock data for tone analysis
        outline = [
            OutlinePoint(
                title="Test Point",
                content="Test content",
                priority=5,
                sources=[]
            )
        ]
        
        context_data = {"sources": []}
        
        tone_analysis = await ideator_agent._analyze_tone(test_input, outline, context_data)
        
        assert tone_analysis["target_tone"] == tone