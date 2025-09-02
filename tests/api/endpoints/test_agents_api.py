"""
API integration tests for agent endpoints.

This test suite validates:
- Agent pipeline execution through REST API
- Individual agent endpoint functionality
- Authentication and authorization for agent access
- Request/response validation and error handling
- Performance and monitoring integration
- Governance enforcement at API layer
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json
from uuid import uuid4
from datetime import datetime, timezone

from src.mcg_agent.api.app import app
from src.mcg_agent.agents.ideator_agent import IdeatorAgent, IdeatorMode, ToneProfile


class TestAgentEndpoints:
    """Test suite for agent API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    # ================================
    # Pipeline Execution Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_execute_pipeline_success(
        self,
        authenticated_async_client,
        test_user,
        mock_external_apis,
        capture_logs
    ):
        """Test successful pipeline execution."""
        
        # Prepare request data
        request_data = {
            "prompt": "Create a comprehensive guide about renewable energy for homeowners",
            "mode": "chat",
            "classification": "content_creation",
            "context_sources": ["personal", "social"],
            "parameters": {
                "target_audience": "homeowners",
                "content_type": "guide",
                "tone_preference": "educational"
            }
        }
        
        # Mock the agent execution to avoid real AI calls
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.return_value = {
                "agent_role": "ideator",
                "success": True,
                "content": "Generated outline with renewable energy topics...",
                "metadata": {
                    "outline_points": 5,
                    "tone_score": 0.85,
                    "coverage_score": 0.78
                },
                "execution_time_ms": 1250.5,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
            
            # Execute request
            response = await authenticated_async_client.post(
                "/agents/pipeline/execute",
                json=request_data
            )
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] in ["executing", "completed"]
        assert "task_id" in response_data
        assert "ideator_result" in response_data
        
        # Validate ideator result
        ideator_result = response_data["ideator_result"]
        assert ideator_result["success"] is True
        assert ideator_result["agent_role"] == "ideator"
        assert ideator_result["governance_status"] == "compliant"
        
        # Check logging occurred
        assert len(capture_logs) > 0
    
    @pytest_asyncio.async_test
    async def test_execute_pipeline_authentication_required(self, async_client):
        """Test that pipeline execution requires authentication."""
        
        request_data = {
            "prompt": "Test prompt",
            "mode": "chat",
            "classification": "content_creation"
        }
        
        response = await async_client.post(
            "/agents/pipeline/execute",
            json=request_data
        )
        
        assert response.status_code == 401  # Unauthorized
    
    @pytest_asyncio.async_test
    async def test_execute_pipeline_invalid_request(
        self,
        authenticated_async_client
    ):
        """Test pipeline execution with invalid request data."""
        
        # Missing required prompt
        invalid_request = {
            "mode": "chat",
            "classification": "content_creation"
        }
        
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            json=invalid_request
        )
        
        assert response.status_code == 422  # Validation error
        
        # Empty prompt
        empty_prompt_request = {
            "prompt": "",
            "mode": "chat", 
            "classification": "content_creation"
        }
        
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            json=empty_prompt_request
        )
        
        assert response.status_code == 422  # Validation error
    
    # ================================
    # Individual Agent Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_execute_ideator_success(
        self,
        authenticated_async_client,
        test_user,
        capture_logs
    ):
        """Test individual Ideator agent execution."""
        
        request_data = {
            "content": "Create a guide about sustainable living practices",
            "mode": "outline",
            "target_audience": "environmentally conscious consumers",
            "tone_preference": "educational",
            "context_depth": 3
        }
        
        # Mock the actual agent execution
        with patch('src.mcg_agent.agents.ideator_agent.IdeatorAgent.execute') as mock_execute:
            mock_result = {
                "success": True,
                "content": "# Sustainable Living Guide Outline\n\n## 1. Energy Conservation...",
                "metadata": {
                    "mode": "outline",
                    "outline_points": 5,
                    "processing_time_ms": 1200
                },
                "attribution": [
                    {
                        "source_id": "personal_1",
                        "usage": "context_research",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "agent": "IdeatorAgent"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 1200,
                    "api_calls": 1,
                    "corpus_queries": 2
                },
                "governance_summary": {
                    "governance_compliant": True,
                    "api_calls_used": 1,
                    "api_calls_limit": 2
                }
            }
            
            # Create a mock AgentResult
            from src.mcg_agent.agents.base_agent import AgentResult
            mock_execute.return_value = AgentResult(
                success=True,
                content=mock_result["content"],
                metadata=mock_result["metadata"],
                attribution=mock_result["attribution"],
                performance_metrics=mock_result["performance_metrics"],
                governance_summary=mock_result["governance_summary"]
            )
            
            response = await authenticated_async_client.post(
                "/agents/ideator",
                json=request_data
            )
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["success"] is True
        assert response_data["agent_role"] == "ideator"
        assert "content" in response_data
        assert "metadata" in response_data
        assert "governance_status" in response_data
        
        # Validate content
        assert "Sustainable Living Guide Outline" in response_data["content"]
        
        # Validate metadata
        metadata = response_data["metadata"]
        assert metadata["mode"] == "outline"
        assert metadata["outline_points"] == 5
    
    @pytest_asyncio.async_test
    async def test_execute_ideator_governance_violation(
        self,
        authenticated_async_client,
        mock_security_alerts
    ):
        """Test Ideator agent with governance violation."""
        
        request_data = {
            "content": "Test content for governance violation",
            "mode": "outline"
        }
        
        # Mock governance violation
        with patch('src.mcg_agent.agents.ideator_agent.IdeatorAgent.execute') as mock_execute:
            from src.mcg_agent.utils.exceptions import GovernanceViolationError
            mock_execute.side_effect = GovernanceViolationError("API call limit exceeded")
            
            response = await authenticated_async_client.post(
                "/agents/ideator",
                json=request_data
            )
        
        # Should return error response
        assert response.status_code == 400  # Bad Request for governance violation
        response_data = response.json()
        
        assert "governance_violation" in response_data["detail"].lower()
        
        # Check that security alert was triggered
        assert len(mock_security_alerts) > 0
    
    @pytest_asyncio.async_test  
    async def test_execute_ideator_invalid_mode(
        self,
        authenticated_async_client
    ):
        """Test Ideator agent with invalid mode."""
        
        request_data = {
            "content": "Test content",
            "mode": "invalid_mode"  # Invalid mode
        }
        
        response = await authenticated_async_client.post(
            "/agents/ideator",
            json=request_data
        )
        
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "detail" in error_data
        
        # Should mention validation error
        assert any("mode" in str(error).lower() for error in error_data["detail"])
    
    # ================================
    # Corpus Query Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_corpus_query_success(
        self,
        authenticated_async_client,
        mock_corpus_search
    ):
        """Test successful corpus query."""
        
        request_data = {
            "query": "renewable energy sustainability",
            "corpus_types": ["personal", "social"],
            "max_results": 5
        }
        
        # Mock corpus search results
        with patch('src.mcg_agent.search.personal.PersonalSearch.query') as mock_personal:
            with patch('src.mcg_agent.search.social.SocialSearch.query') as mock_social:
                mock_personal.return_value = mock_corpus_search["personal"]
                mock_social.return_value = mock_corpus_search["social"]
                
                response = await authenticated_async_client.get(
                    "/agents/corpus/query",
                    params=request_data
                )
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        assert "results" in response_data
        assert "total_results" in response_data
        assert "query_metadata" in response_data
        
        # Validate results structure
        results = response_data["results"]
        assert isinstance(results, list)
        assert len(results) <= request_data["max_results"]
        
        # Check result structure
        if results:
            result = results[0]
            assert "content" in result
            assert "source" in result
            assert "timestamp" in result
    
    @pytest_asyncio.async_test
    async def test_corpus_query_unauthorized_corpus(
        self,
        authenticated_async_client
    ):
        """Test corpus query with unauthorized corpus type."""
        
        request_data = {
            "query": "test query",
            "corpus_types": ["unauthorized_corpus"],
            "max_results": 5
        }
        
        response = await authenticated_async_client.get(
            "/agents/corpus/query",
            params=request_data
        )
        
        assert response.status_code == 422  # Validation error for invalid corpus type
    
    @pytest_asyncio.async_test
    async def test_corpus_query_missing_parameters(
        self,
        authenticated_async_client
    ):
        """Test corpus query with missing parameters."""
        
        # Missing query parameter
        response = await authenticated_async_client.get(
            "/agents/corpus/query",
            params={"corpus_types": ["personal"]}
        )
        
        assert response.status_code == 422  # Validation error
    
    # ================================
    # Task Management Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_get_task_status(
        self,
        authenticated_async_client
    ):
        """Test retrieving task status."""
        
        task_id = str(uuid4())
        
        # Mock task status
        with patch('src.mcg_agent.api.routers.agents.get_task_status') as mock_status:
            mock_status.return_value = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "stages_completed": ["ideator", "drafter", "critic", "revisor", "summarizer"],
                "current_stage": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = await authenticated_async_client.get(f"/agents/tasks/{task_id}/status")
        
        # Validate response
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "completed"
        assert response_data["progress"] == 100
        assert isinstance(response_data["stages_completed"], list)
    
    @pytest_asyncio.async_test
    async def test_get_nonexistent_task_status(
        self,
        authenticated_async_client
    ):
        """Test retrieving status for nonexistent task."""
        
        nonexistent_task_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/agents/tasks/{nonexistent_task_id}/status"
        )
        
        assert response.status_code == 404  # Not Found
    
    # ================================
    # Performance and Monitoring Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_pipeline_execution_performance(
        self,
        authenticated_async_client,
        performance_timer
    ):
        """Test pipeline execution performance monitoring."""
        
        request_data = {
            "prompt": "Performance test prompt",
            "mode": "chat",
            "classification": "content_creation"
        }
        
        # Mock quick execution
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.return_value = {
                "agent_role": "ideator",
                "success": True,
                "content": "Quick test response",
                "metadata": {"execution_time_ms": 500},
                "execution_time_ms": 500,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
            
            # Time the request
            performance_timer["start"]("api_request")
            response = await authenticated_async_client.post(
                "/agents/pipeline/execute",
                json=request_data
            )
            request_time = performance_timer["stop"]("api_request")
        
        # Validate response and performance
        assert response.status_code == 200
        assert request_time < 5000  # Should complete within 5 seconds
        
        response_data = response.json()
        assert "total_execution_time_ms" in response_data
        
        # Performance should be reasonable
        total_time = response_data["total_execution_time_ms"]
        assert total_time > 0
        assert total_time < 10000  # Should be under 10 seconds
    
    # ================================
    # Error Handling Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_pipeline_execution_internal_error(
        self,
        authenticated_async_client,
        mock_security_alerts
    ):
        """Test pipeline execution with internal error."""
        
        request_data = {
            "prompt": "Test prompt for internal error",
            "mode": "chat",
            "classification": "content_creation"
        }
        
        # Mock internal error
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.side_effect = Exception("Internal processing error")
            
            response = await authenticated_async_client.post(
                "/agents/pipeline/execute",
                json=request_data
            )
        
        # Should return error response
        assert response.status_code == 500  # Internal Server Error
        
        # Check that error was logged/alerted
        # Note: Actual implementation may vary based on error handling strategy
    
    @pytest_asyncio.async_test
    async def test_malformed_request_handling(
        self,
        authenticated_async_client
    ):
        """Test handling of malformed requests."""
        
        # Invalid JSON
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            content="invalid json content",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
        
        # Completely empty request
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    # ================================
    # Concurrent Request Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_concurrent_pipeline_executions(
        self,
        authenticated_async_client
    ):
        """Test concurrent pipeline executions."""
        import asyncio
        
        request_data = {
            "prompt": "Concurrent test prompt {}",
            "mode": "chat",
            "classification": "content_creation"
        }
        
        # Mock fast execution
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.return_value = {
                "agent_role": "ideator",
                "success": True,
                "content": "Concurrent response",
                "metadata": {},
                "execution_time_ms": 200,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
            
            # Create multiple concurrent requests
            tasks = []
            for i in range(3):
                request = request_data.copy()
                request["prompt"] = request["prompt"].format(i)
                
                task = authenticated_async_client.post(
                    "/agents/pipeline/execute",
                    json=request
                )
                tasks.append(task)
            
            # Execute concurrently
            responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["status"] in ["executing", "completed"]
            assert "task_id" in response_data
            
            # Each should have unique task ID
            task_ids = [r.json()["task_id"] for r in responses]
            assert len(set(task_ids)) == len(task_ids)  # All unique
    
    # ================================
    # Content Validation Tests
    # ================================
    
    @pytest_asyncio.async_test
    async def test_content_length_limits(
        self,
        authenticated_async_client
    ):
        """Test content length validation."""
        
        # Very long prompt (test upper limit)
        very_long_prompt = "Test prompt " * 1000  # 11,000 characters
        
        request_data = {
            "prompt": very_long_prompt,
            "mode": "chat",
            "classification": "content_creation"
        }
        
        response = await authenticated_async_client.post(
            "/agents/pipeline/execute",
            json=request_data
        )
        
        # Should either accept or reject based on configured limits
        assert response.status_code in [200, 422]  # Success or validation error
        
        if response.status_code == 422:
            error_data = response.json()
            assert "prompt" in str(error_data).lower() or "length" in str(error_data).lower()
    
    @pytest_asyncio.async_test
    async def test_special_characters_handling(
        self,
        authenticated_async_client
    ):
        """Test handling of special characters in content."""
        
        # Prompt with various special characters
        special_prompt = "Create content about: émojis 🚀, symbols ©®™, and unicode ∞≈≠"
        
        request_data = {
            "prompt": special_prompt,
            "mode": "chat", 
            "classification": "content_creation"
        }
        
        # Mock execution
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.return_value = {
                "agent_role": "ideator",
                "success": True,
                "content": "Response with special characters handled",
                "metadata": {},
                "execution_time_ms": 300,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
            
            response = await authenticated_async_client.post(
                "/agents/pipeline/execute",
                json=request_data
            )
        
        # Should handle special characters correctly
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] in ["executing", "completed"]


# ================================
# Parametrized API Tests
# ================================

class TestParametrizedAgentAPI:
    """Parametrized tests for different agent configurations."""
    
    @pytest.mark.parametrize("mode", ["chat", "draft", "brief"])
    @pytest_asyncio.async_test
    async def test_pipeline_execution_modes(
        self,
        authenticated_async_client,
        mode
    ):
        """Test pipeline execution with different modes."""
        
        request_data = {
            "prompt": f"Test prompt for {mode} mode",
            "mode": mode,
            "classification": "content_creation"
        }
        
        with patch('src.mcg_agent.api.routers.agents._execute_ideator_stage') as mock_ideator:
            mock_ideator.return_value = {
                "agent_role": "ideator",
                "success": True,
                "content": f"Response for {mode} mode",
                "metadata": {"mode": mode},
                "execution_time_ms": 400,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
            
            response = await authenticated_async_client.post(
                "/agents/pipeline/execute",
                json=request_data
            )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["mode"] == mode
    
    @pytest.mark.parametrize("corpus_types", [
        ["personal"],
        ["social"],
        ["published"],
        ["personal", "social"],
        ["social", "published"],
        ["personal", "social", "published"]
    ])
    @pytest_asyncio.async_test
    async def test_corpus_query_different_types(
        self,
        authenticated_async_client,
        corpus_types,
        mock_corpus_search
    ):
        """Test corpus queries with different corpus type combinations."""
        
        request_data = {
            "query": "test query for corpus types",
            "corpus_types": corpus_types,
            "max_results": 3
        }
        
        # Mock all corpus searches
        patches = []
        if "personal" in corpus_types:
            patches.append(patch('src.mcg_agent.search.personal.PersonalSearch.query'))
        if "social" in corpus_types:
            patches.append(patch('src.mcg_agent.search.social.SocialSearch.query'))
        if "published" in corpus_types:
            patches.append(patch('src.mcg_agent.search.published.PublishedSearch.query'))
        
        # Apply patches and set return values
        mock_objects = []
        for patch_obj in patches:
            mock_obj = patch_obj.start()
            mock_obj.return_value = []  # Empty results for simplicity
            mock_objects.append(mock_obj)
        
        try:
            response = await authenticated_async_client.get(
                "/agents/corpus/query",
                params=request_data
            )
            
            assert response.status_code == 200
            response_data = response.json()
            
            assert "results" in response_data
            assert "total_results" in response_data
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()