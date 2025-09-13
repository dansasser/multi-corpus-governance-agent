"""Advanced intent analysis system for sophisticated user intent understanding."""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass

from .protocols import (
    IntentAnalysisProtocol,
    AssistantRequest,
    AssistantContext
)

logger = logging.getLogger(__name__)


@dataclass
class EntityMatch:
    """Represents an extracted entity with metadata."""
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    context: str


@dataclass
class IntentPrediction:
    """Represents an intent prediction with confidence and evidence."""
    intent_type: str
    confidence: float
    evidence: List[str]
    sub_intents: List[str]
    complexity_score: float
    urgency_score: float


class AdvancedIntentAnalyzer(IntentAnalysisProtocol):
    """
    Advanced intent analysis system that provides sophisticated
    intent classification, entity extraction, and context-aware
    intent resolution capabilities.
    
    This analyzer specializes in:
    - Multi-layered intent classification with confidence scoring
    - Named entity recognition and relationship mapping
    - Context-aware intent disambiguation
    - Sub-intent detection for complex requests
    - Temporal and spatial entity extraction
    """
    
    def __init__(self):
        """Initialize advanced intent analyzer."""
        
        # Enhanced intent classification patterns
        self.intent_patterns = {
            'question': {
                'patterns': [
                    r'\b(what|how|why|when|where|who|which)\b',
                    r'\?',
                    r'\b(explain|tell me|describe|define)\b',
                    r'\b(is it|are there|can you|do you know)\b'
                ],
                'weight': 1.0,
                'sub_intents': ['factual_question', 'explanation_request', 'clarification']
            },
            'request': {
                'patterns': [
                    r'\b(please|can you|could you|would you|help me)\b',
                    r'\b(assist|support|guide|show me)\b',
                    r'\b(need help|looking for|want to)\b'
                ],
                'weight': 1.2,
                'sub_intents': ['assistance_request', 'guidance_request', 'support_request']
            },
            'command': {
                'patterns': [
                    r'\b(create|write|generate|make|build|draft)\b',
                    r'\b(send|post|publish|share|upload)\b',
                    r'\b(delete|remove|cancel|stop)\b',
                    r'\b(schedule|remind|set up|configure)\b'
                ],
                'weight': 1.5,
                'sub_intents': ['creation_command', 'action_command', 'configuration_command']
            },
            'information': {
                'patterns': [
                    r'\b(tell me about|information on|details about)\b',
                    r'\b(research|find out|look up|search for)\b',
                    r'\b(summary|overview|breakdown)\b'
                ],
                'weight': 1.1,
                'sub_intents': ['research_request', 'summary_request', 'detail_request']
            },
            'task_automation': {
                'patterns': [
                    r'\b(automate|schedule|set up|configure)\b',
                    r'\b(email|message|post|tweet|update)\b',
                    r'\b(reminder|notification|alert)\b',
                    r'\b(workflow|process|routine)\b'
                ],
                'weight': 1.4,
                'sub_intents': ['email_automation', 'social_automation', 'scheduling_automation']
            },
            'creative': {
                'patterns': [
                    r'\b(brainstorm|ideas|creative|imagine|story)\b',
                    r'\b(design|concept|innovative|original)\b',
                    r'\b(write creatively|compose|craft)\b'
                ],
                'weight': 1.3,
                'sub_intents': ['brainstorming', 'creative_writing', 'design_thinking']
            },
            'analysis': {
                'patterns': [
                    r'\b(analyze|compare|evaluate|assess|review)\b',
                    r'\b(pros and cons|advantages|disadvantages)\b',
                    r'\b(data|statistics|metrics|performance)\b',
                    r'\b(trend|pattern|insight)\b'
                ],
                'weight': 1.2,
                'sub_intents': ['data_analysis', 'comparative_analysis', 'performance_analysis']
            },
            'conversation': {
                'patterns': [
                    r'\b(chat|talk|discuss|conversation)\b',
                    r'\b(opinion|thoughts|feelings|perspective)\b',
                    r'\b(agree|disagree|think|believe)\b'
                ],
                'weight': 0.8,
                'sub_intents': ['casual_chat', 'opinion_sharing', 'discussion']
            }
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'person': {
                'patterns': [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                    r'\b(Mr|Mrs|Ms|Dr|Prof)\.? [A-Z][a-z]+\b',  # Title Name
                    r'\b@[a-zA-Z0-9_]+\b'  # @username
                ],
                'confidence_base': 0.7
            },
            'organization': {
                'patterns': [
                    r'\b[A-Z][a-z]+ (Inc|LLC|Corp|Company|Ltd)\b',
                    r'\b(Google|Microsoft|Apple|Amazon|Facebook|Twitter|LinkedIn)\b',
                    r'\b[A-Z]{2,5}\b'  # Acronyms
                ],
                'confidence_base': 0.8
            },
            'platform': {
                'patterns': [
                    r'\b(email|gmail|outlook|yahoo)\b',
                    r'\b(twitter|facebook|instagram|linkedin|tiktok)\b',
                    r'\b(slack|discord|teams|zoom)\b',
                    r'\b(blog|website|youtube|medium)\b'
                ],
                'confidence_base': 0.9
            },
            'time': {
                'patterns': [
                    r'\b(today|tomorrow|yesterday|tonight)\b',
                    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                    r'\b(morning|afternoon|evening|night)\b',
                    r'\b\d{1,2}:\d{2}\s?(am|pm)?\b',
                    r'\b(next week|last week|this week)\b',
                    r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b'
                ],
                'confidence_base': 0.8
            },
            'location': {
                'patterns': [
                    r'\b[A-Z][a-z]+,\s?[A-Z]{2}\b',  # City, State
                    r'\b(office|home|work|meeting room)\b',
                    r'\b(here|there|everywhere|anywhere)\b'
                ],
                'confidence_base': 0.6
            },
            'task_type': {
                'patterns': [
                    r'\b(email|message|post|tweet|article|blog)\b',
                    r'\b(meeting|appointment|call|presentation)\b',
                    r'\b(document|report|proposal|contract)\b',
                    r'\b(reminder|notification|alert|follow-up)\b'
                ],
                'confidence_base': 0.8
            },
            'emotion': {
                'patterns': [
                    r'\b(happy|sad|excited|frustrated|angry|pleased)\b',
                    r'\b(love|hate|like|dislike|enjoy|prefer)\b',
                    r'\b(worried|concerned|confident|nervous)\b'
                ],
                'confidence_base': 0.7
            },
            'urgency': {
                'patterns': [
                    r'\b(urgent|asap|immediately|right away|quickly)\b',
                    r'\b(emergency|critical|important|priority)\b',
                    r'\b(deadline|due date|time sensitive)\b'
                ],
                'confidence_base': 0.9
            }
        }
        
        # Context-aware intent modifiers
        self.context_modifiers = {
            'conversation_history': {
                'follow_up_indicators': ['also', 'additionally', 'furthermore', 'and', 'plus'],
                'clarification_indicators': ['actually', 'i mean', 'to clarify', 'what i meant'],
                'correction_indicators': ['no', 'not that', 'instead', 'rather', 'correction']
            },
            'temporal_context': {
                'immediate': ['now', 'right now', 'immediately', 'asap'],
                'scheduled': ['later', 'tomorrow', 'next week', 'schedule'],
                'ongoing': ['continue', 'keep', 'maintain', 'ongoing']
            },
            'complexity_indicators': {
                'simple': ['quick', 'simple', 'brief', 'short', 'basic', 'easy'],
                'moderate': ['detailed', 'thorough', 'complete', 'comprehensive'],
                'complex': ['in-depth', 'advanced', 'sophisticated', 'elaborate', 'extensive']
            }
        }
        
        # Intent relationship mappings
        self.intent_relationships = {
            'question': ['information', 'analysis'],
            'request': ['task_automation', 'creative'],
            'command': ['task_automation', 'information'],
            'creative': ['question', 'analysis'],
            'analysis': ['information', 'question']
        }
        
        # Analysis statistics
        self.analysis_stats = {
            'total_analyses': 0,
            'intent_distribution': defaultdict(int),
            'entity_distribution': defaultdict(int),
            'confidence_scores': [],
            'complexity_scores': [],
            'context_usage': defaultdict(int)
        }
    
    async def analyze_intent(
        self,
        user_input: str,
        context: Optional[AssistantContext] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent with advanced classification.
        
        Args:
            user_input: User's input text
            context: Optional context information
            
        Returns:
            Comprehensive intent analysis
        """
        try:
            # Preprocess input
            processed_input = await self._preprocess_input(user_input)
            
            # Extract entities
            entities = await self.extract_entities(user_input)
            
            # Classify primary intent
            intent_predictions = await self._classify_intents(processed_input, entities)
            
            # Apply context-aware modifications
            if context:
                intent_predictions = await self._apply_context_modifications(
                    intent_predictions, context, processed_input
                )
            
            # Determine primary intent
            primary_intent = await self._determine_primary_intent(intent_predictions)
            
            # Calculate complexity and urgency
            complexity_score = await self._calculate_complexity(processed_input, entities)
            urgency_score = await self._calculate_urgency(processed_input, entities)
            
            # Generate response requirements
            response_requirements = await self._generate_response_requirements(
                primary_intent, entities, complexity_score, urgency_score, context
            )
            
            # Create comprehensive analysis result
            analysis_result = {
                'primary_intent': primary_intent.intent_type,
                'confidence': primary_intent.confidence,
                'sub_intents': primary_intent.sub_intents,
                'evidence': primary_intent.evidence,
                'all_intent_predictions': [
                    {
                        'intent': pred.intent_type,
                        'confidence': pred.confidence,
                        'evidence': pred.evidence
                    }
                    for pred in intent_predictions
                ],
                'entities': [
                    {
                        'type': entity.entity_type,
                        'value': entity.value,
                        'confidence': entity.confidence,
                        'position': (entity.start_pos, entity.end_pos)
                    }
                    for entity in entities
                ],
                'complexity_score': complexity_score,
                'urgency_score': urgency_score,
                'response_requirements': response_requirements,
                'context_factors': await self._analyze_context_factors(context, processed_input),
                'analysis_metadata': {
                    'processed_input_length': len(processed_input),
                    'entity_count': len(entities),
                    'intent_candidates': len(intent_predictions),
                    'analysis_timestamp': datetime.now().isoformat()
                }
            }
            
            # Update statistics
            await self._update_analysis_statistics(analysis_result)
            
            logger.debug(f"Intent analysis completed: {primary_intent.intent_type} (confidence: {primary_intent.confidence:.3f})")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return {
                'primary_intent': 'question',
                'confidence': 0.3,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    async def extract_entities(self, text: str) -> List[EntityMatch]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        try:
            for entity_type, config in self.entity_patterns.items():
                for pattern in config['patterns']:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Calculate confidence based on pattern specificity and context
                        base_confidence = config['confidence_base']
                        context_boost = await self._calculate_entity_context_boost(
                            match.group(), entity_type, text, match.start(), match.end()
                        )
                        
                        confidence = min(1.0, base_confidence + context_boost)
                        
                        # Extract surrounding context
                        context_start = max(0, match.start() - 20)
                        context_end = min(len(text), match.end() + 20)
                        context = text[context_start:context_end]
                        
                        entity = EntityMatch(
                            entity_type=entity_type,
                            value=match.group().strip(),
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=context
                        )
                        
                        entities.append(entity)
            
            # Remove duplicate entities (same value, overlapping positions)
            entities = await self._deduplicate_entities(entities)
            
            # Sort by confidence and position
            entities.sort(key=lambda x: (-x.confidence, x.start_pos))
            
            logger.debug(f"Extracted {len(entities)} entities")
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return []
    
    async def resolve_intent_context(
        self,
        intent: str,
        entities: List[Dict[str, Any]],
        context: AssistantContext
    ) -> Dict[str, Any]:
        """
        Resolve intent using context information.
        
        Args:
            intent: Primary intent
            entities: Extracted entities
            context: Assistant context
            
        Returns:
            Context-resolved intent information
        """
        try:
            resolution = {
                'resolved_intent': intent,
                'context_modifications': [],
                'disambiguation': None,
                'confidence_adjustments': [],
                'related_intents': []
            }
            
            # Check for conversation history context
            if context.conversation_history:
                history_context = await self._analyze_conversation_context(
                    intent, context.conversation_history
                )
                resolution['context_modifications'].extend(history_context)
            
            # Check for platform-specific context
            if context.platform:
                platform_context = await self._analyze_platform_context(intent, context.platform)
                resolution['context_modifications'].extend(platform_context)
            
            # Check for mode-specific context
            mode_context = await self._analyze_mode_context(intent, context.mode)
            resolution['context_modifications'].extend(mode_context)
            
            # Resolve ambiguous intents
            if intent in self.intent_relationships:
                related_intents = self.intent_relationships[intent]
                entity_support = await self._calculate_entity_support_for_intents(
                    entities, related_intents
                )
                
                if entity_support:
                    best_supported = max(entity_support.items(), key=lambda x: x[1])
                    if best_supported[1] > 0.3:  # Threshold for disambiguation
                        resolution['disambiguation'] = {
                            'original_intent': intent,
                            'suggested_intent': best_supported[0],
                            'support_score': best_supported[1],
                            'reason': 'Entity support suggests more specific intent'
                        }
            
            # Calculate related intents
            resolution['related_intents'] = self.intent_relationships.get(intent, [])
            
            logger.debug(f"Intent context resolved for: {intent}")
            return resolution
            
        except Exception as e:
            logger.error(f"Intent context resolution failed: {str(e)}")
            return {
                'resolved_intent': intent,
                'error': str(e)
            }
    
    # Private helper methods
    
    async def _preprocess_input(self, user_input: str) -> str:
        """Preprocess user input for analysis."""
        # Convert to lowercase for pattern matching
        processed = user_input.lower()
        
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        # Expand contractions for better pattern matching
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "wouldn't": "would not",
            "shouldn't": "should not",
            "it's": "it is",
            "you're": "you are",
            "we're": "we are",
            "i'm": "i am",
            "they're": "they are"
        }
        
        for contraction, expansion in contractions.items():
            processed = processed.replace(contraction, expansion)
        
        return processed
    
    async def _classify_intents(
        self,
        processed_input: str,
        entities: List[EntityMatch]
    ) -> List[IntentPrediction]:
        """Classify intents with confidence scoring."""
        intent_scores = {}
        
        # Score each intent type
        for intent_type, config in self.intent_patterns.items():
            score = 0.0
            evidence = []
            
            # Pattern matching score
            for pattern in config['patterns']:
                matches = re.findall(pattern, processed_input)
                if matches:
                    pattern_score = len(matches) * config['weight']
                    score += pattern_score
                    evidence.extend([f"Pattern match: {match}" for match in matches])
            
            # Entity support score
            entity_boost = await self._calculate_entity_boost_for_intent(
                intent_type, entities
            )
            score += entity_boost
            
            if entity_boost > 0:
                evidence.append(f"Entity support: {entity_boost:.2f}")
            
            # Normalize score
            normalized_score = min(1.0, score / 10.0)  # Normalize to 0-1 range
            
            if normalized_score > 0.1:  # Only include intents with meaningful scores
                intent_scores[intent_type] = {
                    'score': normalized_score,
                    'evidence': evidence
                }
        
        # Create intent predictions
        predictions = []
        for intent_type, data in intent_scores.items():
            # Determine sub-intents
            sub_intents = await self._determine_sub_intents(
                intent_type, processed_input, entities
            )
            
            prediction = IntentPrediction(
                intent_type=intent_type,
                confidence=data['score'],
                evidence=data['evidence'],
                sub_intents=sub_intents,
                complexity_score=0.0,  # Will be calculated separately
                urgency_score=0.0      # Will be calculated separately
            )
            predictions.append(prediction)
        
        # Sort by confidence
        predictions.sort(key=lambda x: x.confidence, reverse=True)
        
        return predictions
    
    async def _apply_context_modifications(
        self,
        predictions: List[IntentPrediction],
        context: AssistantContext,
        processed_input: str
    ) -> List[IntentPrediction]:
        """Apply context-aware modifications to intent predictions."""
        
        # Check for conversation flow indicators
        for modifier_type, indicators in self.context_modifiers['conversation_history'].items():
            if any(indicator in processed_input for indicator in indicators):
                # Boost related intents based on conversation history
                if context.conversation_history:
                    last_intent = await self._get_last_conversation_intent(context.conversation_history)
                    if last_intent:
                        await self._boost_related_intents(predictions, last_intent, 0.2)
        
        # Apply temporal context modifications
        for temporal_type, indicators in self.context_modifiers['temporal_context'].items():
            if any(indicator in processed_input for indicator in indicators):
                if temporal_type == 'immediate':
                    await self._boost_intent_type(predictions, 'command', 0.3)
                elif temporal_type == 'scheduled':
                    await self._boost_intent_type(predictions, 'task_automation', 0.3)
        
        # Apply mode-specific boosts
        if context.mode:
            mode_boosts = {
                'creative': ['creative', 'question'],
                'analytical': ['analysis', 'information'],
                'professional': ['task_automation', 'command'],
                'personal': ['conversation', 'request']
            }
            
            mode_name = context.mode.value.lower()
            if mode_name in mode_boosts:
                for intent_type in mode_boosts[mode_name]:
                    await self._boost_intent_type(predictions, intent_type, 0.15)
        
        return predictions
    
    async def _determine_primary_intent(
        self,
        predictions: List[IntentPrediction]
    ) -> IntentPrediction:
        """Determine the primary intent from predictions."""
        if not predictions:
            # Default intent
            return IntentPrediction(
                intent_type='question',
                confidence=0.3,
                evidence=['Default fallback'],
                sub_intents=[],
                complexity_score=0.5,
                urgency_score=0.0
            )
        
        # Return highest confidence prediction
        primary = predictions[0]
        
        # Boost confidence if there's strong evidence
        if len(primary.evidence) >= 3:
            primary.confidence = min(1.0, primary.confidence + 0.1)
        
        return primary
    
    async def _calculate_complexity(
        self,
        processed_input: str,
        entities: List[EntityMatch]
    ) -> float:
        """Calculate complexity score for the request."""
        complexity_score = 0.5  # Base complexity
        
        # Length-based complexity
        input_length = len(processed_input.split())
        if input_length > 20:
            complexity_score += 0.2
        elif input_length > 50:
            complexity_score += 0.4
        
        # Entity-based complexity
        entity_count = len(entities)
        if entity_count > 3:
            complexity_score += 0.2
        elif entity_count > 6:
            complexity_score += 0.3
        
        # Pattern-based complexity
        for complexity_level, indicators in self.context_modifiers['complexity_indicators'].items():
            if any(indicator in processed_input for indicator in indicators):
                if complexity_level == 'simple':
                    complexity_score -= 0.2
                elif complexity_level == 'complex':
                    complexity_score += 0.3
        
        return max(0.0, min(1.0, complexity_score))
    
    async def _calculate_urgency(
        self,
        processed_input: str,
        entities: List[EntityMatch]
    ) -> float:
        """Calculate urgency score for the request."""
        urgency_score = 0.0
        
        # Check for urgency entities
        urgency_entities = [e for e in entities if e.entity_type == 'urgency']
        if urgency_entities:
            urgency_score += 0.5 + (len(urgency_entities) * 0.2)
        
        # Check for temporal urgency indicators
        immediate_indicators = self.context_modifiers['temporal_context']['immediate']
        if any(indicator in processed_input for indicator in immediate_indicators):
            urgency_score += 0.4
        
        # Check for emotional urgency
        urgent_emotions = ['frustrated', 'angry', 'worried', 'concerned']
        if any(emotion in processed_input for emotion in urgent_emotions):
            urgency_score += 0.3
        
        return max(0.0, min(1.0, urgency_score))
    
    async def _generate_response_requirements(
        self,
        primary_intent: IntentPrediction,
        entities: List[EntityMatch],
        complexity_score: float,
        urgency_score: float,
        context: Optional[AssistantContext]
    ) -> Dict[str, Any]:
        """Generate response requirements based on analysis."""
        requirements = {
            'requires_corpus_access': True,
            'corpus_types_needed': ['personal'],
            'response_style': 'conversational',
            'estimated_length': 'medium',
            'requires_creativity': False,
            'requires_analysis': False,
            'requires_task_automation': False,
            'priority_level': 'normal',
            'processing_complexity': 'medium'
        }
        
        # Intent-specific requirements
        intent_requirements = {
            'creative': {
                'requires_creativity': True,
                'corpus_types_needed': ['personal', 'social'],
                'estimated_length': 'long',
                'processing_complexity': 'high'
            },
            'analysis': {
                'requires_analysis': True,
                'corpus_types_needed': ['personal', 'published'],
                'estimated_length': 'long',
                'processing_complexity': 'high'
            },
            'task_automation': {
                'requires_task_automation': True,
                'corpus_types_needed': ['personal', 'social', 'published'],
                'processing_complexity': 'high'
            },
            'command': {
                'requires_task_automation': True,
                'response_style': 'concise',
                'estimated_length': 'short'
            },
            'question': {
                'corpus_types_needed': ['personal', 'published'],
                'response_style': 'detailed'
            }
        }
        
        if primary_intent.intent_type in intent_requirements:
            requirements.update(intent_requirements[primary_intent.intent_type])
        
        # Complexity-based adjustments
        if complexity_score > 0.7:
            requirements['processing_complexity'] = 'high'
            requirements['estimated_length'] = 'long'
        elif complexity_score < 0.3:
            requirements['processing_complexity'] = 'low'
            requirements['estimated_length'] = 'short'
        
        # Urgency-based adjustments
        if urgency_score > 0.6:
            requirements['priority_level'] = 'high'
            requirements['response_style'] = 'concise'
        elif urgency_score > 0.3:
            requirements['priority_level'] = 'medium'
        
        # Entity-based adjustments
        platform_entities = [e for e in entities if e.entity_type == 'platform']
        if platform_entities:
            requirements['requires_task_automation'] = True
            requirements['corpus_types_needed'] = ['personal', 'social', 'published']
        
        return requirements
    
    async def _analyze_context_factors(
        self,
        context: Optional[AssistantContext],
        processed_input: str
    ) -> Dict[str, Any]:
        """Analyze context factors that influence intent."""
        factors = {
            'conversation_continuity': False,
            'platform_influence': None,
            'mode_alignment': True,
            'temporal_context': None,
            'user_preference_match': False
        }
        
        if not context:
            return factors
        
        # Check conversation continuity
        if context.conversation_history:
            factors['conversation_continuity'] = len(context.conversation_history) > 0
        
        # Check platform influence
        if context.platform:
            factors['platform_influence'] = context.platform
        
        # Check temporal context
        time_entities = ['today', 'tomorrow', 'now', 'later', 'schedule']
        if any(entity in processed_input for entity in time_entities):
            factors['temporal_context'] = 'time_sensitive'
        
        # Check user preference alignment
        if context.user_preferences and 'successful_patterns' in context.user_preferences:
            # This would check against successful patterns
            factors['user_preference_match'] = True  # Simplified
        
        return factors
    
    async def _calculate_entity_context_boost(
        self,
        entity_value: str,
        entity_type: str,
        full_text: str,
        start_pos: int,
        end_pos: int
    ) -> float:
        """Calculate confidence boost based on entity context."""
        boost = 0.0
        
        # Context window around entity
        context_start = max(0, start_pos - 10)
        context_end = min(len(full_text), end_pos + 10)
        context = full_text[context_start:context_end].lower()
        
        # Type-specific context boosts
        if entity_type == 'person':
            if any(word in context for word in ['email', 'message', 'call', 'meet']):
                boost += 0.2
        elif entity_type == 'platform':
            if any(word in context for word in ['post', 'send', 'publish', 'share']):
                boost += 0.2
        elif entity_type == 'time':
            if any(word in context for word in ['schedule', 'remind', 'meeting', 'deadline']):
                boost += 0.2
        
        return boost
    
    async def _deduplicate_entities(self, entities: List[EntityMatch]) -> List[EntityMatch]:
        """Remove duplicate entities with overlapping positions."""
        if not entities:
            return entities
        
        # Sort by position
        entities.sort(key=lambda x: (x.start_pos, x.end_pos))
        
        deduplicated = []
        for entity in entities:
            # Check for overlap with existing entities
            overlaps = False
            for existing in deduplicated:
                if (entity.start_pos < existing.end_pos and 
                    entity.end_pos > existing.start_pos and
                    entity.entity_type == existing.entity_type):
                    # Keep the one with higher confidence
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated
    
    async def _calculate_entity_boost_for_intent(
        self,
        intent_type: str,
        entities: List[EntityMatch]
    ) -> float:
        """Calculate entity support boost for specific intent."""
        boost = 0.0
        
        # Intent-entity relationships
        intent_entity_boosts = {
            'task_automation': {
                'platform': 0.3,
                'time': 0.2,
                'task_type': 0.4
            },
            'creative': {
                'emotion': 0.2,
                'person': 0.1
            },
            'analysis': {
                'organization': 0.2,
                'time': 0.1
            },
            'command': {
                'platform': 0.2,
                'task_type': 0.3,
                'urgency': 0.2
            }
        }
        
        if intent_type in intent_entity_boosts:
            for entity in entities:
                if entity.entity_type in intent_entity_boosts[intent_type]:
                    entity_boost = intent_entity_boosts[intent_type][entity.entity_type]
                    boost += entity_boost * entity.confidence
        
        return boost
    
    async def _determine_sub_intents(
        self,
        intent_type: str,
        processed_input: str,
        entities: List[EntityMatch]
    ) -> List[str]:
        """Determine sub-intents for the primary intent."""
        if intent_type not in self.intent_patterns:
            return []
        
        available_sub_intents = self.intent_patterns[intent_type]['sub_intents']
        detected_sub_intents = []
        
        # Simple sub-intent detection based on keywords and entities
        sub_intent_keywords = {
            'email_automation': ['email', 'send', 'draft', 'compose'],
            'social_automation': ['post', 'tweet', 'share', 'publish'],
            'scheduling_automation': ['schedule', 'remind', 'calendar', 'meeting'],
            'creative_writing': ['write', 'story', 'compose', 'craft'],
            'data_analysis': ['analyze', 'data', 'statistics', 'metrics'],
            'research_request': ['research', 'find', 'look up', 'search']
        }
        
        for sub_intent in available_sub_intents:
            if sub_intent in sub_intent_keywords:
                keywords = sub_intent_keywords[sub_intent]
                if any(keyword in processed_input for keyword in keywords):
                    detected_sub_intents.append(sub_intent)
        
        # Entity-based sub-intent detection
        platform_entities = [e for e in entities if e.entity_type == 'platform']
        if platform_entities and intent_type == 'task_automation':
            for entity in platform_entities:
                if entity.value in ['email', 'gmail']:
                    detected_sub_intents.append('email_automation')
                elif entity.value in ['twitter', 'facebook', 'instagram']:
                    detected_sub_intents.append('social_automation')
        
        return list(set(detected_sub_intents))  # Remove duplicates
    
    async def _get_last_conversation_intent(self, history: List[Dict[str, Any]]) -> Optional[str]:
        """Get the intent from the last conversation turn."""
        if not history:
            return None
        
        last_turn = history[-1]
        return last_turn.get('intent')
    
    async def _boost_related_intents(
        self,
        predictions: List[IntentPrediction],
        related_intent: str,
        boost_amount: float
    ) -> None:
        """Boost intents related to a given intent."""
        related_intents = self.intent_relationships.get(related_intent, [])
        
        for prediction in predictions:
            if prediction.intent_type in related_intents:
                prediction.confidence = min(1.0, prediction.confidence + boost_amount)
                prediction.evidence.append(f"Context boost from related intent: {related_intent}")
    
    async def _boost_intent_type(
        self,
        predictions: List[IntentPrediction],
        intent_type: str,
        boost_amount: float
    ) -> None:
        """Boost a specific intent type."""
        for prediction in predictions:
            if prediction.intent_type == intent_type:
                prediction.confidence = min(1.0, prediction.confidence + boost_amount)
                prediction.evidence.append(f"Context boost for {intent_type}")
    
    async def _analyze_conversation_context(
        self,
        intent: str,
        history: List[Dict[str, Any]]
    ) -> List[str]:
        """Analyze conversation history for context modifications."""
        modifications = []
        
        if not history:
            return modifications
        
        # Check for follow-up patterns
        recent_intents = [turn.get('intent') for turn in history[-3:] if turn.get('intent')]
        if recent_intents:
            if intent in recent_intents:
                modifications.append('follow_up_conversation')
            
            # Check for intent progression patterns
            if len(recent_intents) >= 2:
                if recent_intents[-1] == 'question' and intent == 'command':
                    modifications.append('question_to_action_progression')
        
        return modifications
    
    async def _analyze_platform_context(self, intent: str, platform: str) -> List[str]:
        """Analyze platform-specific context modifications."""
        modifications = []
        
        platform_intent_boosts = {
            'email': ['task_automation', 'command'],
            'slack': ['conversation', 'request'],
            'twitter': ['creative', 'task_automation'],
            'linkedin': ['task_automation', 'analysis']
        }
        
        if platform in platform_intent_boosts:
            if intent in platform_intent_boosts[platform]:
                modifications.append(f'platform_boost_{platform}')
        
        return modifications
    
    async def _analyze_mode_context(self, intent: str, mode) -> List[str]:
        """Analyze mode-specific context modifications."""
        modifications = []
        
        mode_name = mode.value.lower() if hasattr(mode, 'value') else str(mode).lower()
        
        mode_intent_alignment = {
            'creative': ['creative', 'question'],
            'analytical': ['analysis', 'information'],
            'professional': ['task_automation', 'command'],
            'personal': ['conversation', 'request']
        }
        
        if mode_name in mode_intent_alignment:
            if intent in mode_intent_alignment[mode_name]:
                modifications.append(f'mode_alignment_{mode_name}')
        
        return modifications
    
    async def _calculate_entity_support_for_intents(
        self,
        entities: List[EntityMatch],
        intent_candidates: List[str]
    ) -> Dict[str, float]:
        """Calculate entity support scores for intent candidates."""
        support_scores = {}
        
        for intent in intent_candidates:
            score = await self._calculate_entity_boost_for_intent(intent, entities)
            if score > 0:
                support_scores[intent] = score
        
        return support_scores
    
    async def _update_analysis_statistics(self, analysis_result: Dict[str, Any]) -> None:
        """Update analysis statistics."""
        self.analysis_stats['total_analyses'] += 1
        
        # Update intent distribution
        primary_intent = analysis_result.get('primary_intent', 'unknown')
        self.analysis_stats['intent_distribution'][primary_intent] += 1
        
        # Update entity distribution
        entities = analysis_result.get('entities', [])
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            self.analysis_stats['entity_distribution'][entity_type] += 1
        
        # Update confidence scores
        confidence = analysis_result.get('confidence', 0.0)
        self.analysis_stats['confidence_scores'].append(confidence)
        if len(self.analysis_stats['confidence_scores']) > 1000:
            self.analysis_stats['confidence_scores'] = self.analysis_stats['confidence_scores'][-1000:]
        
        # Update complexity scores
        complexity = analysis_result.get('complexity_score', 0.0)
        self.analysis_stats['complexity_scores'].append(complexity)
        if len(self.analysis_stats['complexity_scores']) > 1000:
            self.analysis_stats['complexity_scores'] = self.analysis_stats['complexity_scores'][-1000:]
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get intent analysis statistics."""
        avg_confidence = (
            sum(self.analysis_stats['confidence_scores']) / len(self.analysis_stats['confidence_scores'])
            if self.analysis_stats['confidence_scores'] else 0.0
        )
        
        avg_complexity = (
            sum(self.analysis_stats['complexity_scores']) / len(self.analysis_stats['complexity_scores'])
            if self.analysis_stats['complexity_scores'] else 0.0
        )
        
        return {
            'statistics': {
                'total_analyses': self.analysis_stats['total_analyses'],
                'average_confidence': avg_confidence,
                'average_complexity': avg_complexity,
                'intent_distribution': dict(self.analysis_stats['intent_distribution']),
                'entity_distribution': dict(self.analysis_stats['entity_distribution'])
            },
            'supported_intents': list(self.intent_patterns.keys()),
            'supported_entities': list(self.entity_patterns.keys()),
            'intent_relationships': self.intent_relationships
        }
