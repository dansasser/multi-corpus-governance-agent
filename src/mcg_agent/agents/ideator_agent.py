"""
Ideator Agent implementation for Multi-Corpus Governance Agent.

The Ideator is the first agent in the pipeline responsible for:
- Analyzing user prompts and generating structured outlines
- Performing initial corpus queries for context
- Creating tone and coverage scoring annotations
- Establishing the foundation for subsequent agents

Governance Rules:
- Maximum 2 API calls allowed
- May query all corpus types (Personal, Social, Published)
- RAG access only for coverage gap filling
- Must preserve attribution for all sources
- Must generate structured outline with metadata
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum
import json

from pydantic import BaseModel, Field, validator

from .base_agent import (
    BaseAgent, 
    AgentResult, 
    AgentInput, 
    AgentCapability, 
    AgentState
)
from ..governance.protocol import AgentRole
from ..utils.exceptions import GovernanceViolationError, MCGBaseException


class IdeatorMode(str, Enum):
    """Ideator execution modes."""
    OUTLINE = "outline"           # Generate structured outline
    BRAINSTORM = "brainstorm"     # Generate idea variations
    RESEARCH = "research"         # Research-focused ideation
    CREATIVE = "creative"         # Creative content ideation


class ToneProfile(str, Enum):
    """Tone profiles for content analysis."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    PERSUASIVE = "persuasive"
    EDUCATIONAL = "educational"
    CONVERSATIONAL = "conversational"


class IdeatorInput(AgentInput):
    """Input model for Ideator agent."""
    mode: IdeatorMode = Field(default=IdeatorMode.OUTLINE, description="Ideation mode")
    target_audience: Optional[str] = Field(None, description="Target audience for content")
    content_type: Optional[str] = Field(None, description="Type of content to create")
    tone_preference: Optional[ToneProfile] = Field(None, description="Preferred tone profile")
    context_depth: int = Field(default=3, ge=1, le=10, description="Depth of context research")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v.strip() if v else None


class OutlinePoint(BaseModel):
    """Individual outline point with metadata."""
    title: str = Field(..., description="Point title")
    content: str = Field(..., description="Point content/description")
    priority: int = Field(..., ge=1, le=10, description="Priority level (1-10)")
    sources: List[str] = Field(default_factory=list, description="Supporting sources")
    tone_notes: Optional[str] = Field(None, description="Tone guidance for this point")


class IdeatorOutput(BaseModel):
    """Structured output from Ideator agent."""
    outline: List[OutlinePoint] = Field(..., description="Generated outline points")
    tone_analysis: Dict[str, Any] = Field(..., description="Tone analysis and scoring")
    coverage_analysis: Dict[str, Any] = Field(..., description="Content coverage analysis")
    research_sources: List[Dict[str, Any]] = Field(default_factory=list, description="Research sources used")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for next stages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IdeatorAgent(BaseAgent):
    """
    Ideator Agent implementation with comprehensive logging and governance.
    
    Responsibilities:
    1. Analyze user prompts for intent and requirements
    2. Generate structured outlines with priority scoring
    3. Perform contextual corpus research
    4. Provide tone and coverage analysis
    5. Set foundation for subsequent pipeline stages
    """
    
    def __init__(self):
        """Initialize Ideator agent."""
        super().__init__(
            agent_name="IdeatorAgent",
            agent_role=AgentRole.IDEATOR,
            capabilities=[
                AgentCapability.API_CALLS,
                AgentCapability.CORPUS_QUERY,
                AgentCapability.CONTENT_GENERATION,
                AgentCapability.VALIDATION
            ],
            max_api_calls=2,
            max_corpus_queries=3
        )
        
        # Ideator-specific configuration
        self.supported_modes = list(IdeatorMode)
        self.default_outline_points = 5
        self.min_outline_points = 2
        self.max_outline_points = 10
        
    async def _execute_agent_logic(
        self,
        agent_input: AgentInput,
        **kwargs
    ) -> AgentResult:
        """Execute Ideator agent logic with comprehensive monitoring."""
        
        # Convert to IdeatorInput if needed
        if isinstance(agent_input, dict):
            ideator_input = IdeatorInput(**agent_input)
        elif isinstance(agent_input, AgentInput):
            ideator_input = IdeatorInput(
                content=agent_input.content,
                context_sources=agent_input.context_sources,
                parameters=agent_input.parameters
            )
        else:
            ideator_input = agent_input
        
        await self.logger.info(f"Starting ideation in {ideator_input.mode} mode")
        await self.logger.log_checkpoint("ideation_start")
        
        try:
            # Step 1: Analyze the input prompt
            prompt_analysis = await self._analyze_prompt(ideator_input)
            await self.logger.log_checkpoint("prompt_analysis_complete", prompt_analysis)
            
            # Step 2: Gather contextual information
            context_data = await self._gather_context(ideator_input, prompt_analysis)
            await self.logger.log_checkpoint("context_gathering_complete")
            
            # Step 3: Generate initial outline
            outline = await self._generate_outline(ideator_input, prompt_analysis, context_data)
            await self.logger.log_checkpoint("outline_generation_complete")
            
            # Step 4: Perform tone analysis
            tone_analysis = await self._analyze_tone(ideator_input, outline, context_data)
            await self.logger.log_checkpoint("tone_analysis_complete")
            
            # Step 5: Analyze coverage and gaps
            coverage_analysis = await self._analyze_coverage(outline, context_data)
            await self.logger.log_checkpoint("coverage_analysis_complete")
            
            # Step 6: Generate recommendations
            recommendations = await self._generate_recommendations(
                ideator_input, outline, tone_analysis, coverage_analysis
            )
            await self.logger.log_checkpoint("recommendations_complete")
            
            # Create structured output
            ideator_output = IdeatorOutput(
                outline=outline,
                tone_analysis=tone_analysis,
                coverage_analysis=coverage_analysis,
                research_sources=context_data.get("sources", []),
                recommendations=recommendations,
                metadata={
                    "mode": ideator_input.mode,
                    "target_audience": ideator_input.target_audience,
                    "content_type": ideator_input.content_type,
                    "processing_time_ms": self.get_performance_stats()["execution_time_ms"]
                }
            )
            
            # Create attribution chain
            attribution = self._create_attribution_chain(context_data, ideator_output)
            
            await self.logger.info(f"Ideation completed successfully with {len(outline)} outline points")
            
            return AgentResult(
                success=True,
                content=self._format_outline_output(ideator_output),
                metadata=ideator_output.metadata,
                attribution=attribution,
                performance_metrics=self.get_performance_stats(),
                governance_summary=self._get_governance_summary()
            )
            
        except Exception as e:
            await self.logger.error(f"Ideation failed: {str(e)}", error=e)
            raise MCGBaseException(f"Ideator agent execution failed: {str(e)}")
    
    async def _analyze_prompt(self, ideator_input: IdeatorInput) -> Dict[str, Any]:
        """Analyze the input prompt for intent and requirements."""
        
        await self.logger.debug("Analyzing input prompt")
        self.logger.start_timer("prompt_analysis")
        
        # Extract key information from prompt
        prompt = ideator_input.content
        
        # Basic analysis (would be enhanced with AI in full implementation)
        analysis = {
            "word_count": len(prompt.split()),
            "character_count": len(prompt),
            "detected_intent": self._detect_intent(prompt),
            "complexity_score": self._calculate_complexity_score(prompt),
            "key_topics": self._extract_key_topics(prompt),
            "questions": self._extract_questions(prompt),
            "requirements": self._extract_requirements(prompt)
        }
        
        # Log performance metric
        analysis_time = self.logger.stop_timer("prompt_analysis")
        await self.logger.log_performance_metric(
            "prompt_analysis_time_ms", 
            analysis_time, 
            "milliseconds",
            {"word_count": analysis["word_count"]}
        )
        
        await self.logger.debug(f"Prompt analysis complete: {analysis['detected_intent']}")
        return analysis
    
    async def _gather_context(
        self,
        ideator_input: IdeatorInput,
        prompt_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gather contextual information from available corpora."""
        
        await self.logger.debug("Gathering contextual information")
        self.logger.start_timer("context_gathering")
        
        context_data = {
            "sources": [],
            "personal_context": [],
            "social_context": [],
            "published_context": []
        }
        
        # Query each corpus type based on key topics
        key_topics = prompt_analysis.get("key_topics", [])
        
        for topic in key_topics[:ideator_input.context_depth]:
            # Query personal corpus
            try:
                personal_results = await self.query_corpus("personal", topic, max_results=2)
                context_data["personal_context"].extend(personal_results)
                await self.logger.debug(f"Found {len(personal_results)} personal context items for '{topic}'")
            except Exception as e:
                await self.logger.warning(f"Personal corpus query failed for '{topic}': {str(e)}")
            
            # Query social corpus
            try:
                social_results = await self.query_corpus("social", topic, max_results=2)
                context_data["social_context"].extend(social_results)
                await self.logger.debug(f"Found {len(social_results)} social context items for '{topic}'")
            except Exception as e:
                await self.logger.warning(f"Social corpus query failed for '{topic}': {str(e)}")
        
        # Compile sources for attribution
        all_results = (
            context_data["personal_context"] + 
            context_data["social_context"] + 
            context_data["published_context"]
        )
        
        context_data["sources"] = [
            {
                "id": result.get("id"),
                "type": result.get("source"),
                "content_preview": result.get("content", "")[:100],
                "timestamp": result.get("timestamp")
            }
            for result in all_results
        ]
        
        context_time = self.logger.stop_timer("context_gathering")
        await self.logger.log_performance_metric(
            "context_gathering_time_ms",
            context_time,
            "milliseconds",
            {"sources_found": len(all_results)}
        )
        
        await self.logger.info(f"Context gathering complete: {len(all_results)} sources found")
        return context_data
    
    async def _generate_outline(
        self,
        ideator_input: IdeatorInput,
        prompt_analysis: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> List[OutlinePoint]:
        """Generate structured outline based on analysis and context."""
        
        await self.logger.debug("Generating content outline")
        self.logger.start_timer("outline_generation")
        
        # For full implementation, this would use AI API calls
        # Currently using rule-based generation for testing
        
        key_topics = prompt_analysis.get("key_topics", [])
        requirements = prompt_analysis.get("requirements", [])
        
        outline_points = []
        
        # Create outline points from key topics
        for i, topic in enumerate(key_topics[:self.max_outline_points]):
            # Find supporting sources
            supporting_sources = [
                source["id"] for source in context_data.get("sources", [])
                if topic.lower() in source.get("content_preview", "").lower()
            ]
            
            outline_point = OutlinePoint(
                title=f"Key Point: {topic.title()}",
                content=f"Detailed discussion of {topic} based on available context and requirements.",
                priority=min(10, max(1, 10 - i)),  # Decreasing priority
                sources=supporting_sources[:3],  # Limit to 3 sources per point
                tone_notes=f"Maintain {ideator_input.tone_preference or 'professional'} tone"
            )
            
            outline_points.append(outline_point)
        
        # Add requirement-based points
        for req in requirements[:3]:  # Limit additional points
            if len(outline_points) >= self.max_outline_points:
                break
                
            outline_point = OutlinePoint(
                title=f"Requirement: {req[:50]}...",
                content=f"Address the specific requirement: {req}",
                priority=8,  # High priority for explicit requirements
                sources=[],
                tone_notes="Focus on clarity and completeness"
            )
            
            outline_points.append(outline_point)
        
        # Ensure minimum outline points
        while len(outline_points) < self.min_outline_points:
            outline_point = OutlinePoint(
                title=f"Supporting Point {len(outline_points) + 1}",
                content="Additional supporting information and context.",
                priority=5,
                sources=[],
                tone_notes="Maintain consistency with main points"
            )
            outline_points.append(outline_point)
        
        outline_time = self.logger.stop_timer("outline_generation")
        await self.logger.log_performance_metric(
            "outline_generation_time_ms",
            outline_time,
            "milliseconds",
            {"outline_points": len(outline_points)}
        )
        
        await self.logger.info(f"Outline generation complete: {len(outline_points)} points created")
        return outline_points
    
    async def _analyze_tone(
        self,
        ideator_input: IdeatorInput,
        outline: List[OutlinePoint],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze tone requirements and provide guidance."""
        
        await self.logger.debug("Analyzing tone requirements")
        
        # Analyze existing content tone from context
        tone_samples = []
        for source in context_data.get("sources", []):
            if source.get("content_preview"):
                tone_samples.append(source["content_preview"])
        
        # Basic tone analysis (would use AI in full implementation)
        tone_analysis = {
            "target_tone": ideator_input.tone_preference or ToneProfile.PROFESSIONAL,
            "detected_patterns": self._analyze_tone_patterns(tone_samples),
            "consistency_score": 0.85,  # Mock score
            "recommendations": [
                f"Maintain {ideator_input.tone_preference or 'professional'} tone throughout",
                "Ensure consistency across all outline points",
                "Consider audience expectations and context"
            ],
            "tone_flags": [],
            "voice_matching_score": 0.78  # Mock score
        }
        
        await self.logger.debug(f"Tone analysis complete: target={tone_analysis['target_tone']}")
        return tone_analysis
    
    async def _analyze_coverage(
        self,
        outline: List[OutlinePoint],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze content coverage and identify gaps."""
        
        await self.logger.debug("Analyzing content coverage")
        
        # Analyze coverage based on outline and available context
        total_sources = len(context_data.get("sources", []))
        covered_topics = set()
        
        for point in outline:
            # Extract topics from outline point
            point_topics = self._extract_key_topics(f"{point.title} {point.content}")
            covered_topics.update(point_topics)
        
        coverage_analysis = {
            "coverage_score": min(1.0, len(covered_topics) / max(5, len(covered_topics))),
            "covered_topics": list(covered_topics),
            "source_utilization": len([p for p in outline if p.sources]) / len(outline) if outline else 0,
            "gaps_identified": [],
            "recommendations": [
                "Strong coverage of main topics",
                "Good source utilization",
                "Consider expanding on key points"
            ],
            "metadata": {
                "total_outline_points": len(outline),
                "points_with_sources": len([p for p in outline if p.sources]),
                "total_sources_available": total_sources
            }
        }
        
        await self.logger.debug(f"Coverage analysis complete: score={coverage_analysis['coverage_score']:.2f}")
        return coverage_analysis
    
    async def _generate_recommendations(
        self,
        ideator_input: IdeatorInput,
        outline: List[OutlinePoint],
        tone_analysis: Dict[str, Any],
        coverage_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for subsequent pipeline stages."""
        
        await self.logger.debug("Generating recommendations")
        
        recommendations = []
        
        # Recommendations based on outline
        if len(outline) > 7:
            recommendations.append("Consider consolidating outline points for better focus")
        elif len(outline) < 3:
            recommendations.append("Consider expanding outline with additional supporting points")
        
        # Recommendations based on tone analysis
        if tone_analysis.get("consistency_score", 0) < 0.7:
            recommendations.append("Pay special attention to tone consistency during drafting")
        
        # Recommendations based on coverage
        if coverage_analysis.get("coverage_score", 0) < 0.6:
            recommendations.append("Consider additional research to improve content coverage")
        
        # Source-based recommendations
        source_count = sum(len(p.sources) for p in outline)
        if source_count < len(outline):
            recommendations.append("Gather additional sources to support all outline points")
        
        # Mode-specific recommendations
        if ideator_input.mode == IdeatorMode.TECHNICAL:
            recommendations.append("Ensure technical accuracy and include relevant examples")
        elif ideator_input.mode == IdeatorMode.CREATIVE:
            recommendations.append("Focus on engaging narrative and creative elements")
        
        # Always include general recommendations
        recommendations.extend([
            "Maintain attribution for all source materials",
            "Preserve tone consistency throughout content development",
            "Validate claims and ensure factual accuracy"
        ])
        
        await self.logger.debug(f"Generated {len(recommendations)} recommendations")
        return recommendations
    
    def _format_outline_output(self, ideator_output: IdeatorOutput) -> str:
        """Format the outline for human readability."""
        
        output_lines = ["# Content Outline", ""]
        
        # Add outline points
        for i, point in enumerate(ideator_output.outline, 1):
            output_lines.extend([
                f"## {i}. {point.title}",
                f"**Priority:** {point.priority}/10",
                f"**Content:** {point.content}",
                ""
            ])
            
            if point.sources:
                output_lines.append(f"**Sources:** {', '.join(point.sources)}")
                output_lines.append("")
            
            if point.tone_notes:
                output_lines.append(f"**Tone Notes:** {point.tone_notes}")
                output_lines.append("")
        
        # Add analysis summaries
        output_lines.extend([
            "## Tone Analysis",
            f"- Target Tone: {ideator_output.tone_analysis.get('target_tone', 'Not specified')}",
            f"- Consistency Score: {ideator_output.tone_analysis.get('consistency_score', 0):.2f}",
            "",
            "## Coverage Analysis", 
            f"- Coverage Score: {ideator_output.coverage_analysis.get('coverage_score', 0):.2f}",
            f"- Sources Used: {len(ideator_output.research_sources)}",
            ""
        ])
        
        # Add recommendations
        if ideator_output.recommendations:
            output_lines.extend(["## Recommendations"])
            for rec in ideator_output.recommendations:
                output_lines.append(f"- {rec}")
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    def _create_attribution_chain(
        self,
        context_data: Dict[str, Any],
        ideator_output: IdeatorOutput
    ) -> List[Dict[str, Any]]:
        """Create attribution chain for all sources used."""
        
        attribution = []
        
        # Add source attributions
        for source in context_data.get("sources", []):
            attribution.append({
                "source_id": source.get("id"),
                "source_type": source.get("type"),
                "usage": "context_research",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": self.agent_name
            })
        
        # Add outline point attributions
        for point in ideator_output.outline:
            if point.sources:
                for source_id in point.sources:
                    attribution.append({
                        "source_id": source_id,
                        "usage": f"outline_point_{point.title}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "agent": self.agent_name
                    })
        
        return attribution
    
    def _get_governance_summary(self) -> Dict[str, Any]:
        """Get governance compliance summary."""
        return {
            "api_calls_used": self._api_call_count,
            "api_calls_limit": self.max_api_calls,
            "corpus_queries_used": self._corpus_query_count,
            "corpus_queries_limit": self.max_corpus_queries,
            "governance_compliant": True,
            "role": self.agent_role.value,
            "capabilities_used": [cap.value for cap in self.capabilities]
        }
    
    # Utility methods for text analysis
    
    def _detect_intent(self, prompt: str) -> str:
        """Detect the intent of the input prompt."""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["create", "write", "draft", "compose"]):
            return "content_creation"
        elif any(word in prompt_lower for word in ["analyze", "review", "examine", "study"]):
            return "content_analysis"
        elif any(word in prompt_lower for word in ["improve", "enhance", "optimize", "refine"]):
            return "content_improvement"
        elif any(word in prompt_lower for word in ["explain", "describe", "define", "clarify"]):
            return "explanation"
        else:
            return "general_request"
    
    def _calculate_complexity_score(self, prompt: str) -> float:
        """Calculate complexity score of the prompt."""
        # Simple complexity scoring based on length and structure
        word_count = len(prompt.split())
        sentence_count = len([s for s in prompt.split('.') if s.strip()])
        question_count = prompt.count('?')
        
        # Normalize to 0-1 scale
        complexity = min(1.0, (word_count / 100) + (sentence_count / 10) + (question_count / 5))
        return complexity
    
    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        # Simple keyword extraction (would use NLP in full implementation)
        import re
        
        # Remove common words and extract meaningful terms
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stop_words = {
            'that', 'this', 'with', 'from', 'they', 'been', 'have', 'their', 
            'said', 'each', 'which', 'these', 'about', 'would', 'there'
        }
        
        meaningful_words = [word for word in words if word not in stop_words]
        
        # Return top topics (simplified)
        return list(set(meaningful_words))[:5]
    
    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions from the text."""
        sentences = text.split('.')
        questions = [s.strip() + '?' for s in sentences if '?' in s]
        return questions
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract explicit requirements from text."""
        requirements = []
        
        # Look for requirement indicators
        req_patterns = [
            r'must\s+(.+?)(?:\.|$)',
            r'should\s+(.+?)(?:\.|$)',
            r'need\s+to\s+(.+?)(?:\.|$)',
            r'required?\s+to\s+(.+?)(?:\.|$)'
        ]
        
        import re
        for pattern in req_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend([match.strip() for match in matches])
        
        return requirements[:5]  # Limit to 5 requirements
    
    def _analyze_tone_patterns(self, text_samples: List[str]) -> Dict[str, Any]:
        """Analyze tone patterns in text samples."""
        if not text_samples:
            return {"patterns": [], "confidence": 0.0}
        
        # Simple tone pattern analysis
        combined_text = ' '.join(text_samples).lower()
        
        patterns = []
        if any(word in combined_text for word in ['however', 'furthermore', 'therefore']):
            patterns.append("formal")
        if any(word in combined_text for word in ['great', 'awesome', 'cool', 'nice']):
            patterns.append("casual")
        if any(word in combined_text for word in ['analyze', 'implement', 'optimize', 'configure']):
            patterns.append("technical")
        
        return {
            "patterns": patterns,
            "confidence": 0.7,  # Mock confidence
            "sample_count": len(text_samples)
        }