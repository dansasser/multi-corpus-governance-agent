"""Voice learning protocols defining interfaces for voice evolution and improvement."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ...voice.voice_fingerprint_extractor import VoiceFingerprint


class FeedbackType(Enum):
    """Types of voice feedback."""
    AUTHENTICITY = "authenticity"
    APPROPRIATENESS = "appropriateness"
    CLARITY = "clarity"
    TONE = "tone"
    STYLE = "style"
    ENGAGEMENT = "engagement"
    OVERALL = "overall"


class LearningMode(Enum):
    """Voice learning modes."""
    PASSIVE = "passive"          # Learn from usage patterns
    ACTIVE = "active"            # Learn from explicit feedback
    REINFORCEMENT = "reinforcement"  # Learn from success/failure
    ADAPTIVE = "adaptive"        # Adapt learning based on context


@dataclass
class VoiceFeedback:
    """Voice feedback data structure."""
    feedback_type: FeedbackType
    score: float  # 0.0 to 1.0
    text_sample: str
    context: Dict[str, Any]
    timestamp: datetime
    source: str  # "user", "system", "automatic"
    notes: Optional[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class VoiceEvolutionRecord:
    """Record of voice pattern evolution."""
    timestamp: datetime
    pattern_changes: Dict[str, Any]
    trigger_event: str
    confidence_change: float
    performance_impact: Dict[str, float]
    rollback_data: Optional[Dict[str, Any]] = None


@dataclass
class LearningSession:
    """Voice learning session data."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    learning_mode: LearningMode
    feedback_items: List[VoiceFeedback]
    patterns_learned: List[str]
    improvements_made: List[str]
    performance_metrics: Dict[str, float]


class VoiceLearningProtocol(ABC):
    """Protocol for voice learning systems."""
    
    @abstractmethod
    async def learn_from_usage(
        self,
        voice_fingerprint: VoiceFingerprint,
        usage_data: List[Dict[str, Any]],
        learning_mode: LearningMode = LearningMode.PASSIVE
    ) -> VoiceFingerprint:
        """
        Learn and update voice patterns from usage data.
        
        Args:
            voice_fingerprint: Current voice fingerprint
            usage_data: Usage data to learn from
            learning_mode: Learning mode to use
            
        Returns:
            Updated voice fingerprint
        """
        pass
    
    @abstractmethod
    async def apply_feedback(
        self,
        voice_fingerprint: VoiceFingerprint,
        feedback: VoiceFeedback
    ) -> Tuple[VoiceFingerprint, List[str]]:
        """
        Apply feedback to improve voice patterns.
        
        Args:
            voice_fingerprint: Current voice fingerprint
            feedback: Feedback to apply
            
        Returns:
            Tuple of (updated fingerprint, improvement notes)
        """
        pass
    
    @abstractmethod
    async def start_learning_session(
        self,
        learning_mode: LearningMode,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new learning session.
        
        Args:
            learning_mode: Learning mode for session
            context: Optional session context
            
        Returns:
            Session ID
        """
        pass
    
    @abstractmethod
    async def end_learning_session(
        self,
        session_id: str
    ) -> LearningSession:
        """
        End learning session and return results.
        
        Args:
            session_id: Session to end
            
        Returns:
            Completed learning session data
        """
        pass


class FeedbackProcessingProtocol(ABC):
    """Protocol for feedback processing systems."""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class EvolutionTrackingProtocol(ABC):
    """Protocol for voice evolution tracking systems."""
    
    @abstractmethod
    async def track_evolution(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint,
        trigger_event: str
    ) -> VoiceEvolutionRecord:
        """
        Track voice pattern evolution.
        
        Args:
            old_fingerprint: Previous voice fingerprint
            new_fingerprint: Updated voice fingerprint
            trigger_event: Event that triggered evolution
            
        Returns:
            Evolution record
        """
        pass
    
    @abstractmethod
    async def analyze_evolution_trends(
        self,
        evolution_history: List[VoiceEvolutionRecord],
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Analyze voice evolution trends.
        
        Args:
            evolution_history: Historical evolution records
            time_window: Optional time window filter
            
        Returns:
            Evolution trend analysis
        """
        pass
    
    @abstractmethod
    async def detect_regression(
        self,
        evolution_history: List[VoiceEvolutionRecord],
        performance_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Detect voice quality regression.
        
        Args:
            evolution_history: Historical evolution records
            performance_threshold: Minimum performance threshold
            
        Returns:
            List of detected regressions
        """
        pass
    
    @abstractmethod
    async def recommend_rollback(
        self,
        current_fingerprint: VoiceFingerprint,
        evolution_history: List[VoiceEvolutionRecord]
    ) -> Optional[VoiceFingerprint]:
        """
        Recommend rollback to previous voice state if needed.
        
        Args:
            current_fingerprint: Current voice fingerprint
            evolution_history: Historical evolution records
            
        Returns:
            Recommended rollback fingerprint or None
        """
        pass
