"""
Voice-Aware Critic Agent

Validates voice authenticity against all corpora.
Ensures draft maintains authentic voice patterns and consistency.
"""

import re
from typing import Dict, List, Any, Optional, Tuple

from mcg_agent.pydantic_ai.personal_voice_agent import PersonalVoiceAgent, VoiceAgentContext
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext
from mcg_agent.mvlm.voice_aware_text_generator import VoiceValidationResult
from mcg_agent.search.tools import personal_search, social_search, published_search
from mcg_agent.search.connectors import PersonalSearchFilters, SocialSearchFilters, PublishedSearchFilters
from mcg_agent.utils.exceptions import VoiceAgentError


class VoiceAwareCriticAgent(PersonalVoiceAgent):
    """
    Critic agent with comprehensive voice validation capabilities.
    
    Responsibilities:
    - Validate draft against all accessible corpora
    - Check voice authenticity and consistency
    - Identify voice pattern mismatches
    - Provide specific improvement recommendations
    - Ensure tone and style alignment
    """
    
    def __init__(self, voice_profile=None):
        super().__init__(role="critic", voice_profile=voice_profile)
        
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content to validate voice authenticity and provide critique.
        
        Args:
            input_data: Input data containing draft from Drafter
            voice_context: Voice context for validation
            agent_context: Agent-specific context
            
        Returns:
            str: Critique with validation results and recommendations
        """
        try:
            draft_content = input_data.content
            
            # Perform comprehensive voice validation
            validation_results = await self._validate_voice_authenticity(
                draft_content, 
                agent_context
            )
            
            # Check voice consistency across corpora
            consistency_analysis = await self._analyze_voice_consistency(
                draft_content,
                agent_context
            )
            
            # Validate tone and style alignment
            tone_style_validation = await self._validate_tone_and_style(
                draft_content,
                agent_context
            )
            
            # Generate improvement recommendations
            recommendations = self._generate_improvement_recommendations(
                draft_content,
                validation_results,
                consistency_analysis,
                tone_style_validation
            )
            
            # Create comprehensive critique
            critique = self._create_comprehensive_critique(
                draft_content,
                validation_results,
                consistency_analysis,
                tone_style_validation,
                recommendations
            )
            
            self.audit_logger.log_info(
                f"Critic completed voice validation for task {input_data.task_id}"
            )
            
            return critique
            
        except Exception as e:
            raise VoiceAgentError(f"Critic processing failed: {str(e)}")
            
    async def _validate_voice_authenticity(
        self, 
        draft_content: str, 
        context: VoiceAgentContext
    ) -> VoiceValidationResult:
        """Validate voice authenticity using voice profile"""
        try:
            if context.voice_profile:
                # Use existing voice profile for validation
                validation_result = self.voice_generator.validate_voice_consistency(
                    draft_content, 
                    context.voice_profile
                )
            else:
                # Create temporary voice profile from available data
                temp_voice_profile = await self._create_temporary_voice_profile(context)
                validation_result = self.voice_generator.validate_voice_consistency(
                    draft_content, 
                    temp_voice_profile
                )
                
            return validation_result
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice authenticity validation failed: {str(e)}")
            # Return default validation result
            from mcg_agent.mvlm.voice_aware_text_generator import VoiceValidationResult
            return VoiceValidationResult(
                is_consistent=False,
                consistency_score=0.5,
                issues_found=[f"Validation error: {str(e)}"],
                suggestions=["Manual review required"],
                tone_match=False,
                pattern_match_score=0.5,
                style_consistency=0.5
            )
            
    async def _create_temporary_voice_profile(self, context: VoiceAgentContext):
        """Create temporary voice profile for validation"""
        from mcg_agent.mvlm.voice_aware_text_generator import VoiceProfile
        
        # Gather sample patterns from corpora
        personal_patterns = await self._get_sample_patterns("personal", context)
        social_patterns = await self._get_sample_patterns("social", context)
        published_patterns = await self._get_sample_patterns("published", context)
        
        return VoiceProfile(
            personal_patterns=personal_patterns,
            social_patterns=social_patterns,
            published_patterns=published_patterns,
            preferred_tone=context.desired_tone,
            common_phrases=personal_patterns + social_patterns,
            writing_style="conversational",
            professional_voice={"tone": "professional", "patterns": published_patterns},
            casual_voice={"tone": "casual", "patterns": social_patterns}
        )
        
    async def _get_sample_patterns(self, corpus_type: str, context: VoiceAgentContext) -> List[str]:
        """Get sample patterns from a specific corpus"""
        patterns = []
        
        try:
            if corpus_type not in self.corpus_access:
                return patterns
                
            # Use a generic query to get representative content
            sample_query = "example communication style"
            
            if corpus_type == "personal":
                results = await personal_search(
                    None,
                    sample_query,
                    PersonalSearchFilters(),
                    limit=3
                )
            elif corpus_type == "social":
                results = await social_search(
                    None,
                    sample_query,
                    SocialSearchFilters(),
                    limit=3
                )
            elif corpus_type == "published":
                results = await published_search(
                    None,
                    sample_query,
                    PublishedSearchFilters(),
                    limit=3
                )
            else:
                return patterns
                
            # Extract patterns from results
            for result in results.get("results", []):
                content = result.get("content", "")
                extracted = self._extract_representative_patterns(content, corpus_type)
                patterns.extend(extracted)
                
        except Exception as e:
            self.audit_logger.log_warning(f"Sample pattern extraction failed for {corpus_type}: {str(e)}")
            
        return patterns[:5]  # Limit to top 5
        
    def _extract_representative_patterns(self, content: str, corpus_type: str) -> List[str]:
        """Extract representative patterns from content"""
        patterns = []
        
        try:
            sentences = content.split('.')
            
            for sentence in sentences[:3]:
                sentence = sentence.strip()
                if 15 < len(sentence) < 80:  # Good length for patterns
                    if corpus_type == "personal":
                        if any(phrase in sentence.lower() for phrase in ["i", "my", "me", "think", "feel"]):
                            patterns.append(sentence)
                    elif corpus_type == "social":
                        if any(phrase in sentence.lower() for phrase in ["thanks", "great", "love", "excited", "happy"]):
                            patterns.append(sentence)
                    elif corpus_type == "published":
                        if any(phrase in sentence.lower() for phrase in ["important", "however", "therefore", "furthermore"]):
                            patterns.append(sentence)
                            
        except Exception:
            pass
            
        return patterns[:2]
        
    async def _analyze_voice_consistency(
        self, 
        draft_content: str, 
        context: VoiceAgentContext
    ) -> Dict[str, Any]:
        """Analyze voice consistency across different corpora"""
        try:
            consistency_analysis = {
                "personal_alignment": 0.0,
                "social_alignment": 0.0,
                "published_alignment": 0.0,
                "overall_consistency": 0.0,
                "inconsistencies": []
            }
            
            # Check alignment with each corpus type
            for corpus_type in ["personal", "social", "published"]:
                if corpus_type in self.corpus_access:
                    alignment_score = await self._check_corpus_alignment(
                        draft_content, 
                        corpus_type, 
                        context
                    )
                    consistency_analysis[f"{corpus_type}_alignment"] = alignment_score
                    
            # Calculate overall consistency
            alignments = [
                consistency_analysis["personal_alignment"],
                consistency_analysis["social_alignment"],
                consistency_analysis["published_alignment"]
            ]
            non_zero_alignments = [a for a in alignments if a > 0]
            
            if non_zero_alignments:
                consistency_analysis["overall_consistency"] = sum(non_zero_alignments) / len(non_zero_alignments)
            else:
                consistency_analysis["overall_consistency"] = 0.5
                
            # Identify inconsistencies
            if consistency_analysis["overall_consistency"] < 0.6:
                consistency_analysis["inconsistencies"].append("Low overall voice consistency")
                
            if abs(consistency_analysis["personal_alignment"] - consistency_analysis["social_alignment"]) > 0.3:
                consistency_analysis["inconsistencies"].append("Mismatch between personal and social voice")
                
            return consistency_analysis
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice consistency analysis failed: {str(e)}")
            return {
                "personal_alignment": 0.5,
                "social_alignment": 0.5,
                "published_alignment": 0.5,
                "overall_consistency": 0.5,
                "inconsistencies": [f"Analysis error: {str(e)}"]
            }
            
    async def _check_corpus_alignment(
        self, 
        draft_content: str, 
        corpus_type: str, 
        context: VoiceAgentContext
    ) -> float:
        """Check how well draft aligns with a specific corpus"""
        try:
            # Get representative content from corpus
            representative_patterns = await self._get_sample_patterns(corpus_type, context)
            
            if not representative_patterns:
                return 0.0
                
            # Calculate alignment score
            alignment_score = 0.0
            total_checks = 0
            
            draft_lower = draft_content.lower()
            
            # Check for pattern presence
            for pattern in representative_patterns:
                pattern_words = pattern.lower().split()
                common_words = [word for word in pattern_words if word in draft_lower]
                
                if common_words:
                    alignment_score += len(common_words) / len(pattern_words)
                    
                total_checks += 1
                
            # Check for corpus-specific characteristics
            if corpus_type == "personal":
                personal_indicators = ["i think", "in my", "i believe", "my experience"]
                personal_matches = sum(1 for indicator in personal_indicators if indicator in draft_lower)
                alignment_score += personal_matches * 0.2
                total_checks += 1
                
            elif corpus_type == "social":
                social_indicators = ["thanks", "great", "love", "excited", "really"]
                social_matches = sum(1 for indicator in social_indicators if indicator in draft_lower)
                alignment_score += social_matches * 0.2
                total_checks += 1
                
            elif corpus_type == "published":
                published_indicators = ["however", "therefore", "furthermore", "important", "significant"]
                published_matches = sum(1 for indicator in published_indicators if indicator in draft_lower)
                alignment_score += published_matches * 0.2
                total_checks += 1
                
            return min(alignment_score / max(total_checks, 1), 1.0)
            
        except Exception as e:
            self.audit_logger.log_error(f"Corpus alignment check failed for {corpus_type}: {str(e)}")
            return 0.5
            
    async def _validate_tone_and_style(
        self, 
        draft_content: str, 
        context: VoiceAgentContext
    ) -> Dict[str, Any]:
        """Validate tone and style alignment"""
        try:
            validation = {
                "tone_match": False,
                "style_consistency": 0.0,
                "tone_issues": [],
                "style_issues": []
            }
            
            expected_tone = context.desired_tone
            draft_lower = draft_content.lower()
            
            # Check tone alignment
            tone_indicators = {
                "professional": ["however", "therefore", "furthermore", "important", "significant"],
                "casual": ["really", "pretty", "kind of", "sort of", "basically"],
                "formal": ["nevertheless", "accordingly", "subsequently", "notwithstanding"],
                "friendly": ["great", "awesome", "wonderful", "fantastic", "amazing"]
            }
            
            if expected_tone in tone_indicators:
                expected_indicators = tone_indicators[expected_tone]
                tone_matches = sum(1 for indicator in expected_indicators if indicator in draft_lower)
                validation["tone_match"] = tone_matches > 0
                
                if not validation["tone_match"]:
                    validation["tone_issues"].append(f"No {expected_tone} tone indicators found")
                    
            # Check style consistency
            sentences = draft_content.split('.')
            sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
            
            if sentence_lengths:
                avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
                
                # Style scoring based on sentence structure
                if expected_tone == "casual":
                    # Casual should have shorter, varied sentences
                    if avg_sentence_length < 20:
                        validation["style_consistency"] += 0.5
                    if len(set(sentence_lengths)) > 2:  # Variety in length
                        validation["style_consistency"] += 0.3
                elif expected_tone == "professional":
                    # Professional should have moderate, consistent sentences
                    if 15 <= avg_sentence_length <= 25:
                        validation["style_consistency"] += 0.5
                    if "'t" not in draft_content:  # No contractions
                        validation["style_consistency"] += 0.3
                        
                # Check for style issues
                if avg_sentence_length > 30:
                    validation["style_issues"].append("Sentences too long for natural flow")
                elif avg_sentence_length < 8:
                    validation["style_issues"].append("Sentences too short, may sound choppy")
                    
            return validation
            
        except Exception as e:
            self.audit_logger.log_error(f"Tone and style validation failed: {str(e)}")
            return {
                "tone_match": False,
                "style_consistency": 0.5,
                "tone_issues": [f"Validation error: {str(e)}"],
                "style_issues": []
            }
            
    def _generate_improvement_recommendations(
        self,
        draft_content: str,
        validation_results: VoiceValidationResult,
        consistency_analysis: Dict[str, Any],
        tone_style_validation: Dict[str, Any]
    ) -> List[str]:
        """Generate specific improvement recommendations"""
        recommendations = []
        
        try:
            # Voice authenticity recommendations
            if not validation_results.is_consistent:
                recommendations.extend(validation_results.suggestions)
                
            # Consistency recommendations
            if consistency_analysis["overall_consistency"] < 0.6:
                recommendations.append("Improve overall voice consistency across corpora")
                
            for inconsistency in consistency_analysis["inconsistencies"]:
                recommendations.append(f"Address: {inconsistency}")
                
            # Tone and style recommendations
            if not tone_style_validation["tone_match"]:
                for issue in tone_style_validation["tone_issues"]:
                    recommendations.append(f"Tone: {issue}")
                    
            for issue in tone_style_validation["style_issues"]:
                recommendations.append(f"Style: {issue}")
                
            # Specific content recommendations
            if len(draft_content) < 100:
                recommendations.append("Expand response for more comprehensive coverage")
            elif len(draft_content) > 600:
                recommendations.append("Consider condensing for better readability")
                
            # Remove duplicates and limit
            unique_recommendations = list(dict.fromkeys(recommendations))
            return unique_recommendations[:8]  # Limit to top 8
            
        except Exception as e:
            self.audit_logger.log_error(f"Recommendation generation failed: {str(e)}")
            return ["Manual review recommended due to analysis error"]
            
    def _create_comprehensive_critique(
        self,
        draft_content: str,
        validation_results: VoiceValidationResult,
        consistency_analysis: Dict[str, Any],
        tone_style_validation: Dict[str, Any],
        recommendations: List[str]
    ) -> str:
        """Create comprehensive critique with all analysis results"""
        try:
            critique_parts = []
            
            # Voice authenticity section
            critique_parts.append("Voice Authenticity Analysis:")
            critique_parts.append(f"- Overall Consistency: {validation_results.consistency_score:.2f}")
            critique_parts.append(f"- Voice Authentic: {'Yes' if validation_results.is_consistent else 'No'}")
            critique_parts.append(f"- Pattern Match Score: {validation_results.pattern_match_score:.2f}")
            critique_parts.append(f"- Style Consistency: {validation_results.style_consistency:.2f}")
            
            if validation_results.issues_found:
                critique_parts.append("- Issues Found:")
                for issue in validation_results.issues_found[:3]:
                    critique_parts.append(f"  * {issue}")
                    
            # Corpus consistency section
            critique_parts.append("\nCorpus Consistency Analysis:")
            critique_parts.append(f"- Personal Alignment: {consistency_analysis['personal_alignment']:.2f}")
            critique_parts.append(f"- Social Alignment: {consistency_analysis['social_alignment']:.2f}")
            critique_parts.append(f"- Published Alignment: {consistency_analysis['published_alignment']:.2f}")
            critique_parts.append(f"- Overall Consistency: {consistency_analysis['overall_consistency']:.2f}")
            
            if consistency_analysis["inconsistencies"]:
                critique_parts.append("- Inconsistencies:")
                for inconsistency in consistency_analysis["inconsistencies"][:3]:
                    critique_parts.append(f"  * {inconsistency}")
                    
            # Tone and style section
            critique_parts.append("\nTone and Style Validation:")
            critique_parts.append(f"- Tone Match: {'Yes' if tone_style_validation['tone_match'] else 'No'}")
            critique_parts.append(f"- Style Consistency: {tone_style_validation['style_consistency']:.2f}")
            
            # Recommendations section
            if recommendations:
                critique_parts.append("\nImprovement Recommendations:")
                for i, rec in enumerate(recommendations[:5], 1):
                    critique_parts.append(f"{i}. {rec}")
                    
            # Overall assessment
            overall_score = (
                validation_results.consistency_score * 0.4 +
                consistency_analysis["overall_consistency"] * 0.4 +
                tone_style_validation["style_consistency"] * 0.2
            )
            
            critique_parts.append(f"\nOverall Voice Quality Score: {overall_score:.2f}")
            
            if overall_score >= 0.8:
                critique_parts.append("Assessment: Excellent voice consistency - ready for next stage")
            elif overall_score >= 0.6:
                critique_parts.append("Assessment: Good voice consistency - minor improvements recommended")
            else:
                critique_parts.append("Assessment: Voice consistency needs improvement - revisions recommended")
                
            # Include original draft for reference
            critique_parts.append(f"\nOriginal Draft:\n{draft_content}")
            
            return "\n".join(critique_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Critique creation failed: {str(e)}")
            return f"Critique Error: {str(e)}\n\nOriginal Draft:\n{draft_content}"


__all__ = ["VoiceAwareCriticAgent"]
