"""Context-aware response generator for sophisticated response adaptation."""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict

from .protocols import (
    ContextAwareResponseProtocol,
    AssistantRequest,
    AssistantContext,
    ResponseStyle,
    AssistantMode
)
from ..voice_features.adapters import DynamicVoiceAdapter, ContextVoiceAdapter, AudienceVoiceAdapter

logger = logging.getLogger(__name__)


class ContextAwareResponder(ContextAwareResponseProtocol):
    """
    Context-aware response generator that provides sophisticated
    context analysis and response adaptation capabilities.
    
    This responder specializes in:
    - Deep context analysis from conversation history and current request
    - Intelligent response style adaptation based on multiple factors
    - Context appropriateness validation with detailed scoring
    - Multi-dimensional context consideration (audience, platform, history, intent)
    """
    
    def __init__(
        self,
        voice_adapter: DynamicVoiceAdapter,
        context_adapter: Optional[ContextVoiceAdapter] = None,
        audience_adapter: Optional[AudienceVoiceAdapter] = None
    ):
        """
        Initialize context-aware responder.
        
        Args:
            voice_adapter: Dynamic voice adaptation system
            context_adapter: Optional context-specific voice adapter
            audience_adapter: Optional audience-specific voice adapter
        """
        self.voice_adapter = voice_adapter
        self.context_adapter = context_adapter
        self.audience_adapter = audience_adapter
        
        # Context analysis configuration
        self.context_config = {
            'conversation_history_weight': 0.3,
            'current_request_weight': 0.4,
            'user_preferences_weight': 0.2,
            'platform_context_weight': 0.1,
            'context_memory_turns': 10,
            'context_confidence_threshold': 0.7,
            'style_adaptation_threshold': 0.6
        }
        
        # Context patterns for analysis
        self.context_patterns = {
            'urgency_indicators': [
                'urgent', 'asap', 'immediately', 'right away', 'quickly',
                'emergency', 'critical', 'deadline', 'time sensitive'
            ],
            'formality_indicators': {
                'formal': ['please', 'thank you', 'regarding', 'furthermore', 'sincerely'],
                'casual': ['hey', 'thanks', 'btw', 'lol', 'cool', 'awesome']
            },
            'emotional_indicators': {
                'positive': ['excited', 'happy', 'great', 'wonderful', 'amazing'],
                'negative': ['frustrated', 'upset', 'disappointed', 'concerned', 'worried'],
                'neutral': ['okay', 'fine', 'alright', 'sure', 'understood']
            },
            'complexity_indicators': {
                'simple': ['quick', 'simple', 'brief', 'short', 'basic'],
                'complex': ['detailed', 'comprehensive', 'thorough', 'in-depth', 'complete']
            }
        }
        
        # Platform-specific context rules
        self.platform_contexts = {
            'email': {
                'default_formality': 0.7,
                'default_length': 'medium',
                'greeting_expected': True,
                'closing_expected': True
            },
            'slack': {
                'default_formality': 0.4,
                'default_length': 'short',
                'greeting_expected': False,
                'closing_expected': False
            },
            'twitter': {
                'default_formality': 0.3,
                'default_length': 'short',
                'character_limit': 280,
                'hashtag_friendly': True
            },
            'linkedin': {
                'default_formality': 0.8,
                'default_length': 'medium',
                'professional_tone': True,
                'networking_context': True
            },
            'discord': {
                'default_formality': 0.2,
                'default_length': 'short',
                'casual_tone': True,
                'emoji_friendly': True
            }
        }
        
        # Response style adaptation rules
        self.style_adaptation_rules = {
            ResponseStyle.CONCISE: {
                'max_sentences': 3,
                'avoid_elaboration': True,
                'bullet_points_preferred': True,
                'direct_answers': True
            },
            ResponseStyle.DETAILED: {
                'min_sentences': 5,
                'include_examples': True,
                'explain_reasoning': True,
                'comprehensive_coverage': True
            },
            ResponseStyle.CONVERSATIONAL: {
                'use_contractions': True,
                'include_personal_touches': True,
                'natural_flow': True,
                'engaging_tone': True
            },
            ResponseStyle.FORMAL: {
                'avoid_contractions': True,
                'professional_language': True,
                'structured_format': True,
                'respectful_tone': True
            }
        }
        
        # Context analysis statistics
        self.context_stats = {
            'total_analyses': 0,
            'context_confidence_average': 0.0,
            'style_adaptations': 0,
            'appropriateness_scores': [],
            'platform_usage': defaultdict(int),
            'style_usage': defaultdict(int)
        }
    
    async def analyze_context(
        self,
        request: AssistantRequest,
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze context for response generation.
        
        Args:
            request: Current request
            conversation_history: Previous conversation
            
        Returns:
            Context analysis results
        """
        try:
            # Analyze current request context
            current_context = await self._analyze_current_request(request)
            
            # Analyze conversation history context
            history_context = await self._analyze_conversation_history(conversation_history)
            
            # Analyze platform context
            platform_context = await self._analyze_platform_context(request)
            
            # Analyze user preferences context
            preferences_context = await self._analyze_user_preferences(request.context)
            
            # Combine context analyses
            combined_context = await self._combine_context_analyses(
                current_context, history_context, platform_context, preferences_context
            )
            
            # Determine context confidence
            context_confidence = await self._calculate_context_confidence(combined_context)
            
            # Generate context recommendations
            recommendations = await self._generate_context_recommendations(combined_context)
            
            context_analysis = {
                'current_request': current_context,
                'conversation_history': history_context,
                'platform_context': platform_context,
                'user_preferences': preferences_context,
                'combined_context': combined_context,
                'context_confidence': context_confidence,
                'recommendations': recommendations,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Update statistics
            self.context_stats['total_analyses'] += 1
            current_avg = self.context_stats['context_confidence_average']
            total_analyses = self.context_stats['total_analyses']
            self.context_stats['context_confidence_average'] = (
                (current_avg * (total_analyses - 1) + context_confidence) / total_analyses
            )
            
            if request.context and request.context.platform:
                self.context_stats['platform_usage'][request.context.platform] += 1
            
            logger.debug(f"Context analysis completed with confidence: {context_confidence:.3f}")
            return context_analysis
            
        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            return {
                'error': str(e),
                'context_confidence': 0.3,
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    async def adapt_response_style(
        self,
        base_response: str,
        context: AssistantContext,
        target_style: ResponseStyle
    ) -> str:
        """
        Adapt response style based on context.
        
        Args:
            base_response: Base response text
            context: Assistant context
            target_style: Target response style
            
        Returns:
            Style-adapted response
        """
        try:
            # Get style adaptation rules
            style_rules = self.style_adaptation_rules.get(target_style, {})
            
            # Apply style-specific adaptations
            adapted_response = base_response
            
            if target_style == ResponseStyle.CONCISE:
                adapted_response = await self._adapt_to_concise(adapted_response, style_rules)
            elif target_style == ResponseStyle.DETAILED:
                adapted_response = await self._adapt_to_detailed(adapted_response, style_rules, context)
            elif target_style == ResponseStyle.CONVERSATIONAL:
                adapted_response = await self._adapt_to_conversational(adapted_response, style_rules)
            elif target_style == ResponseStyle.FORMAL:
                adapted_response = await self._adapt_to_formal(adapted_response, style_rules)
            
            # Apply platform-specific adaptations
            if context.platform and context.platform in self.platform_contexts:
                adapted_response = await self._apply_platform_adaptations(
                    adapted_response, context.platform
                )
            
            # Apply voice adapter for final style consistency
            if self.voice_adapter:
                voice_adaptation = await self.voice_adapter.adapt_voice(
                    text=adapted_response,
                    context={
                        'target_style': target_style.value,
                        'platform': context.platform,
                        'audience': context.audience,
                        'mode': context.mode.value
                    },
                    strategy='context_specific'
                )
                adapted_response = voice_adaptation.adapted_text
            
            # Update statistics
            self.context_stats['style_adaptations'] += 1
            self.context_stats['style_usage'][target_style.value] += 1
            
            logger.debug(f"Response adapted to {target_style.value} style")
            return adapted_response
            
        except Exception as e:
            logger.error(f"Style adaptation failed: {str(e)}")
            return base_response
    
    async def validate_context_appropriateness(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """
        Validate response appropriateness for context.
        
        Args:
            response: Generated response
            context: Assistant context
            
        Returns:
            Appropriateness score (0.0-1.0)
        """
        try:
            appropriateness_scores = []
            
            # Validate length appropriateness
            length_score = await self._validate_length_appropriateness(response, context)
            appropriateness_scores.append(('length', length_score, 0.2))
            
            # Validate formality appropriateness
            formality_score = await self._validate_formality_appropriateness(response, context)
            appropriateness_scores.append(('formality', formality_score, 0.3))
            
            # Validate platform appropriateness
            platform_score = await self._validate_platform_appropriateness(response, context)
            appropriateness_scores.append(('platform', platform_score, 0.2))
            
            # Validate audience appropriateness
            audience_score = await self._validate_audience_appropriateness(response, context)
            appropriateness_scores.append(('audience', audience_score, 0.2))
            
            # Validate mode appropriateness
            mode_score = await self._validate_mode_appropriateness(response, context)
            appropriateness_scores.append(('mode', mode_score, 0.1))
            
            # Calculate weighted average
            total_weight = sum(weight for _, _, weight in appropriateness_scores)
            weighted_score = sum(score * weight for _, score, weight in appropriateness_scores) / total_weight
            
            # Store score for statistics
            self.context_stats['appropriateness_scores'].append(weighted_score)
            if len(self.context_stats['appropriateness_scores']) > 100:
                self.context_stats['appropriateness_scores'] = self.context_stats['appropriateness_scores'][-100:]
            
            logger.debug(f"Context appropriateness validated: {weighted_score:.3f}")
            return weighted_score
            
        except Exception as e:
            logger.error(f"Context appropriateness validation failed: {str(e)}")
            return 0.5
    
    # Private helper methods
    
    async def _analyze_current_request(self, request: AssistantRequest) -> Dict[str, Any]:
        """Analyze current request for context clues."""
        analysis = {
            'urgency_level': 0.0,
            'formality_level': 0.5,
            'emotional_tone': 'neutral',
            'complexity_level': 'medium',
            'specific_requirements': []
        }
        
        user_input = request.user_input.lower()
        
        # Analyze urgency
        urgency_count = sum(1 for indicator in self.context_patterns['urgency_indicators'] if indicator in user_input)
        analysis['urgency_level'] = min(1.0, urgency_count * 0.3)
        
        # Analyze formality
        formal_count = sum(1 for indicator in self.context_patterns['formality_indicators']['formal'] if indicator in user_input)
        casual_count = sum(1 for indicator in self.context_patterns['formality_indicators']['casual'] if indicator in user_input)
        
        if formal_count > casual_count:
            analysis['formality_level'] = min(1.0, 0.5 + formal_count * 0.2)
        elif casual_count > formal_count:
            analysis['formality_level'] = max(0.0, 0.5 - casual_count * 0.2)
        
        # Analyze emotional tone
        for emotion, indicators in self.context_patterns['emotional_indicators'].items():
            if any(indicator in user_input for indicator in indicators):
                analysis['emotional_tone'] = emotion
                break
        
        # Analyze complexity
        simple_count = sum(1 for indicator in self.context_patterns['complexity_indicators']['simple'] if indicator in user_input)
        complex_count = sum(1 for indicator in self.context_patterns['complexity_indicators']['complex'] if indicator in user_input)
        
        if complex_count > simple_count:
            analysis['complexity_level'] = 'high'
        elif simple_count > complex_count:
            analysis['complexity_level'] = 'low'
        
        return analysis
    
    async def _analyze_conversation_history(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation history for context patterns."""
        if not history:
            return {'no_history': True}
        
        # Analyze recent conversation turns
        recent_history = history[-self.context_config['context_memory_turns']:]
        
        analysis = {
            'conversation_length': len(history),
            'recent_turns': len(recent_history),
            'formality_trend': 0.5,
            'topic_consistency': 0.8,
            'user_satisfaction_trend': 0.8,
            'response_style_preferences': []
        }
        
        # Analyze formality trend
        formality_scores = []
        for turn in recent_history:
            if 'user_input' in turn:
                user_input = turn['user_input'].lower()
                formal_indicators = sum(1 for indicator in self.context_patterns['formality_indicators']['formal'] if indicator in user_input)
                casual_indicators = sum(1 for indicator in self.context_patterns['formality_indicators']['casual'] if indicator in user_input)
                
                if formal_indicators + casual_indicators > 0:
                    formality = formal_indicators / (formal_indicators + casual_indicators)
                    formality_scores.append(formality)
        
        if formality_scores:
            analysis['formality_trend'] = sum(formality_scores) / len(formality_scores)
        
        # Analyze user satisfaction from response quality scores
        quality_scores = []
        for turn in recent_history:
            if 'voice_consistency' in turn and 'context_appropriateness' in turn:
                avg_quality = (turn['voice_consistency'] + turn['context_appropriateness']) / 2
                quality_scores.append(avg_quality)
        
        if quality_scores:
            analysis['user_satisfaction_trend'] = sum(quality_scores) / len(quality_scores)
        
        return analysis
    
    async def _analyze_platform_context(self, request: AssistantRequest) -> Dict[str, Any]:
        """Analyze platform-specific context."""
        if not request.context or not request.context.platform:
            return {'no_platform': True}
        
        platform = request.context.platform
        platform_rules = self.platform_contexts.get(platform, {})
        
        return {
            'platform': platform,
            'platform_rules': platform_rules,
            'has_character_limit': 'character_limit' in platform_rules,
            'formality_expectation': platform_rules.get('default_formality', 0.5),
            'length_expectation': platform_rules.get('default_length', 'medium')
        }
    
    async def _analyze_user_preferences(self, context: Optional[AssistantContext]) -> Dict[str, Any]:
        """Analyze user preferences from context."""
        if not context or not context.user_preferences:
            return {'no_preferences': True}
        
        preferences = context.user_preferences
        
        analysis = {
            'has_preferences': True,
            'successful_patterns': preferences.get('successful_patterns', []),
            'preferred_modes': [],
            'preferred_styles': [],
            'preference_confidence': 0.5
        }
        
        # Analyze successful patterns
        successful_patterns = preferences.get('successful_patterns', [])
        if successful_patterns:
            # Extract preferred modes and styles
            modes = [pattern.get('mode') for pattern in successful_patterns if pattern.get('mode')]
            styles = [pattern.get('style') for pattern in successful_patterns if pattern.get('style')]
            
            if modes:
                mode_counts = defaultdict(int)
                for mode in modes:
                    mode_counts[mode] += 1
                analysis['preferred_modes'] = sorted(mode_counts.items(), key=lambda x: x[1], reverse=True)
            
            if styles:
                style_counts = defaultdict(int)
                for style in styles:
                    style_counts[style] += 1
                analysis['preferred_styles'] = sorted(style_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Calculate preference confidence based on pattern consistency
            analysis['preference_confidence'] = min(1.0, len(successful_patterns) * 0.1)
        
        return analysis
    
    async def _combine_context_analyses(
        self,
        current: Dict[str, Any],
        history: Dict[str, Any],
        platform: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine multiple context analyses into unified context."""
        combined = {
            'overall_formality': 0.5,
            'overall_urgency': 0.0,
            'overall_complexity': 'medium',
            'recommended_style': ResponseStyle.CONVERSATIONAL,
            'recommended_length': 'medium',
            'context_factors': []
        }
        
        # Combine formality
        formality_factors = []
        
        if 'formality_level' in current:
            formality_factors.append((current['formality_level'], self.context_config['current_request_weight']))
        
        if 'formality_trend' in history:
            formality_factors.append((history['formality_trend'], self.context_config['conversation_history_weight']))
        
        if 'formality_expectation' in platform:
            formality_factors.append((platform['formality_expectation'], self.context_config['platform_context_weight']))
        
        if formality_factors:
            total_weight = sum(weight for _, weight in formality_factors)
            combined['overall_formality'] = sum(value * weight for value, weight in formality_factors) / total_weight
        
        # Combine urgency
        if 'urgency_level' in current:
            combined['overall_urgency'] = current['urgency_level']
        
        # Combine complexity
        if 'complexity_level' in current:
            combined['overall_complexity'] = current['complexity_level']
        
        # Determine recommended style
        if combined['overall_formality'] > 0.7:
            combined['recommended_style'] = ResponseStyle.FORMAL
        elif combined['overall_urgency'] > 0.5:
            combined['recommended_style'] = ResponseStyle.CONCISE
        elif combined['overall_complexity'] == 'high':
            combined['recommended_style'] = ResponseStyle.DETAILED
        else:
            combined['recommended_style'] = ResponseStyle.CONVERSATIONAL
        
        # Determine recommended length
        if 'length_expectation' in platform:
            combined['recommended_length'] = platform['length_expectation']
        elif combined['overall_urgency'] > 0.5:
            combined['recommended_length'] = 'short'
        elif combined['overall_complexity'] == 'high':
            combined['recommended_length'] = 'long'
        
        return combined
    
    async def _calculate_context_confidence(self, combined_context: Dict[str, Any]) -> float:
        """Calculate confidence in context analysis."""
        confidence_factors = []
        
        # Base confidence
        base_confidence = 0.5
        confidence_factors.append(base_confidence)
        
        # Boost confidence if we have clear indicators
        if combined_context.get('overall_urgency', 0) > 0.3:
            confidence_factors.append(0.2)  # Clear urgency indicators
        
        if abs(combined_context.get('overall_formality', 0.5) - 0.5) > 0.2:
            confidence_factors.append(0.2)  # Clear formality indicators
        
        if combined_context.get('overall_complexity') in ['high', 'low']:
            confidence_factors.append(0.1)  # Clear complexity indicators
        
        return min(1.0, sum(confidence_factors))
    
    async def _generate_context_recommendations(self, combined_context: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on context analysis."""
        recommendations = []
        
        # Style recommendations
        recommended_style = combined_context.get('recommended_style', ResponseStyle.CONVERSATIONAL)
        recommendations.append(f"Use {recommended_style.value} response style")
        
        # Length recommendations
        recommended_length = combined_context.get('recommended_length', 'medium')
        recommendations.append(f"Target {recommended_length} response length")
        
        # Urgency recommendations
        if combined_context.get('overall_urgency', 0) > 0.5:
            recommendations.append("Prioritize direct, actionable response due to urgency")
        
        # Formality recommendations
        formality = combined_context.get('overall_formality', 0.5)
        if formality > 0.7:
            recommendations.append("Maintain professional, formal tone")
        elif formality < 0.3:
            recommendations.append("Use casual, friendly tone")
        
        # Complexity recommendations
        complexity = combined_context.get('overall_complexity', 'medium')
        if complexity == 'high':
            recommendations.append("Provide detailed, comprehensive response")
        elif complexity == 'low':
            recommendations.append("Keep response simple and straightforward")
        
        return recommendations
    
    async def _adapt_to_concise(self, response: str, style_rules: Dict[str, Any]) -> str:
        """Adapt response to concise style."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Limit to max sentences
        max_sentences = style_rules.get('max_sentences', 3)
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]
        
        # Remove elaborative phrases
        if style_rules.get('avoid_elaboration', False):
            elaboration_phrases = ['for example', 'in other words', 'furthermore', 'additionally']
            for i, sentence in enumerate(sentences):
                for phrase in elaboration_phrases:
                    sentence = sentence.replace(phrase, '')
                sentences[i] = sentence.strip()
        
        return '. '.join(sentences) + '.'
    
    async def _adapt_to_detailed(self, response: str, style_rules: Dict[str, Any], context: AssistantContext) -> str:
        """Adapt response to detailed style."""
        # If response is too short, suggest expansion
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        min_sentences = style_rules.get('min_sentences', 5)
        if len(sentences) < min_sentences:
            # Add explanatory content
            if style_rules.get('explain_reasoning', False):
                response += " Let me explain the reasoning behind this approach."
            
            if style_rules.get('include_examples', False):
                response += " Here are some examples to illustrate this point."
        
        return response
    
    async def _adapt_to_conversational(self, response: str, style_rules: Dict[str, Any]) -> str:
        """Adapt response to conversational style."""
        # Add contractions
        if style_rules.get('use_contractions', False):
            contractions = {
                'do not': "don't",
                'will not': "won't",
                'cannot': "can't",
                'would not': "wouldn't",
                'should not': "shouldn't",
                'it is': "it's",
                'you are': "you're",
                'we are': "we're"
            }
            
            for full, contracted in contractions.items():
                response = response.replace(full, contracted)
        
        # Add personal touches
        if style_rules.get('include_personal_touches', False):
            if not any(word in response.lower() for word in ['i', 'me', 'my']):
                response = "I think " + response.lower()
        
        return response
    
    async def _adapt_to_formal(self, response: str, style_rules: Dict[str, Any]) -> str:
        """Adapt response to formal style."""
        # Remove contractions
        if style_rules.get('avoid_contractions', False):
            contractions = {
                "don't": 'do not',
                "won't": 'will not',
                "can't": 'cannot',
                "wouldn't": 'would not',
                "shouldn't": 'should not',
                "it's": 'it is',
                "you're": 'you are',
                "we're": 'we are'
            }
            
            for contracted, full in contractions.items():
                response = response.replace(contracted, full)
        
        # Ensure professional language
        if style_rules.get('professional_language', False):
            casual_replacements = {
                'hey': 'hello',
                'thanks': 'thank you',
                'ok': 'acceptable',
                'cool': 'excellent'
            }
            
            for casual, professional in casual_replacements.items():
                response = response.replace(casual, professional)
        
        return response
    
    async def _apply_platform_adaptations(self, response: str, platform: str) -> str:
        """Apply platform-specific adaptations."""
        platform_rules = self.platform_contexts.get(platform, {})
        
        # Handle character limits
        if 'character_limit' in platform_rules:
            char_limit = platform_rules['character_limit']
            if len(response) > char_limit:
                # Truncate and add ellipsis
                response = response[:char_limit-3] + '...'
        
        # Add platform-specific formatting
        if platform == 'twitter' and platform_rules.get('hashtag_friendly', False):
            # Could add hashtag suggestions here
            pass
        
        if platform == 'email':
            if platform_rules.get('greeting_expected', False) and not response.startswith(('Hello', 'Hi', 'Dear')):
                response = 'Hello,\n\n' + response
            
            if platform_rules.get('closing_expected', False) and not response.endswith(('regards', 'sincerely', 'thanks')):
                response += '\n\nBest regards'
        
        return response
    
    async def _validate_length_appropriateness(self, response: str, context: AssistantContext) -> float:
        """Validate response length appropriateness."""
        response_length = len(response)
        
        # Base score
        score = 0.8
        
        # Check against response style expectations
        if context.response_style == ResponseStyle.CONCISE:
            if response_length > 500:
                score -= 0.3
            elif response_length < 100:
                score += 0.1
        elif context.response_style == ResponseStyle.DETAILED:
            if response_length < 200:
                score -= 0.3
            elif response_length > 800:
                score += 0.1
        
        # Check against platform expectations
        if context.platform and context.platform in self.platform_contexts:
            platform_rules = self.platform_contexts[context.platform]
            if 'character_limit' in platform_rules:
                char_limit = platform_rules['character_limit']
                if response_length > char_limit:
                    score -= 0.5  # Major penalty for exceeding platform limits
        
        return max(0.0, min(1.0, score))
    
    async def _validate_formality_appropriateness(self, response: str, context: AssistantContext) -> float:
        """Validate formality appropriateness."""
        # Analyze response formality
        response_lower = response.lower()
        
        formal_indicators = sum(1 for indicator in self.context_patterns['formality_indicators']['formal'] if indicator in response_lower)
        casual_indicators = sum(1 for indicator in self.context_patterns['formality_indicators']['casual'] if indicator in response_lower)
        
        if formal_indicators + casual_indicators == 0:
            response_formality = 0.5  # Neutral
        else:
            response_formality = formal_indicators / (formal_indicators + casual_indicators)
        
        # Compare with expected formality
        expected_formality = 0.5  # Default
        
        if context.mode == AssistantMode.PROFESSIONAL:
            expected_formality = 0.8
        elif context.mode == AssistantMode.PERSONAL:
            expected_formality = 0.3
        
        if context.platform and context.platform in self.platform_contexts:
            platform_formality = self.platform_contexts[context.platform].get('default_formality', 0.5)
            expected_formality = (expected_formality + platform_formality) / 2
        
        # Calculate appropriateness score
        formality_diff = abs(response_formality - expected_formality)
        score = max(0.0, 1.0 - formality_diff * 2)
        
        return score
    
    async def _validate_platform_appropriateness(self, response: str, context: AssistantContext) -> float:
        """Validate platform-specific appropriateness."""
        if not context.platform or context.platform not in self.platform_contexts:
            return 0.8  # Neutral score if no platform context
        
        platform_rules = self.platform_contexts[context.platform]
        score = 0.8
        
        # Check character limits
        if 'character_limit' in platform_rules:
            if len(response) > platform_rules['character_limit']:
                score -= 0.4
        
        # Check platform-specific tone requirements
        if platform_rules.get('professional_tone', False):
            if any(casual in response.lower() for casual in ['hey', 'lol', 'awesome']):
                score -= 0.2
        
        if platform_rules.get('casual_tone', False):
            if all(formal not in response.lower() for formal in ['hello', 'thank you', 'sincerely']):
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _validate_audience_appropriateness(self, response: str, context: AssistantContext) -> float:
        """Validate audience-specific appropriateness."""
        if not context.audience:
            return 0.8  # Neutral score if no audience specified
        
        # Use audience adapter if available
        if self.audience_adapter:
            try:
                audience_analysis = await self.audience_adapter.analyze_audience_fit(
                    text=response,
                    target_audience=context.audience
                )
                return audience_analysis.get('appropriateness_score', 0.8)
            except Exception as e:
                logger.error(f"Audience analysis failed: {str(e)}")
        
        # Basic audience appropriateness check
        score = 0.8
        
        if 'executive' in context.audience.lower():
            # Check for executive-appropriate language
            if any(word in response.lower() for word in ['strategic', 'business', 'results']):
                score += 0.1
        elif 'technical' in context.audience.lower():
            # Check for technical appropriateness
            if any(word in response.lower() for word in ['implementation', 'system', 'process']):
                score += 0.1
        
        return score
    
    async def _validate_mode_appropriateness(self, response: str, context: AssistantContext) -> float:
        """Validate mode-specific appropriateness."""
        score = 0.8
        
        if context.mode == AssistantMode.CREATIVE:
            # Check for creative language
            creative_words = ['imagine', 'creative', 'innovative', 'unique', 'original']
            if any(word in response.lower() for word in creative_words):
                score += 0.1
        elif context.mode == AssistantMode.ANALYTICAL:
            # Check for analytical language
            analytical_words = ['analyze', 'data', 'evidence', 'conclusion', 'assessment']
            if any(word in response.lower() for word in analytical_words):
                score += 0.1
        elif context.mode == AssistantMode.PROFESSIONAL:
            # Check for professional language
            professional_words = ['professional', 'business', 'strategy', 'objective']
            if any(word in response.lower() for word in professional_words):
                score += 0.1
        
        return score
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Get context analysis statistics."""
        avg_appropriateness = (
            sum(self.context_stats['appropriateness_scores']) / len(self.context_stats['appropriateness_scores'])
            if self.context_stats['appropriateness_scores'] else 0.0
        )
        
        return {
            'statistics': self.context_stats.copy(),
            'average_appropriateness': avg_appropriateness,
            'configuration': self.context_config.copy(),
            'supported_platforms': list(self.platform_contexts.keys()),
            'supported_styles': list(self.style_adaptation_rules.keys())
        }
