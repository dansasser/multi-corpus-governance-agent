"""
Voice-Aware Summarizer Agent

Final voice consistency check and output preparation.
Implements the "firebreak" pattern with direct MVLM usage.
"""

from typing import Dict, List, Any, Optional

from mcg_agent.pydantic_ai.personal_voice_agent import PersonalVoiceAgent, VoiceAgentContext
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext, VoiceGenerationRequest, MVLMModelType
from mcg_agent.mvlm.voice_aware_text_generator import VoiceValidationResult
from mcg_agent.utils.exceptions import VoiceAgentError


class VoiceAwareSummarizerAgent(PersonalVoiceAgent):
    """
    Summarizer agent with final voice consistency validation.
    
    Responsibilities:
    - Perform final voice consistency check
    - Ensure output meets quality standards
    - Use MVLM directly for efficient final processing (firebreak pattern)
    - Prepare final output with metadata
    - No new corpus access - works with refined content
    """
    
    def __init__(self, voice_profile=None):
        super().__init__(role="summarizer", voice_profile=voice_profile)
        
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content for final voice consistency check and output preparation.
        
        Args:
            input_data: Input data containing refined content from Revisor
            voice_context: Voice context for final validation
            agent_context: Agent-specific context
            
        Returns:
            str: Final output with voice consistency validation
        """
        try:
            refined_content = input_data.content
            
            # Perform final voice consistency validation
            final_validation = await self._perform_final_voice_validation(
                refined_content,
                agent_context
            )
            
            # Determine if final adjustments are needed
            if self._needs_final_adjustment(final_validation):
                # Use MVLM for minimal final adjustments
                final_content = await self._make_final_adjustments(
                    refined_content,
                    final_validation,
                    agent_context,
                    input_data.task_id
                )
            else:
                final_content = refined_content
                
            # Prepare final output with metadata
            final_output = self._prepare_final_output(
                final_content,
                final_validation,
                agent_context,
                input_data.task_id
            )
            
            self.audit_logger.log_info(
                f"Summarizer completed final processing for task {input_data.task_id} "
                f"with final voice score {final_validation.consistency_score:.2f}"
            )
            
            return final_output
            
        except Exception as e:
            raise VoiceAgentError(f"Summarizer processing failed: {str(e)}")
            
    async def _perform_final_voice_validation(
        self,
        content: str,
        context: VoiceAgentContext
    ) -> VoiceValidationResult:
        """Perform comprehensive final voice validation"""
        try:
            if context.voice_profile:
                # Use existing voice profile
                validation_result = self.voice_generator.validate_voice_consistency(
                    content,
                    context.voice_profile
                )
            else:
                # Create minimal voice profile for validation
                from mcg_agent.mvlm.voice_aware_text_generator import VoiceProfile
                
                minimal_profile = VoiceProfile(
                    personal_patterns=[],
                    social_patterns=[],
                    published_patterns=[],
                    preferred_tone=context.desired_tone,
                    common_phrases=[],
                    writing_style="conversational",
                    professional_voice={"tone": "professional"},
                    casual_voice={"tone": "casual"}
                )
                
                validation_result = self.voice_generator.validate_voice_consistency(
                    content,
                    minimal_profile
                )
                
            # Enhance validation with final checks
            enhanced_validation = self._enhance_final_validation(
                validation_result,
                content,
                context
            )
            
            return enhanced_validation
            
        except Exception as e:
            self.audit_logger.log_error(f"Final voice validation failed: {str(e)}")
            # Return default validation
            from mcg_agent.mvlm.voice_aware_text_generator import VoiceValidationResult
            return VoiceValidationResult(
                is_consistent=True,  # Default to consistent for final stage
                consistency_score=0.7,
                issues_found=[],
                suggestions=[],
                tone_match=True,
                pattern_match_score=0.7,
                style_consistency=0.7
            )
            
    def _enhance_final_validation(
        self,
        base_validation: VoiceValidationResult,
        content: str,
        context: VoiceAgentContext
    ) -> VoiceValidationResult:
        """Enhance validation with final-stage specific checks"""
        try:
            enhanced_issues = list(base_validation.issues_found)
            enhanced_suggestions = list(base_validation.suggestions)
            
            # Final readability check
            readability_score = self._check_readability(content)
            if readability_score < 0.6:
                enhanced_issues.append("Content may be difficult to read")
                enhanced_suggestions.append("Simplify sentence structure for better readability")
                
            # Final completeness check
            completeness_score = self._check_completeness(content, context)
            if completeness_score < 0.7:
                enhanced_issues.append("Response may be incomplete")
                enhanced_suggestions.append("Ensure all aspects of the query are addressed")
                
            # Final tone consistency check
            tone_consistency = self._check_final_tone_consistency(content, context)
            if not tone_consistency:
                enhanced_issues.append("Tone inconsistency detected")
                enhanced_suggestions.append("Ensure consistent tone throughout response")
                
            # Calculate enhanced consistency score
            enhanced_score = (
                base_validation.consistency_score * 0.6 +
                readability_score * 0.2 +
                completeness_score * 0.2
            )
            
            # Create enhanced validation result
            from mcg_agent.mvlm.voice_aware_text_generator import VoiceValidationResult
            return VoiceValidationResult(
                is_consistent=enhanced_score >= 0.7 and len(enhanced_issues) <= 1,
                consistency_score=enhanced_score,
                issues_found=enhanced_issues,
                suggestions=enhanced_suggestions,
                tone_match=base_validation.tone_match and tone_consistency,
                pattern_match_score=base_validation.pattern_match_score,
                style_consistency=base_validation.style_consistency
            )
            
        except Exception as e:
            self.audit_logger.log_error(f"Validation enhancement failed: {str(e)}")
            return base_validation
            
    def _check_readability(self, content: str) -> float:
        """Check content readability"""
        try:
            sentences = content.split('.')
            words = content.split()
            
            if not sentences or not words:
                return 0.5
                
            # Simple readability metrics
            avg_sentence_length = len(words) / len([s for s in sentences if s.strip()])
            
            # Optimal sentence length is 15-20 words
            if 15 <= avg_sentence_length <= 20:
                length_score = 1.0
            elif 10 <= avg_sentence_length <= 25:
                length_score = 0.8
            else:
                length_score = 0.6
                
            # Check for complex words (simplified)
            complex_words = [word for word in words if len(word) > 8]
            complexity_ratio = len(complex_words) / len(words)
            
            if complexity_ratio < 0.1:
                complexity_score = 1.0
            elif complexity_ratio < 0.2:
                complexity_score = 0.8
            else:
                complexity_score = 0.6
                
            return (length_score + complexity_score) / 2
            
        except Exception as e:
            self.audit_logger.log_error(f"Readability check failed: {str(e)}")
            return 0.7
            
    def _check_completeness(self, content: str, context: VoiceAgentContext) -> float:
        """Check if response is complete"""
        try:
            # Basic completeness checks
            word_count = len(content.split())
            
            # Minimum word count based on context
            min_words = 50  # Default minimum
            if context.context_type == "explanation":
                min_words = 100
            elif context.context_type == "communication":
                min_words = 30
                
            if word_count < min_words:
                return 0.5
            elif word_count < min_words * 1.5:
                return 0.7
            else:
                return 1.0
                
        except Exception as e:
            self.audit_logger.log_error(f"Completeness check failed: {str(e)}")
            return 0.8
            
    def _check_final_tone_consistency(self, content: str, context: VoiceAgentContext) -> bool:
        """Check tone consistency throughout the content"""
        try:
            expected_tone = context.desired_tone
            content_lower = content.lower()
            
            # Check for tone indicators
            professional_indicators = ["however", "therefore", "furthermore", "important"]
            casual_indicators = ["really", "pretty", "kind of", "basically"]
            
            professional_count = sum(1 for indicator in professional_indicators if indicator in content_lower)
            casual_count = sum(1 for indicator in casual_indicators if indicator in content_lower)
            
            if expected_tone == "professional":
                return professional_count >= casual_count
            elif expected_tone == "casual":
                return casual_count >= professional_count
            else:
                return True  # Default to consistent for other tones
                
        except Exception as e:
            self.audit_logger.log_error(f"Tone consistency check failed: {str(e)}")
            return True
            
    def _needs_final_adjustment(self, validation: VoiceValidationResult) -> bool:
        """Determine if final adjustments are needed"""
        try:
            # Only make adjustments for significant issues
            if validation.consistency_score < 0.6:
                return True
                
            # Check for critical issues
            critical_issues = [
                issue for issue in validation.issues_found
                if any(keyword in issue.lower() for keyword in [
                    "incomplete", "inconsistent", "difficult to read"
                ])
            ]
            
            return len(critical_issues) > 0
            
        except Exception as e:
            self.audit_logger.log_error(f"Final adjustment decision failed: {str(e)}")
            return False  # Default to no adjustment
            
    async def _make_final_adjustments(
        self,
        content: str,
        validation: VoiceValidationResult,
        context: VoiceAgentContext,
        task_id: str
    ) -> str:
        """Make minimal final adjustments using MVLM"""
        try:
            # Create minimal adjustment prompt
            adjustment_prompt = self._create_final_adjustment_prompt(
                content,
                validation,
                context
            )
            
            # Create voice context for MVLM
            voice_context = VoiceContext(
                voice_patterns=[],  # No new patterns for final adjustment
                tone=context.desired_tone,
                audience=context.target_audience,
                context_type="final_adjustment",
                corpus_sources=[],  # No corpus access
                influence_level=0.9  # High influence to preserve existing voice
            )
            
            # Create generation request
            generation_request = VoiceGenerationRequest(
                prompt=adjustment_prompt,
                voice_context=voice_context,
                model_type=self.mvlm_manager.active_model
            )
            
            # Generate adjusted content
            result = await self.mvlm_manager.generate_with_voice(generation_request)
            
            # Minimal post-processing
            adjusted_content = self._post_process_final_adjustment(
                result.generated_text,
                content
            )
            
            self.audit_logger.log_info(f"Final adjustment completed for task {task_id}")
            
            return adjusted_content
            
        except Exception as e:
            self.audit_logger.log_error(f"Final adjustment failed: {str(e)}")
            return content  # Return original if adjustment fails
            
    def _create_final_adjustment_prompt(
        self,
        content: str,
        validation: VoiceValidationResult,
        context: VoiceAgentContext
    ) -> str:
        """Create prompt for minimal final adjustments"""
        try:
            prompt_parts = []
            
            prompt_parts.append("Make MINIMAL adjustments to improve this content while preserving the voice:")
            
            # Specific issues to address
            if validation.issues_found:
                prompt_parts.append("Address these issues:")
                for issue in validation.issues_found[:3]:
                    prompt_parts.append(f"- {issue}")
                    
            # Preservation instructions
            prompt_parts.append("\nIMPORTANT: Keep the same voice, tone, and style. Only make minimal improvements.")
            
            # Original content
            prompt_parts.append(f"\nContent to adjust:\n{content}")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Final adjustment prompt creation failed: {str(e)}")
            return f"Improve this content minimally:\n{content}"
            
    def _post_process_final_adjustment(self, adjusted_content: str, original_content: str) -> str:
        """Post-process final adjustment to ensure minimal changes"""
        try:
            processed = adjusted_content.strip()
            
            # Remove prompt artifacts
            if "Make MINIMAL adjustments" in processed:
                processed = processed.split("Content to adjust:")[-1].strip()
                
            # Ensure length didn't change dramatically
            original_length = len(original_content)
            if len(processed) < original_length * 0.8 or len(processed) > original_length * 1.3:
                return original_content  # Too much change, use original
                
            return processed
            
        except Exception as e:
            self.audit_logger.log_error(f"Final adjustment post-processing failed: {str(e)}")
            return adjusted_content
            
    def _prepare_final_output(
        self,
        content: str,
        validation: VoiceValidationResult,
        context: VoiceAgentContext,
        task_id: str
    ) -> str:
        """Prepare final output with metadata"""
        try:
            output_parts = []
            
            # Main content
            output_parts.append(content)
            
            # Add metadata section (optional, can be configured)
            if context.governance_context.classification != "chat":
                output_parts.append("\n" + "="*50)
                output_parts.append("Voice Replication Summary:")
                output_parts.append(f"- Voice Consistency Score: {validation.consistency_score:.2f}")
                output_parts.append(f"- Tone Match: {'Yes' if validation.tone_match else 'No'}")
                output_parts.append(f"- Style Consistency: {validation.style_consistency:.2f}")
                output_parts.append(f"- Task ID: {task_id}")
                
                if validation.issues_found:
                    output_parts.append("- Remaining Issues:")
                    for issue in validation.issues_found[:2]:
                        output_parts.append(f"  * {issue}")
                        
            return "\n".join(output_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Final output preparation failed: {str(e)}")
            return content  # Return content without metadata if preparation fails
            
    def _should_use_voice_generation(self, input_data: AgentInput, context: VoiceAgentContext) -> bool:
        """Summarizer uses MVLM directly, not voice generation"""
        return False  # Summarizer implements firebreak pattern with direct MVLM


__all__ = ["VoiceAwareSummarizerAgent"]
