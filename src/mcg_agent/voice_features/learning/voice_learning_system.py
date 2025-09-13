"""Voice learning system for continuous voice improvement and evolution."""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..protocols.voice_learning_protocol import (
    VoiceLearningProtocol,
    VoiceFeedback,
    VoiceEvolutionRecord,
    LearningSession,
    LearningMode,
    FeedbackType
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint, VoiceFingerprintExtractor
from ...governance.personal_data_governance import PersonalDataGovernanceManager
from ...security.personal_voice_audit_trail import PersonalVoiceAuditTrail

logger = logging.getLogger(__name__)


class VoiceLearningSystem(VoiceLearningProtocol):
    """
    Voice learning system that continuously improves voice patterns
    based on usage data, feedback, and performance metrics.
    
    This system implements:
    - Passive learning from usage patterns
    - Active learning from explicit feedback
    - Reinforcement learning from success/failure patterns
    - Adaptive learning that adjusts based on context
    """
    
    def __init__(
        self,
        fingerprint_extractor: VoiceFingerprintExtractor,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail,
        feedback_processor: Optional['FeedbackProcessor'] = None,
        evolution_tracker: Optional['EvolutionTracker'] = None
    ):
        """
        Initialize voice learning system.
        
        Args:
            fingerprint_extractor: Voice fingerprint extractor
            governance_manager: Personal data governance manager
            audit_trail: Voice audit trail system
            feedback_processor: Optional feedback processor
            evolution_tracker: Optional evolution tracker
        """
        self.fingerprint_extractor = fingerprint_extractor
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        self.feedback_processor = feedback_processor
        self.evolution_tracker = evolution_tracker
        
        # Learning configuration
        self.learning_config = {
            'passive_learning_threshold': 10,  # Minimum usage samples for passive learning
            'feedback_weight': 0.7,           # Weight for explicit feedback
            'usage_weight': 0.3,              # Weight for usage patterns
            'evolution_threshold': 0.1,       # Minimum change for evolution record
            'max_learning_rate': 0.2,         # Maximum change per learning cycle
            'confidence_threshold': 0.8       # Minimum confidence for pattern updates
        }
        
        # Active learning sessions
        self.active_sessions: Dict[str, LearningSession] = {}
        
        # Learning metrics
        self.learning_metrics = {
            'sessions_completed': 0,
            'patterns_learned': 0,
            'improvements_made': 0,
            'feedback_processed': 0,
            'evolution_records': 0
        }
        
        # Pattern learning cache
        self.pattern_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=1)
    
    async def learn_from_usage(
        self,
        voice_fingerprint: VoiceFingerprint,
        usage_data: List[Dict[str, Any]],
        learning_mode: LearningMode = LearningMode.PASSIVE
    ) -> VoiceFingerprint:
        """
        Learn and update voice patterns from usage data.
        
        Args:
            voice_fingerprint: Current voice fingerprint
            usage_data: Usage data to learn from
            learning_mode: Learning mode to use
            
        Returns:
            Updated voice fingerprint
        """
        try:
            # Validate learning permissions
            await self._validate_learning_permissions(voice_fingerprint.user_id)
            
            # Filter and validate usage data
            valid_usage_data = await self._validate_usage_data(usage_data)
            
            if len(valid_usage_data) < self.learning_config['passive_learning_threshold']:
                logger.debug(f"Insufficient usage data for learning: {len(valid_usage_data)} samples")
                return voice_fingerprint
            
            # Extract patterns from usage data
            learned_patterns = await self._extract_patterns_from_usage(
                valid_usage_data, learning_mode
            )
            
            if not learned_patterns:
                logger.debug("No new patterns learned from usage data")
                return voice_fingerprint
            
            # Create updated fingerprint
            updated_fingerprint = await self._apply_learned_patterns(
                voice_fingerprint, learned_patterns, learning_mode
            )
            
            # Track evolution if significant changes
            if await self._is_significant_evolution(voice_fingerprint, updated_fingerprint):
                evolution_record = await self._create_evolution_record(
                    voice_fingerprint, updated_fingerprint, f"usage_learning_{learning_mode.value}"
                )
                
                if self.evolution_tracker:
                    await self.evolution_tracker.track_evolution(
                        voice_fingerprint, updated_fingerprint, f"usage_learning_{learning_mode.value}"
                    )
            
            # Update metrics
            self.learning_metrics['patterns_learned'] += len(learned_patterns)
            self.learning_metrics['improvements_made'] += 1
            
            # Log learning activity
            await self.audit_trail.log_voice_pattern_access(
                user_id=voice_fingerprint.user_id,
                access_type="voice_learning",
                patterns_accessed=list(learned_patterns.keys()),
                context={
                    'learning_mode': learning_mode.value,
                    'usage_samples': len(valid_usage_data),
                    'patterns_updated': len(learned_patterns)
                }
            )
            
            logger.info(f"Voice learning completed: {len(learned_patterns)} patterns updated")
            return updated_fingerprint
            
        except Exception as e:
            logger.error(f"Voice learning from usage failed: {str(e)}")
            return voice_fingerprint
    
    async def apply_feedback(
        self,
        voice_fingerprint: VoiceFingerprint,
        feedback: VoiceFeedback
    ) -> Tuple[VoiceFingerprint, List[str]]:
        """
        Apply feedback to improve voice patterns.
        
        Args:
            voice_fingerprint: Current voice fingerprint
            feedback: Feedback to apply
            
        Returns:
            Tuple of (updated fingerprint, improvement notes)
        """
        try:
            # Validate feedback permissions
            await self._validate_learning_permissions(voice_fingerprint.user_id)
            
            # Process feedback if processor available
            if self.feedback_processor:
                processed_feedback = await self.feedback_processor.process_feedback(
                    feedback, voice_fingerprint
                )
            else:
                processed_feedback = await self._process_feedback_basic(feedback)
            
            # Extract improvement actions
            improvement_actions = await self._extract_improvement_actions(
                processed_feedback, feedback
            )
            
            if not improvement_actions:
                return voice_fingerprint, ["No actionable improvements identified"]
            
            # Apply improvements
            updated_fingerprint = await self._apply_feedback_improvements(
                voice_fingerprint, improvement_actions, feedback
            )
            
            # Generate improvement notes
            improvement_notes = await self._generate_improvement_notes(
                improvement_actions, feedback
            )
            
            # Track evolution
            if await self._is_significant_evolution(voice_fingerprint, updated_fingerprint):
                if self.evolution_tracker:
                    await self.evolution_tracker.track_evolution(
                        voice_fingerprint, updated_fingerprint, 
                        f"feedback_{feedback.feedback_type.value}"
                    )
            
            # Update metrics
            self.learning_metrics['feedback_processed'] += 1
            self.learning_metrics['improvements_made'] += 1
            
            # Log feedback application
            await self.audit_trail.log_voice_pattern_access(
                user_id=voice_fingerprint.user_id,
                access_type="feedback_application",
                patterns_accessed=list(improvement_actions.keys()),
                context={
                    'feedback_type': feedback.feedback_type.value,
                    'feedback_score': feedback.score,
                    'improvements_applied': len(improvement_actions)
                }
            )
            
            logger.info(f"Feedback applied: {len(improvement_actions)} improvements made")
            return updated_fingerprint, improvement_notes
            
        except Exception as e:
            logger.error(f"Feedback application failed: {str(e)}")
            return voice_fingerprint, [f"Feedback application failed: {str(e)}"]
    
    async def start_learning_session(
        self,
        learning_mode: LearningMode,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new learning session.
        
        Args:
            learning_mode: Learning mode for session
            context: Optional session context
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        session = LearningSession(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            learning_mode=learning_mode,
            feedback_items=[],
            patterns_learned=[],
            improvements_made=[],
            performance_metrics={}
        )
        
        self.active_sessions[session_id] = session
        
        logger.info(f"Learning session started: {session_id} ({learning_mode.value})")
        return session_id
    
    async def end_learning_session(
        self,
        session_id: str
    ) -> LearningSession:
        """
        End learning session and return results.
        
        Args:
            session_id: Session to end
            
        Returns:
            Completed learning session data
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Learning session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.now()
        
        # Calculate session performance metrics
        session.performance_metrics = await self._calculate_session_metrics(session)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        # Update global metrics
        self.learning_metrics['sessions_completed'] += 1
        
        logger.info(f"Learning session completed: {session_id}")
        return session
    
    # Private helper methods
    
    async def _validate_learning_permissions(self, user_id: str) -> None:
        """Validate permissions for voice learning."""
        can_learn = await self.governance_manager.can_access_personal_data(
            user_id=user_id,
            access_level="STANDARD",
            usage_type="voice_learning"
        )
        
        if not can_learn:
            raise PermissionError("Voice learning not permitted by governance policy")
    
    async def _validate_usage_data(self, usage_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter usage data."""
        valid_data = []
        
        for data_point in usage_data:
            # Check required fields
            if not all(key in data_point for key in ['text', 'context', 'timestamp']):
                continue
            
            # Check data quality
            if len(data_point['text'].strip()) < 10:  # Minimum text length
                continue
            
            # Check timestamp validity
            try:
                if isinstance(data_point['timestamp'], str):
                    datetime.fromisoformat(data_point['timestamp'])
                elif not isinstance(data_point['timestamp'], datetime):
                    continue
            except ValueError:
                continue
            
            valid_data.append(data_point)
        
        return valid_data
    
    async def _extract_patterns_from_usage(
        self,
        usage_data: List[Dict[str, Any]],
        learning_mode: LearningMode
    ) -> Dict[str, Any]:
        """Extract voice patterns from usage data."""
        patterns = {}
        
        # Group usage data by context
        context_groups = defaultdict(list)
        for data_point in usage_data:
            context_type = data_point.get('context', {}).get('context_type', 'general')
            context_groups[context_type].append(data_point)
        
        # Extract patterns for each context
        for context_type, context_data in context_groups.items():
            if len(context_data) < 3:  # Minimum samples per context
                continue
            
            # Extract text samples
            text_samples = [dp['text'] for dp in context_data]
            
            # Use fingerprint extractor to analyze patterns
            context_patterns = await self.fingerprint_extractor._analyze_conversational_patterns(
                text_samples
            )
            
            if context_patterns:
                patterns[f"{context_type}_patterns"] = context_patterns
        
        return patterns
    
    async def _apply_learned_patterns(
        self,
        voice_fingerprint: VoiceFingerprint,
        learned_patterns: Dict[str, Any],
        learning_mode: LearningMode
    ) -> VoiceFingerprint:
        """Apply learned patterns to voice fingerprint."""
        # Create a copy of the fingerprint
        updated_fingerprint = VoiceFingerprint(
            user_id=voice_fingerprint.user_id,
            personal_patterns=voice_fingerprint.personal_patterns.copy(),
            social_patterns=voice_fingerprint.social_patterns.copy(),
            published_patterns=voice_fingerprint.published_patterns.copy(),
            created_at=voice_fingerprint.created_at,
            updated_at=datetime.now(),
            confidence_scores=voice_fingerprint.confidence_scores.copy(),
            metadata=voice_fingerprint.metadata.copy()
        )
        
        # Apply learned patterns based on learning mode
        learning_rate = self._get_learning_rate(learning_mode)
        
        for pattern_key, pattern_data in learned_patterns.items():
            # Determine which corpus to update
            if 'personal' in pattern_key:
                target_patterns = updated_fingerprint.personal_patterns
            elif 'social' in pattern_key:
                target_patterns = updated_fingerprint.social_patterns
            elif 'published' in pattern_key:
                target_patterns = updated_fingerprint.published_patterns
            else:
                # Apply to personal patterns by default
                target_patterns = updated_fingerprint.personal_patterns
            
            # Blend new patterns with existing ones
            for sub_pattern, value in pattern_data.items():
                if sub_pattern in target_patterns:
                    # Weighted average with existing pattern
                    current_value = target_patterns[sub_pattern]
                    if isinstance(current_value, (int, float)) and isinstance(value, (int, float)):
                        target_patterns[sub_pattern] = (
                            current_value * (1 - learning_rate) + value * learning_rate
                        )
                    elif isinstance(current_value, list) and isinstance(value, list):
                        # Merge lists with deduplication
                        combined = list(set(current_value + value))
                        target_patterns[sub_pattern] = combined[:max(len(current_value), 20)]
                else:
                    # Add new pattern with reduced confidence
                    target_patterns[sub_pattern] = value
        
        # Update metadata
        updated_fingerprint.metadata['last_learning'] = datetime.now().isoformat()
        updated_fingerprint.metadata['learning_mode'] = learning_mode.value
        
        return updated_fingerprint
    
    def _get_learning_rate(self, learning_mode: LearningMode) -> float:
        """Get learning rate based on learning mode."""
        rates = {
            LearningMode.PASSIVE: 0.05,
            LearningMode.ACTIVE: 0.15,
            LearningMode.REINFORCEMENT: 0.10,
            LearningMode.ADAPTIVE: 0.12
        }
        return min(rates.get(learning_mode, 0.1), self.learning_config['max_learning_rate'])
    
    async def _is_significant_evolution(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> bool:
        """Check if evolution is significant enough to record."""
        # Simple change detection - could be enhanced
        old_patterns = {**old_fingerprint.personal_patterns, **old_fingerprint.social_patterns}
        new_patterns = {**new_fingerprint.personal_patterns, **new_fingerprint.social_patterns}
        
        changes = 0
        total_patterns = len(old_patterns)
        
        for key, old_value in old_patterns.items():
            new_value = new_patterns.get(key)
            if new_value != old_value:
                changes += 1
        
        change_ratio = changes / max(total_patterns, 1)
        return change_ratio >= self.learning_config['evolution_threshold']
    
    async def _create_evolution_record(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint,
        trigger_event: str
    ) -> VoiceEvolutionRecord:
        """Create evolution record for significant changes."""
        # Calculate pattern changes
        pattern_changes = {}
        
        # Compare personal patterns
        for key, new_value in new_fingerprint.personal_patterns.items():
            old_value = old_fingerprint.personal_patterns.get(key)
            if old_value != new_value:
                pattern_changes[f"personal.{key}"] = {
                    'old': old_value,
                    'new': new_value
                }
        
        # Calculate confidence change
        old_avg_confidence = sum(old_fingerprint.confidence_scores.values()) / len(old_fingerprint.confidence_scores)
        new_avg_confidence = sum(new_fingerprint.confidence_scores.values()) / len(new_fingerprint.confidence_scores)
        confidence_change = new_avg_confidence - old_avg_confidence
        
        return VoiceEvolutionRecord(
            timestamp=datetime.now(),
            pattern_changes=pattern_changes,
            trigger_event=trigger_event,
            confidence_change=confidence_change,
            performance_impact={},  # TODO: Calculate performance impact
            rollback_data={
                'personal_patterns': old_fingerprint.personal_patterns,
                'social_patterns': old_fingerprint.social_patterns,
                'published_patterns': old_fingerprint.published_patterns
            }
        )
    
    async def _process_feedback_basic(self, feedback: VoiceFeedback) -> Dict[str, Any]:
        """Basic feedback processing when no processor available."""
        return {
            'feedback_type': feedback.feedback_type.value,
            'score': feedback.score,
            'improvement_areas': await self._identify_improvement_areas_basic(feedback),
            'confidence': 0.6  # Lower confidence for basic processing
        }
    
    async def _identify_improvement_areas_basic(self, feedback: VoiceFeedback) -> List[str]:
        """Basic improvement area identification."""
        areas = []
        
        if feedback.score < 0.5:
            if feedback.feedback_type == FeedbackType.AUTHENTICITY:
                areas.extend(['voice_consistency', 'pattern_alignment'])
            elif feedback.feedback_type == FeedbackType.APPROPRIATENESS:
                areas.extend(['context_adaptation', 'audience_targeting'])
            elif feedback.feedback_type == FeedbackType.CLARITY:
                areas.extend(['language_clarity', 'structure_improvement'])
            elif feedback.feedback_type == FeedbackType.TONE:
                areas.extend(['tone_adjustment', 'emotional_alignment'])
        
        return areas
    
    async def _extract_improvement_actions(
        self,
        processed_feedback: Dict[str, Any],
        feedback: VoiceFeedback
    ) -> Dict[str, Any]:
        """Extract actionable improvements from processed feedback."""
        actions = {}
        
        improvement_areas = processed_feedback.get('improvement_areas', [])
        
        for area in improvement_areas:
            if area == 'voice_consistency':
                actions['consistency_boost'] = 0.1
            elif area == 'context_adaptation':
                actions['context_sensitivity'] = 0.15
            elif area == 'tone_adjustment':
                actions['tone_flexibility'] = 0.1
            elif area == 'language_clarity':
                actions['clarity_enhancement'] = 0.12
        
        return actions
    
    async def _apply_feedback_improvements(
        self,
        voice_fingerprint: VoiceFingerprint,
        improvement_actions: Dict[str, Any],
        feedback: VoiceFeedback
    ) -> VoiceFingerprint:
        """Apply improvement actions to voice fingerprint."""
        # Create updated fingerprint
        updated_fingerprint = VoiceFingerprint(
            user_id=voice_fingerprint.user_id,
            personal_patterns=voice_fingerprint.personal_patterns.copy(),
            social_patterns=voice_fingerprint.social_patterns.copy(),
            published_patterns=voice_fingerprint.published_patterns.copy(),
            created_at=voice_fingerprint.created_at,
            updated_at=datetime.now(),
            confidence_scores=voice_fingerprint.confidence_scores.copy(),
            metadata=voice_fingerprint.metadata.copy()
        )
        
        # Apply improvements
        for action, adjustment in improvement_actions.items():
            if action == 'consistency_boost':
                # Boost consistency-related patterns
                for pattern_key in ['sentence_structure', 'vocabulary_consistency']:
                    if pattern_key in updated_fingerprint.personal_patterns:
                        current = updated_fingerprint.personal_patterns[pattern_key]
                        if isinstance(current, (int, float)):
                            updated_fingerprint.personal_patterns[pattern_key] = min(1.0, current + adjustment)
            
            elif action == 'context_sensitivity':
                # Improve context adaptation
                updated_fingerprint.metadata['context_sensitivity'] = adjustment
            
            elif action == 'tone_flexibility':
                # Enhance tone adaptation
                updated_fingerprint.metadata['tone_flexibility'] = adjustment
        
        # Update metadata
        updated_fingerprint.metadata['last_feedback'] = datetime.now().isoformat()
        updated_fingerprint.metadata['feedback_type'] = feedback.feedback_type.value
        
        return updated_fingerprint
    
    async def _generate_improvement_notes(
        self,
        improvement_actions: Dict[str, Any],
        feedback: VoiceFeedback
    ) -> List[str]:
        """Generate human-readable improvement notes."""
        notes = []
        
        for action, adjustment in improvement_actions.items():
            if action == 'consistency_boost':
                notes.append(f"Enhanced voice consistency by {adjustment:.1%}")
            elif action == 'context_sensitivity':
                notes.append(f"Improved context adaptation sensitivity by {adjustment:.1%}")
            elif action == 'tone_flexibility':
                notes.append(f"Increased tone flexibility by {adjustment:.1%}")
            elif action == 'clarity_enhancement':
                notes.append(f"Enhanced language clarity by {adjustment:.1%}")
        
        notes.append(f"Applied feedback from {feedback.source} with score {feedback.score:.2f}")
        
        return notes
    
    async def _calculate_session_metrics(self, session: LearningSession) -> Dict[str, float]:
        """Calculate performance metrics for learning session."""
        duration = (session.end_time - session.start_time).total_seconds()
        
        return {
            'session_duration_seconds': duration,
            'feedback_items_processed': len(session.feedback_items),
            'patterns_learned_count': len(session.patterns_learned),
            'improvements_made_count': len(session.improvements_made),
            'learning_efficiency': len(session.patterns_learned) / max(duration / 60, 1)  # patterns per minute
        }
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        return {
            'metrics': self.learning_metrics.copy(),
            'active_sessions': len(self.active_sessions),
            'configuration': self.learning_config.copy(),
            'cache_size': len(self.pattern_cache)
        }
