"""
Voice-Aware Revisor Agent

Refines content using MVLM while preserving voice authenticity.
Implements the "firebreak" pattern with direct MVLM usage.
"""

import re
from typing import Dict, List, Any, Optional

from mcg_agent.pydantic_ai.personal_voice_agent import PersonalVoiceAgent, VoiceAgentContext
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext, VoiceGenerationRequest, MVLMModelType
from mcg_agent.utils.exceptions import VoiceAgentError


class VoiceAwareRevisorAgent(PersonalVoiceAgent):
    """
    Revisor agent with MVLM-focused refinement.
    
    Responsibilities:
    - Parse critique and identify improvement areas
    - Use MVLM directly for efficient refinement (firebreak pattern)
    - Preserve voice authenticity while improving quality
    - Focus on clarity, flow, and technical accuracy
    - No new corpus access - works with existing content
    """
    
    def __init__(self, voice_profile=None):
        super().__init__(role="revisor", voice_profile=voice_profile)
        
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content to refine based on critique while preserving voice.
        
        Args:
            input_data: Input data containing critique from Critic
            voice_context: Voice context for refinement
            agent_context: Agent-specific context
            
        Returns:
            str: Refined content with preserved voice authenticity
        """
        try:
            critique_content = input_data.content
            
            # Parse critique to extract original draft and recommendations
            parsed_critique = self._parse_critique(critique_content)
            
            original_draft = parsed_critique.get("original_draft", "")
            if not original_draft:
                raise VoiceAgentError("No original draft found in critique")
                
            recommendations = parsed_critique.get("recommendations", [])
            voice_scores = parsed_critique.get("voice_scores", {})
            
            # Determine if refinement is needed
            if self._should_refine(voice_scores, recommendations):
                # Create refinement prompt preserving voice
                refinement_prompt = self._create_voice_preserving_prompt(
                    original_draft,
                    recommendations,
                    voice_scores,
                    agent_context
                )
                
                # Use MVLM directly for efficient refinement
                refined_content = await self._refine_with_mvlm(
                    refinement_prompt,
                    original_draft,
                    agent_context,
                    input_data.task_id
                )
                
                # Validate voice preservation
                final_content = self._validate_voice_preservation(
                    original_draft,
                    refined_content,
                    voice_scores
                )
            else:
                # No refinement needed
                final_content = original_draft
                self.audit_logger.log_info(f"Revisor: No refinement needed for task {input_data.task_id}")
                
            self.audit_logger.log_info(
                f"Revisor completed refinement for task {input_data.task_id}"
            )
            
            return final_content
            
        except Exception as e:
            raise VoiceAgentError(f"Revisor processing failed: {str(e)}")
            
    def _parse_critique(self, critique_content: str) -> Dict[str, Any]:
        """Parse critique to extract original draft and analysis"""
        try:
            parsed = {
                "original_draft": "",
                "recommendations": [],
                "voice_scores": {},
                "issues": []
            }
            
            lines = critique_content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("Voice Authenticity Analysis:"):
                    current_section = "voice_analysis"
                elif line.startswith("Corpus Consistency Analysis:"):
                    current_section = "corpus_analysis"
                elif line.startswith("Tone and Style Validation:"):
                    current_section = "tone_style"
                elif line.startswith("Improvement Recommendations:"):
                    current_section = "recommendations"
                elif line.startswith("Overall Voice Quality Score:"):
                    current_section = "overall_score"
                elif line.startswith("Original Draft:"):
                    current_section = "original_draft"
                elif line and current_section:
                    if current_section == "voice_analysis":
                        if "Overall Consistency:" in line:
                            score = self._extract_score(line)
                            if score is not None:
                                parsed["voice_scores"]["overall_consistency"] = score
                        elif "Pattern Match Score:" in line:
                            score = self._extract_score(line)
                            if score is not None:
                                parsed["voice_scores"]["pattern_match"] = score
                        elif "Style Consistency:" in line:
                            score = self._extract_score(line)
                            if score is not None:
                                parsed["voice_scores"]["style_consistency"] = score
                                
                    elif current_section == "corpus_analysis":
                        if "Overall Consistency:" in line:
                            score = self._extract_score(line)
                            if score is not None:
                                parsed["voice_scores"]["corpus_consistency"] = score
                                
                    elif current_section == "tone_style":
                        if "Style Consistency:" in line:
                            score = self._extract_score(line)
                            if score is not None:
                                parsed["voice_scores"]["tone_style_consistency"] = score
                                
                    elif current_section == "recommendations":
                        if line and line[0].isdigit():
                            # Extract recommendation text
                            rec_text = line.split('. ', 1)
                            if len(rec_text) > 1:
                                parsed["recommendations"].append(rec_text[1])
                                
                    elif current_section == "overall_score":
                        score = self._extract_score(line)
                        if score is not None:
                            parsed["voice_scores"]["overall_score"] = score
                            
                    elif current_section == "original_draft":
                        if not line.startswith("Original Draft:"):
                            parsed["original_draft"] += line + "\n"
                            
            # Clean up original draft
            parsed["original_draft"] = parsed["original_draft"].strip()
            
            return parsed
            
        except Exception as e:
            self.audit_logger.log_error(f"Critique parsing failed: {str(e)}")
            return {
                "original_draft": critique_content,  # Fallback to full content
                "recommendations": [],
                "voice_scores": {},
                "issues": [f"Parse error: {str(e)}"]
            }
            
    def _extract_score(self, line: str) -> Optional[float]:
        """Extract numeric score from a line"""
        try:
            # Look for patterns like "Score: 0.75" or "Consistency: 0.8"
            import re
            match = re.search(r':\s*(\d+\.?\d*)', line)
            if match:
                return float(match.group(1))
        except (ValueError, AttributeError):
            pass
        return None
        
    def _should_refine(self, voice_scores: Dict[str, float], recommendations: List[str]) -> bool:
        """Determine if refinement is needed based on scores and recommendations"""
        try:
            # Check overall score
            overall_score = voice_scores.get("overall_score", 0.7)
            if overall_score < 0.6:
                return True
                
            # Check individual scores
            consistency_score = voice_scores.get("overall_consistency", 0.7)
            if consistency_score < 0.5:
                return True
                
            # Check if there are actionable recommendations
            actionable_recommendations = [
                rec for rec in recommendations 
                if any(keyword in rec.lower() for keyword in [
                    "expand", "condense", "improve", "adjust", "clarify", "fix"
                ])
            ]
            
            if len(actionable_recommendations) >= 3:
                return True
                
            return False
            
        except Exception as e:
            self.audit_logger.log_error(f"Refinement decision failed: {str(e)}")
            return True  # Default to refining if unsure
            
    def _create_voice_preserving_prompt(
        self,
        original_draft: str,
        recommendations: List[str],
        voice_scores: Dict[str, float],
        context: VoiceAgentContext
    ) -> str:
        """Create prompt for MVLM that preserves voice while addressing issues"""
        try:
            prompt_parts = []
            
            # Voice preservation instruction
            prompt_parts.append("IMPORTANT: Preserve the original voice, tone, and personal style while making improvements.")
            
            # Context about desired voice
            prompt_parts.append(f"Target tone: {context.desired_tone}")
            prompt_parts.append(f"Target audience: {context.target_audience}")
            
            # Specific improvements needed
            if recommendations:
                prompt_parts.append("Address these specific issues:")
                for i, rec in enumerate(recommendations[:5], 1):
                    prompt_parts.append(f"{i}. {rec}")
                    
            # Voice preservation guidelines
            prompt_parts.append("\nVoice Preservation Guidelines:")
            prompt_parts.append("- Keep the same personal expressions and phrases")
            prompt_parts.append("- Maintain the same level of formality")
            prompt_parts.append("- Preserve characteristic sentence patterns")
            prompt_parts.append("- Keep the same conversational style")
            
            # Original content
            prompt_parts.append(f"\nOriginal Content to Refine:\n{original_draft}")
            
            # Final instruction
            prompt_parts.append("\nProvide the refined version that addresses the issues while preserving the authentic voice:")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice preserving prompt creation failed: {str(e)}")
            return f"Improve this content while preserving the voice:\n{original_draft}"
            
    async def _refine_with_mvlm(
        self,
        refinement_prompt: str,
        original_draft: str,
        context: VoiceAgentContext,
        task_id: str
    ) -> str:
        """Use MVLM directly for efficient refinement"""
        try:
            # Create voice context for MVLM
            voice_context = VoiceContext(
                voice_patterns=[],  # Revisor doesn't access new patterns
                tone=context.desired_tone,
                audience=context.target_audience,
                context_type="refinement",
                corpus_sources=[],  # No corpus access for Revisor
                influence_level=0.8  # High influence to preserve voice
            )
            
            # Create generation request
            generation_request = VoiceGenerationRequest(
                prompt=refinement_prompt,
                voice_context=voice_context,
                model_type=self.mvlm_manager.active_model
            )
            
            # Generate refined content
            result = await self.mvlm_manager.generate_with_voice(generation_request)
            
            # Post-process to ensure voice preservation
            refined_content = self._post_process_refinement(
                result.generated_text,
                original_draft,
                context
            )
            
            self.audit_logger.log_info(
                f"MVLM refinement completed for task {task_id} with voice score {result.voice_consistency_score:.2f}"
            )
            
            return refined_content
            
        except Exception as e:
            self.audit_logger.log_error(f"MVLM refinement failed: {str(e)}")
            # Fallback to original draft
            return original_draft
            
    def _post_process_refinement(
        self,
        refined_content: str,
        original_draft: str,
        context: VoiceAgentContext
    ) -> str:
        """Post-process refined content to ensure voice preservation"""
        try:
            processed = refined_content
            
            # Remove prompt artifacts
            if "IMPORTANT:" in processed:
                processed = processed.split("Provide the refined version")[-1]
            if "Original Content to Refine:" in processed:
                processed = processed.split("Original Content to Refine:")[-1]
                
            # Clean up formatting
            processed = processed.strip()
            
            # Ensure reasonable length (not too different from original)
            original_length = len(original_draft)
            if len(processed) < original_length * 0.5:
                # Too short, might have lost content
                processed = original_draft  # Fallback
            elif len(processed) > original_length * 2:
                # Too long, might have added too much
                sentences = processed.split('.')
                truncated = []
                current_length = 0
                target_length = int(original_length * 1.5)
                
                for sentence in sentences:
                    if current_length + len(sentence) < target_length:
                        truncated.append(sentence)
                        current_length += len(sentence)
                    else:
                        break
                processed = '.'.join(truncated) + '.'
                
            # Preserve key phrases from original if they're missing
            original_lower = original_draft.lower()
            processed_lower = processed.lower()
            
            # Look for personal expressions that might have been lost
            personal_expressions = [
                "i think", "in my experience", "i believe", "from my perspective"
            ]
            
            for expr in personal_expressions:
                if expr in original_lower and expr not in processed_lower:
                    # Try to preserve the voice by keeping original if too much was lost
                    self.audit_logger.log_warning(f"Personal expression '{expr}' lost in refinement")
                    
            return processed
            
        except Exception as e:
            self.audit_logger.log_error(f"Refinement post-processing failed: {str(e)}")
            return refined_content  # Return unprocessed if post-processing fails
            
    def _validate_voice_preservation(
        self,
        original_draft: str,
        refined_content: str,
        original_voice_scores: Dict[str, float]
    ) -> str:
        """Validate that voice was preserved during refinement"""
        try:
            # Quick voice preservation check
            original_length = len(original_draft)
            refined_length = len(refined_content)
            
            # Check if length changed dramatically
            length_ratio = refined_length / max(original_length, 1)
            if length_ratio < 0.3 or length_ratio > 3.0:
                self.audit_logger.log_warning("Dramatic length change detected, using original")
                return original_draft
                
            # Check if key personal indicators are preserved
            original_lower = original_draft.lower()
            refined_lower = refined_content.lower()
            
            personal_indicators = ["i ", "my ", "me ", "myself"]
            original_personal_count = sum(original_lower.count(indicator) for indicator in personal_indicators)
            refined_personal_count = sum(refined_lower.count(indicator) for indicator in personal_indicators)
            
            if original_personal_count > 0 and refined_personal_count == 0:
                self.audit_logger.log_warning("Personal voice indicators lost, using original")
                return original_draft
                
            # If voice preservation looks good, use refined content
            return refined_content
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice preservation validation failed: {str(e)}")
            return refined_content  # Default to refined if validation fails
            
    def _should_use_voice_generation(self, input_data: AgentInput, context: VoiceAgentContext) -> bool:
        """Revisor uses MVLM directly, not voice generation"""
        return False  # Revisor implements firebreak pattern with direct MVLM


__all__ = ["VoiceAwareRevisorAgent"]
