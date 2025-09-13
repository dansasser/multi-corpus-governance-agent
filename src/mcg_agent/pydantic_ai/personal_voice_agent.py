"""
Personal Voice Agent Base Class

Base class for PydanticAI agents that replicate user's voice.
Integrates with MVLM models and governance systems for authentic voice replication.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field

from mcg_agent.pydantic_ai.agent_base import AgentRole, AgentInput, AgentOutput, GovernanceContext
from mcg_agent.mvlm.personal_voice_mvlm_manager import PersonalVoiceMVLMManager, VoiceContext, MVLMModelType
from mcg_agent.mvlm.voice_aware_text_generator import VoiceAwareTextGenerator, VoiceProfile
from mcg_agent.security.voice_pattern_access_control import VoicePatternAccessControl
from mcg_agent.security.personal_voice_audit_trail import PersonalVoiceAuditTrail
from mcg_agent.utils.exceptions import VoiceAgentError
from mcg_agent.utils.audit import AuditLogger


class VoiceAgentContext(BaseModel):
    """Extended context for voice-aware agents"""
    governance_context: GovernanceContext
    voice_profile: Optional[VoiceProfile] = None
    target_audience: str = Field(default="general")
    desired_tone: str = Field(default="professional")
    context_type: str = Field(default="general")
    corpus_preferences: List[str] = Field(default_factory=lambda: ["personal", "social", "published"])
    voice_influence_level: float = Field(default=0.7, description="0-1 level of voice influence")


class VoiceAgentResult(BaseModel):
    """Result from voice-aware agent processing"""
    agent_output: AgentOutput
    voice_consistency_score: float = Field(description="0-1 score of voice consistency")
    voice_patterns_used: List[str] = Field(description="Voice patterns that influenced output")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonalVoiceAgent(ABC):
    """
    Base class for voice-replicating agents.
    
    Provides common functionality for agents that need to replicate user's voice:
    - Voice pattern access and integration
    - MVLM text generation with voice consistency
    - Governance and audit compliance
    - Performance monitoring
    """
    
    def __init__(self, role: AgentRole, voice_profile: Optional[VoiceProfile] = None):
        self.role = role
        self.voice_profile = voice_profile
        
        # Initialize voice components
        self.mvlm_manager = PersonalVoiceMVLMManager()
        self.voice_generator = VoiceAwareTextGenerator()
        self.access_control = VoicePatternAccessControl()
        self.audit_trail = PersonalVoiceAuditTrail()
        self.audit_logger = AuditLogger()
        
        # Agent-specific corpus access permissions
        self.corpus_access = self._get_corpus_permissions()
        
        # Performance tracking
        self._processing_times: List[float] = []
        self._voice_scores: List[float] = []
        
    def _get_corpus_permissions(self) -> List[str]:
        """Get corpus access permissions for this agent role"""
        permissions = {
            "ideator": ["personal", "social", "published"],  # Full access for analysis
            "drafter": ["personal", "social"],               # Personal + Social for natural tone
            "critic": ["personal", "social", "published"],   # Full access for validation
            "revisor": [],                                   # No new corpus access
            "summarizer": []                                 # No new corpus access
        }
        
        return permissions.get(self.role, [])
        
    async def process_with_voice(self, input_data: AgentInput, context: VoiceAgentContext) -> VoiceAgentResult:
        """
        Process input while maintaining user's voice.
        
        Args:
            input_data: Agent input data
            context: Voice-aware context
            
        Returns:
            VoiceAgentResult: Processing result with voice consistency
        """
        try:
            start_time = datetime.utcnow()
            
            # Validate agent has permission to process this input
            if not self._validate_processing_permission(input_data, context):
                raise VoiceAgentError(f"Agent {self.role} not authorized for this processing")
                
            # Create voice context for generation
            voice_context = self._create_voice_context(input_data, context)
            
            # Process with role-specific logic
            processed_content = await self._process_content(input_data, voice_context, context)
            
            # Generate voice-consistent output if needed
            if self._should_use_voice_generation(input_data, context):
                final_content, voice_patterns_used = await self.voice_generator.generate_with_voice(
                    user_query=processed_content,
                    voice_context=voice_context,
                    agent_role=self.role,
                    task_id=input_data.task_id
                )
            else:
                final_content = processed_content
                voice_patterns_used = []
                
            # Calculate voice consistency score
            voice_consistency_score = await self._calculate_voice_consistency(
                final_content, 
                context.voice_profile or self.voice_profile
            )
            
            # Create agent output
            agent_output = AgentOutput(
                task_id=input_data.task_id,
                agent_role=self.role,
                content=final_content,
                context_pack=input_data.context_pack,
                metadata={
                    "voice_consistency_score": voice_consistency_score,
                    "voice_patterns_used": [vp.pattern_content for vp in voice_patterns_used] if hasattr(voice_patterns_used[0], 'pattern_content') if voice_patterns_used else [],
                    "processing_agent": self.role,
                    "corpus_sources_used": voice_context.corpus_sources,
                    "voice_influence_level": voice_context.influence_level
                }
            )
            
            # Track performance
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._processing_times.append(processing_time)
            self._voice_scores.append(voice_consistency_score)
            
            # Create result
            result = VoiceAgentResult(
                agent_output=agent_output,
                voice_consistency_score=voice_consistency_score,
                voice_patterns_used=[vp.pattern_content for vp in voice_patterns_used] if hasattr(voice_patterns_used[0], 'pattern_content') if voice_patterns_used else [],
                processing_metadata={
                    "processing_time_ms": processing_time,
                    "model_used": self.mvlm_manager.active_model,
                    "corpus_access_used": self.corpus_access
                }
            )
            
            self.audit_logger.log_info(
                f"Agent {self.role} processed task {input_data.task_id} with voice score {voice_consistency_score:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.audit_logger.log_error(f"Agent {self.role} processing failed: {str(e)}")
            raise VoiceAgentError(f"Failed to process with voice: {str(e)}")
            
    def _validate_processing_permission(self, input_data: AgentInput, context: VoiceAgentContext) -> bool:
        """Validate agent has permission to process this input"""
        # Basic validation - can be extended with more sophisticated rules
        return input_data.agent_role == self.role
        
    def _create_voice_context(self, input_data: AgentInput, context: VoiceAgentContext) -> VoiceContext:
        """Create voice context for MVLM generation"""
        # Extract voice patterns from profile if available
        voice_patterns = []
        if context.voice_profile:
            voice_patterns.extend(context.voice_profile.common_phrases[:5])  # Limit to top 5
            
        return VoiceContext(
            voice_patterns=voice_patterns,
            tone=context.desired_tone,
            audience=context.target_audience,
            context_type=context.context_type,
            corpus_sources=self.corpus_access,  # Use agent's permitted corpora
            influence_level=context.voice_influence_level
        )
        
    @abstractmethod
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content with agent-specific logic.
        
        This method must be implemented by each agent type to define
        their specific processing behavior.
        """
        pass
        
    def _should_use_voice_generation(self, input_data: AgentInput, context: VoiceAgentContext) -> bool:
        """Determine if voice generation should be used"""
        # Revisor and Summarizer typically use MVLM directly
        # Other agents may use voice generation for consistency
        return self.role not in ["revisor", "summarizer"]
        
    async def _calculate_voice_consistency(
        self, 
        content: str, 
        voice_profile: Optional[VoiceProfile]
    ) -> float:
        """Calculate voice consistency score"""
        if not voice_profile:
            return 0.5  # Default moderate score
            
        validation_result = self.voice_generator.validate_voice_consistency(content, voice_profile)
        return validation_result.consistency_score
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this agent"""
        if not self._processing_times:
            return {"no_data": True}
            
        return {
            "agent_role": self.role,
            "total_processed": len(self._processing_times),
            "avg_processing_time_ms": sum(self._processing_times) / len(self._processing_times),
            "avg_voice_consistency": sum(self._voice_scores) / len(self._voice_scores),
            "corpus_access": self.corpus_access,
            "recent_performance": {
                "last_10_avg_time": sum(self._processing_times[-10:]) / min(len(self._processing_times), 10),
                "last_10_avg_voice": sum(self._voice_scores[-10:]) / min(len(self._voice_scores), 10)
            }
        }
        
    async def switch_mvlm_model(self, model_type: MVLMModelType) -> bool:
        """Switch MVLM model for benchmarking"""
        return self.mvlm_manager.switch_model(model_type)
        
    def update_voice_profile(self, voice_profile: VoiceProfile) -> None:
        """Update the voice profile for this agent"""
        self.voice_profile = voice_profile
        self.audit_logger.log_info(f"Updated voice profile for agent {self.role}")


class VoiceReplicationPipeline:
    """
    Orchestrate agents for authentic voice replication.
    
    Manages the complete pipeline: Ideator → Drafter → Critic → Revisor → Summarizer
    """
    
    def __init__(self, voice_profile: Optional[VoiceProfile] = None):
        self.voice_profile = voice_profile
        self.audit_logger = AuditLogger()
        
        # Initialize agents (will be created by specific implementations)
        self.agents: Dict[AgentRole, PersonalVoiceAgent] = {}
        
    def register_agent(self, agent: PersonalVoiceAgent) -> None:
        """Register an agent in the pipeline"""
        self.agents[agent.role] = agent
        if self.voice_profile:
            agent.update_voice_profile(self.voice_profile)
            
    async def replicate_voice(
        self, 
        user_query: str, 
        context: Optional[VoiceAgentContext] = None
    ) -> VoiceAgentResult:
        """
        Complete pipeline for voice replication.
        
        Args:
            user_query: User's query to process
            context: Optional voice context
            
        Returns:
            VoiceAgentResult: Final result with voice consistency
        """
        try:
            task_id = f"voice_replication_{datetime.utcnow().isoformat()}"
            
            # Create default context if not provided
            if not context:
                governance_context = GovernanceContext(
                    task_id=task_id,
                    user_prompt=user_query,
                    classification="voice"
                )
                context = VoiceAgentContext(governance_context=governance_context)
                
            # 1. Ideator: Analyze query and gather voice context from all corpora
            if "ideator" in self.agents:
                ideator_input = AgentInput(
                    task_id=task_id,
                    agent_role="ideator",
                    content=user_query
                )
                ideator_result = await self.agents["ideator"].process_with_voice(ideator_input, context)
                current_content = ideator_result.agent_output.content
            else:
                current_content = user_query
                
            # 2. Drafter: Create initial response using personal + social voice
            if "drafter" in self.agents:
                drafter_input = AgentInput(
                    task_id=task_id,
                    agent_role="drafter",
                    content=current_content
                )
                drafter_result = await self.agents["drafter"].process_with_voice(drafter_input, context)
                current_content = drafter_result.agent_output.content
                
            # 3. Critic: Validate voice authenticity against all corpora
            if "critic" in self.agents:
                critic_input = AgentInput(
                    task_id=task_id,
                    agent_role="critic",
                    content=current_content
                )
                critic_result = await self.agents["critic"].process_with_voice(critic_input, context)
                current_content = critic_result.agent_output.content
                
            # 4. Revisor: Refine using MVLM while preserving voice
            if "revisor" in self.agents:
                revisor_input = AgentInput(
                    task_id=task_id,
                    agent_role="revisor",
                    content=current_content
                )
                revisor_result = await self.agents["revisor"].process_with_voice(revisor_input, context)
                current_content = revisor_result.agent_output.content
                
            # 5. Summarizer: Final voice consistency check
            if "summarizer" in self.agents:
                summarizer_input = AgentInput(
                    task_id=task_id,
                    agent_role="summarizer",
                    content=current_content
                )
                final_result = await self.agents["summarizer"].process_with_voice(summarizer_input, context)
            else:
                # Create final result if no summarizer
                final_result = VoiceAgentResult(
                    agent_output=AgentOutput(
                        task_id=task_id,
                        agent_role="pipeline",
                        content=current_content
                    ),
                    voice_consistency_score=0.8,  # Default score
                    voice_patterns_used=[],
                    processing_metadata={"pipeline_complete": True}
                )
                
            self.audit_logger.log_info(f"Voice replication pipeline completed for task {task_id}")
            
            return final_result
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice replication pipeline failed: {str(e)}")
            raise VoiceAgentError(f"Pipeline failed: {str(e)}")
            
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics for the entire pipeline"""
        stats = {
            "registered_agents": list(self.agents.keys()),
            "voice_profile_loaded": self.voice_profile is not None,
            "agent_stats": {}
        }
        
        for role, agent in self.agents.items():
            stats["agent_stats"][role] = agent.get_performance_stats()
            
        return stats


__all__ = [
    "PersonalVoiceAgent",
    "VoiceAgentContext",
    "VoiceAgentResult",
    "VoiceReplicationPipeline"
]
