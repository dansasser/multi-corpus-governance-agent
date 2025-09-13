"""
Voice-Aware Ideator Agent

Analyzes user queries and gathers voice context from all corpora.
Provides comprehensive voice analysis for authentic replication.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from mcg_agent.pydantic_ai.personal_voice_agent import PersonalVoiceAgent, VoiceAgentContext
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext
from mcg_agent.search.tools import personal_search, social_search, published_search
from mcg_agent.search.connectors import PersonalSearchFilters, SocialSearchFilters, PublishedSearchFilters
from mcg_agent.utils.exceptions import VoiceAgentError


class VoiceAwareIdeatorAgent(PersonalVoiceAgent):
    """
    Ideator agent with full voice analysis capabilities.
    
    Responsibilities:
    - Analyze user query for intent and context
    - Gather relevant voice patterns from all accessible corpora
    - Identify appropriate tone and audience for response
    - Provide comprehensive voice context for downstream agents
    """
    
    def __init__(self, voice_profile=None):
        super().__init__(role="ideator", voice_profile=voice_profile)
        
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content with comprehensive voice analysis.
        
        Args:
            input_data: Input data to process
            voice_context: Voice context for generation
            agent_context: Agent-specific context
            
        Returns:
            str: Processed content with voice analysis
        """
        try:
            user_query = input_data.content
            
            # 1. Analyze query intent and context
            query_analysis = await self._analyze_query_intent(user_query)
            
            # 2. Gather voice patterns from all accessible corpora
            voice_patterns = await self._gather_voice_patterns(user_query, agent_context)
            
            # 3. Determine appropriate voice characteristics
            voice_characteristics = await self._determine_voice_characteristics(
                user_query, 
                query_analysis, 
                voice_patterns
            )
            
            # 4. Create comprehensive voice analysis
            voice_analysis = self._create_voice_analysis(
                user_query,
                query_analysis,
                voice_patterns,
                voice_characteristics
            )
            
            self.audit_logger.log_info(
                f"Ideator completed voice analysis for task {input_data.task_id}"
            )
            
            return voice_analysis
            
        except Exception as e:
            raise VoiceAgentError(f"Ideator processing failed: {str(e)}")
            
    async def _analyze_query_intent(self, user_query: str) -> Dict[str, Any]:
        """Analyze user query for intent and context requirements"""
        try:
            # Determine query type
            query_type = "general"
            if any(word in user_query.lower() for word in ["email", "message", "write to"]):
                query_type = "communication"
            elif any(word in user_query.lower() for word in ["article", "blog", "post"]):
                query_type = "content_creation"
            elif any(word in user_query.lower() for word in ["explain", "help", "how"]):
                query_type = "explanation"
                
            # Determine formality level
            formality = "professional"
            if any(word in user_query.lower() for word in ["casual", "friendly", "informal"]):
                formality = "casual"
            elif any(word in user_query.lower() for word in ["formal", "official", "business"]):
                formality = "formal"
                
            # Determine audience
            audience = "general"
            if any(word in user_query.lower() for word in ["colleague", "team", "work"]):
                audience = "professional"
            elif any(word in user_query.lower() for word in ["friend", "family", "personal"]):
                audience = "personal"
                
            return {
                "query_type": query_type,
                "formality": formality,
                "audience": audience,
                "length": len(user_query),
                "complexity": "high" if len(user_query.split()) > 20 else "medium" if len(user_query.split()) > 10 else "low"
            }
            
        except Exception as e:
            self.audit_logger.log_error(f"Query intent analysis failed: {str(e)}")
            return {"query_type": "general", "formality": "professional", "audience": "general"}
            
    async def _gather_voice_patterns(self, user_query: str, context: VoiceAgentContext) -> Dict[str, List[str]]:
        """Gather relevant voice patterns from all accessible corpora"""
        voice_patterns = {
            "personal": [],
            "social": [],
            "published": []
        }
        
        try:
            # Search personal corpus for reasoning patterns
            if "personal" in self.corpus_access:
                try:
                    personal_results = await personal_search(
                        None,  # RunContext would be provided in real implementation
                        user_query,
                        PersonalSearchFilters(),
                        limit=5
                    )
                    
                    # Extract voice patterns from personal results
                    for result in personal_results.get("results", []):
                        content = result.get("content", "")
                        patterns = self._extract_voice_patterns(content, "personal")
                        voice_patterns["personal"].extend(patterns)
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Personal corpus search failed: {str(e)}")
                    
            # Search social corpus for engagement patterns
            if "social" in self.corpus_access:
                try:
                    social_results = await social_search(
                        None,  # RunContext would be provided in real implementation
                        user_query,
                        SocialSearchFilters(),
                        limit=5
                    )
                    
                    # Extract voice patterns from social results
                    for result in social_results.get("results", []):
                        content = result.get("content", "")
                        patterns = self._extract_voice_patterns(content, "social")
                        voice_patterns["social"].extend(patterns)
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Social corpus search failed: {str(e)}")
                    
            # Search published corpus for professional patterns
            if "published" in self.corpus_access:
                try:
                    published_results = await published_search(
                        None,  # RunContext would be provided in real implementation
                        user_query,
                        PublishedSearchFilters(),
                        limit=5
                    )
                    
                    # Extract voice patterns from published results
                    for result in published_results.get("results", []):
                        content = result.get("content", "")
                        patterns = self._extract_voice_patterns(content, "published")
                        voice_patterns["published"].extend(patterns)
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Published corpus search failed: {str(e)}")
                    
        except Exception as e:
            self.audit_logger.log_error(f"Voice pattern gathering failed: {str(e)}")
            
        return voice_patterns
        
    def _extract_voice_patterns(self, content: str, corpus_type: str) -> List[str]:
        """Extract voice patterns from content based on corpus type"""
        patterns = []
        
        try:
            # Simple pattern extraction (would be more sophisticated in production)
            sentences = content.split('.')
            
            for sentence in sentences[:3]:  # Limit to first 3 sentences
                sentence = sentence.strip()
                if len(sentence) > 10 and len(sentence) < 100:
                    # Extract characteristic phrases
                    if corpus_type == "personal":
                        # Look for personal reasoning patterns
                        if any(phrase in sentence.lower() for phrase in ["i think", "in my experience", "i believe"]):
                            patterns.append(sentence)
                    elif corpus_type == "social":
                        # Look for engagement patterns
                        if any(phrase in sentence.lower() for phrase in ["thanks", "great", "love", "excited"]):
                            patterns.append(sentence)
                    elif corpus_type == "published":
                        # Look for professional patterns
                        if any(phrase in sentence.lower() for phrase in ["furthermore", "however", "therefore", "important"]):
                            patterns.append(sentence)
                            
        except Exception as e:
            self.audit_logger.log_error(f"Pattern extraction failed: {str(e)}")
            
        return patterns[:2]  # Limit to top 2 patterns per content
        
    async def _determine_voice_characteristics(
        self, 
        user_query: str, 
        query_analysis: Dict[str, Any],
        voice_patterns: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Determine appropriate voice characteristics for the response"""
        try:
            # Base characteristics on query analysis
            characteristics = {
                "tone": query_analysis.get("formality", "professional"),
                "audience": query_analysis.get("audience", "general"),
                "context_type": query_analysis.get("query_type", "general"),
                "voice_influence_level": 0.7  # Default moderate influence
            }
            
            # Adjust based on available voice patterns
            total_patterns = sum(len(patterns) for patterns in voice_patterns.values())
            
            if total_patterns > 10:
                characteristics["voice_influence_level"] = 0.8  # High influence
            elif total_patterns > 5:
                characteristics["voice_influence_level"] = 0.7  # Moderate influence
            else:
                characteristics["voice_influence_level"] = 0.5  # Lower influence
                
            # Determine primary corpus for voice
            corpus_scores = {
                "personal": len(voice_patterns.get("personal", [])),
                "social": len(voice_patterns.get("social", [])),
                "published": len(voice_patterns.get("published", []))
            }
            
            primary_corpus = max(corpus_scores.keys(), key=lambda k: corpus_scores[k])
            characteristics["primary_corpus"] = primary_corpus
            
            # Adjust tone based on primary corpus
            if primary_corpus == "social" and characteristics["tone"] == "professional":
                characteristics["tone"] = "casual"
            elif primary_corpus == "published" and characteristics["tone"] == "casual":
                characteristics["tone"] = "professional"
                
            return characteristics
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice characteristics determination failed: {str(e)}")
            return {
                "tone": "professional",
                "audience": "general", 
                "context_type": "general",
                "voice_influence_level": 0.5,
                "primary_corpus": "personal"
            }
            
    def _create_voice_analysis(
        self,
        user_query: str,
        query_analysis: Dict[str, Any],
        voice_patterns: Dict[str, List[str]],
        voice_characteristics: Dict[str, Any]
    ) -> str:
        """Create comprehensive voice analysis for downstream agents"""
        try:
            analysis_parts = []
            
            # Query analysis summary
            analysis_parts.append(f"Query Analysis:")
            analysis_parts.append(f"- Type: {query_analysis.get('query_type', 'general')}")
            analysis_parts.append(f"- Formality: {query_analysis.get('formality', 'professional')}")
            analysis_parts.append(f"- Audience: {query_analysis.get('audience', 'general')}")
            analysis_parts.append(f"- Complexity: {query_analysis.get('complexity', 'medium')}")
            
            # Voice patterns summary
            analysis_parts.append(f"\nVoice Patterns Found:")
            for corpus, patterns in voice_patterns.items():
                if patterns:
                    analysis_parts.append(f"- {corpus.title()}: {len(patterns)} patterns")
                    for pattern in patterns[:2]:  # Show top 2
                        analysis_parts.append(f"  * \"{pattern[:50]}...\"")
                        
            # Voice characteristics
            analysis_parts.append(f"\nRecommended Voice Characteristics:")
            analysis_parts.append(f"- Tone: {voice_characteristics.get('tone', 'professional')}")
            analysis_parts.append(f"- Audience: {voice_characteristics.get('audience', 'general')}")
            analysis_parts.append(f"- Context: {voice_characteristics.get('context_type', 'general')}")
            analysis_parts.append(f"- Voice Influence: {voice_characteristics.get('voice_influence_level', 0.5):.1f}")
            analysis_parts.append(f"- Primary Corpus: {voice_characteristics.get('primary_corpus', 'personal')}")
            
            # Original query
            analysis_parts.append(f"\nOriginal Query: {user_query}")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice analysis creation failed: {str(e)}")
            return f"Voice Analysis Error: {str(e)}\n\nOriginal Query: {user_query}"


__all__ = ["VoiceAwareIdeatorAgent"]
