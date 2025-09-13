"""Audience voice adapter for audience-specific voice adaptation."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..protocols.voice_adaptation_protocol import AdaptationContext, ContextType
from ...voice.voice_fingerprint_extractor import VoiceFingerprint
from ...voice.voice_fingerprint_applicator import VoiceFingerprintApplicator

logger = logging.getLogger(__name__)


class AudienceVoiceAdapter:
    """
    Audience-specific voice adapter that modifies voice patterns
    based on target audience characteristics and preferences.
    
    This adapter specializes in:
    - Audience analysis and categorization
    - Relationship-based voice adjustments
    - Professional vs. personal voice switching
    - Cultural and demographic considerations
    """
    
    def __init__(self, voice_applicator: VoiceFingerprintApplicator):
        """
        Initialize audience voice adapter.
        
        Args:
            voice_applicator: Voice fingerprint applicator
        """
        self.voice_applicator = voice_applicator
        
        # Audience categories and their voice characteristics
        self.audience_profiles = {
            'executive': {
                'formality_level': 0.9,
                'technical_depth': 0.3,
                'directness': 0.8,
                'respect_markers': 0.9,
                'time_consciousness': 0.9
            },
            'technical': {
                'formality_level': 0.4,
                'technical_depth': 0.9,
                'directness': 0.7,
                'precision': 0.9,
                'detail_level': 0.8
            },
            'creative': {
                'formality_level': 0.3,
                'expressiveness': 0.9,
                'enthusiasm': 0.8,
                'innovation_focus': 0.9,
                'flexibility': 0.8
            },
            'customer': {
                'formality_level': 0.6,
                'helpfulness': 0.9,
                'clarity': 0.9,
                'patience': 0.8,
                'solution_focus': 0.9
            },
            'colleague': {
                'formality_level': 0.5,
                'collaboration': 0.8,
                'directness': 0.6,
                'supportiveness': 0.8,
                'team_focus': 0.8
            },
            'friend': {
                'formality_level': 0.2,
                'warmth': 0.9,
                'humor': 0.7,
                'personal_touch': 0.9,
                'casualness': 0.9
            },
            'family': {
                'formality_level': 0.1,
                'warmth': 1.0,
                'personal_touch': 1.0,
                'emotional_openness': 0.9,
                'intimacy': 0.9
            }
        }
        
        # Relationship-based adjustments
        self.relationship_adjustments = {
            'stranger': {
                'politeness_boost': 0.3,
                'formality_boost': 0.2,
                'caution_level': 0.8
            },
            'acquaintance': {
                'politeness_boost': 0.1,
                'formality_boost': 0.1,
                'caution_level': 0.5
            },
            'friend': {
                'warmth_boost': 0.3,
                'casualness_boost': 0.3,
                'humor_allowance': 0.8
            },
            'family': {
                'warmth_boost': 0.5,
                'casualness_boost': 0.5,
                'emotional_openness': 0.9
            }
        }
    
    async def adapt_for_audience(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """
        Adapt voice patterns for specific audience.
        
        Args:
            voice_fingerprint: User's voice fingerprint
            context: Adaptation context with audience information
            
        Returns:
            Adapted voice context
        """
        try:
            # Analyze audience characteristics
            audience_analysis = await self._analyze_audience(context)
            
            # Get audience profile
            audience_profile = await self._get_audience_profile(audience_analysis)
            
            # Apply relationship adjustments
            relationship_adjustments = await self._get_relationship_adjustments(context)
            
            # Combine audience and relationship factors
            adaptation_factors = await self._combine_adaptation_factors(
                audience_profile, relationship_adjustments, context
            )
            
            # Apply voice adaptation
            adapted_context = await self.voice_applicator.apply_voice_patterns(
                voice_fingerprint,
                target_context={
                    'strategy': 'audience_adaptation',
                    'audience_profile': audience_profile,
                    'relationship_factors': relationship_adjustments,
                    'adaptation_factors': adaptation_factors,
                    'context_type': context.context_type.value,
                    'formality_override': adaptation_factors.get('formality_level'),
                    'tone_adjustments': adaptation_factors.get('tone_adjustments', {}),
                    'style_modifications': adaptation_factors.get('style_modifications', {})
                }
            )
            
            # Add audience-specific metadata
            adapted_context['audience_adaptation'] = {
                'target_audience': audience_analysis.get('primary_category'),
                'relationship_level': context.relationship_level,
                'adaptation_confidence': audience_analysis.get('confidence', 0.8),
                'key_adjustments': list(adaptation_factors.keys())
            }
            
            logger.debug(f"Audience adaptation completed for: {audience_analysis.get('primary_category')}")
            return adapted_context
            
        except Exception as e:
            logger.error(f"Audience adaptation failed: {str(e)}")
            # Return fallback adaptation
            return await self._create_fallback_audience_adaptation(voice_fingerprint, context)
    
    async def analyze_audience_preferences(
        self,
        audience_description: str,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """
        Analyze audience preferences and communication style.
        
        Args:
            audience_description: Description of the target audience
            context: Adaptation context
            
        Returns:
            Audience preference analysis
        """
        audience_lower = audience_description.lower()
        
        preferences = {
            'communication_style': 'balanced',
            'formality_preference': 0.5,
            'detail_preference': 0.5,
            'interaction_style': 'professional',
            'response_expectations': {}
        }
        
        # Analyze communication style preferences
        if any(term in audience_lower for term in ['executive', 'ceo', 'director', 'vp']):
            preferences.update({
                'communication_style': 'executive',
                'formality_preference': 0.9,
                'detail_preference': 0.3,  # High-level overview preferred
                'interaction_style': 'respectful',
                'response_expectations': {
                    'brevity': 0.9,
                    'action_orientation': 0.9,
                    'strategic_focus': 0.8
                }
            })
        elif any(term in audience_lower for term in ['engineer', 'developer', 'technical', 'architect']):
            preferences.update({
                'communication_style': 'technical',
                'formality_preference': 0.4,
                'detail_preference': 0.9,  # Technical details appreciated
                'interaction_style': 'direct',
                'response_expectations': {
                    'precision': 0.9,
                    'technical_depth': 0.9,
                    'evidence_based': 0.8
                }
            })
        elif any(term in audience_lower for term in ['customer', 'client', 'user']):
            preferences.update({
                'communication_style': 'service',
                'formality_preference': 0.6,
                'detail_preference': 0.7,
                'interaction_style': 'helpful',
                'response_expectations': {
                    'clarity': 0.9,
                    'helpfulness': 0.9,
                    'solution_focus': 0.8
                }
            })
        elif any(term in audience_lower for term in ['friend', 'buddy', 'pal']):
            preferences.update({
                'communication_style': 'friendly',
                'formality_preference': 0.2,
                'detail_preference': 0.5,
                'interaction_style': 'casual',
                'response_expectations': {
                    'warmth': 0.9,
                    'personal_touch': 0.8,
                    'humor_allowance': 0.7
                }
            })
        
        return preferences
    
    async def get_audience_voice_adjustments(
        self,
        audience_category: str,
        relationship_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get specific voice adjustments for audience category.
        
        Args:
            audience_category: Category of the audience
            relationship_level: Relationship level with audience
            
        Returns:
            Voice adjustment parameters
        """
        # Get base audience profile
        base_profile = self.audience_profiles.get(audience_category, {})
        
        # Get relationship adjustments
        relationship_adj = self.relationship_adjustments.get(relationship_level, {})
        
        # Combine adjustments
        voice_adjustments = {
            'formality_level': base_profile.get('formality_level', 0.5),
            'tone_adjustments': {},
            'style_modifications': {},
            'vocabulary_adjustments': {}
        }
        
        # Apply relationship adjustments
        if 'formality_boost' in relationship_adj:
            voice_adjustments['formality_level'] = min(1.0, 
                voice_adjustments['formality_level'] + relationship_adj['formality_boost']
            )
        
        # Tone adjustments based on audience
        if 'warmth' in base_profile:
            voice_adjustments['tone_adjustments']['warmth'] = base_profile['warmth']
        if 'directness' in base_profile:
            voice_adjustments['tone_adjustments']['directness'] = base_profile['directness']
        if 'enthusiasm' in base_profile:
            voice_adjustments['tone_adjustments']['enthusiasm'] = base_profile['enthusiasm']
        
        # Style modifications
        if 'technical_depth' in base_profile:
            voice_adjustments['style_modifications']['technical_language'] = base_profile['technical_depth']
        if 'expressiveness' in base_profile:
            voice_adjustments['style_modifications']['expressiveness'] = base_profile['expressiveness']
        if 'precision' in base_profile:
            voice_adjustments['style_modifications']['precision'] = base_profile['precision']
        
        # Vocabulary adjustments
        if audience_category == 'technical':
            voice_adjustments['vocabulary_adjustments']['technical_terms'] = 0.9
            voice_adjustments['vocabulary_adjustments']['jargon_allowance'] = 0.8
        elif audience_category == 'executive':
            voice_adjustments['vocabulary_adjustments']['business_terms'] = 0.8
            voice_adjustments['vocabulary_adjustments']['strategic_language'] = 0.9
        elif audience_category in ['friend', 'family']:
            voice_adjustments['vocabulary_adjustments']['casual_language'] = 0.9
            voice_adjustments['vocabulary_adjustments']['colloquialisms'] = 0.7
        
        return voice_adjustments
    
    # Private helper methods
    
    async def _analyze_audience(self, context: AdaptationContext) -> Dict[str, Any]:
        """Analyze audience from context information."""
        analysis = {
            'primary_category': 'general',
            'confidence': 0.5,
            'characteristics': {},
            'inferred_preferences': {}
        }
        
        if not context.audience:
            return analysis
        
        audience_lower = context.audience.lower()
        
        # Categorize audience
        category_scores = {}
        for category in self.audience_profiles.keys():
            score = 0
            if category in audience_lower:
                score += 1.0
            
            # Check for related terms
            category_terms = {
                'executive': ['ceo', 'director', 'vp', 'president', 'chief', 'head'],
                'technical': ['engineer', 'developer', 'architect', 'programmer', 'tech'],
                'creative': ['designer', 'artist', 'creative', 'marketing', 'content'],
                'customer': ['client', 'user', 'customer', 'buyer', 'consumer'],
                'colleague': ['team', 'colleague', 'coworker', 'peer', 'staff'],
                'friend': ['friend', 'buddy', 'pal', 'mate'],
                'family': ['family', 'mom', 'dad', 'sister', 'brother', 'relative']
            }
            
            related_terms = category_terms.get(category, [])
            for term in related_terms:
                if term in audience_lower:
                    score += 0.5
            
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)
            analysis['primary_category'] = primary_category
            analysis['confidence'] = min(1.0, category_scores[primary_category] / 2.0)
        
        # Extract characteristics
        analysis['characteristics'] = self.audience_profiles.get(
            analysis['primary_category'], {}
        ).copy()
        
        return analysis
    
    async def _get_audience_profile(self, audience_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed audience profile."""
        primary_category = audience_analysis.get('primary_category', 'general')
        base_profile = self.audience_profiles.get(primary_category, {}).copy()
        
        # Add analysis metadata
        base_profile['category'] = primary_category
        base_profile['analysis_confidence'] = audience_analysis.get('confidence', 0.5)
        
        return base_profile
    
    async def _get_relationship_adjustments(self, context: AdaptationContext) -> Dict[str, Any]:
        """Get relationship-based adjustments."""
        if not context.relationship_level:
            return {}
        
        return self.relationship_adjustments.get(context.relationship_level, {}).copy()
    
    async def _combine_adaptation_factors(
        self,
        audience_profile: Dict[str, Any],
        relationship_adjustments: Dict[str, Any],
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Combine all adaptation factors."""
        factors = {}
        
        # Base formality from audience profile
        base_formality = audience_profile.get('formality_level', 0.5)
        
        # Apply relationship adjustments
        if 'formality_boost' in relationship_adjustments:
            base_formality += relationship_adjustments['formality_boost']
        
        # Apply context formality if available
        if context.formality_level is not None:
            # Blend context and audience formality
            base_formality = (base_formality + context.formality_level) / 2
        
        factors['formality_level'] = max(0.0, min(1.0, base_formality))
        
        # Tone adjustments
        tone_adjustments = {}
        
        # From audience profile
        for key in ['warmth', 'directness', 'enthusiasm', 'helpfulness']:
            if key in audience_profile:
                tone_adjustments[key] = audience_profile[key]
        
        # From relationship adjustments
        if 'warmth_boost' in relationship_adjustments:
            current_warmth = tone_adjustments.get('warmth', 0.5)
            tone_adjustments['warmth'] = min(1.0, current_warmth + relationship_adjustments['warmth_boost'])
        
        factors['tone_adjustments'] = tone_adjustments
        
        # Style modifications
        style_modifications = {}
        
        for key in ['technical_depth', 'expressiveness', 'precision', 'detail_level']:
            if key in audience_profile:
                style_modifications[key] = audience_profile[key]
        
        factors['style_modifications'] = style_modifications
        
        return factors
    
    async def _create_fallback_audience_adaptation(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Create fallback audience adaptation on error."""
        return await self.voice_applicator.apply_voice_patterns(
            voice_fingerprint,
            target_context={
                'strategy': 'preserve_original',
                'fallback_reason': 'audience_adaptation_error',
                'context_type': context.context_type.value
            }
        )
