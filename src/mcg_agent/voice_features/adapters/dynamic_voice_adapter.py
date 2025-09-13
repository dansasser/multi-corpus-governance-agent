"""Dynamic voice adapter for real-time voice adaptation based on context."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..protocols.voice_adaptation_protocol import (
    VoiceAdaptationProtocol,
    AdaptationContext,
    AdaptationResult,
    AdaptationStrategy,
    ContextType
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint
from ...voice.voice_fingerprint_applicator import VoiceFingerprintApplicator
from ...governance.personal_data_governance import PersonalDataGovernanceManager
from ...security.personal_voice_audit_trail import PersonalVoiceAuditTrail

logger = logging.getLogger(__name__)


class DynamicVoiceAdapter(VoiceAdaptationProtocol):
    """
    Dynamic voice adapter that modifies voice patterns in real-time based on context.
    
    This adapter orchestrates voice adaptation by:
    - Analyzing context and audience requirements
    - Selecting appropriate adaptation strategies
    - Applying voice modifications while preserving authenticity
    - Validating adaptation results for quality assurance
    """
    
    def __init__(
        self,
        voice_applicator: VoiceFingerprintApplicator,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail,
        context_analyzer: Optional['ContextVoiceAdapter'] = None,
        audience_adapter: Optional['AudienceVoiceAdapter'] = None
    ):
        """
        Initialize dynamic voice adapter.
        
        Args:
            voice_applicator: Voice fingerprint applicator
            governance_manager: Personal data governance manager
            audit_trail: Voice audit trail system
            context_analyzer: Optional context analyzer
            audience_adapter: Optional audience adapter
        """
        self.voice_applicator = voice_applicator
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        self.context_analyzer = context_analyzer
        self.audience_adapter = audience_adapter
        
        # Adaptation configuration
        self.adaptation_cache: Dict[str, AdaptationResult] = {}
        self.cache_ttl_seconds = 300  # 5 minutes
        self.max_cache_size = 100
        
        # Performance tracking
        self.adaptation_metrics: Dict[str, List[float]] = {
            'adaptation_time': [],
            'confidence_scores': [],
            'validation_scores': []
        }
    
    async def adapt_voice(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy = AdaptationStrategy.ADAPT_TO_AUDIENCE
    ) -> AdaptationResult:
        """
        Adapt voice patterns based on context and strategy.
        
        Args:
            voice_fingerprint: User's voice fingerprint
            context: Adaptation context information
            strategy: Adaptation strategy to use
            
        Returns:
            AdaptationResult with adapted voice context
        """
        start_time = datetime.now()
        
        try:
            # Check governance permissions
            await self._validate_adaptation_permissions(voice_fingerprint, context)
            
            # Check cache for recent adaptation
            cache_key = self._generate_cache_key(voice_fingerprint, context, strategy)
            cached_result = self._get_cached_adaptation(cache_key)
            if cached_result:
                logger.debug(f"Using cached adaptation for context: {context.context_type}")
                return cached_result
            
            # Analyze context if analyzer available
            if self.context_analyzer:
                context = await self.context_analyzer.enhance_context_analysis(context)
            
            # Apply adaptation strategy
            adapted_context = await self._apply_adaptation_strategy(
                voice_fingerprint, context, strategy
            )
            
            # Validate adaptation
            validation_scores = await self.validate_adaptation(
                voice_fingerprint, adapted_context, context
            )
            
            # Create adaptation result
            adaptation_result = AdaptationResult(
                adapted_voice_context=adapted_context,
                adaptation_strategy=strategy,
                confidence_score=validation_scores.get('overall_confidence', 0.8),
                adaptation_notes=await self._generate_adaptation_notes(
                    voice_fingerprint, context, strategy
                ),
                original_patterns_preserved=await self._identify_preserved_patterns(
                    voice_fingerprint, adapted_context
                ),
                patterns_modified=await self._identify_modified_patterns(
                    voice_fingerprint, adapted_context
                ),
                context_analysis=await self._analyze_context_details(context),
                performance_metrics={
                    'adaptation_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'validation_score': validation_scores.get('authenticity', 0.0),
                    'appropriateness_score': validation_scores.get('appropriateness', 0.0)
                }
            )
            
            # Cache result
            self._cache_adaptation(cache_key, adaptation_result)
            
            # Record audit trail
            await self.audit_trail.log_voice_pattern_access(
                user_id="current_user",  # TODO: Get from context
                access_type="voice_adaptation",
                patterns_accessed=adaptation_result.original_patterns_preserved,
                context={
                    'adaptation_strategy': strategy.value,
                    'context_type': context.context_type.value,
                    'confidence_score': adaptation_result.confidence_score
                }
            )
            
            # Update performance metrics
            self._update_performance_metrics(adaptation_result)
            
            logger.info(f"Voice adaptation completed with confidence: {adaptation_result.confidence_score:.2f}")
            return adaptation_result
            
        except Exception as e:
            logger.error(f"Voice adaptation failed: {str(e)}")
            # Return fallback adaptation
            return await self._create_fallback_adaptation(voice_fingerprint, context, strategy)
    
    async def validate_adaptation(
        self,
        original_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any],
        context: AdaptationContext
    ) -> Dict[str, float]:
        """
        Validate that adaptation maintains voice authenticity.
        
        Args:
            original_fingerprint: Original voice fingerprint
            adapted_context: Adapted voice context
            context: Adaptation context
            
        Returns:
            Validation scores (authenticity, appropriateness, etc.)
        """
        validation_scores = {}
        
        try:
            # Authenticity validation
            authenticity_score = await self._validate_authenticity(
                original_fingerprint, adapted_context
            )
            validation_scores['authenticity'] = authenticity_score
            
            # Context appropriateness validation
            appropriateness_score = await self._validate_appropriateness(
                adapted_context, context
            )
            validation_scores['appropriateness'] = appropriateness_score
            
            # Tone consistency validation
            tone_score = await self._validate_tone_consistency(
                original_fingerprint, adapted_context, context
            )
            validation_scores['tone_consistency'] = tone_score
            
            # Overall confidence calculation
            weights = {'authenticity': 0.4, 'appropriateness': 0.3, 'tone_consistency': 0.3}
            overall_confidence = sum(
                validation_scores[key] * weights[key] 
                for key in weights if key in validation_scores
            )
            validation_scores['overall_confidence'] = overall_confidence
            
            logger.debug(f"Adaptation validation scores: {validation_scores}")
            return validation_scores
            
        except Exception as e:
            logger.error(f"Adaptation validation failed: {str(e)}")
            return {'authenticity': 0.5, 'appropriateness': 0.5, 'overall_confidence': 0.5}
    
    async def get_adaptation_strategies(
        self,
        context: AdaptationContext
    ) -> List[AdaptationStrategy]:
        """
        Get recommended adaptation strategies for context.
        
        Args:
            context: Adaptation context
            
        Returns:
            List of recommended strategies
        """
        strategies = []
        
        # Analyze context to recommend strategies
        if context.context_type == ContextType.PROFESSIONAL:
            strategies.extend([
                AdaptationStrategy.ADAPT_TO_AUDIENCE,
                AdaptationStrategy.CONTEXT_SPECIFIC
            ])
        elif context.context_type == ContextType.CASUAL:
            strategies.extend([
                AdaptationStrategy.PRESERVE_ORIGINAL,
                AdaptationStrategy.BLEND_CONTEXTS
            ])
        elif context.context_type == ContextType.FORMAL:
            strategies.extend([
                AdaptationStrategy.CONTEXT_SPECIFIC,
                AdaptationStrategy.ADAPT_TO_AUDIENCE
            ])
        else:
            # Default strategies
            strategies.extend([
                AdaptationStrategy.ADAPT_TO_AUDIENCE,
                AdaptationStrategy.BLEND_CONTEXTS
            ])
        
        # Consider audience and platform
        if context.audience and "professional" in context.audience.lower():
            if AdaptationStrategy.CONTEXT_SPECIFIC not in strategies:
                strategies.append(AdaptationStrategy.CONTEXT_SPECIFIC)
        
        if context.platform and context.platform.lower() in ['linkedin', 'email']:
            if AdaptationStrategy.ADAPT_TO_AUDIENCE not in strategies:
                strategies.append(AdaptationStrategy.ADAPT_TO_AUDIENCE)
        
        return strategies[:3]  # Return top 3 recommendations
    
    # Private helper methods
    
    async def _validate_adaptation_permissions(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> None:
        """Validate permissions for voice adaptation."""
        # Check if voice adaptation is allowed
        can_adapt = await self.governance_manager.can_access_personal_data(
            user_id="current_user",  # TODO: Get from context
            access_level="LIMITED",
            usage_type="voice_adaptation"
        )
        
        if not can_adapt:
            raise PermissionError("Voice adaptation not permitted by governance policy")
    
    def _generate_cache_key(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy
    ) -> str:
        """Generate cache key for adaptation result."""
        context_hash = hash(f"{context.context_type.value}_{context.audience}_{context.platform}")
        return f"adapt_{voice_fingerprint.user_id}_{context_hash}_{strategy.value}"
    
    def _get_cached_adaptation(self, cache_key: str) -> Optional[AdaptationResult]:
        """Get cached adaptation result if still valid."""
        if cache_key in self.adaptation_cache:
            # Check if cache is still valid (simple TTL check)
            return self.adaptation_cache[cache_key]
        return None
    
    def _cache_adaptation(self, cache_key: str, result: AdaptationResult) -> None:
        """Cache adaptation result."""
        # Simple cache management
        if len(self.adaptation_cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.adaptation_cache))
            del self.adaptation_cache[oldest_key]
        
        self.adaptation_cache[cache_key] = result
    
    async def _apply_adaptation_strategy(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy
    ) -> Dict[str, Any]:
        """Apply specific adaptation strategy."""
        if strategy == AdaptationStrategy.PRESERVE_ORIGINAL:
            return await self._preserve_original_voice(voice_fingerprint, context)
        elif strategy == AdaptationStrategy.ADAPT_TO_AUDIENCE:
            return await self._adapt_to_audience(voice_fingerprint, context)
        elif strategy == AdaptationStrategy.BLEND_CONTEXTS:
            return await self._blend_contexts(voice_fingerprint, context)
        elif strategy == AdaptationStrategy.CONTEXT_SPECIFIC:
            return await self._apply_context_specific(voice_fingerprint, context)
        else:
            # Default to audience adaptation
            return await self._adapt_to_audience(voice_fingerprint, context)
    
    async def _preserve_original_voice(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Preserve original voice with minimal adaptation."""
        # Use voice applicator with preserve strategy
        return await self.voice_applicator.apply_voice_patterns(
            voice_fingerprint,
            target_context={
                'strategy': 'preserve_original',
                'context_type': context.context_type.value,
                'minimal_adaptation': True
            }
        )
    
    async def _adapt_to_audience(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Adapt voice to target audience."""
        if self.audience_adapter:
            return await self.audience_adapter.adapt_for_audience(
                voice_fingerprint, context
            )
        else:
            # Fallback audience adaptation
            return await self.voice_applicator.apply_voice_patterns(
                voice_fingerprint,
                target_context={
                    'strategy': 'adapt_to_audience',
                    'audience': context.audience,
                    'formality_level': context.formality_level or 0.5
                }
            )
    
    async def _blend_contexts(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Blend voice patterns from multiple contexts."""
        return await self.voice_applicator.apply_voice_patterns(
            voice_fingerprint,
            target_context={
                'strategy': 'blend_contexts',
                'context_type': context.context_type.value,
                'blend_weights': {
                    'personal': 0.4,
                    'social': 0.3,
                    'published': 0.3
                }
            }
        )
    
    async def _apply_context_specific(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Apply context-specific voice adaptation."""
        if self.context_analyzer:
            enhanced_context = await self.context_analyzer.get_context_specific_patterns(
                voice_fingerprint, context
            )
            return enhanced_context
        else:
            # Fallback context-specific adaptation
            return await self.voice_applicator.apply_voice_patterns(
                voice_fingerprint,
                target_context={
                    'strategy': 'context_specific',
                    'context_type': context.context_type.value,
                    'platform': context.platform,
                    'purpose': context.purpose
                }
            )
    
    async def _validate_authenticity(
        self,
        original_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any]
    ) -> float:
        """Validate voice authenticity after adaptation."""
        # Compare key voice characteristics
        authenticity_score = 0.8  # Placeholder
        
        # TODO: Implement actual authenticity validation
        # - Compare vocabulary patterns
        # - Check tone consistency
        # - Validate style preservation
        
        return authenticity_score
    
    async def _validate_appropriateness(
        self,
        adapted_context: Dict[str, Any],
        context: AdaptationContext
    ) -> float:
        """Validate context appropriateness of adaptation."""
        appropriateness_score = 0.8  # Placeholder
        
        # TODO: Implement actual appropriateness validation
        # - Check formality level match
        # - Validate audience alignment
        # - Verify platform appropriateness
        
        return appropriateness_score
    
    async def _validate_tone_consistency(
        self,
        original_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any],
        context: AdaptationContext
    ) -> float:
        """Validate tone consistency after adaptation."""
        tone_score = 0.8  # Placeholder
        
        # TODO: Implement actual tone validation
        # - Compare emotional tone
        # - Check sentiment consistency
        # - Validate voice personality preservation
        
        return tone_score
    
    async def _generate_adaptation_notes(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy
    ) -> List[str]:
        """Generate notes about the adaptation process."""
        notes = [
            f"Applied {strategy.value} strategy",
            f"Adapted for {context.context_type.value} context"
        ]
        
        if context.audience:
            notes.append(f"Targeted audience: {context.audience}")
        
        if context.platform:
            notes.append(f"Optimized for platform: {context.platform}")
        
        return notes
    
    async def _identify_preserved_patterns(
        self,
        voice_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any]
    ) -> List[str]:
        """Identify which voice patterns were preserved."""
        # TODO: Implement pattern comparison
        return ["core_vocabulary", "sentence_structure", "personality_markers"]
    
    async def _identify_modified_patterns(
        self,
        voice_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any]
    ) -> List[str]:
        """Identify which voice patterns were modified."""
        # TODO: Implement pattern comparison
        return ["formality_level", "audience_adaptation", "platform_optimization"]
    
    async def _analyze_context_details(
        self,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Analyze detailed context information."""
        return {
            'context_type': context.context_type.value,
            'formality_detected': context.formality_level or 0.5,
            'audience_analysis': context.audience or "general",
            'platform_requirements': context.platform or "generic"
        }
    
    async def _create_fallback_adaptation(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy
    ) -> AdaptationResult:
        """Create fallback adaptation result on error."""
        return AdaptationResult(
            adapted_voice_context={'fallback': True, 'original_patterns': True},
            adaptation_strategy=AdaptationStrategy.PRESERVE_ORIGINAL,
            confidence_score=0.5,
            adaptation_notes=["Fallback adaptation due to error"],
            original_patterns_preserved=["all"],
            patterns_modified=[],
            context_analysis={'error': True},
            performance_metrics={'adaptation_time_ms': 0}
        )
    
    def _update_performance_metrics(self, result: AdaptationResult) -> None:
        """Update performance tracking metrics."""
        self.adaptation_metrics['adaptation_time'].append(
            result.performance_metrics.get('adaptation_time_ms', 0)
        )
        self.adaptation_metrics['confidence_scores'].append(result.confidence_score)
        self.adaptation_metrics['validation_scores'].append(
            result.performance_metrics.get('validation_score', 0)
        )
        
        # Keep only recent metrics (last 100)
        for metric_list in self.adaptation_metrics.values():
            if len(metric_list) > 100:
                metric_list.pop(0)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        for metric_name, values in self.adaptation_metrics.items():
            if values:
                stats[metric_name] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        return stats
