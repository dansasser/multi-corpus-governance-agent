"""Voice adaptation protocols defining interfaces for dynamic voice adaptation."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from ...voice.voice_fingerprint_extractor import VoiceFingerprint


class AdaptationStrategy(Enum):
    """Voice adaptation strategies."""
    PRESERVE_ORIGINAL = "preserve_original"
    ADAPT_TO_AUDIENCE = "adapt_to_audience"
    BLEND_CONTEXTS = "blend_contexts"
    CONTEXT_SPECIFIC = "context_specific"


class ContextType(Enum):
    """Types of communication contexts."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FORMAL = "formal"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    SOCIAL = "social"
    PERSONAL = "personal"


@dataclass
class AdaptationContext:
    """Context information for voice adaptation."""
    context_type: ContextType
    audience: Optional[str] = None
    platform: Optional[str] = None
    purpose: Optional[str] = None
    tone_preference: Optional[str] = None
    formality_level: Optional[float] = None  # 0.0 = very casual, 1.0 = very formal
    urgency_level: Optional[float] = None    # 0.0 = no urgency, 1.0 = very urgent
    relationship_level: Optional[str] = None # "stranger", "acquaintance", "friend", "family"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AdaptationResult:
    """Result of voice adaptation process."""
    adapted_voice_context: Dict[str, Any]
    adaptation_strategy: AdaptationStrategy
    confidence_score: float
    adaptation_notes: List[str]
    original_patterns_preserved: List[str]
    patterns_modified: List[str]
    context_analysis: Dict[str, Any]
    performance_metrics: Dict[str, float]


class VoiceAdaptationProtocol(ABC):
    """Protocol for voice adaptation systems."""
    
    @abstractmethod
    async def adapt_voice(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy = AdaptationStrategy.ADAPT_TO_AUDIENCE
    ) -> AdaptationResult:
        """
        Adapt voice patterns based on context and strategy.
        
        Args:
            voice_fingerprint: User's voice fingerprint
            context: Adaptation context information
            strategy: Adaptation strategy to use
            
        Returns:
            AdaptationResult with adapted voice context
        """
        pass
    
    @abstractmethod
    async def validate_adaptation(
        self,
        original_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any],
        context: AdaptationContext
    ) -> Dict[str, float]:
        """
        Validate that adaptation maintains voice authenticity.
        
        Args:
            original_fingerprint: Original voice fingerprint
            adapted_context: Adapted voice context
            context: Adaptation context
            
        Returns:
            Validation scores (authenticity, appropriateness, etc.)
        """
        pass
    
    @abstractmethod
    async def get_adaptation_strategies(
        self,
        context: AdaptationContext
    ) -> List[AdaptationStrategy]:
        """
        Get recommended adaptation strategies for context.
        
        Args:
            context: Adaptation context
            
        Returns:
            List of recommended strategies
        """
        pass


class ContextAnalysisProtocol(ABC):
    """Protocol for context analysis systems."""
    
    @abstractmethod
    async def analyze_context(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AdaptationContext:
        """
        Analyze text and metadata to determine context.
        
        Args:
            text: Text to analyze
            metadata: Additional context metadata
            
        Returns:
            AdaptationContext with analysis results
        """
        pass
    
    @abstractmethod
    async def extract_audience_info(
        self,
        context: AdaptationContext,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract detailed audience information.
        
        Args:
            context: Base context information
            additional_data: Additional audience data
            
        Returns:
            Detailed audience analysis
        """
        pass
    
    @abstractmethod
    async def determine_formality_level(
        self,
        context: AdaptationContext
    ) -> float:
        """
        Determine appropriate formality level for context.
        
        Args:
            context: Context to analyze
            
        Returns:
            Formality level (0.0 = casual, 1.0 = formal)
        """
        pass


class AdaptationStrategyProtocol(ABC):
    """Protocol for adaptation strategy implementations."""
    
    @abstractmethod
    async def apply_strategy(
        self,
        voice_fingerprint: VoiceFingerprint,
        context: AdaptationContext,
        strategy: AdaptationStrategy
    ) -> Dict[str, Any]:
        """
        Apply specific adaptation strategy.
        
        Args:
            voice_fingerprint: User's voice fingerprint
            context: Adaptation context
            strategy: Strategy to apply
            
        Returns:
            Adapted voice context
        """
        pass
    
    @abstractmethod
    async def blend_voice_patterns(
        self,
        patterns: List[Dict[str, Any]],
        weights: List[float],
        context: AdaptationContext
    ) -> Dict[str, Any]:
        """
        Blend multiple voice patterns with weights.
        
        Args:
            patterns: Voice patterns to blend
            weights: Blending weights
            context: Adaptation context
            
        Returns:
            Blended voice context
        """
        pass
    
    @abstractmethod
    async def preserve_core_voice(
        self,
        voice_fingerprint: VoiceFingerprint,
        adapted_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensure core voice characteristics are preserved.
        
        Args:
            voice_fingerprint: Original voice fingerprint
            adapted_context: Adapted voice context
            
        Returns:
            Context with core voice preserved
        """
        pass
