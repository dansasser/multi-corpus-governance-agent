"""
Voice-Aware Text Generator

Generates text that authentically replicates user voice patterns.
Integrates with MVLM models to produce voice-consistent outputs.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from pydantic import BaseModel, Field

from mcg_agent.mvlm.personal_voice_mvlm_manager import (
    PersonalVoiceMVLMManager, 
    VoiceGenerationRequest, 
    VoiceContext,
    MVLMModelType
)
from mcg_agent.security.voice_pattern_access_control import VoicePatternAccessControl
from mcg_agent.security.personal_voice_audit_trail import PersonalVoiceAuditTrail, VoicePatternUsage
from mcg_agent.pydantic_ai.agent_base import AgentRole
from mcg_agent.utils.exceptions import VoiceGenerationError
from mcg_agent.utils.audit import AuditLogger


class VoiceProfile(BaseModel):
    """Complete voice profile for a user"""
    personal_patterns: List[str] = Field(description="Patterns from personal corpus")
    social_patterns: List[str] = Field(description="Patterns from social corpus")
    published_patterns: List[str] = Field(description="Patterns from published corpus")
    
    # Voice characteristics
    preferred_tone: str = Field(description="Default tone preference")
    common_phrases: List[str] = Field(description="Frequently used phrases")
    writing_style: str = Field(description="Overall writing style")
    
    # Context adaptations
    professional_voice: Dict[str, Any] = Field(description="Professional context voice")
    casual_voice: Dict[str, Any] = Field(description="Casual context voice")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class VoiceValidationResult(BaseModel):
    """Result of voice consistency validation"""
    is_consistent: bool = Field(description="Whether text matches expected voice")
    consistency_score: float = Field(description="0-1 score of voice consistency")
    issues_found: List[str] = Field(description="List of voice consistency issues")
    suggestions: List[str] = Field(description="Suggestions for improvement")
    
    # Detailed analysis
    tone_match: bool = Field(description="Whether tone matches expected")
    pattern_match_score: float = Field(description="How well patterns match")
    style_consistency: float = Field(description="Style consistency score")


class VoiceAwareTextGenerator:
    """
    Generate text that authentically replicates user voice.
    
    Integrates with MVLM models and governance systems to produce
    text that maintains voice consistency while respecting access controls.
    """
    
    def __init__(self):
        self.mvlm_manager = PersonalVoiceMVLMManager()
        self.access_control = VoicePatternAccessControl()
        self.audit_trail = PersonalVoiceAuditTrail()
        self.audit_logger = AuditLogger()
        
        # Voice pattern caches for performance
        self._voice_pattern_cache: Dict[str, List[str]] = {}
        self._voice_profile_cache: Optional[VoiceProfile] = None
        
    def craft_voice_prompt(
        self, 
        user_query: str, 
        voice_context: VoiceContext,
        agent_role: AgentRole,
        task_id: str
    ) -> str:
        """
        Create prompts that include user's voice patterns.
        
        Args:
            user_query: Original user query
            voice_context: Voice context to apply
            agent_role: Agent requesting voice patterns
            task_id: Task identifier for audit
            
        Returns:
            str: Voice-enhanced prompt
        """
        try:
            # Request access to voice patterns
            from mcg_agent.security.voice_pattern_access_control import VoiceAccessRequest, CorpusType, VoicePatternType
            
            voice_patterns_collected = []
            
            # Collect patterns from each corpus based on context
            for corpus_source in voice_context.corpus_sources:
                corpus_type = CorpusType(corpus_source)
                
                # Determine which voice pattern types to request
                pattern_types = self._determine_pattern_types(voice_context, corpus_type)
                
                access_request = VoiceAccessRequest(
                    agent_role=agent_role,
                    corpus_type=corpus_type,
                    voice_pattern_types=pattern_types,
                    task_id=task_id,
                    justification=f"Voice pattern access for {voice_context.context_type} generation"
                )
                
                access_log = self.access_control.request_voice_access(access_request)
                
                if access_log.granted:
                    # Get actual voice patterns (would integrate with corpus search)
                    patterns = self._get_voice_patterns(corpus_type, pattern_types)
                    voice_patterns_collected.extend(patterns)
                    
                    # Log voice access for audit
                    self.audit_trail.log_voice_access(
                        agent_role=agent_role,
                        corpus=corpus_source,
                        voice_patterns=patterns,
                        task_id=task_id,
                        context=f"Voice prompt crafting for {voice_context.context_type}"
                    )
                    
            # Apply voice patterns to create enhanced prompt
            enhanced_prompt = self._apply_voice_patterns_to_prompt(
                user_query, 
                voice_context, 
                voice_patterns_collected
            )
            
            return enhanced_prompt
            
        except Exception as e:
            self.audit_logger.log_error(f"Failed to craft voice prompt: {str(e)}")
            return user_query  # Fallback to original query
            
    def _determine_pattern_types(
        self, 
        voice_context: VoiceContext, 
        corpus_type: CorpusType
    ) -> List:
        """Determine which voice pattern types to request based on context"""
        from mcg_agent.security.voice_pattern_access_control import VoicePatternType
        
        pattern_types = []
        
        if corpus_type == CorpusType.PERSONAL:
            pattern_types.extend([
                VoicePatternType.REASONING_PATTERNS,
                VoicePatternType.CONVERSATIONAL_STYLE,
                VoicePatternType.PHRASE_PREFERENCES
            ])
            
        elif corpus_type == CorpusType.SOCIAL:
            if voice_context.tone == "casual":
                pattern_types.extend([
                    VoicePatternType.CASUAL_TONE,
                    VoicePatternType.ENGAGEMENT_PATTERNS
                ])
            pattern_types.append(VoicePatternType.COLLOCATIONS)
            
        elif corpus_type == CorpusType.PUBLISHED:
            if voice_context.tone == "professional":
                pattern_types.extend([
                    VoicePatternType.PROFESSIONAL_TONE,
                    VoicePatternType.ARGUMENTATION_STYLE
                ])
            pattern_types.append(VoicePatternType.COLLOCATIONS)
            
        return pattern_types
        
    def _get_voice_patterns(self, corpus_type: CorpusType, pattern_types: List) -> List[str]:
        """Get actual voice patterns from corpus (placeholder implementation)"""
        # This would integrate with the actual corpus search system
        # For now, return sample patterns based on type
        
        cache_key = f"{corpus_type}_{','.join(str(pt) for pt in pattern_types)}"
        
        if cache_key in self._voice_pattern_cache:
            return self._voice_pattern_cache[cache_key]
            
        patterns = []
        
        if corpus_type == CorpusType.PERSONAL:
            patterns.extend([
                "I think that",
                "In my experience",
                "What I've found is",
                "The way I see it",
                "From my perspective"
            ])
            
        elif corpus_type == CorpusType.SOCIAL:
            patterns.extend([
                "Really excited about",
                "Thanks for sharing",
                "Great point about",
                "I love how",
                "This reminds me of"
            ])
            
        elif corpus_type == CorpusType.PUBLISHED:
            patterns.extend([
                "It's important to note",
                "Furthermore",
                "In conclusion",
                "This demonstrates",
                "The key insight is"
            ])
            
        # Cache for performance
        self._voice_pattern_cache[cache_key] = patterns
        
        return patterns
        
    def _apply_voice_patterns_to_prompt(
        self, 
        user_query: str, 
        voice_context: VoiceContext, 
        voice_patterns: List[str]
    ) -> str:
        """Apply voice patterns to create an enhanced prompt"""
        try:
            # Select most relevant patterns based on influence level
            max_patterns = max(1, int(len(voice_patterns) * voice_context.influence_level))
            selected_patterns = voice_patterns[:max_patterns]
            
            # Build voice instruction
            voice_instruction_parts = []
            
            if selected_patterns:
                patterns_text = ", ".join(f'"{pattern}"' for pattern in selected_patterns)
                voice_instruction_parts.append(f"Use voice patterns like: {patterns_text}")
                
            voice_instruction_parts.append(f"Tone: {voice_context.tone}")
            voice_instruction_parts.append(f"Audience: {voice_context.audience}")
            voice_instruction_parts.append(f"Context: {voice_context.context_type}")
            
            voice_instruction = " | ".join(voice_instruction_parts)
            
            # Create enhanced prompt
            enhanced_prompt = f"""[Voice Context: {voice_instruction}]

User Query: {user_query}

Response (maintain authentic voice):"""
            
            return enhanced_prompt
            
        except Exception as e:
            self.audit_logger.log_error(f"Failed to apply voice patterns: {str(e)}")
            return user_query
            
    async def generate_with_voice(
        self,
        user_query: str,
        voice_context: VoiceContext,
        agent_role: AgentRole,
        task_id: str,
        model_type: Optional[MVLMModelType] = None
    ) -> Tuple[str, List[VoicePatternUsage]]:
        """
        Generate text with voice consistency.
        
        Args:
            user_query: Original user query
            voice_context: Voice context to apply
            agent_role: Agent requesting generation
            task_id: Task identifier
            model_type: Optional specific model to use
            
        Returns:
            Tuple[str, List[VoicePatternUsage]]: Generated text and voice patterns used
        """
        try:
            # Craft voice-enhanced prompt
            voice_prompt = self.craft_voice_prompt(
                user_query, 
                voice_context, 
                agent_role, 
                task_id
            )
            
            # Create generation request
            generation_request = VoiceGenerationRequest(
                prompt=voice_prompt,
                voice_context=voice_context,
                model_type=model_type or self.mvlm_manager.active_model
            )
            
            # Generate text
            result = await self.mvlm_manager.generate_with_voice(generation_request)
            
            # Track voice pattern usage
            voice_patterns_used = self._track_voice_pattern_usage(
                voice_context,
                result.generated_text,
                result.voice_consistency_score
            )
            
            # Log personal data influence
            self.audit_trail.log_personal_data_influence(
                task_id=task_id,
                agent_role=agent_role,
                voice_patterns_used=voice_patterns_used,
                output_text=result.generated_text,
                user_query=user_query,
                context_summary=f"Voice generation with {voice_context.context_type} context",
                processing_duration_ms=result.generation_time_ms
            )
            
            return result.generated_text, voice_patterns_used
            
        except Exception as e:
            raise VoiceGenerationError(f"Failed to generate with voice: {str(e)}")
            
    def _track_voice_pattern_usage(
        self,
        voice_context: VoiceContext,
        generated_text: str,
        consistency_score: float
    ) -> List[VoicePatternUsage]:
        """Track which voice patterns were used in generation"""
        voice_patterns_used = []
        
        for i, pattern in enumerate(voice_context.voice_patterns):
            # Check if pattern appears in generated text
            pattern_found = pattern.lower() in generated_text.lower()
            
            if pattern_found:
                # Determine corpus source (simplified)
                corpus_source = voice_context.corpus_sources[0] if voice_context.corpus_sources else "unknown"
                
                usage = VoicePatternUsage(
                    pattern_id=f"pattern_{i}_{pattern[:10]}",
                    pattern_type="phrase_pattern",  # Simplified
                    corpus_source=corpus_source,
                    pattern_content=pattern,
                    usage_context=f"Applied in {voice_context.context_type} generation",
                    influence_score=consistency_score * 0.8  # Estimate influence
                )
                
                voice_patterns_used.append(usage)
                
        return voice_patterns_used
        
    def validate_voice_consistency(
        self, 
        generated_text: str, 
        expected_voice: VoiceProfile
    ) -> VoiceValidationResult:
        """
        Ensure generated text matches user's voice.
        
        Args:
            generated_text: Text to validate
            expected_voice: Expected voice profile
            
        Returns:
            VoiceValidationResult: Validation results
        """
        try:
            issues_found = []
            suggestions = []
            
            # Check tone consistency
            tone_match = self._validate_tone(generated_text, expected_voice.preferred_tone)
            if not tone_match:
                issues_found.append(f"Tone doesn't match expected '{expected_voice.preferred_tone}'")
                suggestions.append(f"Adjust language to be more {expected_voice.preferred_tone}")
                
            # Check pattern presence
            pattern_match_score = self._calculate_pattern_match(generated_text, expected_voice)
            if pattern_match_score < 0.3:
                issues_found.append("Few recognizable voice patterns found")
                suggestions.append("Include more characteristic phrases and expressions")
                
            # Check style consistency
            style_consistency = self._validate_style(generated_text, expected_voice.writing_style)
            if style_consistency < 0.5:
                issues_found.append("Writing style doesn't match expected pattern")
                suggestions.append("Adjust sentence structure and vocabulary to match style")
                
            # Overall consistency score
            consistency_score = (
                (1.0 if tone_match else 0.0) * 0.3 +
                pattern_match_score * 0.4 +
                style_consistency * 0.3
            )
            
            is_consistent = consistency_score >= 0.7
            
            return VoiceValidationResult(
                is_consistent=is_consistent,
                consistency_score=consistency_score,
                issues_found=issues_found,
                suggestions=suggestions,
                tone_match=tone_match,
                pattern_match_score=pattern_match_score,
                style_consistency=style_consistency
            )
            
        except Exception as e:
            self.audit_logger.log_error(f"Failed to validate voice consistency: {str(e)}")
            return VoiceValidationResult(
                is_consistent=False,
                consistency_score=0.0,
                issues_found=[f"Validation error: {str(e)}"],
                suggestions=["Manual review required"],
                tone_match=False,
                pattern_match_score=0.0,
                style_consistency=0.0
            )
            
    def _validate_tone(self, text: str, expected_tone: str) -> bool:
        """Validate tone consistency (simplified implementation)"""
        tone_indicators = {
            "professional": ["furthermore", "however", "therefore", "consequently", "moreover"],
            "casual": ["really", "pretty", "kind of", "sort of", "basically"],
            "formal": ["nevertheless", "accordingly", "subsequently", "notwithstanding"],
            "friendly": ["great", "awesome", "wonderful", "fantastic", "amazing"]
        }
        
        if expected_tone not in tone_indicators:
            return True  # Can't validate unknown tone
            
        indicators = tone_indicators[expected_tone]
        text_lower = text.lower()
        
        matches = sum(1 for indicator in indicators if indicator in text_lower)
        return matches > 0
        
    def _calculate_pattern_match(self, text: str, voice_profile: VoiceProfile) -> float:
        """Calculate how well text matches voice patterns"""
        all_patterns = (
            voice_profile.personal_patterns +
            voice_profile.social_patterns +
            voice_profile.published_patterns +
            voice_profile.common_phrases
        )
        
        if not all_patterns:
            return 1.0  # No patterns to match
            
        text_lower = text.lower()
        matches = sum(1 for pattern in all_patterns if pattern.lower() in text_lower)
        
        return min(matches / len(all_patterns), 1.0)
        
    def _validate_style(self, text: str, expected_style: str) -> float:
        """Validate writing style consistency (simplified implementation)"""
        style_characteristics = {
            "concise": {"max_avg_sentence_length": 20, "prefer_short_words": True},
            "detailed": {"min_avg_sentence_length": 25, "prefer_complex_words": True},
            "conversational": {"contractions_ok": True, "informal_ok": True},
            "formal": {"contractions_ok": False, "informal_ok": False}
        }
        
        if expected_style not in style_characteristics:
            return 0.8  # Default moderate score
            
        characteristics = style_characteristics[expected_style]
        score = 0.0
        checks = 0
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / len([s for s in sentences if s.strip()])
            
            if "max_avg_sentence_length" in characteristics:
                if avg_sentence_length <= characteristics["max_avg_sentence_length"]:
                    score += 1.0
                checks += 1
                
            if "min_avg_sentence_length" in characteristics:
                if avg_sentence_length >= characteristics["min_avg_sentence_length"]:
                    score += 1.0
                checks += 1
                
        # Check contractions
        if "contractions_ok" in characteristics:
            contractions = ["don't", "won't", "can't", "isn't", "aren't", "wasn't", "weren't"]
            has_contractions = any(contraction in text.lower() for contraction in contractions)
            
            if characteristics["contractions_ok"] == has_contractions:
                score += 1.0
            checks += 1
            
        return score / max(checks, 1)
        
    def get_voice_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about voice generation performance"""
        return {
            "cache_size": len(self._voice_pattern_cache),
            "mvlm_status": self.mvlm_manager.get_model_status(),
            "access_summary": self.access_control.get_access_summary(),
            "audit_summary": self.audit_trail.get_voice_usage_summary()
        }


__all__ = [
    "VoiceAwareTextGenerator",
    "VoiceProfile",
    "VoiceValidationResult"
]
