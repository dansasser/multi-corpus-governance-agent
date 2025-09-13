"""
Voice-Aware Drafter Agent

Creates initial responses using personal + social voice patterns.
Focuses on natural tone and authentic voice replication.
"""

import re
from typing import Dict, List, Any, Optional

from mcg_agent.pydantic_ai.personal_voice_agent import PersonalVoiceAgent, VoiceAgentContext
from mcg_agent.pydantic_ai.agent_base import AgentInput
from mcg_agent.mvlm.personal_voice_mvlm_manager import VoiceContext
from mcg_agent.search.tools import personal_search, social_search
from mcg_agent.search.connectors import PersonalSearchFilters, SocialSearchFilters
from mcg_agent.utils.exceptions import VoiceAgentError


class VoiceAwareDrafterAgent(PersonalVoiceAgent):
    """
    Drafter agent with personal + social voice focus.
    
    Responsibilities:
    - Parse voice analysis from Ideator
    - Access personal and social corpora for natural tone
    - Create initial draft with authentic voice patterns
    - Focus on conversational style and personal expressions
    """
    
    def __init__(self, voice_profile=None):
        super().__init__(role="drafter", voice_profile=voice_profile)
        
    async def _process_content(
        self, 
        input_data: AgentInput, 
        voice_context: VoiceContext,
        agent_context: VoiceAgentContext
    ) -> str:
        """
        Process content to create initial voice-consistent draft.
        
        Args:
            input_data: Input data containing voice analysis from Ideator
            voice_context: Voice context for generation
            agent_context: Agent-specific context
            
        Returns:
            str: Initial draft with voice consistency
        """
        try:
            # Parse voice analysis from Ideator
            voice_analysis = input_data.content
            parsed_analysis = self._parse_voice_analysis(voice_analysis)
            
            # Extract original query
            original_query = parsed_analysis.get("original_query", "")
            if not original_query:
                raise VoiceAgentError("No original query found in voice analysis")
                
            # Get voice characteristics
            voice_characteristics = parsed_analysis.get("voice_characteristics", {})
            
            # Gather personal and social voice patterns
            voice_patterns = await self._gather_drafting_voice_patterns(
                original_query, 
                voice_characteristics
            )
            
            # Create voice-enhanced prompt for drafting
            drafting_prompt = self._create_drafting_prompt(
                original_query,
                voice_characteristics,
                voice_patterns
            )
            
            # Generate initial draft using voice patterns
            draft = await self._generate_voice_draft(
                drafting_prompt,
                voice_characteristics,
                voice_patterns,
                input_data.task_id
            )
            
            self.audit_logger.log_info(
                f"Drafter created initial draft for task {input_data.task_id}"
            )
            
            return draft
            
        except Exception as e:
            raise VoiceAgentError(f"Drafter processing failed: {str(e)}")
            
    def _parse_voice_analysis(self, voice_analysis: str) -> Dict[str, Any]:
        """Parse voice analysis from Ideator"""
        try:
            parsed = {
                "query_analysis": {},
                "voice_patterns": {"personal": [], "social": []},
                "voice_characteristics": {},
                "original_query": ""
            }
            
            lines = voice_analysis.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("Query Analysis:"):
                    current_section = "query_analysis"
                elif line.startswith("Voice Patterns Found:"):
                    current_section = "voice_patterns"
                elif line.startswith("Recommended Voice Characteristics:"):
                    current_section = "voice_characteristics"
                elif line.startswith("Original Query:"):
                    current_section = "original_query"
                elif line and current_section:
                    if current_section == "query_analysis":
                        if line.startswith("- "):
                            key_value = line[2:].split(": ", 1)
                            if len(key_value) == 2:
                                parsed["query_analysis"][key_value[0].lower()] = key_value[1]
                                
                    elif current_section == "voice_patterns":
                        if line.startswith("- Personal:") or line.startswith("- Social:"):
                            corpus = "personal" if "Personal" in line else "social"
                            # Pattern count is extracted but patterns themselves would need more parsing
                        elif line.startswith("  * \""):
                            # Extract pattern content
                            pattern = line[5:].rstrip('..."')
                            if "personal" in [k for k in parsed["voice_patterns"].keys() if parsed["voice_patterns"][k]]:
                                parsed["voice_patterns"]["personal"].append(pattern)
                            else:
                                parsed["voice_patterns"]["social"].append(pattern)
                                
                    elif current_section == "voice_characteristics":
                        if line.startswith("- "):
                            key_value = line[2:].split(": ", 1)
                            if len(key_value) == 2:
                                key = key_value[0].lower().replace(" ", "_")
                                value = key_value[1]
                                # Convert numeric values
                                if key == "voice_influence":
                                    try:
                                        value = float(value)
                                    except ValueError:
                                        pass
                                parsed["voice_characteristics"][key] = value
                                
                    elif current_section == "original_query":
                        if not line.startswith("Original Query:"):
                            parsed["original_query"] += line + " "
                            
            # Clean up original query
            parsed["original_query"] = parsed["original_query"].strip()
            
            return parsed
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice analysis parsing failed: {str(e)}")
            return {
                "query_analysis": {},
                "voice_patterns": {"personal": [], "social": []},
                "voice_characteristics": {"tone": "professional", "audience": "general"},
                "original_query": ""
            }
            
    async def _gather_drafting_voice_patterns(
        self, 
        original_query: str, 
        voice_characteristics: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Gather voice patterns specifically for drafting from personal and social corpora"""
        voice_patterns = {"personal": [], "social": []}
        
        try:
            # Focus on personal corpus for conversational style
            if "personal" in self.corpus_access:
                try:
                    personal_results = await personal_search(
                        None,  # RunContext would be provided in real implementation
                        original_query,
                        PersonalSearchFilters(),
                        limit=8  # More results for drafting
                    )
                    
                    for result in personal_results.get("results", []):
                        content = result.get("content", "")
                        patterns = self._extract_conversational_patterns(content)
                        voice_patterns["personal"].extend(patterns)
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Personal corpus search for drafting failed: {str(e)}")
                    
            # Focus on social corpus for natural engagement
            if "social" in self.corpus_access:
                try:
                    social_results = await social_search(
                        None,  # RunContext would be provided in real implementation
                        original_query,
                        SocialSearchFilters(),
                        limit=8  # More results for drafting
                    )
                    
                    for result in social_results.get("results", []):
                        content = result.get("content", "")
                        patterns = self._extract_engagement_patterns(content)
                        voice_patterns["social"].extend(patterns)
                        
                except Exception as e:
                    self.audit_logger.log_warning(f"Social corpus search for drafting failed: {str(e)}")
                    
        except Exception as e:
            self.audit_logger.log_error(f"Drafting voice pattern gathering failed: {str(e)}")
            
        return voice_patterns
        
    def _extract_conversational_patterns(self, content: str) -> List[str]:
        """Extract conversational patterns from personal content"""
        patterns = []
        
        try:
            # Look for personal expressions and conversational starters
            conversational_indicators = [
                r"I think .*?[.!?]",
                r"In my experience .*?[.!?]",
                r"What I've found .*?[.!?]",
                r"The way I see it .*?[.!?]",
                r"From my perspective .*?[.!?]",
                r"I believe .*?[.!?]",
                r"It seems to me .*?[.!?]",
                r"I've noticed .*?[.!?]"
            ]
            
            for pattern in conversational_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:  # Limit to 2 per pattern
                    if 10 < len(match) < 100:  # Reasonable length
                        patterns.append(match.strip())
                        
        except Exception as e:
            self.audit_logger.log_error(f"Conversational pattern extraction failed: {str(e)}")
            
        return patterns[:3]  # Limit to top 3
        
    def _extract_engagement_patterns(self, content: str) -> List[str]:
        """Extract engagement patterns from social content"""
        patterns = []
        
        try:
            # Look for social engagement expressions
            engagement_indicators = [
                r"Thanks .*?[.!?]",
                r"Great .*?[.!?]",
                r"Love .*?[.!?]",
                r"Excited .*?[.!?]",
                r"Really .*?[.!?]",
                r"Appreciate .*?[.!?]",
                r"Looking forward .*?[.!?]",
                r"Happy to .*?[.!?]"
            ]
            
            for pattern in engagement_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:  # Limit to 2 per pattern
                    if 10 < len(match) < 100:  # Reasonable length
                        patterns.append(match.strip())
                        
        except Exception as e:
            self.audit_logger.log_error(f"Engagement pattern extraction failed: {str(e)}")
            
        return patterns[:3]  # Limit to top 3
        
    def _create_drafting_prompt(
        self,
        original_query: str,
        voice_characteristics: Dict[str, Any],
        voice_patterns: Dict[str, List[str]]
    ) -> str:
        """Create voice-enhanced prompt for drafting"""
        try:
            prompt_parts = []
            
            # Add voice context
            tone = voice_characteristics.get("tone", "professional")
            audience = voice_characteristics.get("audience", "general")
            
            prompt_parts.append(f"Create a response in a {tone} tone for a {audience} audience.")
            
            # Add personal voice patterns
            personal_patterns = voice_patterns.get("personal", [])
            if personal_patterns:
                prompt_parts.append(f"Use personal expressions like: {', '.join(personal_patterns[:3])}")
                
            # Add social voice patterns
            social_patterns = voice_patterns.get("social", [])
            if social_patterns:
                prompt_parts.append(f"Include engaging elements like: {', '.join(social_patterns[:3])}")
                
            # Add the original query
            prompt_parts.append(f"Respond to this query: {original_query}")
            
            # Add drafting instructions
            prompt_parts.append("Create a natural, conversational response that sounds authentic and personal.")
            
            return "\n\n".join(prompt_parts)
            
        except Exception as e:
            self.audit_logger.log_error(f"Drafting prompt creation failed: {str(e)}")
            return f"Respond to: {original_query}"
            
    async def _generate_voice_draft(
        self,
        drafting_prompt: str,
        voice_characteristics: Dict[str, Any],
        voice_patterns: Dict[str, List[str]],
        task_id: str
    ) -> str:
        """Generate initial draft using voice patterns"""
        try:
            # Create voice context for generation
            all_patterns = []
            all_patterns.extend(voice_patterns.get("personal", []))
            all_patterns.extend(voice_patterns.get("social", []))
            
            voice_context = VoiceContext(
                voice_patterns=all_patterns[:5],  # Limit to top 5
                tone=voice_characteristics.get("tone", "professional"),
                audience=voice_characteristics.get("audience", "general"),
                context_type="draft",
                corpus_sources=["personal", "social"],  # Drafter's accessible corpora
                influence_level=float(voice_characteristics.get("voice_influence", 0.7))
            )
            
            # Generate using voice-aware text generator
            draft, voice_patterns_used = await self.voice_generator.generate_with_voice(
                user_query=drafting_prompt,
                voice_context=voice_context,
                agent_role=self.role,
                task_id=task_id
            )
            
            # Post-process draft for natural flow
            processed_draft = self._post_process_draft(draft, voice_characteristics)
            
            return processed_draft
            
        except Exception as e:
            self.audit_logger.log_error(f"Voice draft generation failed: {str(e)}")
            # Fallback to simple response
            return f"I understand you're asking about: {drafting_prompt.split('Respond to this query: ')[-1]}"
            
    def _post_process_draft(self, draft: str, voice_characteristics: Dict[str, Any]) -> str:
        """Post-process draft for natural flow and voice consistency"""
        try:
            processed = draft
            
            # Remove any prompt artifacts
            if "Create a response" in processed:
                processed = processed.split("Create a response")[-1]
            if "Respond to this query:" in processed:
                processed = processed.split("Respond to this query:")[-1]
                
            # Clean up formatting
            processed = processed.strip()
            
            # Ensure appropriate tone
            tone = voice_characteristics.get("tone", "professional")
            if tone == "casual":
                # Make more casual if needed
                processed = processed.replace("Furthermore,", "Also,")
                processed = processed.replace("Therefore,", "So,")
            elif tone == "professional":
                # Ensure professional language
                processed = processed.replace(" gonna ", " going to ")
                processed = processed.replace(" wanna ", " want to ")
                
            # Ensure reasonable length (not too short or too long)
            if len(processed) < 50:
                processed += " I hope this helps address your question."
            elif len(processed) > 500:
                # Truncate if too long, but preserve sentence structure
                sentences = processed.split('.')
                truncated = []
                current_length = 0
                for sentence in sentences:
                    if current_length + len(sentence) < 450:
                        truncated.append(sentence)
                        current_length += len(sentence)
                    else:
                        break
                processed = '.'.join(truncated) + '.'
                
            return processed
            
        except Exception as e:
            self.audit_logger.log_error(f"Draft post-processing failed: {str(e)}")
            return draft  # Return original if post-processing fails


__all__ = ["VoiceAwareDrafterAgent"]
