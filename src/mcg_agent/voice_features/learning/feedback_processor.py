"""Feedback processor for analyzing and processing voice feedback."""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from ..protocols.voice_learning_protocol import (
    FeedbackProcessingProtocol,
    VoiceFeedback,
    FeedbackType
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint

logger = logging.getLogger(__name__)


class FeedbackProcessor(FeedbackProcessingProtocol):
    """
    Feedback processor that analyzes voice feedback to extract
    actionable insights for voice improvement.
    
    This processor specializes in:
    - Detailed feedback analysis and categorization
    - Sentiment and intent extraction from feedback
    - Aggregation of multiple feedback sources
    - Identification of improvement priorities
    """
    
    def __init__(self):
        """Initialize feedback processor."""
        # Feedback analysis patterns
        self.improvement_patterns = {
            FeedbackType.AUTHENTICITY: {
                'positive_indicators': [
                    r'\b(authentic|genuine|natural|real|true to)\b',
                    r'\b(sounds like you|your voice|recognizable)\b',
                    r'\b(consistent|coherent|unified)\b'
                ],
                'negative_indicators': [
                    r'\b(artificial|fake|robotic|generic)\b',
                    r'\b(doesn\'t sound like|not your voice|off)\b',
                    r'\b(inconsistent|contradictory|mixed)\b'
                ],
                'improvement_areas': [
                    'voice_consistency', 'pattern_alignment', 'authenticity_enhancement'
                ]
            },
            FeedbackType.APPROPRIATENESS: {
                'positive_indicators': [
                    r'\b(appropriate|suitable|fitting|right tone)\b',
                    r'\b(professional|formal|casual) when needed\b',
                    r'\b(audience-aware|context-sensitive)\b'
                ],
                'negative_indicators': [
                    r'\b(inappropriate|unsuitable|wrong tone)\b',
                    r'\b(too formal|too casual|mismatched)\b',
                    r'\b(tone-deaf|insensitive|off-putting)\b'
                ],
                'improvement_areas': [
                    'context_adaptation', 'audience_targeting', 'tone_calibration'
                ]
            },
            FeedbackType.CLARITY: {
                'positive_indicators': [
                    r'\b(clear|understandable|easy to follow)\b',
                    r'\b(well-structured|organized|coherent)\b',
                    r'\b(concise|to the point|direct)\b'
                ],
                'negative_indicators': [
                    r'\b(unclear|confusing|hard to follow)\b',
                    r'\b(rambling|verbose|wordy)\b',
                    r'\b(disorganized|scattered|jumbled)\b'
                ],
                'improvement_areas': [
                    'language_clarity', 'structure_improvement', 'conciseness'
                ]
            },
            FeedbackType.TONE: {
                'positive_indicators': [
                    r'\b(good tone|right feeling|appropriate mood)\b',
                    r'\b(warm|friendly|professional|engaging)\b',
                    r'\b(balanced|measured|thoughtful)\b'
                ],
                'negative_indicators': [
                    r'\b(wrong tone|bad feeling|inappropriate mood)\b',
                    r'\b(cold|harsh|unprofessional|boring)\b',
                    r'\b(extreme|unbalanced|thoughtless)\b'
                ],
                'improvement_areas': [
                    'tone_adjustment', 'emotional_alignment', 'mood_calibration'
                ]
            },
            FeedbackType.STYLE: {
                'positive_indicators': [
                    r'\b(good style|well-written|flows well)\b',
                    r'\b(engaging|interesting|compelling)\b',
                    r'\b(polished|refined|sophisticated)\b'
                ],
                'negative_indicators': [
                    r'\b(poor style|awkward|choppy)\b',
                    r'\b(boring|dull|unengaging)\b',
                    r'\b(rough|unpolished|crude)\b'
                ],
                'improvement_areas': [
                    'style_refinement', 'flow_improvement', 'engagement_enhancement'
                ]
            },
            FeedbackType.ENGAGEMENT: {
                'positive_indicators': [
                    r'\b(engaging|captivating|interesting)\b',
                    r'\b(holds attention|compelling|draws you in)\b',
                    r'\b(interactive|responsive|dynamic)\b'
                ],
                'negative_indicators': [
                    r'\b(boring|dull|uninteresting)\b',
                    r'\b(loses attention|dry|static)\b',
                    r'\b(monotonous|repetitive|predictable)\b'
                ],
                'improvement_areas': [
                    'engagement_enhancement', 'variety_increase', 'interaction_improvement'
                ]
            }
        }
        
        # Sentiment analysis patterns
        self.sentiment_patterns = {
            'very_positive': [
                r'\b(excellent|outstanding|amazing|perfect)\b',
                r'\b(love|adore|fantastic|brilliant)\b'
            ],
            'positive': [
                r'\b(good|great|nice|well done|solid)\b',
                r'\b(like|appreciate|enjoy|pleased)\b'
            ],
            'neutral': [
                r'\b(okay|fine|acceptable|adequate)\b',
                r'\b(mixed|average|so-so)\b'
            ],
            'negative': [
                r'\b(bad|poor|weak|disappointing)\b',
                r'\b(dislike|concerned|issues|problems)\b'
            ],
            'very_negative': [
                r'\b(terrible|awful|horrible|unacceptable)\b',
                r'\b(hate|despise|completely wrong)\b'
            ]
        }
        
        # Priority weights for different feedback types
        self.feedback_weights = {
            FeedbackType.AUTHENTICITY: 1.0,      # Highest priority
            FeedbackType.APPROPRIATENESS: 0.9,
            FeedbackType.CLARITY: 0.8,
            FeedbackType.TONE: 0.7,
            FeedbackType.STYLE: 0.6,
            FeedbackType.ENGAGEMENT: 0.5,
            FeedbackType.OVERALL: 0.8
        }
    
    async def process_feedback(
        self,
        feedback: VoiceFeedback,
        voice_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """
        Process feedback to extract actionable insights.
        
        Args:
            feedback: Feedback to process
            voice_fingerprint: Current voice fingerprint
            
        Returns:
            Processed feedback insights
        """
        try:
            # Analyze feedback text
            text_analysis = await self._analyze_feedback_text(feedback)
            
            # Extract sentiment
            sentiment_analysis = await self._analyze_sentiment(feedback)
            
            # Identify improvement areas
            improvement_areas = await self._identify_improvement_areas(feedback, text_analysis)
            
            # Calculate feedback confidence
            confidence = await self._calculate_feedback_confidence(feedback, text_analysis)
            
            # Extract specific suggestions
            suggestions = await self._extract_suggestions(feedback)
            
            # Analyze feedback context
            context_analysis = await self._analyze_feedback_context(feedback, voice_fingerprint)
            
            processed_feedback = {
                'feedback_id': f"fb_{feedback.timestamp.strftime('%Y%m%d_%H%M%S')}",
                'feedback_type': feedback.feedback_type.value,
                'original_score': feedback.score,
                'adjusted_score': await self._adjust_score_based_on_analysis(
                    feedback.score, text_analysis, sentiment_analysis
                ),
                'text_analysis': text_analysis,
                'sentiment_analysis': sentiment_analysis,
                'improvement_areas': improvement_areas,
                'suggestions': suggestions,
                'context_analysis': context_analysis,
                'confidence': confidence,
                'priority_weight': self.feedback_weights.get(feedback.feedback_type, 0.5),
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.debug(f"Feedback processed: {feedback.feedback_type.value}, confidence: {confidence:.2f}")
            return processed_feedback
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            return await self._create_fallback_processing(feedback)
    
    async def aggregate_feedback(
        self,
        feedback_list: List[VoiceFeedback],
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate multiple feedback items.
        
        Args:
            feedback_list: List of feedback items
            time_window: Optional time window filter
            
        Returns:
            Aggregated feedback analysis
        """
        try:
            # Filter by time window if provided
            if time_window:
                start_time, end_time = time_window
                feedback_list = [
                    fb for fb in feedback_list 
                    if start_time <= fb.timestamp <= end_time
                ]
            
            if not feedback_list:
                return {'error': 'No feedback items to aggregate'}
            
            # Group feedback by type
            feedback_by_type = defaultdict(list)
            for feedback in feedback_list:
                feedback_by_type[feedback.feedback_type].append(feedback)
            
            # Aggregate scores by type
            type_aggregations = {}
            for feedback_type, type_feedback in feedback_by_type.items():
                type_aggregations[feedback_type.value] = await self._aggregate_feedback_type(
                    type_feedback
                )
            
            # Calculate overall aggregation
            overall_aggregation = await self._calculate_overall_aggregation(
                feedback_list, type_aggregations
            )
            
            # Identify trends
            trends = await self._identify_feedback_trends(feedback_list)
            
            # Extract common themes
            common_themes = await self._extract_common_themes(feedback_list)
            
            aggregated_feedback = {
                'aggregation_id': f"agg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'time_window': {
                    'start': time_window[0].isoformat() if time_window else None,
                    'end': time_window[1].isoformat() if time_window else None
                },
                'total_feedback_items': len(feedback_list),
                'feedback_by_type': {
                    ftype.value: len(items) for ftype, items in feedback_by_type.items()
                },
                'type_aggregations': type_aggregations,
                'overall_aggregation': overall_aggregation,
                'trends': trends,
                'common_themes': common_themes,
                'aggregation_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Feedback aggregated: {len(feedback_list)} items processed")
            return aggregated_feedback
            
        except Exception as e:
            logger.error(f"Feedback aggregation failed: {str(e)}")
            return {'error': f'Aggregation failed: {str(e)}'}
    
    async def identify_improvement_areas(
        self,
        feedback_analysis: Dict[str, Any],
        voice_fingerprint: VoiceFingerprint
    ) -> List[Dict[str, Any]]:
        """
        Identify areas for voice improvement.
        
        Args:
            feedback_analysis: Processed feedback analysis
            voice_fingerprint: Current voice fingerprint
            
        Returns:
            List of improvement recommendations
        """
        improvement_recommendations = []
        
        try:
            # Extract improvement areas from analysis
            if 'improvement_areas' in feedback_analysis:
                for area in feedback_analysis['improvement_areas']:
                    recommendation = await self._create_improvement_recommendation(
                        area, feedback_analysis, voice_fingerprint
                    )
                    improvement_recommendations.append(recommendation)
            
            # Add type-specific recommendations
            if 'type_aggregations' in feedback_analysis:
                for feedback_type, aggregation in feedback_analysis['type_aggregations'].items():
                    if aggregation.get('average_score', 1.0) < 0.7:  # Below threshold
                        type_recommendation = await self._create_type_improvement_recommendation(
                            feedback_type, aggregation, voice_fingerprint
                        )
                        improvement_recommendations.append(type_recommendation)
            
            # Sort by priority
            improvement_recommendations.sort(
                key=lambda x: x.get('priority_score', 0.5), reverse=True
            )
            
            logger.debug(f"Identified {len(improvement_recommendations)} improvement areas")
            return improvement_recommendations
            
        except Exception as e:
            logger.error(f"Improvement area identification failed: {str(e)}")
            return []
    
    # Private helper methods
    
    async def _analyze_feedback_text(self, feedback: VoiceFeedback) -> Dict[str, Any]:
        """Analyze feedback text for patterns and indicators."""
        if not feedback.notes:
            return {'has_text': False}
        
        text = feedback.notes.lower()
        feedback_type = feedback.feedback_type
        
        analysis = {
            'has_text': True,
            'text_length': len(feedback.notes),
            'positive_indicators': [],
            'negative_indicators': [],
            'specific_mentions': []
        }
        
        # Check for type-specific patterns
        if feedback_type in self.improvement_patterns:
            patterns = self.improvement_patterns[feedback_type]
            
            # Check positive indicators
            for pattern in patterns['positive_indicators']:
                matches = re.findall(pattern, text)
                analysis['positive_indicators'].extend(matches)
            
            # Check negative indicators
            for pattern in patterns['negative_indicators']:
                matches = re.findall(pattern, text)
                analysis['negative_indicators'].extend(matches)
        
        # Extract specific mentions
        analysis['specific_mentions'] = await self._extract_specific_mentions(text)
        
        return analysis
    
    async def _analyze_sentiment(self, feedback: VoiceFeedback) -> Dict[str, Any]:
        """Analyze sentiment of feedback."""
        sentiment_analysis = {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence': 0.5
        }
        
        if not feedback.notes:
            # Use numeric score as sentiment indicator
            sentiment_analysis['sentiment_score'] = (feedback.score - 0.5) * 2  # Scale to -1 to 1
            sentiment_analysis['sentiment_label'] = await self._score_to_sentiment_label(feedback.score)
            sentiment_analysis['confidence'] = 0.7
            return sentiment_analysis
        
        text = feedback.notes.lower()
        sentiment_scores = {}
        
        # Check sentiment patterns
        for sentiment, patterns in self.sentiment_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text))
                score += matches
            sentiment_scores[sentiment] = score
        
        # Calculate overall sentiment
        if sentiment_scores:
            total_matches = sum(sentiment_scores.values())
            if total_matches > 0:
                weighted_score = (
                    sentiment_scores.get('very_positive', 0) * 1.0 +
                    sentiment_scores.get('positive', 0) * 0.5 +
                    sentiment_scores.get('neutral', 0) * 0.0 +
                    sentiment_scores.get('negative', 0) * -0.5 +
                    sentiment_scores.get('very_negative', 0) * -1.0
                ) / total_matches
                
                sentiment_analysis['sentiment_score'] = weighted_score
                sentiment_analysis['sentiment_label'] = await self._score_to_sentiment_label(
                    (weighted_score + 1) / 2  # Convert to 0-1 scale
                )
                sentiment_analysis['confidence'] = min(1.0, total_matches / 5)  # Max confidence at 5+ matches
        
        return sentiment_analysis
    
    async def _identify_improvement_areas(
        self,
        feedback: VoiceFeedback,
        text_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify specific improvement areas from feedback."""
        improvement_areas = []
        
        # Get areas from feedback type patterns
        if feedback.feedback_type in self.improvement_patterns:
            base_areas = self.improvement_patterns[feedback.feedback_type]['improvement_areas']
            
            # Add areas if negative indicators found or low score
            if (text_analysis.get('negative_indicators') or 
                feedback.score < 0.6):
                improvement_areas.extend(base_areas)
        
        # Add areas based on specific mentions
        specific_mentions = text_analysis.get('specific_mentions', [])
        for mention in specific_mentions:
            if 'clarity' in mention:
                improvement_areas.append('language_clarity')
            elif 'tone' in mention:
                improvement_areas.append('tone_adjustment')
            elif 'style' in mention:
                improvement_areas.append('style_refinement')
        
        return list(set(improvement_areas))  # Remove duplicates
    
    async def _calculate_feedback_confidence(
        self,
        feedback: VoiceFeedback,
        text_analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence in feedback analysis."""
        confidence_factors = []
        
        # Source confidence
        source_confidence = {
            'user': 0.9,
            'system': 0.7,
            'automatic': 0.5
        }
        confidence_factors.append(source_confidence.get(feedback.source, 0.6))
        
        # Text analysis confidence
        if text_analysis.get('has_text'):
            text_length = text_analysis.get('text_length', 0)
            text_confidence = min(1.0, text_length / 100)  # Max confidence at 100+ chars
            confidence_factors.append(text_confidence)
        else:
            confidence_factors.append(0.5)
        
        # Score consistency confidence
        if feedback.notes:
            # Check if text sentiment matches numeric score
            positive_indicators = len(text_analysis.get('positive_indicators', []))
            negative_indicators = len(text_analysis.get('negative_indicators', []))
            
            if feedback.score > 0.6 and positive_indicators > negative_indicators:
                confidence_factors.append(0.9)
            elif feedback.score < 0.4 and negative_indicators > positive_indicators:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    async def _extract_suggestions(self, feedback: VoiceFeedback) -> List[str]:
        """Extract specific suggestions from feedback."""
        suggestions = []
        
        if feedback.suggestions:
            suggestions.extend(feedback.suggestions)
        
        if feedback.notes:
            # Look for suggestion patterns in notes
            suggestion_patterns = [
                r'should\s+([^.!?]+)',
                r'could\s+([^.!?]+)',
                r'try\s+([^.!?]+)',
                r'consider\s+([^.!?]+)',
                r'recommend\s+([^.!?]+)'
            ]
            
            for pattern in suggestion_patterns:
                matches = re.findall(pattern, feedback.notes, re.IGNORECASE)
                suggestions.extend([match.strip() for match in matches])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    async def _analyze_feedback_context(
        self,
        feedback: VoiceFeedback,
        voice_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze feedback context."""
        context_analysis = {
            'text_sample_length': len(feedback.text_sample),
            'feedback_recency': (datetime.now() - feedback.timestamp).total_seconds() / 3600,  # hours
            'context_type': feedback.context.get('context_type', 'unknown'),
            'voice_fingerprint_age': (datetime.now() - voice_fingerprint.updated_at).total_seconds() / 3600
        }
        
        return context_analysis
    
    async def _adjust_score_based_on_analysis(
        self,
        original_score: float,
        text_analysis: Dict[str, Any],
        sentiment_analysis: Dict[str, Any]
    ) -> float:
        """Adjust feedback score based on text and sentiment analysis."""
        adjusted_score = original_score
        
        # Adjust based on sentiment if text available
        if text_analysis.get('has_text') and sentiment_analysis.get('confidence', 0) > 0.6:
            sentiment_score = sentiment_analysis.get('sentiment_score', 0)
            # Blend original score with sentiment score
            adjusted_score = (original_score * 0.7) + ((sentiment_score + 1) / 2 * 0.3)
        
        return max(0.0, min(1.0, adjusted_score))
    
    async def _extract_specific_mentions(self, text: str) -> List[str]:
        """Extract specific mentions from feedback text."""
        mentions = []
        
        # Look for specific aspect mentions
        aspect_patterns = [
            r'\b(clarity|clear|unclear)\b',
            r'\b(tone|tonal|mood)\b',
            r'\b(style|styling|stylistic)\b',
            r'\b(authentic|authenticity|genuine)\b',
            r'\b(appropriate|appropriateness|suitable)\b',
            r'\b(engaging|engagement|interesting)\b'
        ]
        
        for pattern in aspect_patterns:
            matches = re.findall(pattern, text)
            mentions.extend(matches)
        
        return list(set(mentions))
    
    async def _score_to_sentiment_label(self, score: float) -> str:
        """Convert numeric score to sentiment label."""
        if score >= 0.8:
            return 'very_positive'
        elif score >= 0.6:
            return 'positive'
        elif score >= 0.4:
            return 'neutral'
        elif score >= 0.2:
            return 'negative'
        else:
            return 'very_negative'
    
    async def _aggregate_feedback_type(self, type_feedback: List[VoiceFeedback]) -> Dict[str, Any]:
        """Aggregate feedback for a specific type."""
        scores = [fb.score for fb in type_feedback]
        
        return {
            'count': len(type_feedback),
            'average_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_trend': await self._calculate_score_trend(type_feedback),
            'recent_feedback': len([fb for fb in type_feedback 
                                 if (datetime.now() - fb.timestamp).days <= 7])
        }
    
    async def _calculate_overall_aggregation(
        self,
        feedback_list: List[VoiceFeedback],
        type_aggregations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall aggregation across all feedback."""
        all_scores = [fb.score for fb in feedback_list]
        
        # Calculate weighted average based on feedback type weights
        weighted_sum = 0
        weight_sum = 0
        
        for feedback in feedback_list:
            weight = self.feedback_weights.get(feedback.feedback_type, 0.5)
            weighted_sum += feedback.score * weight
            weight_sum += weight
        
        weighted_average = weighted_sum / weight_sum if weight_sum > 0 else 0.5
        
        return {
            'total_feedback': len(feedback_list),
            'simple_average': sum(all_scores) / len(all_scores),
            'weighted_average': weighted_average,
            'score_distribution': await self._calculate_score_distribution(all_scores),
            'feedback_sources': Counter([fb.source for fb in feedback_list]),
            'time_span_days': (max(fb.timestamp for fb in feedback_list) - 
                             min(fb.timestamp for fb in feedback_list)).days
        }
    
    async def _identify_feedback_trends(self, feedback_list: List[VoiceFeedback]) -> Dict[str, Any]:
        """Identify trends in feedback over time."""
        # Sort by timestamp
        sorted_feedback = sorted(feedback_list, key=lambda x: x.timestamp)
        
        # Calculate trend for each feedback type
        trends = {}
        feedback_by_type = defaultdict(list)
        
        for feedback in sorted_feedback:
            feedback_by_type[feedback.feedback_type.value].append(feedback)
        
        for feedback_type, type_feedback in feedback_by_type.items():
            if len(type_feedback) >= 3:  # Need at least 3 points for trend
                scores = [fb.score for fb in type_feedback]
                trend = await self._calculate_score_trend(type_feedback)
                trends[feedback_type] = {
                    'direction': 'improving' if trend > 0.05 else 'declining' if trend < -0.05 else 'stable',
                    'trend_value': trend,
                    'sample_size': len(type_feedback)
                }
        
        return trends
    
    async def _extract_common_themes(self, feedback_list: List[VoiceFeedback]) -> List[Dict[str, Any]]:
        """Extract common themes from feedback."""
        themes = []
        
        # Collect all feedback notes
        all_notes = [fb.notes for fb in feedback_list if fb.notes]
        
        if not all_notes:
            return themes
        
        # Simple theme extraction based on common words/phrases
        all_text = ' '.join(all_notes).lower()
        
        # Common improvement themes
        theme_patterns = {
            'clarity_issues': [r'\b(unclear|confusing|hard to understand)\b'],
            'tone_concerns': [r'\b(tone|mood|feeling|emotional)\b'],
            'authenticity_feedback': [r'\b(authentic|genuine|real|natural)\b'],
            'style_comments': [r'\b(style|writing|flow|structure)\b']
        }
        
        for theme_name, patterns in theme_patterns.items():
            mentions = 0
            for pattern in patterns:
                mentions += len(re.findall(pattern, all_text))
            
            if mentions >= 2:  # At least 2 mentions
                themes.append({
                    'theme': theme_name,
                    'mentions': mentions,
                    'frequency': mentions / len(feedback_list)
                })
        
        return sorted(themes, key=lambda x: x['mentions'], reverse=True)
    
    async def _calculate_score_trend(self, feedback_list: List[VoiceFeedback]) -> float:
        """Calculate score trend over time."""
        if len(feedback_list) < 2:
            return 0.0
        
        # Simple linear trend calculation
        sorted_feedback = sorted(feedback_list, key=lambda x: x.timestamp)
        scores = [fb.score for fb in sorted_feedback]
        
        # Calculate slope
        n = len(scores)
        x_values = list(range(n))
        
        x_mean = sum(x_values) / n
        y_mean = sum(scores) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, scores))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    async def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of scores."""
        distribution = {
            'excellent': 0,    # 0.8-1.0
            'good': 0,         # 0.6-0.8
            'average': 0,      # 0.4-0.6
            'poor': 0,         # 0.2-0.4
            'very_poor': 0     # 0.0-0.2
        }
        
        for score in scores:
            if score >= 0.8:
                distribution['excellent'] += 1
            elif score >= 0.6:
                distribution['good'] += 1
            elif score >= 0.4:
                distribution['average'] += 1
            elif score >= 0.2:
                distribution['poor'] += 1
            else:
                distribution['very_poor'] += 1
        
        return distribution
    
    async def _create_improvement_recommendation(
        self,
        area: str,
        feedback_analysis: Dict[str, Any],
        voice_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Create improvement recommendation for specific area."""
        return {
            'area': area,
            'priority_score': 0.8,  # TODO: Calculate based on feedback frequency/severity
            'description': f"Improve {area.replace('_', ' ')}",
            'suggested_actions': [f"Focus on {area.replace('_', ' ')} enhancement"],
            'confidence': feedback_analysis.get('confidence', 0.5)
        }
    
    async def _create_type_improvement_recommendation(
        self,
        feedback_type: str,
        aggregation: Dict[str, Any],
        voice_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Create improvement recommendation for feedback type."""
        return {
            'area': f"{feedback_type}_improvement",
            'priority_score': 1.0 - aggregation.get('average_score', 0.5),
            'description': f"Improve {feedback_type} based on feedback",
            'suggested_actions': [f"Focus on {feedback_type} enhancement"],
            'confidence': 0.8
        }
    
    async def _create_fallback_processing(self, feedback: VoiceFeedback) -> Dict[str, Any]:
        """Create fallback processing result on error."""
        return {
            'feedback_id': f"fb_fallback_{feedback.timestamp.strftime('%Y%m%d_%H%M%S')}",
            'feedback_type': feedback.feedback_type.value,
            'original_score': feedback.score,
            'adjusted_score': feedback.score,
            'improvement_areas': ['general_improvement'],
            'confidence': 0.3,
            'error': True,
            'processing_timestamp': datetime.now().isoformat()
        }
