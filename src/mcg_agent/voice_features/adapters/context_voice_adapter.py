"""Context voice adapter for context-specific voice adaptation logic."""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..protocols.voice_adaptation_protocol import (
    ContextAnalysisProtocol,
    AdaptationContext,
    ContextType
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint
from ...voice.voice_fingerprint_applicator import VoiceFingerprintApplicator

logger = logging.getLogger(__name__)


class ContextVoiceAdapter(ContextAnalysisProtocol):
    """
    Context-specific voice adapter that analyzes communication context
    and adapts voice patterns accordingly.
    
    This adapter specializes in:
    - Deep context analysis from text and metadata
    - Platform-specific voice adaptations
    - Purpose-driven voice modifications
    - Context-appropriate formality adjustments
    """
    
    def __init__(self, voice_applicator: VoiceFingerprintApplicator):
        """
        Initialize context voice adapter.
        
        Args:
            voice_applicator: Voice fingerprint applicator
        """
        self.voice_applicator = voice_applicator
        
        # Context analysis patterns
        self.formality_indicators = {
            'formal': [
                r'\b(dear|sincerely|respectfully|regards)\b',
                r'\b(please|kindly|would you)\b',
                r'\b(furthermore|moreover|consequently)\b',
                r'\b(pursuant to|in accordance with)\b'
            ],
            'casual': [
                r'\b(hey|hi|hello|sup)\b',
                r'\b(gonna|wanna|gotta)\b',
                r'\b(awesome|cool|great|nice)\b',
                r'\b(lol|haha|omg)\b'
            ]
        }
        
        self.urgency_indicators = {
            'high': [
                r'\b(urgent|asap|immediately|emergency)\b',
                r'\b(deadline|critical|important)\b',
                r'[!]{2,}',  # Multiple exclamation marks
                r'\b(need.{0,10}now|time.{0,10}sensitive)\b'
            ],
            'low': [
                r'\b(whenever|eventually|no rush)\b',
                r'\b(when you get a chance|at your convenience)\b'
            ]
        }
        
        self.platform_patterns = {
            'email': {
                'indicators': [r'subject:', r'dear', r'sincerely', r'best regards'],
                'formality_boost': 0.3,
                'professional_weight': 0.7
            },
            'social': {
                'indicators': [r'#\w+', r'@\w+', r'RT:', r'share'],
                'formality_boost': -0.2,
                'casual_weight': 0.8
            },
            'messaging': {
                'indicators': [r'\b(msg|text|chat)\b', r'[😀-🙏]'],  # emoji range
                'formality_boost': -0.3,
                'conversational_weight': 0.9
            }
        }
    
    async def analyze_context(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdaptationContext:
        """
        Analyze text and metadata to determine context.
        
        Args:
            text: Text to analyze
            metadata: Additional context metadata
            
        Returns:
            AdaptationContext with analysis results
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = {}
            
            # Determine context type
            context_type = await self._determine_context_type(text, metadata)
            
            # Extract audience information
            audience = await self._extract_audience(text, metadata)
            
            # Detect platform
            platform = await self._detect_platform(text, metadata)
            
            # Analyze purpose
            purpose = await self._analyze_purpose(text, metadata)
            
            # Determine formality level
            formality_level = await self.determine_formality_level(
                AdaptationContext(
                    context_type=context_type,
                    audience=audience,
                    platform=platform,
                    purpose=purpose
                )
            )
            
            # Analyze urgency
            urgency_level = await self._analyze_urgency(text)
            
            # Determine relationship level
            relationship_level = await self._determine_relationship_level(text, metadata)
            
            # Extract tone preference
            tone_preference = await self._extract_tone_preference(text, metadata)
            
            context = AdaptationContext(
                context_type=context_type,
                audience=audience,
                platform=platform,
                purpose=purpose,
                tone_preference=tone_preference,
                formality_level=formality_level,
                urgency_level=urgency_level,
                relationship_level=relationship_level,
                metadata={
                    **metadata,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'text_length': len(text),
                    'analysis_confidence': 0.8  # TODO: Calculate actual confidence
                }
            )
            
            logger.debug(f"Context analysis completed: {context_type.value}, formality: {formality_level:.2f}")
            return context
            
        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            # Return default context
            return AdaptationContext(
                context_type=ContextType.CASUAL,
                metadata={'analysis_error': str(e)}
            )
    
    async def extract_audience_info(
        self,
        context: AdaptationContext,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract detailed audience information.
        
        Args:
            context: Base context information
            additional_data: Additional audience data
            
        Returns:
            Detailed audience analysis
        """
        audience_info = {
            'primary_audience': context.audience or 'general',
            'relationship_level': context.relationship_level or 'unknown',
            'formality_expectation': context.formality_level or 0.5,
            'platform_context': context.platform or 'generic'
        }
        
        # Add additional data if provided
        if additional_data:
            audience_info.update(additional_data)
        
        # Analyze audience characteristics
        if context.audience:
            audience_info['audience_characteristics'] = await self._analyze_audience_characteristics(
                context.audience
            )
        
        # Platform-specific audience adjustments
        if context.platform:
            audience_info['platform_adjustments'] = await self._get_platform_audience_adjustments(
                context.platform
            )
        
        return audience_info
    
    async def determine_formality_level(
        self,
        context: AdaptationContext
    ) -> float:
        """
        Determine appropriate formality level for context.
        
        Args:
            context: Context to analyze
            
        Returns:
            Formality level (0.0 = casual, 1.0 = formal)
        """
        base_formality = 0.5  # Start with neutral
        
        # Context type adjustments
        context_adjustments = {
            ContextType.PROFESSIONAL: 0.3,
            ContextType.FORMAL: 0.4,
            ContextType.TECHNICAL: 0.2,
            ContextType.CASUAL: -0.3,
            ContextType.SOCIAL: -0.2,
            ContextType.PERSONAL: -0.1,
            ContextType.CREATIVE: 0.0
        }
        
        base_formality += context_adjustments.get(context.context_type, 0.0)
        
        # Platform adjustments
        if context.platform:
            platform_adjustment = self.platform_patterns.get(
                context.platform.lower(), {}
            ).get('formality_boost', 0.0)
            base_formality += platform_adjustment
        
        # Audience adjustments
        if context.audience:
            if any(term in context.audience.lower() for term in ['executive', 'ceo', 'director']):
                base_formality += 0.2
            elif any(term in context.audience.lower() for term in ['friend', 'buddy', 'pal']):
                base_formality -= 0.2
        
        # Relationship level adjustments
        relationship_adjustments = {
            'stranger': 0.2,
            'acquaintance': 0.1,
            'friend': -0.1,
            'family': -0.2
        }
        
        if context.relationship_level:
            base_formality += relationship_adjustments.get(context.relationship_level, 0.0)
        
        # Ensure formality level is within bounds
        return max(0.0, min(1.0, base_formality))
    
    async def enhance_context_analysis(self, context: AdaptationContext) -> AdaptationContext:
        """Enhance existing context with additional analysis."""
        enhanced_metadata = context.metadata.copy() if context.metadata else {}
        
        # Add enhanced analysis
        enhanced_metadata.update({
            'context_confidence': await self._calculate_context_confidence(context),
            'adaptation_recommendations': await self._get_adaptation_recommendations(context),
            'voice_adjustments': await self._get_voice_adjustments(context)
        })
        
        # Create enhanced context
        return AdaptationContext(
            context_type=context.context_type,
            audience=context.audience,
            platform=context.platform,
            purpose=context.purpose,
            tone_preference=context.tone_preference,
            formality_level=context.formality_level,
            urgency_level=context.urgency_level,
            relationship_level=context.relationship_level,
            metadata=enhanced_metadata
        )
    
    async def get_context_specific_patterns(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """Get context-specific voice patterns."""
        # Apply context-specific voice patterns
        return await self.voice_applicator.apply_voice_patterns(
            voice_fingerprint,
            target_context={
                'strategy': 'context_specific',
                'context_type': context.context_type.value,
                'formality_level': context.formality_level,
                'platform': context.platform,
                'purpose': context.purpose,
                'urgency_level': context.urgency_level,
                'relationship_level': context.relationship_level
            }
        )
    
    # Private helper methods
    
    async def _determine_context_type(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> ContextType:
        """Determine the primary context type."""
        text_lower = text.lower()
        
        # Check metadata first
        if 'context_type' in metadata:
            try:
                return ContextType(metadata['context_type'])
            except ValueError:
                pass
        
        # Professional indicators
        professional_indicators = [
            'meeting', 'project', 'deadline', 'proposal', 'business',
            'client', 'customer', 'revenue', 'strategy', 'analysis'
        ]
        
        # Technical indicators
        technical_indicators = [
            'api', 'database', 'algorithm', 'implementation', 'code',
            'system', 'architecture', 'framework', 'deployment'
        ]
        
        # Formal indicators
        formal_indicators = [
            'dear sir', 'madam', 'to whom it may concern', 'respectfully',
            'pursuant to', 'in accordance with', 'hereby'
        ]
        
        # Creative indicators
        creative_indicators = [
            'story', 'creative', 'artistic', 'design', 'inspiration',
            'imagination', 'innovative', 'brainstorm'
        ]
        
        # Count indicators
        professional_count = sum(1 for indicator in professional_indicators if indicator in text_lower)
        technical_count = sum(1 for indicator in technical_indicators if indicator in text_lower)
        formal_count = sum(1 for indicator in formal_indicators if indicator in text_lower)
        creative_count = sum(1 for indicator in creative_indicators if indicator in text_lower)
        
        # Determine context based on highest count
        counts = {
            ContextType.PROFESSIONAL: professional_count,
            ContextType.TECHNICAL: technical_count,
            ContextType.FORMAL: formal_count,
            ContextType.CREATIVE: creative_count
        }
        
        max_context = max(counts, key=counts.get)
        
        # If no clear winner, check for social/personal indicators
        if counts[max_context] == 0:
            if any(pattern in text_lower for pattern in ['friend', 'family', 'personal', 'private']):
                return ContextType.PERSONAL
            elif any(pattern in text_lower for pattern in ['social', 'share', 'post', 'tweet']):
                return ContextType.SOCIAL
            else:
                return ContextType.CASUAL
        
        return max_context
    
    async def _extract_audience(self, text: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract audience information from text and metadata."""
        # Check metadata first
        if 'audience' in metadata:
            return metadata['audience']
        
        # Look for audience indicators in text
        audience_patterns = [
            r'dear\s+([^,\n]+)',
            r'to\s+([^,\n]+)',
            r'@(\w+)',
            r'for\s+([^,\n]+)\s+team',
            r'([^,\n]+)\s+department'
        ]
        
        for pattern in audience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def _detect_platform(self, text: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Detect the communication platform."""
        # Check metadata first
        if 'platform' in metadata:
            return metadata['platform']
        
        # Platform detection patterns
        for platform, config in self.platform_patterns.items():
            for indicator in config['indicators']:
                if re.search(indicator, text, re.IGNORECASE):
                    return platform
        
        return None
    
    async def _analyze_purpose(self, text: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Analyze the purpose of the communication."""
        # Check metadata first
        if 'purpose' in metadata:
            return metadata['purpose']
        
        text_lower = text.lower()
        
        # Purpose indicators
        purpose_patterns = {
            'request': ['please', 'could you', 'would you', 'can you', 'need'],
            'information': ['inform', 'update', 'notify', 'let you know'],
            'question': ['?', 'how', 'what', 'when', 'where', 'why', 'which'],
            'response': ['thank you', 'thanks', 'in response to', 'regarding'],
            'announcement': ['announce', 'pleased to', 'excited to', 'happy to']
        }
        
        purpose_scores = {}
        for purpose, indicators in purpose_patterns.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                purpose_scores[purpose] = score
        
        if purpose_scores:
            return max(purpose_scores, key=purpose_scores.get)
        
        return None
    
    async def _analyze_urgency(self, text: str) -> float:
        """Analyze urgency level from text."""
        urgency_score = 0.0
        text_lower = text.lower()
        
        # High urgency indicators
        for pattern in self.urgency_indicators['high']:
            if re.search(pattern, text_lower):
                urgency_score += 0.3
        
        # Low urgency indicators
        for pattern in self.urgency_indicators['low']:
            if re.search(pattern, text_lower):
                urgency_score -= 0.2
        
        # Normalize to 0.0-1.0 range
        return max(0.0, min(1.0, urgency_score + 0.5))
    
    async def _determine_relationship_level(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Determine relationship level with audience."""
        # Check metadata first
        if 'relationship' in metadata:
            return metadata['relationship']
        
        text_lower = text.lower()
        
        # Relationship indicators
        if any(term in text_lower for term in ['dear', 'sir', 'madam', 'mr.', 'ms.']):
            return 'stranger'
        elif any(term in text_lower for term in ['hi', 'hello', 'colleague']):
            return 'acquaintance'
        elif any(term in text_lower for term in ['hey', 'buddy', 'pal', 'friend']):
            return 'friend'
        elif any(term in text_lower for term in ['love', 'honey', 'dear', 'family']):
            return 'family'
        
        return None
    
    async def _extract_tone_preference(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Extract tone preference from context."""
        # Check metadata first
        if 'tone' in metadata:
            return metadata['tone']
        
        text_lower = text.lower()
        
        # Tone indicators
        tone_patterns = {
            'professional': ['professional', 'business', 'formal'],
            'friendly': ['friendly', 'warm', 'welcoming'],
            'casual': ['casual', 'relaxed', 'informal'],
            'enthusiastic': ['excited', 'thrilled', 'amazing'],
            'serious': ['serious', 'important', 'critical']
        }
        
        for tone, indicators in tone_patterns.items():
            if any(indicator in text_lower for indicator in indicators):
                return tone
        
        return None
    
    async def _analyze_audience_characteristics(self, audience: str) -> Dict[str, Any]:
        """Analyze characteristics of the target audience."""
        audience_lower = audience.lower()
        
        characteristics = {
            'formality_preference': 0.5,
            'technical_level': 0.5,
            'relationship_type': 'professional'
        }
        
        # Adjust based on audience type
        if any(term in audience_lower for term in ['executive', 'ceo', 'director']):
            characteristics['formality_preference'] = 0.8
            characteristics['technical_level'] = 0.6
        elif any(term in audience_lower for term in ['developer', 'engineer', 'technical']):
            characteristics['formality_preference'] = 0.4
            characteristics['technical_level'] = 0.9
        elif any(term in audience_lower for term in ['friend', 'family']):
            characteristics['formality_preference'] = 0.2
            characteristics['relationship_type'] = 'personal'
        
        return characteristics
    
    async def _get_platform_audience_adjustments(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific audience adjustments."""
        platform_config = self.platform_patterns.get(platform.lower(), {})
        
        return {
            'formality_adjustment': platform_config.get('formality_boost', 0.0),
            'style_weights': {
                'professional': platform_config.get('professional_weight', 0.5),
                'casual': platform_config.get('casual_weight', 0.5),
                'conversational': platform_config.get('conversational_weight', 0.5)
            }
        }
    
    async def _calculate_context_confidence(self, context: AdaptationContext) -> float:
        """Calculate confidence in context analysis."""
        confidence_factors = []
        
        # Context type confidence
        if context.context_type != ContextType.CASUAL:  # Default fallback
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Audience confidence
        if context.audience:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.5)
        
        # Platform confidence
        if context.platform:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Formality confidence
        if context.formality_level is not None:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    async def _get_adaptation_recommendations(self, context: AdaptationContext) -> List[str]:
        """Get adaptation recommendations for context."""
        recommendations = []
        
        if context.formality_level and context.formality_level > 0.7:
            recommendations.append("Use formal language and professional tone")
        elif context.formality_level and context.formality_level < 0.3:
            recommendations.append("Use casual language and conversational tone")
        
        if context.urgency_level and context.urgency_level > 0.7:
            recommendations.append("Use direct, concise language")
        
        if context.platform == 'social':
            recommendations.append("Optimize for social media engagement")
        elif context.platform == 'email':
            recommendations.append("Use professional email structure")
        
        return recommendations
    
    async def _get_voice_adjustments(self, context: AdaptationContext) -> Dict[str, Any]:
        """Get specific voice adjustments for context."""
        adjustments = {
            'formality_adjustment': context.formality_level or 0.5,
            'urgency_adjustment': context.urgency_level or 0.5,
            'platform_optimization': context.platform or 'generic',
            'audience_targeting': context.audience or 'general'
        }
        
        # Context-specific adjustments
        if context.context_type == ContextType.TECHNICAL:
            adjustments['technical_language'] = True
            adjustments['precision_level'] = 0.8
        elif context.context_type == ContextType.CREATIVE:
            adjustments['creative_language'] = True
            adjustments['expressiveness_level'] = 0.8
        
        return adjustments
