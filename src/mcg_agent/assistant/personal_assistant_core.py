"""Personal assistant core implementation."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from .protocols import (
    PersonalAssistantProtocol,
    AssistantContext,
    AssistantRequest,
    AssistantResponse,
    AssistantMode,
    ResponseStyle,
    TaskPriority
)
from ..voice_features.adapters import DynamicVoiceAdapter
from ..voice_features.learning import VoiceLearningSystem
from ..voice_features.monitoring import VoiceConsistencyMonitor
from ..mvlm import PersonalVoiceMVLMManager
from ..pydantic_ai.personal_voice_agent import VoiceReplicationPipeline
from ..governance import PersonalDataGovernanceManager
from ..security import PersonalVoiceAuditTrail

logger = logging.getLogger(__name__)


class PersonalAssistantCore(PersonalAssistantProtocol):
    """
    Core personal assistant that orchestrates all voice features
    into a unified, authentic personal AI assistant experience.
    
    This assistant specializes in:
    - Authentic voice replication across all interactions
    - Context-aware response generation
    - Multi-mode operation (personal, professional, creative, analytical)
    - Intelligent task automation with voice consistency
    - Continuous learning and improvement
    """
    
    def __init__(
        self,
        voice_adapter: DynamicVoiceAdapter,
        voice_learning: VoiceLearningSystem,
        voice_monitor: VoiceConsistencyMonitor,
        mvlm_manager: PersonalVoiceMVLMManager,
        voice_pipeline: VoiceReplicationPipeline,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail
    ):
        """
        Initialize personal assistant core.
        
        Args:
            voice_adapter: Dynamic voice adaptation system
            voice_learning: Voice learning and evolution system
            voice_monitor: Voice consistency monitoring
            mvlm_manager: MVLM management for text generation
            voice_pipeline: Complete voice replication pipeline
            governance_manager: Personal data governance
            audit_trail: Voice usage audit trail
        """
        self.voice_adapter = voice_adapter
        self.voice_learning = voice_learning
        self.voice_monitor = voice_monitor
        self.mvlm_manager = mvlm_manager
        self.voice_pipeline = voice_pipeline
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        
        # Assistant configuration
        self.assistant_config = {
            'default_mode': AssistantMode.ADAPTIVE,
            'default_response_style': ResponseStyle.ADAPTIVE,
            'max_conversation_history': 50,
            'voice_consistency_threshold': 0.8,
            'context_appropriateness_threshold': 0.7,
            'learning_enabled': True,
            'monitoring_enabled': True
        }
        
        # Active conversations
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        # Assistant statistics
        self.assistant_stats = {
            'total_requests': 0,
            'successful_responses': 0,
            'voice_consistency_average': 0.0,
            'context_appropriateness_average': 0.0,
            'average_response_time_ms': 0.0,
            'learning_sessions': 0,
            'mode_usage': {mode.value: 0 for mode in AssistantMode},
            'style_usage': {style.value: 0 for style in ResponseStyle}
        }
        
        # Intent classification patterns
        self.intent_patterns = {
            'question': ['what', 'how', 'why', 'when', 'where', 'who', '?'],
            'request': ['please', 'can you', 'could you', 'would you', 'help me'],
            'command': ['create', 'write', 'generate', 'make', 'build', 'draft'],
            'information': ['tell me', 'explain', 'describe', 'define', 'about'],
            'task': ['schedule', 'remind', 'send', 'email', 'post', 'publish'],
            'creative': ['brainstorm', 'ideas', 'creative', 'imagine', 'story'],
            'analysis': ['analyze', 'compare', 'evaluate', 'assess', 'review']
        }
        
        # Response type mappings
        self.response_types = {
            'question': 'informational_response',
            'request': 'helpful_response',
            'command': 'task_completion',
            'information': 'explanatory_response',
            'task': 'automation_response',
            'creative': 'creative_response',
            'analysis': 'analytical_response'
        }
    
    async def process_request(
        self,
        request: AssistantRequest
    ) -> AssistantResponse:
        """
        Process a user request and generate an appropriate response.
        
        Args:
            request: Assistant request with user input and context
            
        Returns:
            Assistant response with generated content
        """
        start_time = datetime.now()
        
        try:
            # Validate governance permissions
            if not await self._validate_request_permissions(request):
                return await self._create_error_response(
                    request, "Insufficient permissions for request"
                )
            
            # Analyze intent
            intent_analysis = await self.analyze_intent(
                request.user_input, request.context
            )
            
            # Determine or create context
            context = request.context or await self._create_default_context(request)
            
            # Update context with intent
            context = await self._update_context_with_intent(context, intent_analysis)
            
            # Generate response using voice pipeline
            response_content = await self.generate_response(intent_analysis, context)
            
            # Validate voice consistency
            voice_consistency = await self._validate_voice_consistency(
                response_content, context
            )
            
            # Validate context appropriateness
            context_appropriateness = await self._validate_context_appropriateness(
                response_content, context
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create response
            response = AssistantResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                content=response_content,
                response_type=self.response_types.get(intent_analysis.get('primary_intent', 'question'), 'general_response'),
                confidence=intent_analysis.get('confidence', 0.8),
                voice_consistency_score=voice_consistency,
                context_appropriateness=context_appropriateness,
                processing_time_ms=int(processing_time),
                sources_used=intent_analysis.get('sources_used', []),
                voice_patterns_applied=intent_analysis.get('voice_patterns_applied', []),
                metadata={
                    'intent_analysis': intent_analysis,
                    'mode_used': context.mode.value,
                    'style_used': context.response_style.value,
                    'learning_applied': self.assistant_config['learning_enabled']
                }
            )
            
            # Update conversation context
            if context.session_id in self.active_conversations:
                await self._update_conversation_history(context.session_id, request, response)
            
            # Apply learning if enabled
            if self.assistant_config['learning_enabled']:
                await self._apply_learning_from_interaction(request, response, context)
            
            # Update statistics
            await self._update_assistant_statistics(request, response, context)
            
            # Log successful interaction
            await self.audit_trail.log_voice_usage(
                user_id=context.user_id,
                operation_type='assistant_response',
                voice_patterns_used=response.voice_patterns_applied,
                success=True,
                metadata={
                    'request_id': request.request_id,
                    'response_id': response.response_id,
                    'intent': intent_analysis.get('primary_intent'),
                    'voice_consistency': voice_consistency,
                    'context_appropriateness': context_appropriateness
                }
            )
            
            logger.info(f"Request processed successfully: {response.response_id}")
            return response
            
        except Exception as e:
            logger.error(f"Request processing failed: {str(e)}")
            
            # Log failed interaction
            await self.audit_trail.log_voice_usage(
                user_id=request.context.user_id if request.context else "unknown",
                operation_type='assistant_response',
                voice_patterns_used=[],
                success=False,
                metadata={
                    'request_id': request.request_id,
                    'error': str(e)
                }
            )
            
            return await self._create_error_response(request, str(e))
    
    async def analyze_intent(
        self,
        user_input: str,
        context: Optional[AssistantContext] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent from input.
        
        Args:
            user_input: User's input text
            context: Optional context information
            
        Returns:
            Intent analysis results
        """
        try:
            # Basic intent classification using patterns
            intent_scores = {}
            user_input_lower = user_input.lower()
            
            for intent_type, patterns in self.intent_patterns.items():
                score = sum(1 for pattern in patterns if pattern in user_input_lower)
                if score > 0:
                    intent_scores[intent_type] = score / len(patterns)
            
            # Determine primary intent
            if intent_scores:
                primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
                confidence = intent_scores[primary_intent]
            else:
                primary_intent = 'question'  # Default intent
                confidence = 0.5
            
            # Extract entities (basic implementation)
            entities = await self._extract_basic_entities(user_input)
            
            # Determine response requirements
            response_requirements = await self._determine_response_requirements(
                primary_intent, entities, context
            )
            
            # Determine voice patterns needed
            voice_patterns_needed = await self._determine_voice_patterns_needed(
                primary_intent, context
            )
            
            intent_analysis = {
                'primary_intent': primary_intent,
                'intent_scores': intent_scores,
                'confidence': confidence,
                'entities': entities,
                'response_requirements': response_requirements,
                'voice_patterns_needed': voice_patterns_needed,
                'requires_corpus_access': response_requirements.get('requires_corpus_access', False),
                'complexity': response_requirements.get('complexity', 'medium'),
                'estimated_response_length': response_requirements.get('estimated_length', 'medium')
            }
            
            logger.debug(f"Intent analysis completed: {primary_intent} (confidence: {confidence:.3f})")
            return intent_analysis
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return {
                'primary_intent': 'question',
                'confidence': 0.3,
                'error': str(e)
            }
    
    async def generate_response(
        self,
        intent: Dict[str, Any],
        context: AssistantContext
    ) -> str:
        """
        Generate response based on intent and context.
        
        Args:
            intent: Analyzed intent information
            context: Assistant context
            
        Returns:
            Generated response text
        """
        try:
            # Prepare voice context for generation
            voice_context = await self._prepare_voice_context(intent, context)
            
            # Use voice pipeline to generate response
            pipeline_result = await self.voice_pipeline.process_request(
                user_prompt=f"Intent: {intent['primary_intent']}\nContext: {context.current_task or 'General assistance'}\nUser needs: {intent.get('response_requirements', {})}\nGenerate an appropriate response in the user's authentic voice.",
                voice_context=voice_context,
                agent_permissions={
                    'ideator': ['personal', 'social', 'published'],
                    'drafter': ['personal', 'social'],
                    'critic': ['personal', 'social', 'published'],
                    'revisor': [],
                    'summarizer': []
                }
            )
            
            # Extract response from pipeline result
            response_content = pipeline_result.get('final_response', '')
            
            # Apply response style adaptation if needed
            if context.response_style != ResponseStyle.ADAPTIVE:
                response_content = await self._adapt_response_style(
                    response_content, context.response_style, context
                )
            
            # Apply final voice consistency check
            response_content = await self._apply_final_voice_consistency(
                response_content, context
            )
            
            logger.debug(f"Response generated successfully: {len(response_content)} characters")
            return response_content
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return f"I apologize, but I encountered an issue generating a response. Please try rephrasing your request."
    
    async def update_context(
        self,
        context: AssistantContext,
        request: AssistantRequest,
        response: AssistantResponse
    ) -> AssistantContext:
        """
        Update context based on interaction.
        
        Args:
            context: Current context
            request: User request
            response: Assistant response
            
        Returns:
            Updated context
        """
        try:
            # Update conversation history
            conversation_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_input': request.user_input,
                'assistant_response': response.content,
                'intent': request.metadata.get('intent_analysis', {}).get('primary_intent'),
                'voice_consistency': response.voice_consistency_score,
                'context_appropriateness': response.context_appropriateness
            }
            
            # Maintain conversation history limit
            context.conversation_history.append(conversation_entry)
            if len(context.conversation_history) > self.assistant_config['max_conversation_history']:
                context.conversation_history = context.conversation_history[-self.assistant_config['max_conversation_history']:]
            
            # Update current task if relevant
            if request.metadata and 'task_update' in request.metadata:
                context.current_task = request.metadata['task_update']
            
            # Update user preferences based on interaction
            if response.voice_consistency_score > 0.9 and response.context_appropriateness > 0.9:
                # High-quality interaction - reinforce preferences
                if 'successful_patterns' not in context.user_preferences:
                    context.user_preferences['successful_patterns'] = []
                
                context.user_preferences['successful_patterns'].append({
                    'mode': context.mode.value,
                    'style': context.response_style.value,
                    'intent': request.metadata.get('intent_analysis', {}).get('primary_intent'),
                    'timestamp': datetime.now().isoformat()
                })
                
                # Keep only recent successful patterns
                context.user_preferences['successful_patterns'] = context.user_preferences['successful_patterns'][-20:]
            
            # Update timestamp
            context.timestamp = datetime.now()
            
            logger.debug(f"Context updated for session: {context.session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Context update failed: {str(e)}")
            return context
    
    # Private helper methods
    
    async def _validate_request_permissions(self, request: AssistantRequest) -> bool:
        """Validate request permissions through governance."""
        try:
            user_id = request.context.user_id if request.context else "unknown"
            
            # Check basic assistant usage permission
            has_permission = await self.governance_manager.check_usage_permission(
                user_id=user_id,
                usage_type='voice_replication',
                agent_type='assistant'
            )
            
            return has_permission
            
        except Exception as e:
            logger.error(f"Permission validation failed: {str(e)}")
            return False
    
    async def _create_default_context(self, request: AssistantRequest) -> AssistantContext:
        """Create default context for request."""
        return AssistantContext(
            user_id=request.metadata.get('user_id', 'default_user'),
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            mode=self.assistant_config['default_mode'],
            response_style=self.assistant_config['default_response_style'],
            conversation_history=[],
            current_task=request.metadata.get('task'),
            user_preferences={},
            platform=request.metadata.get('platform'),
            audience=request.metadata.get('audience')
        )
    
    async def _update_context_with_intent(
        self,
        context: AssistantContext,
        intent_analysis: Dict[str, Any]
    ) -> AssistantContext:
        """Update context with intent analysis results."""
        # Adapt mode based on intent if in adaptive mode
        if context.mode == AssistantMode.ADAPTIVE:
            intent_to_mode = {
                'creative': AssistantMode.CREATIVE,
                'analysis': AssistantMode.ANALYTICAL,
                'task': AssistantMode.PROFESSIONAL,
                'question': AssistantMode.PERSONAL,
                'request': AssistantMode.PERSONAL,
                'command': AssistantMode.PROFESSIONAL,
                'information': AssistantMode.ANALYTICAL
            }
            
            primary_intent = intent_analysis.get('primary_intent', 'question')
            if primary_intent in intent_to_mode:
                context.mode = intent_to_mode[primary_intent]
        
        # Adapt response style based on context and intent
        if context.response_style == ResponseStyle.ADAPTIVE:
            if context.mode == AssistantMode.PROFESSIONAL:
                context.response_style = ResponseStyle.FORMAL
            elif context.mode == AssistantMode.CREATIVE:
                context.response_style = ResponseStyle.CONVERSATIONAL
            elif context.mode == AssistantMode.ANALYTICAL:
                context.response_style = ResponseStyle.DETAILED
            else:
                context.response_style = ResponseStyle.CONVERSATIONAL
        
        return context
    
    async def _validate_voice_consistency(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """Validate voice consistency of response."""
        try:
            # Use voice monitor if available
            if self.assistant_config['monitoring_enabled']:
                # This would integrate with actual voice fingerprint validation
                # For now, return a simulated score based on response characteristics
                return 0.85  # Placeholder
            
            return 0.8  # Default score
            
        except Exception as e:
            logger.error(f"Voice consistency validation failed: {str(e)}")
            return 0.5
    
    async def _validate_context_appropriateness(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """Validate context appropriateness of response."""
        try:
            # Basic appropriateness checks
            appropriateness_score = 0.8  # Base score
            
            # Check response length appropriateness
            response_length = len(response)
            if context.response_style == ResponseStyle.CONCISE and response_length > 500:
                appropriateness_score -= 0.1
            elif context.response_style == ResponseStyle.DETAILED and response_length < 100:
                appropriateness_score -= 0.1
            
            # Check formality appropriateness
            if context.mode == AssistantMode.PROFESSIONAL:
                # Check for professional language indicators
                professional_indicators = ['please', 'thank you', 'regarding', 'furthermore']
                if any(indicator in response.lower() for indicator in professional_indicators):
                    appropriateness_score += 0.1
            
            return min(1.0, max(0.0, appropriateness_score))
            
        except Exception as e:
            logger.error(f"Context appropriateness validation failed: {str(e)}")
            return 0.5
    
    async def _create_error_response(
        self,
        request: AssistantRequest,
        error_message: str
    ) -> AssistantResponse:
        """Create error response."""
        return AssistantResponse(
            response_id=f"error_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            content=f"I apologize, but I encountered an issue: {error_message}",
            response_type='error_response',
            confidence=0.0,
            voice_consistency_score=0.0,
            context_appropriateness=0.0,
            processing_time_ms=0,
            sources_used=[],
            voice_patterns_applied=[],
            metadata={'error': error_message}
        )
    
    async def _extract_basic_entities(self, user_input: str) -> Dict[str, Any]:
        """Extract basic entities from user input."""
        entities = {
            'mentioned_platforms': [],
            'mentioned_people': [],
            'mentioned_tasks': [],
            'time_references': []
        }
        
        # Basic platform detection
        platforms = ['email', 'twitter', 'linkedin', 'facebook', 'instagram', 'slack', 'discord']
        for platform in platforms:
            if platform in user_input.lower():
                entities['mentioned_platforms'].append(platform)
        
        # Basic task detection
        tasks = ['write', 'send', 'create', 'schedule', 'remind', 'post', 'publish']
        for task in tasks:
            if task in user_input.lower():
                entities['mentioned_tasks'].append(task)
        
        return entities
    
    async def _determine_response_requirements(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Optional[AssistantContext]
    ) -> Dict[str, Any]:
        """Determine response requirements based on intent and entities."""
        requirements = {
            'requires_corpus_access': True,  # Most responses benefit from corpus access
            'complexity': 'medium',
            'estimated_length': 'medium',
            'requires_creativity': False,
            'requires_analysis': False,
            'requires_task_automation': False
        }
        
        # Adjust based on intent
        if intent == 'creative':
            requirements['requires_creativity'] = True
            requirements['complexity'] = 'high'
            requirements['estimated_length'] = 'long'
        elif intent == 'analysis':
            requirements['requires_analysis'] = True
            requirements['complexity'] = 'high'
            requirements['estimated_length'] = 'long'
        elif intent == 'task':
            requirements['requires_task_automation'] = True
            requirements['complexity'] = 'high'
        elif intent == 'question':
            requirements['complexity'] = 'low'
            requirements['estimated_length'] = 'short'
        
        # Adjust based on entities
        if entities.get('mentioned_platforms'):
            requirements['requires_task_automation'] = True
            requirements['complexity'] = 'high'
        
        return requirements
    
    async def _determine_voice_patterns_needed(
        self,
        intent: str,
        context: Optional[AssistantContext]
    ) -> List[str]:
        """Determine which voice patterns are needed for the response."""
        patterns_needed = ['personal']  # Always include personal patterns
        
        # Add patterns based on intent
        if intent in ['task', 'command']:
            patterns_needed.append('published')  # Professional patterns
        
        if intent in ['creative', 'question', 'request']:
            patterns_needed.append('social')  # Conversational patterns
        
        # Add patterns based on context mode
        if context and context.mode == AssistantMode.PROFESSIONAL:
            patterns_needed.append('published')
        elif context and context.mode in [AssistantMode.PERSONAL, AssistantMode.CREATIVE]:
            patterns_needed.append('social')
        
        return list(set(patterns_needed))  # Remove duplicates
    
    async def _prepare_voice_context(
        self,
        intent: Dict[str, Any],
        context: AssistantContext
    ) -> Dict[str, Any]:
        """Prepare voice context for generation."""
        return {
            'mode': context.mode.value,
            'response_style': context.response_style.value,
            'audience': context.audience,
            'platform': context.platform,
            'intent': intent['primary_intent'],
            'complexity': intent.get('response_requirements', {}).get('complexity', 'medium'),
            'voice_patterns_needed': intent.get('voice_patterns_needed', ['personal'])
        }
    
    async def _adapt_response_style(
        self,
        response: str,
        target_style: ResponseStyle,
        context: AssistantContext
    ) -> str:
        """Adapt response to target style."""
        # Use voice adapter for style adaptation
        adaptation_context = {
            'target_style': target_style.value,
            'current_mode': context.mode.value,
            'audience': context.audience,
            'platform': context.platform
        }
        
        adapted_response = await self.voice_adapter.adapt_voice(
            text=response,
            context=adaptation_context,
            strategy='context_specific'
        )
        
        return adapted_response.adapted_text
    
    async def _apply_final_voice_consistency(
        self,
        response: str,
        context: AssistantContext
    ) -> str:
        """Apply final voice consistency check and adjustment."""
        # This would integrate with voice consistency validation
        # For now, return the response as-is
        return response
    
    async def _update_conversation_history(
        self,
        session_id: str,
        request: AssistantRequest,
        response: AssistantResponse
    ) -> None:
        """Update conversation history for session."""
        if session_id not in self.active_conversations:
            self.active_conversations[session_id] = {
                'started_at': datetime.now(),
                'last_activity': datetime.now(),
                'message_count': 0,
                'history': []
            }
        
        conversation = self.active_conversations[session_id]
        conversation['last_activity'] = datetime.now()
        conversation['message_count'] += 1
        conversation['history'].append({
            'timestamp': datetime.now().isoformat(),
            'request': {
                'id': request.request_id,
                'input': request.user_input,
                'intent': request.intent
            },
            'response': {
                'id': response.response_id,
                'content': response.content,
                'type': response.response_type,
                'voice_consistency': response.voice_consistency_score,
                'context_appropriateness': response.context_appropriateness
            }
        })
        
        # Limit history size
        if len(conversation['history']) > self.assistant_config['max_conversation_history']:
            conversation['history'] = conversation['history'][-self.assistant_config['max_conversation_history']:]
    
    async def _apply_learning_from_interaction(
        self,
        request: AssistantRequest,
        response: AssistantResponse,
        context: AssistantContext
    ) -> None:
        """Apply learning from successful interaction."""
        try:
            if response.voice_consistency_score > self.assistant_config['voice_consistency_threshold']:
                # Create learning data from successful interaction
                learning_data = {
                    'user_input': request.user_input,
                    'response': response.content,
                    'context': {
                        'mode': context.mode.value,
                        'style': context.response_style.value,
                        'intent': request.intent
                    },
                    'quality_scores': {
                        'voice_consistency': response.voice_consistency_score,
                        'context_appropriateness': response.context_appropriateness
                    }
                }
                
                # Apply learning
                await self.voice_learning.learn_from_usage(
                    usage_data=learning_data,
                    learning_mode='passive'
                )
                
                self.assistant_stats['learning_sessions'] += 1
                
        except Exception as e:
            logger.error(f"Learning application failed: {str(e)}")
    
    async def _update_assistant_statistics(
        self,
        request: AssistantRequest,
        response: AssistantResponse,
        context: AssistantContext
    ) -> None:
        """Update assistant usage statistics."""
        self.assistant_stats['total_requests'] += 1
        
        if response.voice_consistency_score > 0.5:  # Consider successful if above threshold
            self.assistant_stats['successful_responses'] += 1
        
        # Update averages
        total_responses = self.assistant_stats['successful_responses']
        if total_responses > 0:
            # Running average calculation
            current_voice_avg = self.assistant_stats['voice_consistency_average']
            self.assistant_stats['voice_consistency_average'] = (
                (current_voice_avg * (total_responses - 1) + response.voice_consistency_score) / total_responses
            )
            
            current_context_avg = self.assistant_stats['context_appropriateness_average']
            self.assistant_stats['context_appropriateness_average'] = (
                (current_context_avg * (total_responses - 1) + response.context_appropriateness) / total_responses
            )
            
            current_time_avg = self.assistant_stats['average_response_time_ms']
            self.assistant_stats['average_response_time_ms'] = (
                (current_time_avg * (total_responses - 1) + response.processing_time_ms) / total_responses
            )
        
        # Update mode and style usage
        self.assistant_stats['mode_usage'][context.mode.value] += 1
        self.assistant_stats['style_usage'][context.response_style.value] += 1
    
    def get_assistant_statistics(self) -> Dict[str, Any]:
        """Get assistant usage statistics."""
        return {
            'statistics': self.assistant_stats.copy(),
            'configuration': self.assistant_config.copy(),
            'active_conversations': len(self.active_conversations),
            'total_conversation_messages': sum(
                conv['message_count'] for conv in self.active_conversations.values()
            )
        }
