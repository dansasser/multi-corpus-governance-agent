"""
Voice Fingerprint Applicator

Applies extracted voice fingerprints to text generation for authentic voice replication.
Provides intelligent voice adaptation based on context and audience.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from mcg_agent.voice.voice_fingerprint_extractor import VoiceFingerprint, VoicePattern
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext
from mcg_agent.security.personal_data_encryption import PersonalDataEncryption
from mcg_agent.security.personal_voice_audit_trail import PersonalVoiceAuditTrail, VoicePatternUsage
from mcg_agent.utils.exceptions import VoiceApplicationError
from mcg_agent.utils.audit import AuditLogger


class VoiceAdaptationStrategy(str, Enum):
    """Strategies for adapting voice to different contexts"""
    PRESERVE_ORIGINAL = "preserve_original"  # Keep original voice patterns
    ADAPT_TO_AUDIENCE = "adapt_to_audience"  # Adapt based on target audience
    BLEND_CONTEXTS = "blend_contexts"        # Blend patterns from multiple contexts
    CONTEXT_SPECIFIC = "context_specific"    # Use context-specific patterns only


class VoiceApplicationResult(BaseModel):
    """Result of applying voice fingerprint to text generation"""
    adapted_voice_context: VoiceContext = Field(description="Voice context with applied patterns")
    patterns_applied: List[VoicePatternUsage] = Field(description="Voice patterns that were applied")
    adaptation_strategy: VoiceAdaptationStrategy = Field(description="Strategy used for adaptation")
    confidence_score: float = Field(description="Confidence in voice application")
    adaptation_metadata: Dict[str, Any] = Field(description="Metadata about the adaptation process")


class VoiceFingerprintApplicator:
    """
    Apply voice fingerprints to create authentic voice contexts.
    
    Takes extracted voice fingerprints and applies them intelligently
    to text generation contexts, adapting voice patterns based on
    audience, tone, and communication context.
    """
    
    def __init__(self):
        self.encryption = PersonalDataEncryption()
        self.audit_trail = PersonalVoiceAuditTrail()
        self.audit_logger = AuditLogger()
        
        # Application configurations
        self.max_patterns_per_context = 8
        self.min_confidence_threshold = 0.5
        self.adaptation_weights = {
            "personal": 0.4,
            "social": 0.3,
            "published": 0.3
        }
        
    async def apply_voice_fingerprint(
        self,
        voice_fingerprint: VoiceFingerprint,
        target_context: Dict[str, Any],
        adaptation_strategy: VoiceAdaptationStrategy = VoiceAdaptationStrategy.ADAPT_TO_AUDIENCE
    ) -> VoiceApplicationResult:
        """
        Apply voice fingerprint to create context-appropriate voice patterns.
        
        Args:
            voice_fingerprint: Extracted voice fingerprint
            target_context: Target context for voice application
            adaptation_strategy: Strategy for voice adaptation
            
        Returns:
            VoiceApplicationResult: Result with adapted voice context
        """
        try:
            self.audit_logger.log_info(
                f"Applying voice fingerprint for user {voice_fingerprint.user_id} "
                f"with strategy {adaptation_strategy}"
            )
            
            # Analyze target context
            context_analysis = self._analyze_target_context(target_context)
            
            # Select appropriate voice patterns
            selected_patterns = self._select_voice_patterns(
                voice_fingerprint,
                context_analysis,
                adaptation_strategy
            )
            
            # Adapt patterns to context
            adapted_patterns = self._adapt_patterns_to_context(
                selected_patterns,
                context_analysis,
                adaptation_strategy
            )
            
            # Create voice context
            voice_context = self._create_voice_context(
                adapted_patterns,
                context_analysis,
                voice_fingerprint
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_application_confidence(
                adapted_patterns,
                context_analysis,
                voice_fingerprint
            )
            
            # Create pattern usage records
            pattern_usage_records = self._create_pattern_usage_records(
                adapted_patterns,
                target_context,
                voice_fingerprint.user_id
            )
            
            # Create application result
            result = VoiceApplicationResult(
                adapted_voice_context=voice_context,
                patterns_applied=pattern_usage_records,
                adaptation_strategy=adaptation_strategy,
                confidence_score=confidence_score,
                adaptation_metadata={
                    "context_analysis": context_analysis,
                    "patterns_selected": len(selected_patterns),
                    "patterns_adapted": len(adapted_patterns),
                    "fingerprint_confidence": voice_fingerprint.confidence_score,
                    "application_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Log voice application for audit
            self.audit_trail.log_voice_fingerprint_application(
                user_id=voice_fingerprint.user_id,
                target_context=target_context,
                patterns_applied=pattern_usage_records,
                adaptation_strategy=adaptation_strategy.value,
                confidence_score=confidence_score
            )
            
            self.audit_logger.log_info(
                f"Voice fingerprint applied successfully with confidence {confidence_score:.2f}"
            )
            
            return result
            
        except Exception as e:
            raise VoiceApplicationError(f"Failed to apply voice fingerprint: {str(e)}")
            
    def _analyze_target_context(self, target_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze target context to determine voice adaptation needs"""
        try:
            analysis = {
                "tone": target_context.get("tone", "professional"),
                "audience": target_context.get("audience", "general"),
                "context_type": target_context.get("context_type", "general"),
                "formality_level": "moderate",
                "communication_style": "balanced",
                "corpus_preference": []
            }
            
            # Determine formality level
            tone = analysis["tone"].lower()
            if tone in ["formal", "professional", "academic"]:
                analysis["formality_level"] = "formal"
                analysis["corpus_preference"] = ["published", "personal"]
            elif tone in ["casual", "friendly", "informal"]:
                analysis["formality_level"] = "casual"
                analysis["corpus_preference"] = ["social", "personal"]
            else:
                analysis["formality_level"] = "moderate"
                analysis["corpus_preference"] = ["personal", "social", "published"]
                
            # Determine communication style
            audience = analysis["audience"].lower()
            if audience in ["professional", "business", "academic"]:
                analysis["communication_style"] = "professional"
            elif audience in ["personal", "friends", "family"]:
                analysis["communication_style"] = "personal"
            elif audience in ["social", "public", "community"]:
                analysis["communication_style"] = "social"
            else:
                analysis["communication_style"] = "balanced"
                
            # Context-specific adjustments
            context_type = analysis["context_type"].lower()
            if context_type in ["email", "message", "communication"]:
                analysis["corpus_preference"] = ["personal", "social"]
            elif context_type in ["article", "blog", "content"]:
                analysis["corpus_preference"] = ["published", "personal"]
            elif context_type in ["post", "social", "update"]:
                analysis["corpus_preference"] = ["social", "personal"]
                
            return analysis
            
        except Exception as e:
            self.audit_logger.log_error(f"Context analysis failed: {str(e)}")
            return {
                "tone": "professional",
                "audience": "general",
                "context_type": "general",
                "formality_level": "moderate",
                "communication_style": "balanced",
                "corpus_preference": ["personal", "social", "published"]
            }
            
    def _select_voice_patterns(
        self,
        voice_fingerprint: VoiceFingerprint,
        context_analysis: Dict[str, Any],
        adaptation_strategy: VoiceAdaptationStrategy
    ) -> List[VoicePattern]:
        """Select appropriate voice patterns based on context and strategy"""
        try:
            selected_patterns = []
            
            # Get all available patterns
            all_patterns = {
                "personal": voice_fingerprint.personal_voice_patterns,
                "social": voice_fingerprint.social_voice_patterns,
                "published": voice_fingerprint.published_voice_patterns
            }
            
            if adaptation_strategy == VoiceAdaptationStrategy.PRESERVE_ORIGINAL:
                # Use patterns from all corpora equally
                for corpus_patterns in all_patterns.values():
                    selected_patterns.extend(corpus_patterns[:3])  # Top 3 from each
                    
            elif adaptation_strategy == VoiceAdaptationStrategy.ADAPT_TO_AUDIENCE:
                # Prioritize patterns based on context analysis
                corpus_preference = context_analysis.get("corpus_preference", ["personal"])
                
                for corpus in corpus_preference:
                    if corpus in all_patterns:
                        patterns = all_patterns[corpus]
                        # Select more patterns from preferred corpora
                        count = 4 if corpus == corpus_preference[0] else 2
                        selected_patterns.extend(patterns[:count])
                        
            elif adaptation_strategy == VoiceAdaptationStrategy.BLEND_CONTEXTS:
                # Blend patterns from multiple contexts
                weights = self.adaptation_weights
                
                for corpus, corpus_patterns in all_patterns.items():
                    weight = weights.get(corpus, 0.3)
                    count = int(self.max_patterns_per_context * weight)
                    selected_patterns.extend(corpus_patterns[:count])
                    
            elif adaptation_strategy == VoiceAdaptationStrategy.CONTEXT_SPECIFIC:
                # Use only patterns from the most relevant corpus
                primary_corpus = context_analysis.get("corpus_preference", ["personal"])[0]
                if primary_corpus in all_patterns:
                    selected_patterns = all_patterns[primary_corpus][:self.max_patterns_per_context]
                    
            # Filter by confidence threshold
            filtered_patterns = [
                pattern for pattern in selected_patterns
                if pattern.confidence_score >= self.min_confidence_threshold
            ]
            
            # Limit total patterns
            return filtered_patterns[:self.max_patterns_per_context]
            
        except Exception as e:
            self.audit_logger.log_error(f"Pattern selection failed: {str(e)}")
            return []
            
    def _adapt_patterns_to_context(
        self,
        selected_patterns: List[VoicePattern],
        context_analysis: Dict[str, Any],
        adaptation_strategy: VoiceAdaptationStrategy
    ) -> List[VoicePattern]:
        """Adapt selected patterns to the target context"""
        try:
            adapted_patterns = []
            
            target_formality = context_analysis.get("formality_level", "moderate")
            target_tone = context_analysis.get("tone", "professional")
            
            for pattern in selected_patterns:
                adapted_pattern = self._adapt_individual_pattern(
                    pattern,
                    target_formality,
                    target_tone,
                    context_analysis
                )
                
                if adapted_pattern:
                    adapted_patterns.append(adapted_pattern)
                    
            return adapted_patterns
            
        except Exception as e:
            self.audit_logger.log_error(f"Pattern adaptation failed: {str(e)}")
            return selected_patterns  # Return original patterns if adaptation fails
            
    def _adapt_individual_pattern(
        self,
        pattern: VoicePattern,
        target_formality: str,
        target_tone: str,
        context_analysis: Dict[str, Any]
    ) -> Optional[VoicePattern]:
        """Adapt an individual pattern to the target context"""
        try:
            adapted_pattern_text = pattern.pattern
            
            # Formality adaptations
            if target_formality == "formal" and pattern.corpus_source == "social":
                # Make social patterns more formal
                adapted_pattern_text = adapted_pattern_text.replace("really", "particularly")
                adapted_pattern_text = adapted_pattern_text.replace("pretty", "quite")
                adapted_pattern_text = adapted_pattern_text.replace("kind of", "somewhat")
                
            elif target_formality == "casual" and pattern.corpus_source == "published":
                # Make published patterns more casual
                adapted_pattern_text = adapted_pattern_text.replace("furthermore", "also")
                adapted_pattern_text = adapted_pattern_text.replace("however", "but")
                adapted_pattern_text = adapted_pattern_text.replace("therefore", "so")
                
            # Tone adaptations
            if target_tone == "enthusiastic" and "excited" not in adapted_pattern_text.lower():
                # Add enthusiasm markers if appropriate
                if pattern.pattern_type == "conversational":
                    adapted_pattern_text = adapted_pattern_text.replace("I think", "I'm excited to think")
                    
            # Create adapted pattern
            adapted_pattern = VoicePattern(
                pattern=adapted_pattern_text,
                pattern_type=pattern.pattern_type,
                frequency=pattern.frequency,
                corpus_source=pattern.corpus_source,
                confidence_score=pattern.confidence_score * 0.9,  # Slightly lower confidence for adapted
                context_examples=pattern.context_examples
            )
            
            return adapted_pattern
            
        except Exception as e:
            self.audit_logger.log_error(f"Individual pattern adaptation failed: {str(e)}")
            return pattern  # Return original if adaptation fails
            
    def _create_voice_context(
        self,
        adapted_patterns: List[VoicePattern],
        context_analysis: Dict[str, Any],
        voice_fingerprint: VoiceFingerprint
    ) -> VoiceContext:
        """Create voice context from adapted patterns"""
        try:
            # Extract pattern texts
            voice_patterns = [pattern.pattern for pattern in adapted_patterns]
            
            # Determine corpus sources
            corpus_sources = list(set(pattern.corpus_source for pattern in adapted_patterns))
            
            # Calculate influence level based on pattern confidence
            if adapted_patterns:
                avg_confidence = sum(p.confidence_score for p in adapted_patterns) / len(adapted_patterns)
                influence_level = min(avg_confidence * 1.2, 1.0)  # Boost slightly but cap at 1.0
            else:
                influence_level = 0.5
                
            # Create voice context
            voice_context = VoiceContext(
                voice_patterns=voice_patterns,
                tone=context_analysis.get("tone", "professional"),
                audience=context_analysis.get("audience", "general"),
                context_type=context_analysis.get("context_type", "general"),
                corpus_sources=corpus_sources,
                influence_level=influence_level
            )
            
            return voice_context
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice context creation failed: {str(e)}")
            # Return default voice context
            return VoiceContext(
                voice_patterns=[],
                tone="professional",
                audience="general",
                context_type="general",
                corpus_sources=[],
                influence_level=0.5
            )
            
    def _calculate_application_confidence(
        self,
        adapted_patterns: List[VoicePattern],
        context_analysis: Dict[str, Any],
        voice_fingerprint: VoiceFingerprint
    ) -> float:
        """Calculate confidence score for voice application"""
        try:
            if not adapted_patterns:
                return 0.3
                
            # Pattern quality score
            avg_pattern_confidence = sum(p.confidence_score for p in adapted_patterns) / len(adapted_patterns)
            
            # Pattern quantity score
            pattern_quantity_score = min(len(adapted_patterns) / self.max_patterns_per_context, 1.0)
            
            # Corpus alignment score
            preferred_corpora = context_analysis.get("corpus_preference", [])
            pattern_corpora = [p.corpus_source for p in adapted_patterns]
            
            if preferred_corpora:
                alignment_score = sum(
                    1 for corpus in pattern_corpora if corpus in preferred_corpora
                ) / len(pattern_corpora)
            else:
                alignment_score = 0.8
                
            # Fingerprint confidence
            fingerprint_confidence = voice_fingerprint.confidence_score
            
            # Overall confidence
            confidence = (
                avg_pattern_confidence * 0.3 +
                pattern_quantity_score * 0.2 +
                alignment_score * 0.2 +
                fingerprint_confidence * 0.3
            )
            
            return min(confidence, 1.0)
            
        except Exception as e:
            self.audit_logger.log_error(f"Confidence calculation failed: {str(e)}")
            return 0.5
            
    def _create_pattern_usage_records(
        self,
        adapted_patterns: List[VoicePattern],
        target_context: Dict[str, Any],
        user_id: str
    ) -> List[VoicePatternUsage]:
        """Create pattern usage records for audit trail"""
        usage_records = []
        
        try:
            for i, pattern in enumerate(adapted_patterns):
                usage = VoicePatternUsage(
                    pattern_id=f"applied_{user_id}_{i}_{pattern.pattern[:10]}",
                    pattern_type=pattern.pattern_type,
                    corpus_source=pattern.corpus_source,
                    pattern_content=pattern.pattern,
                    usage_context=f"Applied for {target_context.get('context_type', 'general')} context",
                    influence_score=pattern.confidence_score
                )
                
                usage_records.append(usage)
                
        except Exception as e:
            self.audit_logger.log_error(f"Pattern usage record creation failed: {str(e)}")
            
        return usage_records
        
    async def load_voice_fingerprint(self, user_id: str) -> Optional[VoiceFingerprint]:
        """Load encrypted voice fingerprint for a user"""
        try:
            # This would load from actual storage in production
            # For now, return None to indicate no stored fingerprint
            self.audit_logger.log_info(f"Voice fingerprint load requested for user {user_id}")
            return None
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice fingerprint loading failed: {str(e)}")
            return None
            
    def get_adaptation_strategies(self) -> List[VoiceAdaptationStrategy]:
        """Get available voice adaptation strategies"""
        return list(VoiceAdaptationStrategy)
        
    def get_application_stats(self) -> Dict[str, Any]:
        """Get statistics about voice fingerprint applications"""
        return {
            "max_patterns_per_context": self.max_patterns_per_context,
            "min_confidence_threshold": self.min_confidence_threshold,
            "adaptation_weights": self.adaptation_weights,
            "available_strategies": [strategy.value for strategy in VoiceAdaptationStrategy]
        }


__all__ = [
    "VoiceFingerprintApplicator",
    "VoiceApplicationResult",
    "VoiceAdaptationStrategy"
]
