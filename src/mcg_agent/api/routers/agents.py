"""Agent pipeline API endpoints.

This module provides the main agent pipeline endpoints with governance enforcement:
- Five-agent pipeline execution (Ideator → Drafter → Critic → Revisor → Summarizer)
- Individual agent tool endpoints
- Task management and tracking
- Context assembly and corpus queries
- Pipeline status and monitoring

All endpoints enforce governance rules at the architectural level.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, validator

from ..auth import get_current_user, require_permissions
from ...governance.protocol import (
    governance_protocol,
    AgentRole,
    CorpusType,
    TaskGovernanceState
)
from ...governance.context import (
    create_agent_context,
    AgentContext,
    OutputMode,
    TaskClassification
)
from ...utils.exceptions import (
    GovernanceViolationError,
    APICallLimitExceededError,
    UnauthorizedCorpusAccessError,
    SecurityValidationError
)
from ...utils.logging import SecurityLogger

# Create router
router = APIRouter()


# Pydantic models

class PipelineMode(str, Enum):
    """Pipeline execution modes."""
    CHAT = "chat"
    WRITING = "writing" 
    VOICE = "voice"


class PipelineRequest(BaseModel):
    """Pipeline execution request model."""
    
    prompt: str = Field(..., min_length=1, max_length=5000, description="User prompt or query")
    mode: PipelineMode = Field(default=PipelineMode.CHAT, description="Pipeline output mode")
    classification: str = Field(default="standard", description="Task classification level")
    target_length: Optional[int] = Field(None, ge=100, le=10000, description="Target output length")
    context_sources: Optional[List[str]] = Field(default=["personal", "social", "published"], description="Context sources to use")
    
    @validator('context_sources')
    def validate_context_sources(cls, v):
        """Validate context sources."""
        if v:
            valid_sources = ["personal", "social", "published"]
            for source in v:
                if source not in valid_sources:
                    raise ValueError(f"Invalid context source: {source}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Write about the future of AI governance in enterprise systems",
                "mode": "writing",
                "classification": "standard",
                "target_length": 2000,
                "context_sources": ["personal", "social", "published"]
            }
        }


class IdeatorRequest(BaseModel):
    """Request model for individual Ideator agent."""
    
    content: str = Field(..., min_length=1, max_length=5000, description="Input content to process")
    context_sources: List[str] = Field(default=["personal", "social"], description="Context sources to use")
    mode: str = Field(default="outline", description="Ideation mode")
    target_audience: Optional[str] = Field(None, max_length=200, description="Target audience")
    content_type: Optional[str] = Field(None, max_length=100, description="Type of content to create")
    tone_preference: Optional[str] = Field(None, description="Preferred tone")
    context_depth: int = Field(default=3, ge=1, le=10, description="Depth of context research")
    
    @validator('mode')
    def validate_mode(cls, v):
        valid_modes = ["outline", "brainstorm", "research", "creative"]
        if v not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
        return v
    
    @validator('context_sources')
    def validate_context_sources(cls, v):
        valid_sources = ["personal", "social", "published"]
        for source in v:
            if source not in valid_sources:
                raise ValueError(f"Invalid context source: {source}")
        return v
    
    @validator('tone_preference')
    def validate_tone_preference(cls, v):
        if v is None:
            return v
        valid_tones = ["professional", "casual", "technical", "persuasive", "educational", "conversational"]
        if v not in valid_tones:
            raise ValueError(f"Invalid tone preference. Must be one of: {valid_tones}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "content": "Create a comprehensive guide about renewable energy for homeowners",
                "context_sources": ["personal", "social"],
                "mode": "outline",
                "target_audience": "environmentally conscious homeowners",
                "content_type": "guide",
                "tone_preference": "educational",
                "context_depth": 3
            }
        }


class AgentResult(BaseModel):
    """Individual agent result model."""
    
    agent_role: str = Field(..., description="Agent role that produced this result")
    content: str = Field(..., description="Agent output content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific metadata")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    api_calls_used: int = Field(default=0, description="Number of API calls used")
    governance_status: str = Field(default="compliant", description="Governance compliance status")
    
    class Config:
        schema_extra = {
            "example": {
                "agent_role": "ideator",
                "content": "Generated outline with key points...",
                "metadata": {"outline_points": 5, "tone_score": 0.85},
                "execution_time_ms": 1250.5,
                "api_calls_used": 1,
                "governance_status": "compliant"
            }
        }


class PipelineResult(BaseModel):
    """Complete pipeline execution result model."""
    
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Pipeline execution status")
    mode: str = Field(..., description="Pipeline mode used")
    
    # Agent results
    ideator_result: Optional[AgentResult] = Field(None, description="Ideator agent result")
    drafter_result: Optional[AgentResult] = Field(None, description="Drafter agent result")  
    critic_result: Optional[AgentResult] = Field(None, description="Critic agent result")
    revisor_result: Optional[AgentResult] = Field(None, description="Revisor agent result")
    summarizer_result: Optional[AgentResult] = Field(None, description="Summarizer agent result")
    
    # Final output
    final_content: Optional[str] = Field(None, description="Final processed content")
    summary: Optional[str] = Field(None, description="Content summary")
    keywords: Optional[List[str]] = Field(None, description="Extracted keywords")
    
    # Execution metadata
    total_execution_time_ms: float = Field(..., description="Total pipeline execution time")
    total_api_calls: int = Field(..., description="Total API calls across all agents")
    governance_summary: Dict[str, Any] = Field(default_factory=dict, description="Governance compliance summary")
    
    # Attribution and provenance
    attribution_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Complete attribution chain")
    voice_fingerprint_scores: Dict[str, float] = Field(default_factory=dict, description="Voice matching scores")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None, description="Pipeline completion time")


class CorpusQueryRequest(BaseModel):
    """Corpus query request model."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    corpus_types: List[str] = Field(..., description="Corpus types to search")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    
    @validator('corpus_types')
    def validate_corpus_types(cls, v):
        """Validate corpus types."""
        valid_types = ["personal", "social", "published"]
        for corpus_type in v:
            if corpus_type not in valid_types:
                raise ValueError(f"Invalid corpus type: {corpus_type}")
        return v


class CorpusQueryResult(BaseModel):
    """Corpus query result model."""
    
    query: str = Field(..., description="Original query")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    total_results: int = Field(..., description="Total number of results found")
    corpus_breakdown: Dict[str, int] = Field(..., description="Results per corpus")
    execution_time_ms: float = Field(..., description="Query execution time")


class TaskStatus(BaseModel):
    """Task status model."""
    
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current task status")
    current_agent: Optional[str] = Field(None, description="Currently executing agent")
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    created_at: datetime = Field(..., description="Task creation time")
    last_updated: datetime = Field(..., description="Last update time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


# Pipeline endpoints

@router.post(
    "/pipeline/execute",
    response_model=PipelineResult,
    summary="Execute Agent Pipeline",
    description="Execute the complete five-agent pipeline with governance enforcement"
)
async def execute_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_permissions(["pipeline_execution"]))
) -> PipelineResult:
    """
    Execute the complete five-agent pipeline.
    
    **Pipeline Flow:**
    1. **Ideator**: Generate outline with multi-corpus context (max 2 API calls)
    2. **Drafter**: Expand outline into full content (max 1 API call)  
    3. **Critic**: Validate truth, safety, and voice matching (max 2 API calls + RAG)
    4. **Revisor**: Apply corrections using MVLM primarily (API fallback allowed)
    5. **Summarizer**: Compress and extract keywords using MVLM only
    
    **Governance Enforcement:**
    - All agent constraints enforced architecturally
    - Complete audit trail with attribution tracking
    - Real-time violation detection and response
    - Immutable provenance chain maintenance
    """
    
    task_id = str(uuid4())
    start_time = datetime.now(timezone.utc)
    
    try:
        # Initialize task governance
        task_state = await governance_protocol.initialize_task_governance(
            task_id=task_id,
            user_id=current_user["user_id"],
            classification=request.classification
        )
        
        await SecurityLogger.log_governance_event(
            event_type="pipeline_execution_started",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=True,
            details={
                "mode": request.mode.value,
                "classification": request.classification,
                "prompt_length": len(request.prompt)
            }
        )
        
        # Create pipeline result
        pipeline_result = PipelineResult(
            task_id=task_id,
            status="executing",
            mode=request.mode.value,
            total_execution_time_ms=0,
            total_api_calls=0
        )
        
        # Execute pipeline stages
        try:
            # Stage 1: Ideator
            pipeline_result.ideator_result = await _execute_ideator_stage(
                task_id=task_id,
                prompt=request.prompt,
                context_sources=request.context_sources,
                current_user=current_user
            )
            
            # Stage 2: Drafter
            pipeline_result.drafter_result = await _execute_drafter_stage(
                task_id=task_id,
                ideator_result=pipeline_result.ideator_result,
                current_user=current_user
            )
            
            # Stage 3: Critic
            pipeline_result.critic_result = await _execute_critic_stage(
                task_id=task_id,
                drafter_result=pipeline_result.drafter_result,
                current_user=current_user
            )
            
            # Check for critical failures from Critic
            if pipeline_result.critic_result.governance_status == "critical_failure":
                pipeline_result.status = "failed"
                pipeline_result.completed_at = datetime.now(timezone.utc)
                return pipeline_result
            
            # Stage 4: Revisor  
            pipeline_result.revisor_result = await _execute_revisor_stage(
                task_id=task_id,
                drafter_result=pipeline_result.drafter_result,
                critic_result=pipeline_result.critic_result,
                current_user=current_user
            )
            
            # Stage 5: Summarizer
            pipeline_result.summarizer_result = await _execute_summarizer_stage(
                task_id=task_id,
                revisor_result=pipeline_result.revisor_result,
                target_length=request.target_length,
                current_user=current_user
            )
            
            # Finalize pipeline
            pipeline_result.final_content = pipeline_result.revisor_result.content
            pipeline_result.summary = pipeline_result.summarizer_result.content
            pipeline_result.keywords = pipeline_result.summarizer_result.metadata.get("keywords", [])
            
            # Calculate totals
            total_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            pipeline_result.total_execution_time_ms = total_time
            
            total_calls = sum([
                pipeline_result.ideator_result.api_calls_used,
                pipeline_result.drafter_result.api_calls_used,
                pipeline_result.critic_result.api_calls_used,
                pipeline_result.revisor_result.api_calls_used,
                pipeline_result.summarizer_result.api_calls_used
            ])
            pipeline_result.total_api_calls = total_calls
            
            # Finalize governance tracking
            governance_summary = await governance_protocol.finalize_task_governance(task_id)
            pipeline_result.governance_summary = governance_summary
            
            pipeline_result.status = "completed"
            pipeline_result.completed_at = datetime.now(timezone.utc)
            
            await SecurityLogger.log_governance_event(
                event_type="pipeline_execution_completed",
                task_id=task_id,
                user_id=current_user["user_id"],
                success=True,
                details={
                    "total_time_ms": total_time,
                    "total_api_calls": total_calls,
                    "governance_compliant": governance_summary.get("completed_successfully", False)
                }
            )
            
            return pipeline_result
            
        except (GovernanceViolationError, APICallLimitExceededError, UnauthorizedCorpusAccessError) as governance_error:
            # Governance violation during pipeline execution
            pipeline_result.status = "governance_violation"
            pipeline_result.completed_at = datetime.now(timezone.utc)
            
            await SecurityLogger.log_governance_violation(
                violation_type=type(governance_error).__name__,
                agent_name=getattr(governance_error, 'agent_name', 'pipeline'),
                task_id=task_id,
                severity="high",
                details={"pipeline_stage": "execution", "error": str(governance_error)}
            )
            
            # Still return partial results
            return pipeline_result
            
    except Exception as e:
        # Unexpected error
        await SecurityLogger.log_governance_event(
            event_type="pipeline_execution_failed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=False,
            details={"error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.get(
    "/pipeline/status/{task_id}",
    response_model=TaskStatus,
    summary="Get Task Status",
    description="Get current status of pipeline execution"
)
async def get_task_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TaskStatus:
    """
    Get current status of a pipeline task.
    
    Returns execution progress and current agent information.
    """
    
    try:
        # Check if task exists in governance protocol
        if task_id not in governance_protocol.active_tasks:
            # Try to find completed task information
            # This would require extending governance protocol to store completed tasks
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        task_state = governance_protocol.active_tasks[task_id]
        
        # Calculate progress based on agent executions
        total_agents = 5
        completed_agents = len(task_state.api_calls_by_agent)
        progress = (completed_agents / total_agents) * 100
        
        # Determine current agent
        current_agent = None
        if completed_agents < total_agents:
            agent_sequence = ["ideator", "drafter", "critic", "revisor", "summarizer"]
            current_agent = agent_sequence[completed_agents]
        
        return TaskStatus(
            task_id=task_id,
            status="executing" if completed_agents < total_agents else "completed",
            current_agent=current_agent,
            progress_percent=progress,
            created_at=task_state.created_at,
            last_updated=datetime.now(timezone.utc),
            estimated_completion=None  # Could implement estimation logic
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


# Corpus query endpoints

@router.post(
    "/ideator",
    response_model=AgentResult,
    summary="Execute Ideator Agent",
    description="Execute individual Ideator agent with governance enforcement"
)
async def execute_ideator(
    request: IdeatorRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AgentResult:
    """
    Execute Ideator agent individually.
    
    **Governance Rules:**
    - Maximum 2 API calls allowed
    - May query all corpus types (Personal, Social, Published)  
    - RAG access only for coverage gap filling
    - Must preserve attribution for all sources
    - Must generate structured outline with metadata
    """
    
    task_id = str(uuid4())
    start_time = datetime.now(timezone.utc)
    
    try:
        # Initialize and execute Ideator agent
        from ...agents.ideator_agent import IdeatorAgent, IdeatorInput
        
        ideator_agent = IdeatorAgent()
        
        # Initialize agent
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=current_user["user_id"]
        )
        
        # Prepare agent input
        agent_input = IdeatorInput(
            content=request.content,
            context_sources=request.context_sources,
            mode=request.mode,
            target_audience=request.target_audience,
            content_type=request.content_type,
            tone_preference=request.tone_preference,
            context_depth=request.context_depth
        )
        
        # Execute agent
        result = await ideator_agent.execute(agent_input)
        
        # Log successful execution
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_completed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=result.success,
            details={
                "agent": "ideator",
                "content_length": len(result.content or ""),
                "execution_time_ms": result.performance_metrics.get("execution_time_ms", 0) if result.performance_metrics else 0
            }
        )
        
        # Convert to API response format
        return AgentResult(
            agent_role="ideator",
            content=result.content,
            metadata=result.metadata,
            execution_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            api_calls_used=result.performance_metrics.get("api_calls", 0) if result.performance_metrics else 0,
            governance_status="compliant" if result.success else ("failed" if result.error_info else "warning")
        )
        
    except GovernanceViolationError as e:
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_failed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=False,
            details={"agent": "ideator", "violation_type": "governance", "error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Governance violation: {str(e)}"
        )
        
    except Exception as e:
        await SecurityLogger.log_governance_event(
            event_type="agent_execution_failed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=False,
            details={"agent": "ideator", "error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ideator execution failed: {str(e)}"
        )


@router.post(
    "/corpus/query",
    response_model=CorpusQueryResult,
    summary="Query Corpus",
    description="Query multiple corpora with governance enforcement"
)
async def query_corpus(
    request: CorpusQueryRequest,
    current_user: Dict[str, Any] = Depends(require_permissions(["corpus_access"]))
) -> CorpusQueryResult:
    """
    Query multiple corpora with governance enforcement.
    
    **Governance Rules:**
    - Access permissions validated per user role
    - Query rate limiting enforced
    - All queries logged for audit trail
    - Attribution tracking for all results
    """
    
    start_time = datetime.now(timezone.utc)
    task_id = str(uuid4())  # Create temporary task for governance tracking
    
    try:
        # Initialize temporary governance tracking
        await governance_protocol.initialize_task_governance(
            task_id=task_id,
            user_id=current_user["user_id"],
            classification="corpus_query"
        )
        
        results = []
        corpus_breakdown = {}
        
        # Query each requested corpus type
        for corpus_type in request.corpus_types:
            try:
                # Validate corpus access (this would integrate with actual corpus connectors)
                await governance_protocol.validate_corpus_access(
                    agent_role=AgentRole.CRITIC,  # Use Critic role for manual queries (has full access)
                    corpus_type=CorpusType(corpus_type),
                    task_id=task_id
                )
                
                # Execute query (placeholder - would integrate with actual corpus connectors)
                corpus_results = await _execute_corpus_query(
                    corpus_type=corpus_type,
                    query=request.query,
                    max_results=request.max_results
                )
                
                results.extend(corpus_results)
                corpus_breakdown[corpus_type] = len(corpus_results)
                
            except UnauthorizedCorpusAccessError:
                # User doesn't have access to this corpus
                corpus_breakdown[corpus_type] = 0
                continue
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Clean up temporary task
        await governance_protocol.finalize_task_governance(task_id)
        
        await SecurityLogger.log_governance_event(
            event_type="corpus_query_executed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=True,
            details={
                "query": request.query,
                "corpus_types": request.corpus_types,
                "results_count": len(results),
                "execution_time_ms": execution_time
            }
        )
        
        return CorpusQueryResult(
            query=request.query,
            results=results,
            total_results=len(results),
            corpus_breakdown=corpus_breakdown,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        await SecurityLogger.log_governance_event(
            event_type="corpus_query_failed",
            task_id=task_id,
            user_id=current_user["user_id"],
            success=False,
            details={"error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Corpus query failed: {str(e)}"
        )


# Helper functions for pipeline stages

async def _execute_ideator_stage(
    task_id: str,
    prompt: str, 
    context_sources: List[str],
    current_user: Dict[str, Any]
) -> AgentResult:
    """Execute Ideator stage with governance enforcement."""
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Create agent context
        agent_context = create_agent_context(
            task_id=task_id,
            agent_role=AgentRole.IDEATOR,
            input_content=prompt,
            user_id=current_user["user_id"],
            output_mode="chat"
        )
        
        # Initialize and execute real Ideator agent
        from ...agents.ideator_agent import IdeatorAgent, IdeatorInput, IdeatorMode
        
        ideator_agent = IdeatorAgent()
        
        # Initialize agent with governance context
        await ideator_agent.initialize(
            task_id=task_id,
            user_id=current_user["user_id"],
            governance_context=agent_context
        )
        
        # Prepare agent input
        agent_input = IdeatorInput(
            content=prompt,
            context_sources=context_sources,
            mode=IdeatorMode.OUTLINE,
            target_audience="general",
            content_type="content",
            context_depth=min(3, len(context_sources) + 1)
        )
        
        # Execute agent
        agent_result = await ideator_agent.execute(agent_input)
        
        # Convert to API result format
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="ideator",
            content=agent_result.content or "No content generated",
            metadata={
                **agent_result.metadata,
                "context_sources": context_sources,
                "success": agent_result.success
            },
            execution_time_ms=execution_time,
            api_calls_used=agent_result.performance_metrics.get("api_calls", 0) if agent_result.performance_metrics else 0,
            governance_status="compliant" if agent_result.success else "failed"
        )
        
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="ideator", 
            content="",
            metadata={"error": str(e)},
            execution_time_ms=execution_time,
            api_calls_used=0,
            governance_status="failed"
        )


async def _execute_drafter_stage(
    task_id: str,
    ideator_result: AgentResult,
    current_user: Dict[str, Any]
) -> AgentResult:
    """Execute Drafter stage with governance enforcement."""
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Placeholder for Drafter agent execution
        draft_content = f"Expanded draft based on outline: {ideator_result.content[:100]}..."
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="drafter",
            content=draft_content,
            metadata={"word_count": 500, "based_on": "ideator_outline"},
            execution_time_ms=execution_time,
            api_calls_used=1,
            governance_status="compliant"
        )
        
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="drafter",
            content="",
            metadata={"error": str(e)},
            execution_time_ms=execution_time,
            api_calls_used=0,
            governance_status="failed"
        )


async def _execute_critic_stage(
    task_id: str,
    drafter_result: AgentResult,
    current_user: Dict[str, Any]
) -> AgentResult:
    """Execute Critic stage with governance enforcement."""
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Placeholder for Critic agent execution with RAG access
        validation_notes = f"Validation complete for draft: {drafter_result.content[:100]}..."
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="critic",
            content=validation_notes,
            metadata={
                "truth_score": 0.9,
                "safety_score": 0.95,
                "voice_score": 0.85,
                "corrections_needed": 2
            },
            execution_time_ms=execution_time,
            api_calls_used=2,  # Includes RAG queries
            governance_status="compliant"
        )
        
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="critic",
            content="",
            metadata={"error": str(e)},
            execution_time_ms=execution_time,
            api_calls_used=0,
            governance_status="failed"
        )


async def _execute_revisor_stage(
    task_id: str,
    drafter_result: AgentResult,
    critic_result: AgentResult,
    current_user: Dict[str, Any]
) -> AgentResult:
    """Execute Revisor stage with MVLM preference."""
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Placeholder for Revisor agent execution (MVLM primary)
        revised_content = f"Revised content: {drafter_result.content}"
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="revisor",
            content=revised_content,
            metadata={
                "processing_method": "mvlm",
                "corrections_applied": critic_result.metadata.get("corrections_needed", 0)
            },
            execution_time_ms=execution_time,
            api_calls_used=0,  # MVLM used, no API calls
            governance_status="compliant"
        )
        
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="revisor",
            content="",
            metadata={"error": str(e)},
            execution_time_ms=execution_time,
            api_calls_used=0,
            governance_status="failed"
        )


async def _execute_summarizer_stage(
    task_id: str,
    revisor_result: AgentResult,
    target_length: Optional[int],
    current_user: Dict[str, Any]
) -> AgentResult:
    """Execute Summarizer stage with MVLM only."""
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Placeholder for Summarizer agent execution (MVLM only)
        summary_content = f"Summary: {revisor_result.content[:200]}..."
        keywords = ["governance", "agents", "security", "ai"]
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="summarizer",
            content=summary_content,
            metadata={
                "processing_method": "mvlm",
                "keywords": keywords,
                "compression_ratio": 0.3,
                "target_length": target_length
            },
            execution_time_ms=execution_time,
            api_calls_used=0,  # MVLM only, no API calls
            governance_status="compliant"
        )
        
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_role="summarizer",
            content="",
            metadata={"error": str(e)},
            execution_time_ms=execution_time,
            api_calls_used=0,
            governance_status="failed"
        )


async def _execute_corpus_query(
    corpus_type: str,
    query: str,
    max_results: int
) -> List[Dict[str, Any]]:
    """Execute corpus query (placeholder implementation)."""
    
    # Placeholder implementation - would integrate with actual corpus connectors
    mock_results = [
        {
            "id": f"{corpus_type}_result_{i}",
            "content": f"Mock result {i} from {corpus_type} corpus for query: {query}",
            "relevance_score": 0.9 - (i * 0.1),
            "source": corpus_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for i in range(min(3, max_results))  # Return up to 3 mock results
    ]
    
    return mock_results