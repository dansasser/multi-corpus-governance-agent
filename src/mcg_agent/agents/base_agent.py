"""
Base Agent class for Multi-Corpus Governance Agent.

This module provides the foundation for all agent implementations with:
- Comprehensive logging and monitoring
- Governance enforcement integration
- Testing hooks and validation
- Performance monitoring
- Error handling and recovery
- Attribution tracking
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timezone
from uuid import uuid4
from enum import Enum
import time
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator

from ..utils.agent_logger import create_agent_logger, AgentLogger
from ..utils.logging import SecurityLogger
from ..utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    MCGBaseException
)
from ..governance.context import AgentContext, create_agent_context
from ..governance.protocol import governance_protocol, AgentRole


class AgentState(Enum):
    """Agent execution states."""
    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(Enum):
    """Agent capabilities for governance validation."""
    API_CALLS = "api_calls"
    CORPUS_QUERY = "corpus_query"
    RAG_ACCESS = "rag_access"
    MVLM_PREFERRED = "mvlm_preferred"
    MVLM_REQUIRED = "mvlm_required"
    CONTENT_GENERATION = "content_generation"
    CONTENT_REVISION = "content_revision"
    VALIDATION = "validation"
    SUMMARIZATION = "summarization"


@dataclass
class AgentResult:
    """Structured result from agent execution."""
    success: bool
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    attribution: Optional[List[Dict[str, Any]]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    governance_summary: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "content": self.content,
            "metadata": self.metadata or {},
            "attribution": self.attribution or [],
            "performance_metrics": self.performance_metrics or {},
            "governance_summary": self.governance_summary or {},
            "error_info": self.error_info
        }


class AgentInput(BaseModel):
    """Base input model for agents."""
    content: str = Field(..., min_length=1, description="Input content to process")
    context_sources: List[str] = Field(default=[], description="Context sources to use")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific parameters")
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()


class BaseAgent(ABC):
    """
    Abstract base class for all MCG agents with comprehensive logging,
    governance enforcement, and testing capabilities.
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_role: AgentRole,
        capabilities: List[AgentCapability],
        max_api_calls: int = 2,
        max_corpus_queries: int = 3,
        requires_authentication: bool = True
    ):
        """Initialize base agent."""
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.capabilities = capabilities
        self.max_api_calls = max_api_calls
        self.max_corpus_queries = max_corpus_queries
        self.requires_authentication = requires_authentication
        
        # Runtime state
        self.state = AgentState.INITIALIZING
        self.current_task_id: Optional[str] = None
        self.current_user_id: Optional[str] = None
        self.logger: Optional[AgentLogger] = None
        self.governance_context: Optional[AgentContext] = None
        
        # Performance tracking
        self._api_call_count = 0
        self._corpus_query_count = 0
        self._start_time: Optional[float] = None
        
        # Testing hooks
        self._test_mode = False
        self._mock_responses = {}
        self._validation_callbacks = []
        
        # Attribution tracking
        self._attribution_chain = []
        self._input_sources = []
    
    async def initialize(
        self,
        task_id: str,
        user_id: str,
        governance_context: Optional[AgentContext] = None
    ) -> None:
        """Initialize agent for task execution."""
        self.current_task_id = task_id
        self.current_user_id = user_id
        self.state = AgentState.READY
        
        # Create logger
        self.logger = create_agent_logger(
            agent_name=self.agent_name,
            task_id=task_id,
            user_id=user_id
        )
        
        # Set or create governance context
        if governance_context:
            self.governance_context = governance_context
        else:
            self.governance_context = await create_agent_context(
                task_id=task_id,
                agent_role=self.agent_role,
                input_content="",  # Will be set during execution
                user_id=user_id,
                output_mode="chat"
            )
        
        await self.logger.info(f"Agent {self.agent_name} initialized for task {task_id}")
    
    async def execute(
        self,
        agent_input: AgentInput,
        **kwargs
    ) -> AgentResult:
        """Execute agent with comprehensive monitoring and governance."""
        if not self.logger or not self.governance_context:
            raise MCGBaseException("Agent not properly initialized")
        
        self.state = AgentState.EXECUTING
        self._start_time = time.perf_counter()
        
        try:
            # Log execution start
            await self.logger.start_agent_execution(
                input_data=agent_input.dict(),
                configuration=kwargs
            )
            
            # Pre-execution validation
            await self._validate_execution_preconditions(agent_input)
            
            # Execute governance checks
            await self._perform_governance_validation()
            
            # Execute the agent logic
            result = await self._execute_agent_logic(agent_input, **kwargs)
            
            # Post-execution validation
            await self._validate_execution_results(result)
            
            # Log successful completion
            await self.logger.complete_agent_execution(
                output_data=result.to_dict(),
                metadata=self._get_execution_metadata()
            )
            
            self.state = AgentState.COMPLETED
            return result
            
        except Exception as e:
            # Log failure
            await self.logger.fail_agent_execution(
                error=e,
                failure_stage=self.state.value,
                additional_context=self._get_execution_metadata()
            )
            
            self.state = AgentState.FAILED
            
            # Create error result
            return AgentResult(
                success=False,
                error_info={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "failure_stage": self.state.value
                },
                performance_metrics=self._get_execution_metadata()
            )
    
    @abstractmethod
    async def _execute_agent_logic(
        self,
        agent_input: AgentInput,
        **kwargs
    ) -> AgentResult:
        """Execute the core agent logic. Must be implemented by subclasses."""
        pass
    
    async def _validate_execution_preconditions(
        self,
        agent_input: AgentInput
    ) -> None:
        """Validate conditions before execution."""
        await self.logger.debug("Validating execution preconditions")
        
        # Validate input
        if not agent_input.content:
            raise ValueError("Agent input content cannot be empty")
        
        # Validate capabilities vs requirements
        if AgentCapability.API_CALLS in self.capabilities:
            if self._api_call_count >= self.max_api_calls:
                raise APICallLimitExceededError(
                    f"API call limit ({self.max_api_calls}) exceeded"
                )
        
        # Run custom validation callbacks (for testing)
        for callback in self._validation_callbacks:
            await callback(self, agent_input)
        
        await self.logger.debug("Preconditions validation passed")
    
    async def _perform_governance_validation(self) -> None:
        """Perform governance protocol validation."""
        start_time = time.perf_counter()
        
        try:
            # Validate agent role permissions
            validation_result = await governance_protocol.validate_agent_permissions(
                agent_role=self.agent_role,
                required_capabilities=self.capabilities,
                current_context=self.governance_context
            )
            
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            
            await self.logger.log_governance_check(
                check_type="role_permissions",
                passed=validation_result.valid,
                details=validation_result.details,
                validation_time_ms=validation_time_ms
            )
            
            if not validation_result.valid:
                raise GovernanceViolationError(
                    f"Governance validation failed: {validation_result.reason}"
                )
                
        except Exception as e:
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            
            await self.logger.log_governance_check(
                check_type="role_permissions",
                passed=False,
                details={"error": str(e)},
                validation_time_ms=validation_time_ms
            )
            raise
    
    async def _validate_execution_results(self, result: AgentResult) -> None:
        """Validate execution results."""
        await self.logger.debug("Validating execution results")
        
        if result.success and not result.content:
            await self.logger.warning("Successful execution produced no content")
        
        # Validate attribution chain exists
        if result.success and not result.attribution:
            await self.logger.warning("No attribution chain provided in result")
        
        await self.logger.debug("Result validation completed")
    
    async def make_api_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API call with governance and logging."""
        if AgentCapability.API_CALLS not in self.capabilities:
            raise GovernanceViolationError(
                f"Agent {self.agent_name} not authorized for API calls"
            )
        
        if self._api_call_count >= self.max_api_calls:
            raise APICallLimitExceededError(
                f"API call limit ({self.max_api_calls}) exceeded"
            )
        
        self._api_call_count += 1
        
        # In test mode, return mock response
        if self._test_mode and provider in self._mock_responses:
            mock_response = self._mock_responses[provider]
            await self.logger.debug(f"Returning mock response for {provider}")
            return mock_response
        
        # Log API call attempt
        await self.logger.debug(f"Making API call to {provider}/{model}")
        
        async with self.logger.log_tool_execution(
            tool_name=f"{provider}_api_call",
            input_params={"model": model, "prompt_length": len(prompt)},
            expected_output_type="text_completion"
        ):
            # Actual API call implementation would go here
            # This is a placeholder that should be implemented by subclasses
            await self.logger.info(f"API call {self._api_call_count} to {provider}/{model}")
            
            # Mock successful response for now
            response = {
                "content": f"Mock response from {provider}/{model}",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }
            
            # Log API call completion
            await self.logger.log_api_call(
                provider=provider,
                model=model,
                call_type="completion",
                input_tokens=response.get("usage", {}).get("input_tokens"),
                output_tokens=response.get("usage", {}).get("output_tokens")
            )
            
            return response
    
    async def query_corpus(
        self,
        corpus_type: str,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Query corpus with governance and logging."""
        if AgentCapability.CORPUS_QUERY not in self.capabilities:
            raise GovernanceViolationError(
                f"Agent {self.agent_name} not authorized for corpus queries"
            )
        
        if self._corpus_query_count >= self.max_corpus_queries:
            raise UnauthorizedCorpusAccessError(
                f"Corpus query limit ({self.max_corpus_queries}) exceeded"
            )
        
        self._corpus_query_count += 1
        start_time = time.perf_counter()
        
        # Mock corpus query for now
        results = [
            {
                "id": f"{corpus_type}_result_{i}",
                "content": f"Mock {corpus_type} content {i}",
                "source": corpus_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            for i in range(min(max_results, 3))
        ]
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        await self.logger.log_corpus_query(
            corpus_type=corpus_type,
            query=query,
            result_count=len(results),
            execution_time_ms=execution_time_ms,
            sources=[r["source"] for r in results]
        )
        
        return results
    
    def _get_execution_metadata(self) -> Dict[str, Any]:
        """Get execution metadata for logging."""
        execution_time = 0
        if self._start_time:
            execution_time = (time.perf_counter() - self._start_time) * 1000
        
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role.value,
            "execution_time_ms": execution_time,
            "api_calls_made": self._api_call_count,
            "corpus_queries_made": self._corpus_query_count,
            "state": self.state.value,
            "capabilities": [cap.value for cap in self.capabilities]
        }
    
    # Testing support methods
    
    def enable_test_mode(
        self,
        mock_responses: Optional[Dict[str, Any]] = None
    ) -> None:
        """Enable test mode with optional mock responses."""
        self._test_mode = True
        self._mock_responses = mock_responses or {}
    
    def disable_test_mode(self) -> None:
        """Disable test mode."""
        self._test_mode = False
        self._mock_responses.clear()
    
    def add_validation_callback(self, callback) -> None:
        """Add validation callback for testing."""
        self._validation_callbacks.append(callback)
    
    def clear_validation_callbacks(self) -> None:
        """Clear validation callbacks."""
        self._validation_callbacks.clear()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return {
            "api_calls": self._api_call_count,
            "corpus_queries": self._corpus_query_count,
            "execution_time_ms": (time.perf_counter() - self._start_time) * 1000 if self._start_time else 0,
            "state": self.state.value
        }
    
    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        if self.logger:
            await self.logger.flush_logs()
        
        self.state = AgentState.READY
        self._api_call_count = 0
        self._corpus_query_count = 0
        self._attribution_chain.clear()
        self._input_sources.clear()
        
        await self.logger.debug("Agent cleanup completed") if self.logger else None