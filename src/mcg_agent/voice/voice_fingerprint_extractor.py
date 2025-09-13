"""
Voice Fingerprint Extractor

Analyzes user's communication patterns across all corpora to extract
unique voice fingerprints for authentic replication.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, Field

from mcg_agent.search.tools import personal_search, social_search, published_search
from mcg_agent.search.connectors import PersonalSearchFilters, SocialSearchFilters, PublishedSearchFilters
from mcg_agent.security.personal_data_encryption import PersonalDataEncryption
from mcg_agent.security.personal_voice_audit_trail import PersonalVoiceAuditTrail
from mcg_agent.utils.exceptions import VoiceFingerprintError
from mcg_agent.utils.audit import AuditLogger


@dataclass
class VoicePattern:
    """Individual voice pattern with metadata"""
    pattern: str
    pattern_type: str
    frequency: int
    corpus_source: str
    confidence_score: float
    context_examples: List[str]


class VoiceFingerprint(BaseModel):
    """Complete voice fingerprint for a user"""
    user_id: str = Field(description="User identifier")
    
    # Core voice characteristics
    personal_voice_patterns: List[VoicePattern] = Field(description="Patterns from personal corpus")
    social_voice_patterns: List[VoicePattern] = Field(description="Patterns from social corpus")
    published_voice_patterns: List[VoicePattern] = Field(description="Patterns from published corpus")
    
    # Voice characteristics
    preferred_sentence_structures: List[str] = Field(description="Preferred sentence patterns")
    common_transitions: List[str] = Field(description="Common transition phrases")
    characteristic_expressions: List[str] = Field(description="Unique expressions")
    
    # Tone and style analysis
    tone_distribution: Dict[str, float] = Field(description="Distribution of tones used")
    formality_levels: Dict[str, float] = Field(description="Formality level preferences")
    audience_adaptations: Dict[str, Dict[str, Any]] = Field(description="How voice changes by audience")
    
    # Linguistic patterns
    vocabulary_preferences: Dict[str, int] = Field(description="Preferred vocabulary")
    punctuation_patterns: Dict[str, float] = Field(description="Punctuation usage patterns")
    sentence_length_distribution: Dict[str, float] = Field(description="Sentence length preferences")
    
    # Metadata
    extraction_date: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(description="Overall fingerprint confidence")
    corpus_coverage: Dict[str, int] = Field(description="Amount of data from each corpus")
    
    class Config:
        arbitrary_types_allowed = True


class VoiceFingerprintExtractor:
    """
    Extract comprehensive voice fingerprints from user's communication data.
    
    Analyzes patterns across personal, social, and published corpora to create
    a unique voice fingerprint that can be used for authentic replication.
    """
    
    def __init__(self):
        self.encryption = PersonalDataEncryption()
        self.audit_trail = PersonalVoiceAuditTrail()
        self.audit_logger = AuditLogger()
        
        # Pattern recognition configurations
        self.min_pattern_frequency = 2
        self.max_patterns_per_type = 20
        self.confidence_threshold = 0.6
        
    async def extract_voice_fingerprint(
        self, 
        user_id: str,
        corpus_access_permissions: List[str] = None
    ) -> VoiceFingerprint:
        """
        Extract comprehensive voice fingerprint for a user.
        
        Args:
            user_id: User identifier
            corpus_access_permissions: List of corpora the user has access to
            
        Returns:
            VoiceFingerprint: Complete voice fingerprint
        """
        try:
            if not corpus_access_permissions:
                corpus_access_permissions = ["personal", "social", "published"]
                
            self.audit_logger.log_info(f"Starting voice fingerprint extraction for user {user_id}")
            
            # Collect communication data from all accessible corpora
            communication_data = await self._collect_communication_data(
                user_id, 
                corpus_access_permissions
            )
            
            # Extract voice patterns from each corpus
            voice_patterns = await self._extract_voice_patterns(communication_data)
            
            # Analyze voice characteristics
            voice_characteristics = self._analyze_voice_characteristics(communication_data)
            
            # Analyze linguistic patterns
            linguistic_patterns = self._analyze_linguistic_patterns(communication_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_fingerprint_confidence(
                communication_data, 
                voice_patterns
            )
            
            # Create voice fingerprint
            fingerprint = VoiceFingerprint(
                user_id=user_id,
                personal_voice_patterns=voice_patterns.get("personal", []),
                social_voice_patterns=voice_patterns.get("social", []),
                published_voice_patterns=voice_patterns.get("published", []),
                preferred_sentence_structures=voice_characteristics["sentence_structures"],
                common_transitions=voice_characteristics["transitions"],
                characteristic_expressions=voice_characteristics["expressions"],
                tone_distribution=voice_characteristics["tone_distribution"],
                formality_levels=voice_characteristics["formality_levels"],
                audience_adaptations=voice_characteristics["audience_adaptations"],
                vocabulary_preferences=linguistic_patterns["vocabulary"],
                punctuation_patterns=linguistic_patterns["punctuation"],
                sentence_length_distribution=linguistic_patterns["sentence_lengths"],
                confidence_score=confidence_score,
                corpus_coverage={
                    corpus: len(data) for corpus, data in communication_data.items()
                }
            )
            
            # Encrypt and store fingerprint
            await self._store_encrypted_fingerprint(fingerprint)
            
            # Log extraction for audit
            self.audit_trail.log_voice_fingerprint_extraction(
                user_id=user_id,
                corpora_analyzed=list(communication_data.keys()),
                patterns_extracted=sum(len(patterns) for patterns in voice_patterns.values()),
                confidence_score=confidence_score
            )
            
            self.audit_logger.log_info(
                f"Voice fingerprint extraction completed for user {user_id} "
                f"with confidence {confidence_score:.2f}"
            )
            
            return fingerprint
            
        except Exception as e:
            raise VoiceFingerprintError(f"Failed to extract voice fingerprint: {str(e)}")
            
    async def _collect_communication_data(
        self, 
        user_id: str, 
        corpus_permissions: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Collect communication data from all accessible corpora"""
        communication_data = {}
        
        try:
            # Collect from personal corpus (ChatGPT exports, etc.)
            if "personal" in corpus_permissions:
                personal_data = await self._collect_personal_data(user_id)
                communication_data["personal"] = personal_data
                
            # Collect from social corpus (social media posts, etc.)
            if "social" in corpus_permissions:
                social_data = await self._collect_social_data(user_id)
                communication_data["social"] = social_data
                
            # Collect from published corpus (blog posts, articles, etc.)
            if "published" in corpus_permissions:
                published_data = await self._collect_published_data(user_id)
                communication_data["published"] = published_data
                
        except Exception as e:
            self.audit_logger.log_error(f"Communication data collection failed: {str(e)}")
            
        return communication_data
        
    async def _collect_personal_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect data from personal corpus"""
        try:
            # Use broad search to get representative personal communication
            search_queries = [
                "conversation",
                "question",
                "response", 
                "discussion",
                "explanation"
            ]
            
            personal_data = []
            
            for query in search_queries:
                try:
                    results = await personal_search(
                        None,  # RunContext would be provided in real implementation
                        query,
                        PersonalSearchFilters(),
                        limit=20
                    )
                    
                    for result in results.get("results", []):
                        personal_data.append({
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "source": "personal",
                            "query": query
                        })
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Personal data collection failed for query '{query}': {str(e)}")
                    
            return personal_data[:50]  # Limit to 50 samples
            
        except Exception as e:
            self.audit_logger.log_error(f"Personal data collection failed: {str(e)}")
            return []
            
    async def _collect_social_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect data from social corpus"""
        try:
            # Use broad search to get representative social communication
            search_queries = [
                "post",
                "comment",
                "share",
                "update",
                "message"
            ]
            
            social_data = []
            
            for query in search_queries:
                try:
                    results = await social_search(
                        None,  # RunContext would be provided in real implementation
                        query,
                        SocialSearchFilters(),
                        limit=20
                    )
                    
                    for result in results.get("results", []):
                        social_data.append({
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "source": "social",
                            "query": query
                        })
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Social data collection failed for query '{query}': {str(e)}")
                    
            return social_data[:50]  # Limit to 50 samples
            
        except Exception as e:
            self.audit_logger.log_error(f"Social data collection failed: {str(e)}")
            return []
            
    async def _collect_published_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect data from published corpus"""
        try:
            # Use broad search to get representative published content
            search_queries = [
                "article",
                "blog",
                "post",
                "writing",
                "content"
            ]
            
            published_data = []
            
            for query in search_queries:
                try:
                    results = await published_search(
                        None,  # RunContext would be provided in real implementation
                        query,
                        PublishedSearchFilters(),
                        limit=20
                    )
                    
                    for result in results.get("results", []):
                        published_data.append({
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "source": "published",
                            "query": query
                        })
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Published data collection failed for query '{query}': {str(e)}")
                    
            return published_data[:50]  # Limit to 50 samples
            
        except Exception as e:
            self.audit_logger.log_error(f"Published data collection failed: {str(e)}")
            return []
            
    async def _extract_voice_patterns(
        self, 
        communication_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[VoicePattern]]:
        """Extract voice patterns from communication data"""
        voice_patterns = {}
        
        for corpus_type, data in communication_data.items():
            try:
                patterns = []
                
                # Extract different types of patterns
                conversational_patterns = self._extract_conversational_patterns(data, corpus_type)
                patterns.extend(conversational_patterns)
                
                transition_patterns = self._extract_transition_patterns(data, corpus_type)
                patterns.extend(transition_patterns)
                
                expression_patterns = self._extract_expression_patterns(data, corpus_type)
                patterns.extend(expression_patterns)
                
                # Filter and rank patterns
                filtered_patterns = self._filter_and_rank_patterns(patterns)
                
                voice_patterns[corpus_type] = filtered_patterns
                
            except Exception as e:
                self.audit_logger.log_error(f"Pattern extraction failed for {corpus_type}: {str(e)}")
                voice_patterns[corpus_type] = []
                
        return voice_patterns
        
    def _extract_conversational_patterns(
        self, 
        data: List[Dict[str, Any]], 
        corpus_type: str
    ) -> List[VoicePattern]:
        """Extract conversational patterns"""
        patterns = []
        pattern_counts = Counter()
        pattern_examples = defaultdict(list)
        
        try:
            # Define conversational pattern templates
            if corpus_type == "personal":
                pattern_templates = [
                    r"I think .*?[.!?]",
                    r"In my experience .*?[.!?]",
                    r"What I've found .*?[.!?]",
                    r"The way I see it .*?[.!?]",
                    r"From my perspective .*?[.!?]",
                    r"I believe .*?[.!?]",
                    r"It seems to me .*?[.!?]",
                    r"I've noticed .*?[.!?]"
                ]
            elif corpus_type == "social":
                pattern_templates = [
                    r"Thanks .*?[.!?]",
                    r"Great .*?[.!?]",
                    r"Love .*?[.!?]",
                    r"Excited .*?[.!?]",
                    r"Really .*?[.!?]",
                    r"Appreciate .*?[.!?]",
                    r"Looking forward .*?[.!?]",
                    r"Happy to .*?[.!?]"
                ]
            else:  # published
                pattern_templates = [
                    r"It's important to .*?[.!?]",
                    r"Furthermore .*?[.!?]",
                    r"However .*?[.!?]",
                    r"In conclusion .*?[.!?]",
                    r"This demonstrates .*?[.!?]",
                    r"The key insight .*?[.!?]",
                    r"Research shows .*?[.!?]",
                    r"Evidence suggests .*?[.!?]"
                ]
                
            # Extract patterns from data
            for item in data:
                content = item.get("content", "")
                
                for template in pattern_templates:
                    matches = re.findall(template, content, re.IGNORECASE)
                    
                    for match in matches:
                        if 10 < len(match) < 100:  # Reasonable length
                            normalized_match = match.lower().strip()
                            pattern_counts[normalized_match] += 1
                            pattern_examples[normalized_match].append(content[:200])
                            
            # Convert to VoicePattern objects
            for pattern, count in pattern_counts.items():
                if count >= self.min_pattern_frequency:
                    confidence = min(count / 10.0, 1.0)  # Scale confidence
                    
                    voice_pattern = VoicePattern(
                        pattern=pattern,
                        pattern_type="conversational",
                        frequency=count,
                        corpus_source=corpus_type,
                        confidence_score=confidence,
                        context_examples=pattern_examples[pattern][:3]
                    )
                    
                    patterns.append(voice_pattern)
                    
        except Exception as e:
            self.audit_logger.log_error(f"Conversational pattern extraction failed: {str(e)}")
            
        return patterns
        
    def _extract_transition_patterns(
        self, 
        data: List[Dict[str, Any]], 
        corpus_type: str
    ) -> List[VoicePattern]:
        """Extract transition and connector patterns"""
        patterns = []
        transition_counts = Counter()
        
        try:
            # Common transition patterns
            transitions = [
                "however", "furthermore", "moreover", "additionally", "meanwhile",
                "therefore", "consequently", "as a result", "in contrast",
                "on the other hand", "similarly", "likewise", "in addition",
                "for example", "for instance", "specifically", "in particular",
                "in conclusion", "to summarize", "overall", "ultimately"
            ]
            
            for item in data:
                content = item.get("content", "").lower()
                
                for transition in transitions:
                    count = content.count(transition)
                    if count > 0:
                        transition_counts[transition] += count
                        
            # Convert to VoicePattern objects
            for transition, count in transition_counts.items():
                if count >= self.min_pattern_frequency:
                    confidence = min(count / 5.0, 1.0)
                    
                    voice_pattern = VoicePattern(
                        pattern=transition,
                        pattern_type="transition",
                        frequency=count,
                        corpus_source=corpus_type,
                        confidence_score=confidence,
                        context_examples=[]
                    )
                    
                    patterns.append(voice_pattern)
                    
        except Exception as e:
            self.audit_logger.log_error(f"Transition pattern extraction failed: {str(e)}")
            
        return patterns
        
    def _extract_expression_patterns(
        self, 
        data: List[Dict[str, Any]], 
        corpus_type: str
    ) -> List[VoicePattern]:
        """Extract characteristic expressions and phrases"""
        patterns = []
        expression_counts = Counter()
        
        try:
            # Extract phrases of 2-5 words that appear frequently
            for item in data:
                content = item.get("content", "")
                words = re.findall(r'\b\w+\b', content.lower())
                
                # Generate n-grams (2-5 words)
                for n in range(2, 6):
                    for i in range(len(words) - n + 1):
                        phrase = " ".join(words[i:i+n])
                        
                        # Filter out common phrases
                        if not self._is_common_phrase(phrase):
                            expression_counts[phrase] += 1
                            
            # Convert to VoicePattern objects
            for expression, count in expression_counts.items():
                if count >= self.min_pattern_frequency:
                    confidence = min(count / 3.0, 1.0)
                    
                    voice_pattern = VoicePattern(
                        pattern=expression,
                        pattern_type="expression",
                        frequency=count,
                        corpus_source=corpus_type,
                        confidence_score=confidence,
                        context_examples=[]
                    )
                    
                    patterns.append(voice_pattern)
                    
        except Exception as e:
            self.audit_logger.log_error(f"Expression pattern extraction failed: {str(e)}")
            
        return patterns
        
    def _is_common_phrase(self, phrase: str) -> bool:
        """Check if phrase is too common to be characteristic"""
        common_phrases = {
            "of the", "in the", "to the", "for the", "and the", "on the",
            "at the", "by the", "with the", "from the", "that the", "this is",
            "it is", "there is", "there are", "you can", "i can", "we can",
            "will be", "would be", "could be", "should be", "have been",
            "has been", "had been", "going to", "want to", "need to"
        }
        
        return phrase in common_phrases or len(phrase.split()) < 2
        
    def _filter_and_rank_patterns(self, patterns: List[VoicePattern]) -> List[VoicePattern]:
        """Filter and rank patterns by confidence and frequency"""
        try:
            # Filter by confidence threshold
            filtered = [p for p in patterns if p.confidence_score >= self.confidence_threshold]
            
            # Sort by confidence and frequency
            sorted_patterns = sorted(
                filtered, 
                key=lambda p: (p.confidence_score, p.frequency), 
                reverse=True
            )
            
            # Group by pattern type and limit
            pattern_groups = defaultdict(list)
            for pattern in sorted_patterns:
                pattern_groups[pattern.pattern_type].append(pattern)
                
            # Limit each type
            final_patterns = []
            for pattern_type, type_patterns in pattern_groups.items():
                final_patterns.extend(type_patterns[:self.max_patterns_per_type])
                
            return final_patterns
            
        except Exception as e:
            self.audit_logger.log_error(f"Pattern filtering failed: {str(e)}")
            return patterns[:50]  # Fallback limit
            
    def _analyze_voice_characteristics(
        self, 
        communication_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze overall voice characteristics"""
        try:
            characteristics = {
                "sentence_structures": [],
                "transitions": [],
                "expressions": [],
                "tone_distribution": {},
                "formality_levels": {},
                "audience_adaptations": {}
            }
            
            all_content = []
            for corpus_data in communication_data.values():
                for item in corpus_data:
                    all_content.append(item.get("content", ""))
                    
            # Analyze sentence structures
            characteristics["sentence_structures"] = self._analyze_sentence_structures(all_content)
            
            # Analyze tone distribution
            characteristics["tone_distribution"] = self._analyze_tone_distribution(communication_data)
            
            # Analyze formality levels
            characteristics["formality_levels"] = self._analyze_formality_levels(communication_data)
            
            # Analyze audience adaptations
            characteristics["audience_adaptations"] = self._analyze_audience_adaptations(communication_data)
            
            return characteristics
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice characteristics analysis failed: {str(e)}")
            return {
                "sentence_structures": [],
                "transitions": [],
                "expressions": [],
                "tone_distribution": {"neutral": 1.0},
                "formality_levels": {"moderate": 1.0},
                "audience_adaptations": {}
            }
            
    def _analyze_sentence_structures(self, content_list: List[str]) -> List[str]:
        """Analyze preferred sentence structures"""
        structures = []
        
        try:
            structure_patterns = Counter()
            
            for content in content_list:
                sentences = re.split(r'[.!?]+', content)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 10:
                        # Simplified structure analysis
                        words = sentence.split()
                        length_category = "short" if len(words) < 10 else "medium" if len(words) < 20 else "long"
                        
                        # Check for question structure
                        if sentence.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who')):
                            structure_patterns[f"question_{length_category}"] += 1
                        # Check for conditional structure
                        elif 'if' in sentence.lower():
                            structure_patterns[f"conditional_{length_category}"] += 1
                        # Check for compound structure
                        elif any(conj in sentence.lower() for conj in ['and', 'but', 'or', 'however']):
                            structure_patterns[f"compound_{length_category}"] += 1
                        else:
                            structure_patterns[f"simple_{length_category}"] += 1
                            
            # Get top structures
            structures = [struct for struct, count in structure_patterns.most_common(10)]
            
        except Exception as e:
            self.audit_logger.log_error(f"Sentence structure analysis failed: {str(e)}")
            
        return structures
        
    def _analyze_tone_distribution(self, communication_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
        """Analyze tone distribution across corpora"""
        tone_counts = Counter()
        total_items = 0
        
        try:
            for corpus_type, data in communication_data.items():
                for item in data:
                    content = item.get("content", "").lower()
                    total_items += 1
                    
                    # Simple tone detection
                    if any(word in content for word in ['excited', 'amazing', 'fantastic', 'love']):
                        tone_counts['enthusiastic'] += 1
                    elif any(word in content for word in ['however', 'therefore', 'furthermore']):
                        tone_counts['professional'] += 1
                    elif any(word in content for word in ['thanks', 'appreciate', 'grateful']):
                        tone_counts['appreciative'] += 1
                    elif any(word in content for word in ['really', 'pretty', 'kind of']):
                        tone_counts['casual'] += 1
                    else:
                        tone_counts['neutral'] += 1
                        
            # Convert to distribution
            if total_items > 0:
                tone_distribution = {tone: count / total_items for tone, count in tone_counts.items()}
            else:
                tone_distribution = {'neutral': 1.0}
                
        except Exception as e:
            self.audit_logger.log_error(f"Tone distribution analysis failed: {str(e)}")
            tone_distribution = {'neutral': 1.0}
            
        return tone_distribution
        
    def _analyze_formality_levels(self, communication_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
        """Analyze formality level preferences"""
        formality_counts = Counter()
        total_items = 0
        
        try:
            for corpus_type, data in communication_data.items():
                for item in data:
                    content = item.get("content", "")
                    total_items += 1
                    
                    # Simple formality detection
                    contractions = len(re.findall(r"\w+'t|\w+'re|\w+'ll|\w+'ve|\w+'d", content))
                    formal_words = len(re.findall(r'\b(furthermore|however|therefore|consequently|nevertheless)\b', content, re.IGNORECASE))
                    casual_words = len(re.findall(r'\b(really|pretty|kind of|sort of|basically)\b', content, re.IGNORECASE))
                    
                    if formal_words > casual_words and contractions == 0:
                        formality_counts['formal'] += 1
                    elif casual_words > formal_words or contractions > 2:
                        formality_counts['casual'] += 1
                    else:
                        formality_counts['moderate'] += 1
                        
            # Convert to distribution
            if total_items > 0:
                formality_distribution = {level: count / total_items for level, count in formality_counts.items()}
            else:
                formality_distribution = {'moderate': 1.0}
                
        except Exception as e:
            self.audit_logger.log_error(f"Formality analysis failed: {str(e)}")
            formality_distribution = {'moderate': 1.0}
            
        return formality_distribution
        
    def _analyze_audience_adaptations(self, communication_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """Analyze how voice adapts to different audiences/contexts"""
        adaptations = {}
        
        try:
            for corpus_type, data in communication_data.items():
                if not data:
                    continue
                    
                # Analyze characteristics for this corpus type
                avg_sentence_length = 0
                total_sentences = 0
                tone_indicators = Counter()
                
                for item in data:
                    content = item.get("content", "")
                    sentences = re.split(r'[.!?]+', content)
                    
                    for sentence in sentences:
                        if sentence.strip():
                            words = sentence.split()
                            avg_sentence_length += len(words)
                            total_sentences += 1
                            
                            # Count tone indicators
                            sentence_lower = sentence.lower()
                            if any(word in sentence_lower for word in ['excited', 'love', 'amazing']):
                                tone_indicators['enthusiastic'] += 1
                            elif any(word in sentence_lower for word in ['however', 'therefore']):
                                tone_indicators['professional'] += 1
                                
                if total_sentences > 0:
                    avg_sentence_length /= total_sentences
                    
                adaptations[corpus_type] = {
                    "avg_sentence_length": avg_sentence_length,
                    "dominant_tone": tone_indicators.most_common(1)[0][0] if tone_indicators else "neutral",
                    "sample_size": len(data)
                }
                
        except Exception as e:
            self.audit_logger.log_error(f"Audience adaptation analysis failed: {str(e)}")
            
        return adaptations
        
    def _analyze_linguistic_patterns(
        self, 
        communication_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze linguistic patterns like vocabulary and punctuation"""
        try:
            all_content = []
            for corpus_data in communication_data.values():
                for item in corpus_data:
                    all_content.append(item.get("content", ""))
                    
            # Analyze vocabulary preferences
            vocabulary = self._analyze_vocabulary_preferences(all_content)
            
            # Analyze punctuation patterns
            punctuation = self._analyze_punctuation_patterns(all_content)
            
            # Analyze sentence length distribution
            sentence_lengths = self._analyze_sentence_length_distribution(all_content)
            
            return {
                "vocabulary": vocabulary,
                "punctuation": punctuation,
                "sentence_lengths": sentence_lengths
            }
            
        except Exception as e:
            self.audit_logger.log_error(f"Linguistic pattern analysis failed: {str(e)}")
            return {
                "vocabulary": {},
                "punctuation": {},
                "sentence_lengths": {}
            }
            
    def _analyze_vocabulary_preferences(self, content_list: List[str]) -> Dict[str, int]:
        """Analyze vocabulary preferences"""
        word_counts = Counter()
        
        try:
            for content in content_list:
                words = re.findall(r'\b\w+\b', content.lower())
                
                # Filter out common words
                filtered_words = [
                    word for word in words 
                    if len(word) > 3 and word not in {
                        'that', 'this', 'with', 'have', 'will', 'been', 'from', 
                        'they', 'know', 'want', 'been', 'good', 'much', 'some'
                    }
                ]
                
                word_counts.update(filtered_words)
                
            # Return top vocabulary preferences
            return dict(word_counts.most_common(50))
            
        except Exception as e:
            self.audit_logger.log_error(f"Vocabulary analysis failed: {str(e)}")
            return {}
            
    def _analyze_punctuation_patterns(self, content_list: List[str]) -> Dict[str, float]:
        """Analyze punctuation usage patterns"""
        punctuation_counts = Counter()
        total_chars = 0
        
        try:
            for content in content_list:
                total_chars += len(content)
                
                # Count different punctuation marks
                punctuation_counts['.'] += content.count('.')
                punctuation_counts['!'] += content.count('!')
                punctuation_counts['?'] += content.count('?')
                punctuation_counts[','] += content.count(',')
                punctuation_counts[';'] += content.count(';')
                punctuation_counts[':'] += content.count(':')
                punctuation_counts['-'] += content.count('-')
                punctuation_counts['--'] += content.count('--')
                
            # Convert to ratios
            if total_chars > 0:
                punctuation_patterns = {
                    punct: count / total_chars for punct, count in punctuation_counts.items()
                }
            else:
                punctuation_patterns = {}
                
        except Exception as e:
            self.audit_logger.log_error(f"Punctuation analysis failed: {str(e)}")
            punctuation_patterns = {}
            
        return punctuation_patterns
        
    def _analyze_sentence_length_distribution(self, content_list: List[str]) -> Dict[str, float]:
        """Analyze sentence length preferences"""
        length_counts = Counter()
        total_sentences = 0
        
        try:
            for content in content_list:
                sentences = re.split(r'[.!?]+', content)
                
                for sentence in sentences:
                    if sentence.strip():
                        word_count = len(sentence.split())
                        total_sentences += 1
                        
                        if word_count < 8:
                            length_counts['short'] += 1
                        elif word_count < 15:
                            length_counts['medium'] += 1
                        elif word_count < 25:
                            length_counts['long'] += 1
                        else:
                            length_counts['very_long'] += 1
                            
            # Convert to distribution
            if total_sentences > 0:
                length_distribution = {
                    length: count / total_sentences for length, count in length_counts.items()
                }
            else:
                length_distribution = {'medium': 1.0}
                
        except Exception as e:
            self.audit_logger.log_error(f"Sentence length analysis failed: {str(e)}")
            length_distribution = {'medium': 1.0}
            
        return length_distribution
        
    def _calculate_fingerprint_confidence(
        self, 
        communication_data: Dict[str, List[Dict[str, Any]]], 
        voice_patterns: Dict[str, List[VoicePattern]]
    ) -> float:
        """Calculate overall confidence score for the fingerprint"""
        try:
            # Data coverage score
            total_items = sum(len(data) for data in communication_data.values())
            coverage_score = min(total_items / 50.0, 1.0)  # Target 50 items
            
            # Pattern quality score
            total_patterns = sum(len(patterns) for patterns in voice_patterns.values())
            pattern_score = min(total_patterns / 30.0, 1.0)  # Target 30 patterns
            
            # Corpus diversity score
            corpus_count = len([data for data in communication_data.values() if data])
            diversity_score = corpus_count / 3.0  # 3 corpora available
            
            # Average pattern confidence
            all_patterns = []
            for patterns in voice_patterns.values():
                all_patterns.extend(patterns)
                
            if all_patterns:
                avg_pattern_confidence = sum(p.confidence_score for p in all_patterns) / len(all_patterns)
            else:
                avg_pattern_confidence = 0.5
                
            # Overall confidence
            confidence = (
                coverage_score * 0.3 +
                pattern_score * 0.3 +
                diversity_score * 0.2 +
                avg_pattern_confidence * 0.2
            )
            
            return min(confidence, 1.0)
            
        except Exception as e:
            self.audit_logger.log_error(f"Confidence calculation failed: {str(e)}")
            return 0.5
            
    async def _store_encrypted_fingerprint(self, fingerprint: VoiceFingerprint) -> None:
        """Store encrypted voice fingerprint"""
        try:
            # Convert fingerprint to JSON
            fingerprint_data = fingerprint.dict()
            fingerprint_json = json.dumps(fingerprint_data, default=str)
            
            # Encrypt the fingerprint
            encrypted_data = self.encryption.encrypt_personal_data(
                fingerprint_json,
                f"voice_fingerprint_{fingerprint.user_id}"
            )
            
            # Store encrypted fingerprint (implementation would depend on storage backend)
            # For now, just log that it would be stored
            self.audit_logger.log_info(f"Voice fingerprint encrypted and ready for storage for user {fingerprint.user_id}")
            
        except Exception as e:
            self.audit_logger.log_error(f"Fingerprint storage failed: {str(e)}")


__all__ = [
    "VoicePattern",
    "VoiceFingerprint", 
    "VoiceFingerprintExtractor"
]
