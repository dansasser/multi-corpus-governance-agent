"""Advanced conversation management system for multi-turn conversations with voice consistency."""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from .protocols import (
    ConversationManagementProtocol,
    AssistantContext,
    AssistantRequest,
    AssistantResponse
)
from ..voice_features.adapters import DynamicVoiceAdapter
from ..voice_features.monitoring import VoiceConsistencyMonitor
from ..mvlm import PersonalVoiceMVLMManager
from ..governance import PersonalDataGovernanceManager
from ..security import PersonalVoiceAuditTrail

logger = logging.getLogger(__name__)


class ConversationStatus(Enum):
    """Conversation status."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"


class ConversationMode(Enum):
    """Conversation interaction modes."""
    CASUAL = "casual"              # Informal, friendly conversation
    PROFESSIONAL = "professional"  # Business or work-related discussion
    CREATIVE = "creative"          # Creative collaboration and brainstorming
    ANALYTICAL = "analytical"      # Data analysis and problem-solving
    SUPPORTIVE = "supportive"      # Emotional support and guidance
    EDUCATIONAL = "educational"    # Learning and teaching interactions


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    turn_id: str
    conversation_id: str
    user_message: str
    assistant_response: str
    timestamp: datetime
    voice_consistency_score: float
    context_relevance_score: float
    user_satisfaction: Optional[float]
    response_time_ms: int
    voice_patterns_used: List[str]
    corpus_accessed: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSession:
    """Represents a complete conversation session."""
    session_id: str
    user_id: str
    status: ConversationStatus
    mode: ConversationMode
    platform: str
    started_at: datetime
    last_activity: datetime
    ended_at: Optional[datetime]
    turns: List[ConversationTurn]
    context_summary: str
    voice_consistency_average: float
    total_turns: int
    session_quality_score: float
    persistent_context: Dict[str, Any]
    conversation_goals: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationManager(ConversationManagementProtocol):
    """
    Advanced conversation management system that maintains
    multi-turn conversations with voice consistency and context awareness.
    
    This system specializes in:
    - Multi-turn conversation state management
    - Voice consistency across conversation turns
    - Context preservation and evolution
    - Conversation quality monitoring
    - Session analytics and insights
    """
    
    def __init__(
        self,
        voice_adapter: DynamicVoiceAdapter,
        voice_monitor: VoiceConsistencyMonitor,
        mvlm_manager: PersonalVoiceMVLMManager,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail
    ):
        """
        Initialize conversation manager.
        
        Args:
            voice_adapter: Voice adaptation system
            voice_monitor: Voice consistency monitoring
            mvlm_manager: MVLM management for text generation
            governance_manager: Personal data governance
            audit_trail: Voice usage audit trail
        """
        self.voice_adapter = voice_adapter
        self.voice_monitor = voice_monitor
        self.mvlm_manager = mvlm_manager
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        
        # Conversation management configuration
        self.conversation_config = {
            'max_active_sessions': 10,
            'session_timeout_hours': 24,
            'context_memory_turns': 20,
            'voice_consistency_threshold': 0.8,
            'context_relevance_threshold': 0.7,
            'auto_archive_days': 30,
            'quality_score_threshold': 0.75,
            'max_turn_length': 5000,
            'context_summary_frequency': 10  # Summarize context every N turns
        }
        
        # Active conversation sessions
        self.active_sessions: Dict[str, ConversationSession] = {}
        
        # Conversation mode configurations
        self.mode_configs = {
            ConversationMode.CASUAL: {
                'voice_style': 'friendly_casual',
                'formality_level': 0.3,
                'response_length': 'medium',
                'engagement_level': 'high',
                'personal_touch': True
            },
            ConversationMode.PROFESSIONAL: {
                'voice_style': 'professional_warm',
                'formality_level': 0.7,
                'response_length': 'detailed',
                'engagement_level': 'moderate',
                'personal_touch': False
            },
            ConversationMode.CREATIVE: {
                'voice_style': 'enthusiastic_creative',
                'formality_level': 0.4,
                'response_length': 'varied',
                'engagement_level': 'very_high',
                'personal_touch': True
            },
            ConversationMode.ANALYTICAL: {
                'voice_style': 'analytical_precise',
                'formality_level': 0.6,
                'response_length': 'detailed',
                'engagement_level': 'moderate',
                'personal_touch': False
            },
            ConversationMode.SUPPORTIVE: {
                'voice_style': 'warm_empathetic',
                'formality_level': 0.4,
                'response_length': 'thoughtful',
                'engagement_level': 'high',
                'personal_touch': True
            },
            ConversationMode.EDUCATIONAL: {
                'voice_style': 'clear_instructional',
                'formality_level': 0.5,
                'response_length': 'comprehensive',
                'engagement_level': 'moderate',
                'personal_touch': False
            }
        }
        
        # Conversation analytics
        self.conversation_analytics = {
            'total_sessions': 0,
            'active_sessions': 0,
            'completed_sessions': 0,
            'average_session_length': 0.0,
            'average_voice_consistency': 0.0,
            'average_quality_score': 0.0,
            'mode_distribution': {},
            'platform_distribution': {},
            'turn_statistics': {
                'total_turns': 0,
                'average_response_time': 0.0,
                'average_turn_length': 0.0
            }
        }
    
    async def start_conversation(
        self,
        context: AssistantContext,
        initial_message: Optional[str] = None,
        conversation_mode: Optional[ConversationMode] = None
    ) -> str:
        """
        Start a new conversation session.
        
        Args:
            context: Assistant context for the conversation
            initial_message: Optional initial message
            conversation_mode: Conversation mode (auto-detected if not provided)
            
        Returns:
            Conversation session ID
        """
        try:
            # Check session limits
            if len(self.active_sessions) >= self.conversation_config['max_active_sessions']:
                await self._cleanup_inactive_sessions()
                
                if len(self.active_sessions) >= self.conversation_config['max_active_sessions']:
                    raise ValueError("Maximum active conversation sessions reached")
            
            # Detect conversation mode if not provided
            if conversation_mode is None and initial_message:
                conversation_mode = await self._detect_conversation_mode(initial_message, context)
            elif conversation_mode is None:
                conversation_mode = ConversationMode.CASUAL
            
            # Create new conversation session
            session = ConversationSession(
                session_id=f"conv_{uuid.uuid4().hex[:12]}",
                user_id=context.user_id,
                status=ConversationStatus.ACTIVE,
                mode=conversation_mode,
                platform=context.platform or 'unknown',
                started_at=datetime.now(),
                last_activity=datetime.now(),
                ended_at=None,
                turns=[],
                context_summary="",
                voice_consistency_average=0.0,
                total_turns=0,
                session_quality_score=0.0,
                persistent_context={
                    'user_preferences': context.user_preferences or {},
                    'conversation_goals': [],
                    'established_facts': {},
                    'ongoing_topics': [],
                    'voice_baseline': None
                },
                conversation_goals=[],
                metadata={
                    'initial_message': initial_message,
                    'detected_mode': conversation_mode.value,
                    'platform': context.platform,
                    'user_agent': context.metadata.get('user_agent') if context.metadata else None
                }
            )
            
            # Store active session
            self.active_sessions[session.session_id] = session
            
            # Initialize voice baseline for the session
            if initial_message:
                voice_baseline = await self._establish_voice_baseline(
                    initial_message, context, conversation_mode
                )
                session.persistent_context['voice_baseline'] = voice_baseline
            
            # Log conversation start
            await self.audit_trail.log_voice_usage(
                user_id=context.user_id,
                operation_type='conversation_start',
                voice_patterns_used=[],
                success=True,
                metadata={
                    'session_id': session.session_id,
                    'mode': conversation_mode.value,
                    'platform': context.platform
                }
            )
            
            # Update analytics
            self.conversation_analytics['total_sessions'] += 1
            self.conversation_analytics['active_sessions'] += 1
            
            mode_key = conversation_mode.value
            if mode_key not in self.conversation_analytics['mode_distribution']:
                self.conversation_analytics['mode_distribution'][mode_key] = 0
            self.conversation_analytics['mode_distribution'][mode_key] += 1
            
            logger.info(f"Started conversation session: {session.session_id}")
            return session.session_id
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {str(e)}")
            raise
    
    async def continue_conversation(
        self,
        session_id: str,
        user_message: str,
        context: AssistantContext
    ) -> AssistantResponse:
        """
        Continue an existing conversation with a new message.
        
        Args:
            session_id: Conversation session ID
            user_message: User's message
            context: Updated assistant context
            
        Returns:
            Assistant response
        """
        try:
            # Get conversation session
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Conversation session not found: {session_id}")
            
            if session.status != ConversationStatus.ACTIVE:
                raise ValueError(f"Conversation session is not active: {session.status.value}")
            
            # Update session activity
            session.last_activity = datetime.now()
            
            # Validate message length
            if len(user_message) > self.conversation_config['max_turn_length']:
                user_message = user_message[:self.conversation_config['max_turn_length']] + "..."
            
            # Build conversation context
            conversation_context = await self._build_conversation_context(
                session, user_message, context
            )
            
            # Generate response with voice consistency
            start_time = datetime.now()
            response = await self._generate_contextual_response(
                session, user_message, conversation_context
            )
            end_time = datetime.now()
            
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Validate voice consistency
            voice_consistency = await self._validate_conversation_voice_consistency(
                response, session, conversation_context
            )
            
            # Calculate context relevance
            context_relevance = await self._calculate_context_relevance(
                user_message, response, session
            )
            
            # Create conversation turn
            turn = ConversationTurn(
                turn_id=f"turn_{uuid.uuid4().hex[:8]}",
                conversation_id=session.session_id,
                user_message=user_message,
                assistant_response=response,
                timestamp=datetime.now(),
                voice_consistency_score=voice_consistency,
                context_relevance_score=context_relevance,
                user_satisfaction=None,  # To be updated later if feedback provided
                response_time_ms=response_time_ms,
                voice_patterns_used=conversation_context.get('voice_patterns_used', []),
                corpus_accessed=conversation_context.get('corpus_accessed', []),
                metadata={
                    'mode': session.mode.value,
                    'turn_number': len(session.turns) + 1,
                    'context_length': len(session.turns)
                }
            )
            
            # Add turn to session
            session.turns.append(turn)
            session.total_turns += 1
            
            # Update session voice consistency average
            total_consistency = sum(t.voice_consistency_score for t in session.turns)
            session.voice_consistency_average = total_consistency / len(session.turns)
            
            # Update persistent context
            await self._update_persistent_context(session, user_message, response)
            
            # Summarize context if needed
            if len(session.turns) % self.conversation_config['context_summary_frequency'] == 0:
                session.context_summary = await self._summarize_conversation_context(session)
            
            # Calculate session quality score
            session.session_quality_score = await self._calculate_session_quality(session)
            
            # Log conversation turn
            await self.audit_trail.log_voice_usage(
                user_id=context.user_id,
                operation_type='conversation_turn',
                voice_patterns_used=turn.voice_patterns_used,
                success=True,
                metadata={
                    'session_id': session.session_id,
                    'turn_id': turn.turn_id,
                    'voice_consistency': voice_consistency,
                    'context_relevance': context_relevance,
                    'response_time_ms': response_time_ms
                }
            )
            
            # Update analytics
            self._update_turn_analytics(turn)
            
            # Create assistant response
            assistant_response = AssistantResponse(
                response_id=turn.turn_id,
                request_id=context.request_id or turn.turn_id,
                content=response,
                confidence=voice_consistency,
                voice_consistency_score=voice_consistency,
                context_appropriateness_score=context_relevance,
                processing_time_ms=response_time_ms,
                voice_patterns_used=turn.voice_patterns_used,
                corpus_accessed=turn.corpus_accessed,
                metadata={
                    'session_id': session.session_id,
                    'turn_number': session.total_turns,
                    'conversation_mode': session.mode.value,
                    'session_quality': session.session_quality_score,
                    'voice_consistency_average': session.voice_consistency_average
                }
            )
            
            logger.info(f"Conversation turn completed: {session.session_id}/{turn.turn_id}")
            return assistant_response
            
        except Exception as e:
            logger.error(f"Failed to continue conversation: {str(e)}")
            
            # Log failed turn
            await self.audit_trail.log_voice_usage(
                user_id=context.user_id,
                operation_type='conversation_turn',
                voice_patterns_used=[],
                success=False,
                metadata={
                    'session_id': session_id,
                    'error': str(e)
                }
            )
            
            raise
    
    async def end_conversation(
        self,
        session_id: str,
        context: AssistantContext,
        reason: str = "user_ended"
    ) -> Dict[str, Any]:
        """
        End a conversation session.
        
        Args:
            session_id: Conversation session ID
            context: Assistant context
            reason: Reason for ending conversation
            
        Returns:
            Conversation summary
        """
        try:
            # Get conversation session
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Conversation session not found: {session_id}")
            
            # Update session status
            session.status = ConversationStatus.ENDED
            session.ended_at = datetime.now()
            
            # Calculate final session metrics
            session_duration = (session.ended_at - session.started_at).total_seconds()
            session.session_quality_score = await self._calculate_session_quality(session)
            
            # Create conversation summary
            conversation_summary = {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'mode': session.mode.value,
                'platform': session.platform,
                'duration_seconds': session_duration,
                'total_turns': session.total_turns,
                'voice_consistency_average': session.voice_consistency_average,
                'session_quality_score': session.session_quality_score,
                'context_summary': session.context_summary,
                'conversation_goals': session.conversation_goals,
                'key_topics': session.persistent_context.get('ongoing_topics', []),
                'established_facts': session.persistent_context.get('established_facts', {}),
                'ended_reason': reason,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat()
            }
            
            # Log conversation end
            await self.audit_trail.log_voice_usage(
                user_id=context.user_id,
                operation_type='conversation_end',
                voice_patterns_used=[],
                success=True,
                metadata={
                    'session_id': session.session_id,
                    'duration_seconds': session_duration,
                    'total_turns': session.total_turns,
                    'quality_score': session.session_quality_score,
                    'reason': reason
                }
            )
            
            # Update analytics
            self.conversation_analytics['active_sessions'] -= 1
            self.conversation_analytics['completed_sessions'] += 1
            
            # Update average session length
            completed_count = self.conversation_analytics['completed_sessions']
            current_avg = self.conversation_analytics['average_session_length']
            self.conversation_analytics['average_session_length'] = (
                (current_avg * (completed_count - 1) + session_duration) / completed_count
            )
            
            # Update average voice consistency
            current_voice_avg = self.conversation_analytics['average_voice_consistency']
            self.conversation_analytics['average_voice_consistency'] = (
                (current_voice_avg * (completed_count - 1) + session.voice_consistency_average) / completed_count
            )
            
            # Update average quality score
            current_quality_avg = self.conversation_analytics['average_quality_score']
            self.conversation_analytics['average_quality_score'] = (
                (current_quality_avg * (completed_count - 1) + session.session_quality_score) / completed_count
            )
            
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            logger.info(f"Ended conversation session: {session_id}")
            return conversation_summary
            
        except Exception as e:
            logger.error(f"Failed to end conversation: {str(e)}")
            raise
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Conversation session ID
            limit: Maximum number of turns to return
            
        Returns:
            List of conversation turns
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Conversation session not found: {session_id}")
            
            turns = session.turns
            if limit:
                turns = turns[-limit:]  # Get most recent turns
            
            history = []
            for turn in turns:
                history.append({
                    'turn_id': turn.turn_id,
                    'timestamp': turn.timestamp.isoformat(),
                    'user_message': turn.user_message,
                    'assistant_response': turn.assistant_response,
                    'voice_consistency_score': turn.voice_consistency_score,
                    'context_relevance_score': turn.context_relevance_score,
                    'response_time_ms': turn.response_time_ms,
                    'voice_patterns_used': turn.voice_patterns_used,
                    'corpus_accessed': turn.corpus_accessed
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            raise
    
    # Private helper methods
    
    async def _detect_conversation_mode(
        self,
        message: str,
        context: AssistantContext
    ) -> ConversationMode:
        """Detect conversation mode from initial message."""
        message_lower = message.lower()
        
        # Mode detection patterns
        if any(word in message_lower for word in ['help', 'support', 'problem', 'issue', 'struggling']):
            return ConversationMode.SUPPORTIVE
        elif any(word in message_lower for word in ['analyze', 'data', 'research', 'study', 'investigate']):
            return ConversationMode.ANALYTICAL
        elif any(word in message_lower for word in ['create', 'brainstorm', 'idea', 'design', 'imagine']):
            return ConversationMode.CREATIVE
        elif any(word in message_lower for word in ['learn', 'teach', 'explain', 'understand', 'how to']):
            return ConversationMode.EDUCATIONAL
        elif any(word in message_lower for word in ['business', 'work', 'project', 'meeting', 'professional']):
            return ConversationMode.PROFESSIONAL
        else:
            return ConversationMode.CASUAL
    
    async def _establish_voice_baseline(
        self,
        initial_message: str,
        context: AssistantContext,
        mode: ConversationMode
    ) -> Dict[str, Any]:
        """Establish voice baseline for the conversation."""
        try:
            # Use voice adapter to analyze initial message tone
            voice_analysis = await self.voice_adapter.adapt_voice(
                text=initial_message,
                context={
                    'analysis_mode': True,
                    'conversation_mode': mode.value,
                    'platform': context.platform
                },
                strategy='preserve_original'
            )
            
            mode_config = self.mode_configs[mode]
            
            return {
                'detected_formality': voice_analysis.confidence,
                'mode_formality': mode_config['formality_level'],
                'voice_style': mode_config['voice_style'],
                'engagement_level': mode_config['engagement_level'],
                'personal_touch': mode_config['personal_touch'],
                'response_length_preference': mode_config['response_length']
            }
            
        except Exception as e:
            logger.error(f"Failed to establish voice baseline: {str(e)}")
            return self.mode_configs[mode]
    
    async def _build_conversation_context(
        self,
        session: ConversationSession,
        user_message: str,
        context: AssistantContext
    ) -> Dict[str, Any]:
        """Build comprehensive conversation context."""
        # Get recent conversation history
        recent_turns = session.turns[-self.conversation_config['context_memory_turns']:]
        
        # Build conversation history text
        history_text = ""
        for turn in recent_turns:
            history_text += f"User: {turn.user_message}\n"
            history_text += f"Assistant: {turn.assistant_response}\n\n"
        
        # Get mode configuration
        mode_config = self.mode_configs[session.mode]
        
        # Build context
        conversation_context = {
            'session_id': session.session_id,
            'conversation_mode': session.mode.value,
            'platform': session.platform,
            'conversation_history': history_text,
            'context_summary': session.context_summary,
            'persistent_context': session.persistent_context,
            'voice_baseline': session.persistent_context.get('voice_baseline', {}),
            'mode_config': mode_config,
            'turn_number': len(session.turns) + 1,
            'session_quality': session.session_quality_score,
            'voice_consistency_average': session.voice_consistency_average,
            'user_preferences': context.user_preferences or {},
            'current_message': user_message
        }
        
        return conversation_context
    
    async def _generate_contextual_response(
        self,
        session: ConversationSession,
        user_message: str,
        conversation_context: Dict[str, Any]
    ) -> str:
        """Generate contextually appropriate response."""
        try:
            # Create response prompt with conversation context
            mode_config = conversation_context['mode_config']
            
            response_prompt = f"""
            Continue this conversation in the user's authentic voice.
            
            Conversation Mode: {session.mode.value}
            Voice Style: {mode_config['voice_style']}
            Formality Level: {mode_config['formality_level']}
            Response Length: {mode_config['response_length']}
            Personal Touch: {mode_config['personal_touch']}
            
            Recent Conversation:
            {conversation_context['conversation_history'][-1000:]}  # Last 1000 chars
            
            Current Message: {user_message}
            
            Context Summary: {conversation_context['context_summary']}
            
            Generate a response that:
            1. Maintains voice consistency with previous responses
            2. Addresses the user's current message appropriately
            3. Considers the conversation context and history
            4. Matches the conversation mode and style
            5. Feels natural and authentic to the user's voice
            """
            
            # Use voice adapter for contextual voice adaptation
            voice_context = {
                'conversation_mode': session.mode.value,
                'platform': session.platform,
                'formality_level': mode_config['formality_level'],
                'voice_style': mode_config['voice_style'],
                'conversation_context': True,
                'turn_number': conversation_context['turn_number']
            }
            
            adapted_voice = await self.voice_adapter.adapt_voice(
                text=response_prompt,
                context=voice_context,
                strategy='context_specific'
            )
            
            # Generate response using MVLM
            response = await self.mvlm_manager.generate_text(
                prompt=adapted_voice.adapted_text,
                voice_context=voice_context,
                max_length=self._get_response_length_limit(mode_config['response_length'])
            )
            
            # Store voice patterns used
            conversation_context['voice_patterns_used'] = ['personal', 'conversational']
            conversation_context['corpus_accessed'] = ['personal']
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate contextual response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Could you please try again?"
    
    def _get_response_length_limit(self, response_length: str) -> int:
        """Get character limit based on response length preference."""
        length_limits = {
            'short': 500,
            'medium': 1000,
            'detailed': 2000,
            'comprehensive': 3000,
            'varied': 1500,
            'thoughtful': 1200
        }
        return length_limits.get(response_length, 1000)
    
    async def _validate_conversation_voice_consistency(
        self,
        response: str,
        session: ConversationSession,
        conversation_context: Dict[str, Any]
    ) -> float:
        """Validate voice consistency within conversation context."""
        try:
            # Use voice monitor for consistency checking
            consistency_result = await self.voice_monitor.check_consistency(
                text=response,
                context={
                    'conversation_mode': session.mode.value,
                    'voice_baseline': conversation_context['voice_baseline'],
                    'session_average': session.voice_consistency_average,
                    'platform': session.platform
                }
            )
            
            return consistency_result.overall_consistency
            
        except Exception as e:
            logger.error(f"Voice consistency validation failed: {str(e)}")
            return 0.7  # Default moderate consistency
    
    async def _calculate_context_relevance(
        self,
        user_message: str,
        response: str,
        session: ConversationSession
    ) -> float:
        """Calculate how relevant the response is to the conversation context."""
        try:
            # Simple relevance calculation based on keyword overlap and length appropriateness
            user_words = set(user_message.lower().split())
            response_words = set(response.lower().split())
            
            # Calculate word overlap
            overlap = len(user_words.intersection(response_words))
            total_unique = len(user_words.union(response_words))
            word_relevance = overlap / total_unique if total_unique > 0 else 0.0
            
            # Calculate length appropriateness
            user_length = len(user_message)
            response_length = len(response)
            
            if user_length < 50:  # Short message
                ideal_response_length = 100
            elif user_length < 200:  # Medium message
                ideal_response_length = 300
            else:  # Long message
                ideal_response_length = 500
            
            length_diff = abs(response_length - ideal_response_length)
            length_relevance = max(0.0, 1.0 - (length_diff / ideal_response_length))
            
            # Combine relevance factors
            context_relevance = (word_relevance * 0.4) + (length_relevance * 0.6)
            
            return min(1.0, max(0.0, context_relevance))
            
        except Exception as e:
            logger.error(f"Context relevance calculation failed: {str(e)}")
            return 0.7  # Default moderate relevance
    
    async def _update_persistent_context(
        self,
        session: ConversationSession,
        user_message: str,
        response: str
    ) -> None:
        """Update persistent conversation context."""
        try:
            # Extract topics from current exchange
            current_topics = await self._extract_topics(user_message + " " + response)
            
            # Update ongoing topics
            ongoing_topics = session.persistent_context.get('ongoing_topics', [])
            for topic in current_topics:
                if topic not in ongoing_topics:
                    ongoing_topics.append(topic)
            
            # Keep only recent topics (last 10)
            session.persistent_context['ongoing_topics'] = ongoing_topics[-10:]
            
            # Extract and store facts mentioned
            facts = await self._extract_facts(user_message, response)
            established_facts = session.persistent_context.get('established_facts', {})
            established_facts.update(facts)
            session.persistent_context['established_facts'] = established_facts
            
            # Update conversation goals if mentioned
            goals = await self._extract_goals(user_message)
            if goals:
                session.conversation_goals.extend(goals)
                session.conversation_goals = list(set(session.conversation_goals))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Failed to update persistent context: {str(e)}")
    
    async def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        # Simple topic extraction based on nouns and key phrases
        words = text.lower().split()
        
        # Common topic indicators
        topic_words = []
        skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        for word in words:
            if len(word) > 3 and word not in skip_words:
                topic_words.append(word)
        
        # Return unique topics (limit to 5 most relevant)
        return list(set(topic_words))[:5]
    
    async def _extract_facts(self, user_message: str, response: str) -> Dict[str, str]:
        """Extract factual information from conversation."""
        facts = {}
        
        # Look for factual statements in user message
        if "my name is" in user_message.lower():
            name_start = user_message.lower().find("my name is") + 11
            name_end = user_message.find(" ", name_start)
            if name_end == -1:
                name_end = len(user_message)
            name = user_message[name_start:name_end].strip()
            if name:
                facts['user_name'] = name
        
        # Look for preferences
        if "i like" in user_message.lower():
            preference_start = user_message.lower().find("i like") + 7
            preference = user_message[preference_start:].split('.')[0].strip()
            if preference:
                facts['preference'] = preference
        
        return facts
    
    async def _extract_goals(self, user_message: str) -> List[str]:
        """Extract conversation goals from user message."""
        goals = []
        
        goal_indicators = [
            "i want to", "i need to", "help me", "can you help",
            "i'm trying to", "my goal is", "i hope to"
        ]
        
        message_lower = user_message.lower()
        for indicator in goal_indicators:
            if indicator in message_lower:
                goal_start = message_lower.find(indicator) + len(indicator)
                goal = user_message[goal_start:].split('.')[0].strip()
                if goal and len(goal) > 5:
                    goals.append(goal)
        
        return goals
    
    async def _summarize_conversation_context(self, session: ConversationSession) -> str:
        """Summarize conversation context for memory efficiency."""
        try:
            # Get key information from recent turns
            recent_turns = session.turns[-5:]  # Last 5 turns
            
            # Build summary
            summary_parts = []
            
            # Add ongoing topics
            if session.persistent_context.get('ongoing_topics'):
                topics = ", ".join(session.persistent_context['ongoing_topics'][:5])
                summary_parts.append(f"Topics discussed: {topics}")
            
            # Add established facts
            if session.persistent_context.get('established_facts'):
                facts = []
                for key, value in session.persistent_context['established_facts'].items():
                    facts.append(f"{key}: {value}")
                if facts:
                    summary_parts.append(f"Established facts: {'; '.join(facts[:3])}")
            
            # Add conversation goals
            if session.conversation_goals:
                goals = "; ".join(session.conversation_goals[:3])
                summary_parts.append(f"Goals: {goals}")
            
            # Add conversation mode and quality
            summary_parts.append(f"Mode: {session.mode.value}")
            summary_parts.append(f"Quality: {session.session_quality_score:.2f}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation context: {str(e)}")
            return f"Conversation in {session.mode.value} mode with {len(session.turns)} turns"
    
    async def _calculate_session_quality(self, session: ConversationSession) -> float:
        """Calculate overall session quality score."""
        if not session.turns:
            return 0.0
        
        # Calculate component scores
        voice_consistency = session.voice_consistency_average
        
        context_relevance = sum(turn.context_relevance_score for turn in session.turns) / len(session.turns)
        
        # Response time quality (faster is better, but not too fast)
        avg_response_time = sum(turn.response_time_ms for turn in session.turns) / len(session.turns)
        response_time_quality = max(0.0, min(1.0, 1.0 - (avg_response_time - 2000) / 10000))  # Optimal around 2 seconds
        
        # Turn engagement (more turns indicate better engagement)
        engagement_score = min(1.0, len(session.turns) / 10.0)  # Max score at 10+ turns
        
        # Combine scores with weights
        quality_score = (
            voice_consistency * 0.4 +
            context_relevance * 0.3 +
            response_time_quality * 0.2 +
            engagement_score * 0.1
        )
        
        return quality_score
    
    def _update_turn_analytics(self, turn: ConversationTurn) -> None:
        """Update turn-level analytics."""
        self.conversation_analytics['turn_statistics']['total_turns'] += 1
        
        # Update average response time
        total_turns = self.conversation_analytics['turn_statistics']['total_turns']
        current_avg_time = self.conversation_analytics['turn_statistics']['average_response_time']
        self.conversation_analytics['turn_statistics']['average_response_time'] = (
            (current_avg_time * (total_turns - 1) + turn.response_time_ms) / total_turns
        )
        
        # Update average turn length
        turn_length = len(turn.assistant_response)
        current_avg_length = self.conversation_analytics['turn_statistics']['average_turn_length']
        self.conversation_analytics['turn_statistics']['average_turn_length'] = (
            (current_avg_length * (total_turns - 1) + turn_length) / total_turns
        )
    
    async def _cleanup_inactive_sessions(self) -> None:
        """Clean up inactive conversation sessions."""
        timeout_hours = self.conversation_config['session_timeout_hours']
        timeout_threshold = datetime.now() - timedelta(hours=timeout_hours)
        
        inactive_sessions = []
        for session_id, session in self.active_sessions.items():
            if session.last_activity < timeout_threshold:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            session = self.active_sessions[session_id]
            session.status = ConversationStatus.ENDED
            session.ended_at = datetime.now()
            
            # Update analytics
            self.conversation_analytics['active_sessions'] -= 1
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Cleaned up inactive session: {session_id}")
    
    def get_conversation_analytics(self) -> Dict[str, Any]:
        """Get conversation analytics and statistics."""
        return {
            'analytics': self.conversation_analytics.copy(),
            'active_sessions_count': len(self.active_sessions),
            'configuration': self.conversation_config.copy(),
            'mode_configurations': {mode.value: config for mode, config in self.mode_configs.items()},
            'session_details': {
                session_id: {
                    'mode': session.mode.value,
                    'platform': session.platform,
                    'turns': len(session.turns),
                    'quality': session.session_quality_score,
                    'voice_consistency': session.voice_consistency_average,
                    'duration_minutes': (datetime.now() - session.started_at).total_seconds() / 60
                }
                for session_id, session in self.active_sessions.items()
            }
        }
