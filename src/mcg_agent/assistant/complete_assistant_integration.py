"""Complete assistant integration system that orchestrates all components into a unified personal AI assistant."""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from .protocols import (
    PersonalAssistantProtocol,
    AssistantContext,
    AssistantRequest,
    AssistantResponse,
    AssistantMode,
    ResponseStyle
)
from .personal_assistant_core import PersonalAssistantCore
from .context_aware_responder import ContextAwareResponder
from .intent_analyzer import AdvancedIntentAnalyzer
from .conversation_manager import ConversationManager
from .task_automation import TaskAutomationEngine

from ..voice_features.adapters import DynamicVoiceAdapter
from ..voice_features.learning import VoiceLearningSystem
from ..voice_features.monitoring import VoiceConsistencyMonitor, VoiceDriftDetector
from ..voice import VoiceFingerprintExtractor, VoiceFingerprintApplicator

from ..mvlm import PersonalVoiceMVLMManager
from ..governance import PersonalDataGovernanceManager
from ..security import PersonalVoiceAuditTrail
from ..pydantic_ai import VoiceReplicationPipeline

logger = logging.getLogger(__name__)


class AssistantCapability(Enum):
    """Assistant capability types."""
    CONVERSATION = "conversation"
    TASK_AUTOMATION = "task_automation"
    CONTENT_CREATION = "content_creation"
    VOICE_REPLICATION = "voice_replication"
    LEARNING = "learning"
    ANALYSIS = "analysis"


@dataclass
class AssistantPerformanceMetrics:
    """Performance metrics for the complete assistant."""
    total_requests: int
    successful_requests: int
    average_response_time_ms: float
    average_voice_consistency: float
    average_user_satisfaction: float
    capability_usage: Dict[str, int]
    error_rate: float
    uptime_percentage: float
    voice_learning_progress: float
    conversation_quality_average: float


class CompleteAssistantIntegration(PersonalAssistantProtocol):
    """
    Complete personal AI assistant integration that orchestrates all components
    into a unified system for authentic voice replication and personal assistance.
    
    This system provides:
    - Unified interface for all assistant capabilities
    - End-to-end workflow orchestration
    - Performance monitoring and optimization
    - Comprehensive error handling and recovery
    - Real-time quality assurance
    """
    
    def __init__(
        self,
        # Core components
        personal_assistant_core: PersonalAssistantCore,
        context_aware_responder: ContextAwareResponder,
        intent_analyzer: AdvancedIntentAnalyzer,
        conversation_manager: ConversationManager,
        task_automation_engine: TaskAutomationEngine,
        
        # Voice components
        voice_adapter: DynamicVoiceAdapter,
        voice_learning_system: VoiceLearningSystem,
        voice_monitor: VoiceConsistencyMonitor,
        voice_drift_detector: VoiceDriftDetector,
        voice_fingerprint_extractor: VoiceFingerprintExtractor,
        voice_fingerprint_applicator: VoiceFingerprintApplicator,
        
        # Infrastructure components
        mvlm_manager: PersonalVoiceMVLMManager,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail,
        voice_pipeline: VoiceReplicationPipeline
    ):
        """
        Initialize complete assistant integration.
        
        Args:
            All component dependencies for complete assistant functionality
        """
        # Core components
        self.personal_assistant_core = personal_assistant_core
        self.context_aware_responder = context_aware_responder
        self.intent_analyzer = intent_analyzer
        self.conversation_manager = conversation_manager
        self.task_automation_engine = task_automation_engine
        
        # Voice components
        self.voice_adapter = voice_adapter
        self.voice_learning_system = voice_learning_system
        self.voice_monitor = voice_monitor
        self.voice_drift_detector = voice_drift_detector
        self.voice_fingerprint_extractor = voice_fingerprint_extractor
        self.voice_fingerprint_applicator = voice_fingerprint_applicator
        
        # Infrastructure components
        self.mvlm_manager = mvlm_manager
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        self.voice_pipeline = voice_pipeline
        
        # Assistant configuration
        self.assistant_config = {
            'max_concurrent_requests': 10,
            'request_timeout_seconds': 30,
            'voice_consistency_threshold': 0.8,
            'quality_assurance_enabled': True,
            'learning_enabled': True,
            'drift_detection_enabled': True,
            'performance_monitoring_enabled': True,
            'auto_optimization_enabled': True,
            'conversation_context_enabled': True,
            'task_automation_enabled': True
        }
        
        # Performance tracking
        self.performance_metrics = AssistantPerformanceMetrics(
            total_requests=0,
            successful_requests=0,
            average_response_time_ms=0.0,
            average_voice_consistency=0.0,
            average_user_satisfaction=0.0,
            capability_usage={cap.value: 0 for cap in AssistantCapability},
            error_rate=0.0,
            uptime_percentage=100.0,
            voice_learning_progress=0.0,
            conversation_quality_average=0.0
        )
        
        # Active requests tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Component health status
        self.component_health = {
            'personal_assistant_core': True,
            'context_aware_responder': True,
            'intent_analyzer': True,
            'conversation_manager': True,
            'task_automation_engine': True,
            'voice_adapter': True,
            'voice_learning_system': True,
            'voice_monitor': True,
            'mvlm_manager': True,
            'governance_manager': True,
            'voice_pipeline': True
        }
        
        # Assistant startup time
        self.startup_time = datetime.now()
        
        # Initialize component monitoring
        asyncio.create_task(self._start_background_monitoring())
    
    async def process_request(
        self,
        request: AssistantRequest
    ) -> AssistantResponse:
        """
        Process a complete assistant request with full orchestration.
        
        Args:
            request: Assistant request with context and parameters
            
        Returns:
            Complete assistant response
        """
        request_start_time = datetime.now()
        request_id = request.request_id or f"req_{uuid.uuid4().hex[:8]}"
        
        try:
            # Track active request
            self.active_requests[request_id] = {
                'request': request,
                'start_time': request_start_time,
                'status': 'processing'
            }
            
            # Update metrics
            self.performance_metrics.total_requests += 1
            
            # Validate request and governance permissions
            validation_result = await self._validate_request(request)
            if not validation_result['valid']:
                return await self._create_error_response(
                    request, f"Request validation failed: {validation_result['error']}"
                )
            
            # Determine processing strategy based on request type and context
            processing_strategy = await self._determine_processing_strategy(request)
            
            # Execute processing strategy
            response = await self._execute_processing_strategy(
                request, processing_strategy, request_start_time
            )
            
            # Post-process response for quality assurance
            if self.assistant_config['quality_assurance_enabled']:
                response = await self._post_process_response(request, response)
            
            # Update learning system if enabled
            if self.assistant_config['learning_enabled']:
                await self._update_learning_system(request, response)
            
            # Update performance metrics
            await self._update_performance_metrics(request, response, request_start_time)
            
            # Clean up active request
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            # Mark as successful
            self.performance_metrics.successful_requests += 1
            
            logger.info(f"Assistant request completed: {request_id}")
            return response
            
        except Exception as e:
            logger.error(f"Assistant request failed: {request_id} - {str(e)}")
            
            # Clean up active request
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            # Log error for audit
            await self.audit_trail.log_voice_usage(
                user_id=request.context.user_id,
                operation_type='assistant_request',
                voice_patterns_used=[],
                success=False,
                metadata={
                    'request_id': request_id,
                    'error': str(e),
                    'request_type': request.request_type
                }
            )
            
            return await self._create_error_response(request, str(e))
    
    async def analyze_intent(
        self,
        user_input: str,
        context: AssistantContext
    ) -> Dict[str, Any]:
        """
        Analyze user intent with complete context awareness.
        
        Args:
            user_input: User's input text
            context: Assistant context
            
        Returns:
            Complete intent analysis
        """
        try:
            # Use advanced intent analyzer
            intent_result = await self.intent_analyzer.analyze_intent(
                user_input, context
            )
            
            # Enhance with conversation context if available
            if hasattr(context, 'conversation_id') and context.conversation_id:
                conversation_context = await self._get_conversation_context(
                    context.conversation_id
                )
                intent_result['conversation_context'] = conversation_context
            
            # Track capability usage
            if 'primary_intent' in intent_result:
                capability = self._map_intent_to_capability(intent_result['primary_intent'])
                self.performance_metrics.capability_usage[capability.value] += 1
            
            return intent_result
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return {
                'primary_intent': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def generate_response(
        self,
        intent: Dict[str, Any],
        context: AssistantContext,
        style: ResponseStyle = ResponseStyle.ADAPTIVE
    ) -> str:
        """
        Generate response with complete voice replication and context awareness.
        
        Args:
            intent: Analyzed intent information
            context: Assistant context
            style: Response style preference
            
        Returns:
            Generated response text
        """
        try:
            # Determine if this is part of a conversation
            if hasattr(context, 'conversation_id') and context.conversation_id:
                # Use conversation manager for contextual response
                response = await self._generate_conversational_response(
                    intent, context, style
                )
            else:
                # Use context-aware responder for standalone response
                response = await self._generate_standalone_response(
                    intent, context, style
                )
            
            # Validate voice consistency
            if self.assistant_config['quality_assurance_enabled']:
                voice_consistency = await self._validate_response_voice_consistency(
                    response, context
                )
                
                if voice_consistency < self.assistant_config['voice_consistency_threshold']:
                    # Attempt to improve voice consistency
                    response = await self._improve_voice_consistency(
                        response, context, voice_consistency
                    )
            
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Could you please try again?"
    
    # Processing strategy methods
    
    async def _determine_processing_strategy(
        self,
        request: AssistantRequest
    ) -> Dict[str, Any]:
        """Determine the optimal processing strategy for the request."""
        try:
            # Analyze intent to understand request type
            intent_analysis = await self.analyze_intent(
                request.user_input, request.context
            )
            
            primary_intent = intent_analysis.get('primary_intent', 'unknown')
            confidence = intent_analysis.get('confidence', 0.0)
            
            # Determine processing approach
            if primary_intent in ['task', 'command'] and confidence > 0.7:
                strategy = 'task_automation'
            elif primary_intent in ['question', 'request', 'information'] and confidence > 0.6:
                if hasattr(request.context, 'conversation_id') and request.context.conversation_id:
                    strategy = 'conversational'
                else:
                    strategy = 'contextual_response'
            elif primary_intent in ['creative', 'analysis'] and confidence > 0.6:
                strategy = 'voice_pipeline'
            else:
                strategy = 'personal_assistant_core'
            
            return {
                'strategy': strategy,
                'intent_analysis': intent_analysis,
                'confidence': confidence,
                'requires_conversation_context': hasattr(request.context, 'conversation_id') and request.context.conversation_id,
                'requires_task_automation': primary_intent in ['task', 'command'],
                'requires_voice_pipeline': primary_intent in ['creative', 'analysis', 'content_creation']
            }
            
        except Exception as e:
            logger.error(f"Processing strategy determination failed: {str(e)}")
            return {
                'strategy': 'personal_assistant_core',
                'error': str(e)
            }
    
    async def _execute_processing_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any],
        start_time: datetime
    ) -> AssistantResponse:
        """Execute the determined processing strategy."""
        try:
            strategy_type = strategy['strategy']
            
            if strategy_type == 'task_automation':
                return await self._execute_task_automation_strategy(request, strategy)
            elif strategy_type == 'conversational':
                return await self._execute_conversational_strategy(request, strategy)
            elif strategy_type == 'contextual_response':
                return await self._execute_contextual_response_strategy(request, strategy)
            elif strategy_type == 'voice_pipeline':
                return await self._execute_voice_pipeline_strategy(request, strategy)
            else:
                return await self._execute_personal_assistant_strategy(request, strategy)
                
        except Exception as e:
            logger.error(f"Processing strategy execution failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    async def _execute_task_automation_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any]
    ) -> AssistantResponse:
        """Execute task automation strategy."""
        try:
            # Convert request to task automation request
            from .task_automation import TaskAutomationRequest, TaskPriority
            
            intent_analysis = strategy['intent_analysis']
            entities = intent_analysis.get('entities', {})
            
            # Determine task type from intent
            task_type = self._determine_task_type(intent_analysis)
            
            # Create task automation request
            task_request = TaskAutomationRequest(
                request_id=request.request_id,
                task_type=task_type,
                task_parameters=entities,
                target_platform=request.context.platform,
                priority=TaskPriority.NORMAL,
                automation_level=None,  # Let engine decide
                context=request.context
            )
            
            # Execute task automation
            task_result = await self.task_automation_engine.automate_task(task_request)
            
            # Convert to assistant response
            return AssistantResponse(
                response_id=task_result.task_id,
                request_id=request.request_id,
                content=task_result.generated_content or "Task completed successfully.",
                confidence=task_result.voice_consistency_score,
                voice_consistency_score=task_result.voice_consistency_score,
                context_appropriateness_score=0.8,  # Default for task automation
                processing_time_ms=task_result.execution_time_ms,
                voice_patterns_used=task_result.metadata.get('voice_patterns_used', []),
                corpus_accessed=task_result.metadata.get('corpus_access', []),
                metadata={
                    'strategy': 'task_automation',
                    'task_type': task_type,
                    'task_result': task_result.result_data,
                    'automation_level': task_result.automation_level
                }
            )
            
        except Exception as e:
            logger.error(f"Task automation strategy failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    async def _execute_conversational_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any]
    ) -> AssistantResponse:
        """Execute conversational strategy using conversation manager."""
        try:
            conversation_id = getattr(request.context, 'conversation_id', None)
            
            if conversation_id:
                # Continue existing conversation
                response = await self.conversation_manager.continue_conversation(
                    conversation_id, request.user_input, request.context
                )
            else:
                # Start new conversation
                conversation_id = await self.conversation_manager.start_conversation(
                    request.context, request.user_input
                )
                
                # Continue with first response
                response = await self.conversation_manager.continue_conversation(
                    conversation_id, request.user_input, request.context
                )
                
                # Add conversation ID to response metadata
                response.metadata['new_conversation_id'] = conversation_id
            
            return response
            
        except Exception as e:
            logger.error(f"Conversational strategy failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    async def _execute_contextual_response_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any]
    ) -> AssistantResponse:
        """Execute contextual response strategy."""
        try:
            # Use context-aware responder
            response_text = await self.context_aware_responder.generate_response(
                request.context, request.response_style or ResponseStyle.ADAPTIVE
            )
            
            # Calculate metrics
            voice_consistency = await self._validate_response_voice_consistency(
                response_text, request.context
            )
            
            context_appropriateness = await self._calculate_context_appropriateness(
                response_text, request.context
            )
            
            return AssistantResponse(
                response_id=f"ctx_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                content=response_text,
                confidence=voice_consistency,
                voice_consistency_score=voice_consistency,
                context_appropriateness_score=context_appropriateness,
                processing_time_ms=0,  # Will be calculated later
                voice_patterns_used=['personal', 'contextual'],
                corpus_accessed=['personal'],
                metadata={
                    'strategy': 'contextual_response',
                    'response_style': request.response_style.value if request.response_style else 'adaptive'
                }
            )
            
        except Exception as e:
            logger.error(f"Contextual response strategy failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    async def _execute_voice_pipeline_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any]
    ) -> AssistantResponse:
        """Execute voice pipeline strategy for complex content generation."""
        try:
            # Use voice replication pipeline
            pipeline_result = await self.voice_pipeline.process_request(
                user_prompt=request.user_input,
                context=request.context,
                mode=request.mode or AssistantMode.ADAPTIVE
            )
            
            return AssistantResponse(
                response_id=pipeline_result.get('response_id', f"pipe_{uuid.uuid4().hex[:8]}"),
                request_id=request.request_id,
                content=pipeline_result.get('final_response', ''),
                confidence=pipeline_result.get('voice_consistency', 0.8),
                voice_consistency_score=pipeline_result.get('voice_consistency', 0.8),
                context_appropriateness_score=pipeline_result.get('context_appropriateness', 0.8),
                processing_time_ms=pipeline_result.get('processing_time_ms', 0),
                voice_patterns_used=pipeline_result.get('voice_patterns_used', []),
                corpus_accessed=pipeline_result.get('corpus_accessed', []),
                metadata={
                    'strategy': 'voice_pipeline',
                    'pipeline_result': pipeline_result
                }
            )
            
        except Exception as e:
            logger.error(f"Voice pipeline strategy failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    async def _execute_personal_assistant_strategy(
        self,
        request: AssistantRequest,
        strategy: Dict[str, Any]
    ) -> AssistantResponse:
        """Execute personal assistant core strategy."""
        try:
            # Use personal assistant core
            response = await self.personal_assistant_core.process_request(request)
            
            # Add strategy metadata
            response.metadata['strategy'] = 'personal_assistant_core'
            
            return response
            
        except Exception as e:
            logger.error(f"Personal assistant strategy failed: {str(e)}")
            return await self._create_error_response(request, str(e))
    
    # Helper methods
    
    async def _validate_request(self, request: AssistantRequest) -> Dict[str, Any]:
        """Validate assistant request."""
        try:
            # Check governance permissions
            has_permission = await self.governance_manager.check_usage_permission(
                user_id=request.context.user_id,
                usage_type='assistant_request',
                agent_type='complete_assistant'
            )
            
            if not has_permission:
                return {
                    'valid': False,
                    'error': 'Insufficient permissions for assistant request'
                }
            
            # Check request limits
            if len(self.active_requests) >= self.assistant_config['max_concurrent_requests']:
                return {
                    'valid': False,
                    'error': 'Maximum concurrent requests limit reached'
                }
            
            # Validate input length
            if len(request.user_input) > 10000:  # 10k character limit
                return {
                    'valid': False,
                    'error': 'Input text too long (maximum 10,000 characters)'
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    def _determine_task_type(self, intent_analysis: Dict[str, Any]) -> str:
        """Determine task type from intent analysis."""
        entities = intent_analysis.get('entities', {})
        primary_intent = intent_analysis.get('primary_intent', 'unknown')
        
        # Map intent and entities to task types
        if 'email' in entities or 'email' in primary_intent:
            return 'email_draft'
        elif any(platform in entities for platform in ['twitter', 'linkedin', 'facebook']):
            return 'social_post'
        elif 'content' in entities or 'article' in entities:
            return 'content_creation'
        elif 'meeting' in entities or 'schedule' in entities:
            return 'schedule_meeting'
        elif 'reminder' in entities:
            return 'set_reminder'
        else:
            return 'general_task'
    
    def _map_intent_to_capability(self, intent: str) -> AssistantCapability:
        """Map intent to assistant capability."""
        intent_mapping = {
            'question': AssistantCapability.CONVERSATION,
            'request': AssistantCapability.CONVERSATION,
            'task': AssistantCapability.TASK_AUTOMATION,
            'command': AssistantCapability.TASK_AUTOMATION,
            'creative': AssistantCapability.CONTENT_CREATION,
            'analysis': AssistantCapability.ANALYSIS,
            'information': AssistantCapability.CONVERSATION
        }
        
        return intent_mapping.get(intent, AssistantCapability.CONVERSATION)
    
    async def _validate_response_voice_consistency(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """Validate voice consistency of response."""
        try:
            consistency_result = await self.voice_monitor.check_consistency(
                text=response,
                context={
                    'user_id': context.user_id,
                    'platform': context.platform,
                    'validation_mode': True
                }
            )
            
            return consistency_result.overall_consistency
            
        except Exception as e:
            logger.error(f"Voice consistency validation failed: {str(e)}")
            return 0.7  # Default moderate consistency
    
    async def _calculate_context_appropriateness(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """Calculate context appropriateness score."""
        try:
            # Use context-aware responder for appropriateness analysis
            appropriateness = await self.context_aware_responder.analyze_context(context)
            return appropriateness.get('appropriateness_score', 0.8)
            
        except Exception as e:
            logger.error(f"Context appropriateness calculation failed: {str(e)}")
            return 0.8  # Default good appropriateness
    
    async def _post_process_response(
        self,
        request: AssistantRequest,
        response: AssistantResponse
    ) -> AssistantResponse:
        """Post-process response for quality assurance."""
        try:
            # Check voice drift if enabled
            if self.assistant_config['drift_detection_enabled']:
                drift_result = await self.voice_drift_detector.detect_drift(
                    text=response.content,
                    context={
                        'user_id': request.context.user_id,
                        'platform': request.context.platform
                    }
                )
                
                if drift_result.drift_detected:
                    # Log drift detection
                    logger.warning(f"Voice drift detected: {drift_result.drift_type}")
                    response.metadata['voice_drift_detected'] = True
                    response.metadata['drift_severity'] = drift_result.severity
            
            # Update voice consistency score if needed
            if response.voice_consistency_score < self.assistant_config['voice_consistency_threshold']:
                # Attempt improvement
                improved_response = await self._improve_voice_consistency(
                    response.content, request.context, response.voice_consistency_score
                )
                
                if improved_response != response.content:
                    response.content = improved_response
                    response.voice_consistency_score = await self._validate_response_voice_consistency(
                        improved_response, request.context
                    )
                    response.metadata['voice_improved'] = True
            
            return response
            
        except Exception as e:
            logger.error(f"Response post-processing failed: {str(e)}")
            return response
    
    async def _improve_voice_consistency(
        self,
        response: str,
        context: AssistantContext,
        current_consistency: float
    ) -> str:
        """Attempt to improve voice consistency of response."""
        try:
            # Use voice adapter to improve consistency
            improved_voice = await self.voice_adapter.adapt_voice(
                text=response,
                context={
                    'user_id': context.user_id,
                    'platform': context.platform,
                    'improvement_mode': True,
                    'target_consistency': self.assistant_config['voice_consistency_threshold']
                },
                strategy='blend_contexts'
            )
            
            return improved_voice.adapted_text
            
        except Exception as e:
            logger.error(f"Voice consistency improvement failed: {str(e)}")
            return response
    
    async def _update_learning_system(
        self,
        request: AssistantRequest,
        response: AssistantResponse
    ) -> None:
        """Update learning system with successful interaction."""
        try:
            # Create learning data
            learning_data = {
                'user_input': request.user_input,
                'assistant_response': response.content,
                'voice_consistency': response.voice_consistency_score,
                'context_appropriateness': response.context_appropriateness_score,
                'user_satisfaction': None,  # To be updated later if feedback provided
                'platform': request.context.platform,
                'mode': request.mode.value if request.mode else 'adaptive'
            }
            
            # Update voice learning system
            await self.voice_learning_system.learn_from_usage(
                usage_data=learning_data,
                learning_mode='passive'
            )
            
        except Exception as e:
            logger.error(f"Learning system update failed: {str(e)}")
    
    async def _update_performance_metrics(
        self,
        request: AssistantRequest,
        response: AssistantResponse,
        start_time: datetime
    ) -> None:
        """Update performance metrics."""
        try:
            # Calculate response time
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            response.processing_time_ms = int(response_time_ms)
            
            # Update average response time
            total_requests = self.performance_metrics.total_requests
            current_avg = self.performance_metrics.average_response_time_ms
            self.performance_metrics.average_response_time_ms = (
                (current_avg * (total_requests - 1) + response_time_ms) / total_requests
            )
            
            # Update average voice consistency
            current_voice_avg = self.performance_metrics.average_voice_consistency
            self.performance_metrics.average_voice_consistency = (
                (current_voice_avg * (total_requests - 1) + response.voice_consistency_score) / total_requests
            )
            
            # Calculate error rate
            failed_requests = self.performance_metrics.total_requests - self.performance_metrics.successful_requests
            self.performance_metrics.error_rate = failed_requests / self.performance_metrics.total_requests
            
        except Exception as e:
            logger.error(f"Performance metrics update failed: {str(e)}")
    
    async def _create_error_response(
        self,
        request: AssistantRequest,
        error_message: str
    ) -> AssistantResponse:
        """Create error response."""
        return AssistantResponse(
            response_id=f"error_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            content=f"I apologize, but I encountered an error: {error_message}",
            confidence=0.0,
            voice_consistency_score=0.0,
            context_appropriateness_score=0.0,
            processing_time_ms=0,
            voice_patterns_used=[],
            corpus_accessed=[],
            metadata={'error': error_message}
        )
    
    async def _start_background_monitoring(self) -> None:
        """Start background monitoring tasks."""
        try:
            # Monitor component health
            asyncio.create_task(self._monitor_component_health())
            
            # Monitor performance
            asyncio.create_task(self._monitor_performance())
            
            # Monitor voice drift
            if self.assistant_config['drift_detection_enabled']:
                asyncio.create_task(self._monitor_voice_drift())
            
            logger.info("Background monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start background monitoring: {str(e)}")
    
    async def _monitor_component_health(self) -> None:
        """Monitor health of all components."""
        while True:
            try:
                # Check each component
                for component_name in self.component_health:
                    try:
                        # Simple health check - attempt to access component
                        component = getattr(self, component_name, None)
                        if component:
                            self.component_health[component_name] = True
                        else:
                            self.component_health[component_name] = False
                    except Exception:
                        self.component_health[component_name] = False
                
                # Calculate uptime percentage
                healthy_components = sum(1 for health in self.component_health.values() if health)
                total_components = len(self.component_health)
                self.performance_metrics.uptime_percentage = (healthy_components / total_components) * 100
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Component health monitoring failed: {str(e)}")
                await asyncio.sleep(60)
    
    async def _monitor_performance(self) -> None:
        """Monitor overall performance metrics."""
        while True:
            try:
                # Update conversation quality average
                if hasattr(self.conversation_manager, 'get_conversation_analytics'):
                    conv_analytics = self.conversation_manager.get_conversation_analytics()
                    self.performance_metrics.conversation_quality_average = conv_analytics.get(
                        'analytics', {}
                    ).get('average_quality_score', 0.0)
                
                # Update voice learning progress
                if hasattr(self.voice_learning_system, 'get_learning_statistics'):
                    learning_stats = self.voice_learning_system.get_learning_statistics()
                    self.performance_metrics.voice_learning_progress = learning_stats.get(
                        'learning_progress', 0.0
                    )
                
                # Sleep for 300 seconds (5 minutes) before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Performance monitoring failed: {str(e)}")
                await asyncio.sleep(300)
    
    async def _monitor_voice_drift(self) -> None:
        """Monitor for voice drift across all interactions."""
        while True:
            try:
                # Check for drift patterns
                drift_summary = await self.voice_drift_detector.get_drift_summary()
                
                if drift_summary.get('concerning_trends'):
                    logger.warning("Concerning voice drift trends detected")
                    # Could trigger automatic voice recalibration here
                
                # Sleep for 1800 seconds (30 minutes) before next check
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Voice drift monitoring failed: {str(e)}")
                await asyncio.sleep(1800)
    
    def get_assistant_status(self) -> Dict[str, Any]:
        """Get complete assistant status and metrics."""
        uptime_seconds = (datetime.now() - self.startup_time).total_seconds()
        
        return {
            'status': 'healthy' if self.performance_metrics.uptime_percentage > 80 else 'degraded',
            'uptime_seconds': uptime_seconds,
            'performance_metrics': {
                'total_requests': self.performance_metrics.total_requests,
                'successful_requests': self.performance_metrics.successful_requests,
                'success_rate': (
                    self.performance_metrics.successful_requests / self.performance_metrics.total_requests
                    if self.performance_metrics.total_requests > 0 else 0.0
                ),
                'average_response_time_ms': self.performance_metrics.average_response_time_ms,
                'average_voice_consistency': self.performance_metrics.average_voice_consistency,
                'error_rate': self.performance_metrics.error_rate,
                'uptime_percentage': self.performance_metrics.uptime_percentage
            },
            'capability_usage': self.performance_metrics.capability_usage,
            'component_health': self.component_health,
            'active_requests': len(self.active_requests),
            'configuration': self.assistant_config,
            'voice_metrics': {
                'learning_progress': self.performance_metrics.voice_learning_progress,
                'conversation_quality': self.performance_metrics.conversation_quality_average,
                'voice_consistency_average': self.performance_metrics.average_voice_consistency
            }
        }
