"""
Integration tests for agent functionality with API and database.

This test suite validates the complete integration between:
- IdeatorAgent implementation
- FastAPI endpoints
- Database and Redis connections
- Governance system
- Logging and monitoring
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone

from src.mcg_agent.api.app import app
from src.mcg_agent.agents.ideator_agent import IdeatorAgent, IdeatorInput, IdeatorMode


class TestAgentIntegration:
    """Integration tests for complete agent functionality."""
    
    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest_asyncio.async_test
    async def test_ideator_agent_direct_execution(
        self,
        test_user,
        test_governance_context,
        capture_logs
    ):
        """Test direct IdeatorAgent execution without API."""
        
        # Create and initialize agent
        ideator_agent = IdeatorAgent()
        task_id = str(uuid4())
        
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Enable test mode to avoid real API calls
        ideator_agent.enable_test_mode({
            "openai": {
                "content": "Test AI response for integration testing",
                "usage": {"input_tokens": 50, "output_tokens": 100}
            }
        })
        
        # Prepare input
        agent_input = IdeatorInput(
            content="Create a detailed analysis of renewable energy adoption trends",
            context_sources=["personal", "social"],
            mode=IdeatorMode.RESEARCH,
            target_audience="policy makers",
            content_type="analysis",
            context_depth=2
        )
        
        # Execute agent
        result = await ideator_agent.execute(agent_input)
        
        # Validate result
        assert result.success is True
        assert result.content is not None
        assert len(result.content) > 0
        
        # Validate comprehensive result structure
        assert result.metadata is not None
        assert result.attribution is not None
        assert result.performance_metrics is not None
        assert result.governance_summary is not None
        
        # Validate metadata content
        assert result.metadata["mode"] == IdeatorMode.RESEARCH
        assert result.metadata["target_audience"] == "policy makers"
        assert result.metadata["content_type"] == "analysis"
        
        # Validate governance compliance
        governance = result.governance_summary
        assert governance["governance_compliant"] is True
        assert governance["api_calls_used"] <= governance["api_calls_limit"]
        assert governance["corpus_queries_used"] <= governance["corpus_queries_limit"]
        
        # Validate logging occurred
        assert len(capture_logs) > 0
        
        # Check for key events in logs
        event_types = {event.get("event_type") for event in capture_logs}
        expected_events = {"agent_started", "tool_execution_completed", "corpus_query_completed"}
        
        # Should have some of these events
        assert len(event_types.intersection(expected_events)) > 0
        
        # Cleanup
        await ideator_agent.cleanup()
    
    @pytest_asyncio.async_test
    async def test_ideator_api_endpoint_integration(
        self,
        authenticated_async_client,
        test_user,
        capture_logs
    ):
        """Test IdeatorAgent through FastAPI endpoint."""
        
        request_data = {
            "content": "Analyze the impact of artificial intelligence on modern education systems",
            "context_sources": ["personal", "social"],
            "mode": "research",
            "target_audience": "educators and administrators",
            "content_type": "research report",
            "tone_preference": "professional",
            "context_depth": 3
        }
        
        # Execute request through API
        response = await authenticated_async_client.post(
            "/agents/ideator",
            json=request_data
        )
        
        # Validate HTTP response
        assert response.status_code == 200
        response_data = response.json()
        
        # Validate response structure
        assert "agent_role" in response_data
        assert "content" in response_data
        assert "metadata" in response_data
        assert "execution_time_ms" in response_data
        assert "governance_status" in response_data
        
        # Validate response content
        assert response_data["agent_role"] == "ideator"
        assert response_data["governance_status"] in ["compliant", "warning"]
        assert len(response_data["content"]) > 0
        
        # Validate metadata
        metadata = response_data["metadata"]
        assert metadata["mode"] == "research"
        assert metadata["target_audience"] == request_data["target_audience"]
        assert metadata["content_type"] == request_data["content_type"]
        
        # Check that API call was logged
        assert len(capture_logs) > 0
    
    @pytest_asyncio.async_test
    async def test_pipeline_execution_with_ideator(
        self,
        authenticated_async_client,
        test_user,
        capture_logs
    ):
        """Test complete pipeline execution with real Ideator."""
        
        request_data = {
            "prompt": "Develop a comprehensive strategy for implementing sustainable practices in corporate environments",
            "mode": "chat",
            "classification": "content_creation",
            "context_sources": ["personal", "social"],
            "parameters": {
                "target_audience": "corporate executives",
                "content_type": "strategy document"
            }
        }
        
        # Execute pipeline
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            json=request_data
        )
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        # Validate pipeline result structure
        assert "task_id" in response_data
        assert "status" in response_data
        assert "ideator_result" in response_data
        
        # Validate ideator result
        ideator_result = response_data["ideator_result"]
        assert ideator_result is not None
        assert "agent_role" in ideator_result
        assert "content" in ideator_result
        
        # The ideator should have executed successfully
        assert ideator_result["agent_role"] == "ideator"
        assert len(ideator_result["content"]) > 0
        
        # Check governance compliance
        assert ideator_result["governance_status"] in ["compliant", "warning"]
    
    @pytest_asyncio.async_test
    async def test_agent_error_handling_integration(
        self,
        authenticated_async_client,
        test_user
    ):
        """Test error handling throughout the integration stack."""
        
        # Test with invalid input
        invalid_request = {
            "content": "",  # Empty content should fail validation
            "mode": "outline"
        }
        
        response = await authenticated_async_client.post(
            "/agents/ideator",
            json=invalid_request
        )
        
        # Should return validation error
        assert response.status_code == 422
        
        # Test with invalid mode
        invalid_mode_request = {
            "content": "Valid content here",
            "mode": "invalid_mode"
        }
        
        response = await authenticated_async_client.post(
            "/agents/ideator", 
            json=invalid_mode_request
        )
        
        # Should return validation error
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
    
    @pytest_asyncio.async_test
    async def test_agent_performance_monitoring_integration(
        self,
        authenticated_async_client,
        test_user,
        performance_timer,
        capture_logs
    ):
        """Test performance monitoring across the integration."""
        
        request_data = {
            "content": "Performance test: Create analysis of cloud computing trends",
            "mode": "outline",
            "context_depth": 2  # Limit depth for faster execution
        }
        
        # Time the complete request
        performance_timer["start"]("full_request")
        
        response = await authenticated_async_client.post(
            "/agents/ideator",
            json=request_data
        )
        
        total_time = performance_timer["stop"]("full_request")
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        # Check performance metrics
        execution_time = response_data["execution_time_ms"]
        assert execution_time > 0
        assert execution_time < 30000  # Should complete within 30 seconds
        
        # Total request time should be reasonable
        assert total_time < 35000  # Allow extra 5 seconds for HTTP overhead
        
        # Check for performance-related log events
        performance_events = [
            event for event in capture_logs
            if event.get("event_type") == "performance_metric"
        ]
        
        # Should have some performance metrics logged
        assert len(performance_events) > 0
    
    @pytest_asyncio.async_test
    async def test_concurrent_agent_executions(
        self,
        authenticated_async_client,
        test_user
    ):
        """Test concurrent agent executions."""
        import asyncio
        
        # Create multiple concurrent requests
        requests = []
        for i in range(3):
            request_data = {
                "content": f"Concurrent test {i}: Analyze renewable energy trends",
                "mode": "outline",
                "context_depth": 1  # Minimal depth for speed
            }
            
            request_task = authenticated_async_client.post(
                "/agents/ideator",
                json=request_data
            )
            requests.append(request_task)
        
        # Execute concurrently
        responses = await asyncio.gather(*requests)
        
        # All should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed"
            
            response_data = response.json()
            assert response_data["agent_role"] == "ideator"
            assert len(response_data["content"]) > 0
            assert response_data["governance_status"] in ["compliant", "warning"]
    
    @pytest_asyncio.async_test
    async def test_authentication_integration(
        self,
        async_client,
        authenticated_async_client,
        test_user
    ):
        """Test authentication integration with agent endpoints."""
        
        request_data = {
            "content": "Test authentication with agent execution",
            "mode": "outline"
        }
        
        # Test without authentication - should fail
        response = await async_client.post(
            "/agents/ideator",
            json=request_data
        )
        
        assert response.status_code == 401  # Unauthorized
        
        # Test with authentication - should succeed
        response = await authenticated_async_client.post(
            "/agents/ideator",
            json=request_data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["agent_role"] == "ideator"


class TestGovernanceIntegration:
    """Test governance system integration with agents."""
    
    @pytest_asyncio.async_test
    async def test_governance_protocol_integration(
        self,
        test_user,
        test_governance_context,
        capture_logs,
        mock_security_alerts
    ):
        """Test governance protocol enforcement with real agent."""
        
        ideator_agent = IdeatorAgent()
        task_id = str(uuid4())
        
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        # Enable test mode
        ideator_agent.enable_test_mode()
        
        # Execute within limits - should succeed
        agent_input = IdeatorInput(
            content="Test governance compliance with agent execution",
            mode=IdeatorMode.OUTLINE
        )
        
        result = await ideator_agent.execute(agent_input)
        assert result.success is True
        
        # Check governance summary
        governance = result.governance_summary
        assert governance["governance_compliant"] is True
        assert governance["api_calls_used"] <= governance["api_calls_limit"]
        
        # Should not have triggered any security alerts for compliant execution
        violation_alerts = [
            alert for alert in mock_security_alerts
            if "violation" in alert.get("event_type", "").lower()
        ]
        assert len(violation_alerts) == 0
        
        await ideator_agent.cleanup()
    
    @pytest_asyncio.async_test
    async def test_logging_integration_comprehensive(
        self,
        test_user,
        test_governance_context,
        capture_logs
    ):
        """Test comprehensive logging integration."""
        
        ideator_agent = IdeatorAgent()
        task_id = str(uuid4())
        
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=test_user.user_id,
            governance_context=test_governance_context
        )
        
        ideator_agent.enable_test_mode()
        
        # Execute agent
        agent_input = IdeatorInput(
            content="Comprehensive logging test for agent integration",
            context_sources=["personal", "social"],
            mode=IdeatorMode.RESEARCH
        )
        
        result = await ideator_agent.execute(agent_input)
        assert result.success is True
        
        # Validate comprehensive logging
        assert len(capture_logs) > 10  # Should have many log events
        
        # Check for different types of events
        event_types = {event.get("event_type") for event in capture_logs}
        
        # Should have various event types
        expected_event_types = {
            "agent_started", "tool_execution_started", "tool_execution_completed",
            "corpus_query_completed", "governance_check", "performance_metric",
            "state_transition", "agent_completed"
        }
        
        # Should have intersection with expected events
        actual_events = event_types.intersection(expected_event_types)
        assert len(actual_events) > 3, f"Expected more event types, got: {actual_events}"
        
        # Check for task_id consistency
        logged_task_ids = {event.get("task_id") for event in capture_logs if event.get("task_id")}
        assert task_id in logged_task_ids, "Task ID should appear in logs"
        
        await ideator_agent.cleanup()