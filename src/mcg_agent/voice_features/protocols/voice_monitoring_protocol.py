"""Voice monitoring protocols defining interfaces for consistency and drift detection."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ...voice.voice_fingerprint_extractor import VoiceFingerprint


class MonitoringLevel(Enum):
    """Voice monitoring levels."""
    BASIC = "basic"              # Basic consistency checks
    STANDARD = "standard"        # Standard monitoring with alerts
    COMPREHENSIVE = "comprehensive"  # Full monitoring with analytics
    REAL_TIME = "real_time"      # Real-time monitoring


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DriftType(Enum):
    """Types of voice drift."""
    GRADUAL = "gradual"          # Slow drift over time
    SUDDEN = "sudden"            # Abrupt change
    CONTEXTUAL = "contextual"    # Context-specific drift
    SYSTEMATIC = "systematic"    # Systematic pattern change


@dataclass
class ConsistencyMetrics:
    """Voice consistency measurement metrics."""
    overall_score: float         # 0.0 to 1.0
    tone_consistency: float
    style_consistency: float
    vocabulary_consistency: float
    pattern_consistency: float
    temporal_consistency: float
    context_consistency: float
    measurement_timestamp: datetime
    sample_size: int
    confidence_interval: Tuple[float, float]


@dataclass
class VoiceDriftAlert:
    """Voice drift alert data structure."""
    alert_id: str
    severity: AlertSeverity
    drift_type: DriftType
    detected_at: datetime
    affected_patterns: List[str]
    drift_magnitude: float
    confidence_score: float
    recommended_actions: List[str]
    context: Dict[str, Any]
    auto_correctable: bool


@dataclass
class MonitoringReport:
    """Voice monitoring report."""
    report_id: str
    generated_at: datetime
    monitoring_period: Tuple[datetime, datetime]
    consistency_metrics: ConsistencyMetrics
    drift_alerts: List[VoiceDriftAlert]
    performance_trends: Dict[str, List[float]]
    recommendations: List[str]
    health_score: float


class VoiceMonitoringProtocol(ABC):
    """Protocol for voice monitoring systems."""
    
    @abstractmethod
    async def monitor_voice_consistency(
        self,
        voice_fingerprint: VoiceFingerprint,
        recent_outputs: List[str],
        monitoring_level: MonitoringLevel = MonitoringLevel.STANDARD
    ) -> ConsistencyMetrics:
        """
        Monitor voice consistency across recent outputs.
        
        Args:
            voice_fingerprint: Reference voice fingerprint
            recent_outputs: Recent text outputs to analyze
            monitoring_level: Level of monitoring detail
            
        Returns:
            Consistency metrics
        """
        pass
    
    @abstractmethod
    async def generate_monitoring_report(
        self,
        voice_fingerprint: VoiceFingerprint,
        time_period: Tuple[datetime, datetime],
        include_trends: bool = True
    ) -> MonitoringReport:
        """
        Generate comprehensive monitoring report.
        
        Args:
            voice_fingerprint: Voice fingerprint to monitor
            time_period: Time period for report
            include_trends: Whether to include trend analysis
            
        Returns:
            Monitoring report
        """
        pass
    
    @abstractmethod
    async def set_monitoring_thresholds(
        self,
        consistency_threshold: float = 0.8,
        drift_threshold: float = 0.2,
        alert_frequency: int = 24  # hours
    ) -> None:
        """
        Set monitoring thresholds and alert frequency.
        
        Args:
            consistency_threshold: Minimum consistency score
            drift_threshold: Maximum allowed drift
            alert_frequency: Alert frequency in hours
        """
        pass
    
    @abstractmethod
    async def get_health_status(
        self,
        voice_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """
        Get current voice health status.
        
        Args:
            voice_fingerprint: Voice fingerprint to check
            
        Returns:
            Health status information
        """
        pass


class ConsistencyCheckProtocol(ABC):
    """Protocol for voice consistency checking systems."""
    
    @abstractmethod
    async def check_tone_consistency(
        self,
        reference_patterns: Dict[str, Any],
        current_output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Check tone consistency against reference patterns.
        
        Args:
            reference_patterns: Reference voice patterns
            current_output: Current text output
            context: Optional context information
            
        Returns:
            Tone consistency score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    async def check_style_consistency(
        self,
        reference_patterns: Dict[str, Any],
        current_output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Check style consistency against reference patterns.
        
        Args:
            reference_patterns: Reference voice patterns
            current_output: Current text output
            context: Optional context information
            
        Returns:
            Style consistency score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    async def check_vocabulary_consistency(
        self,
        reference_patterns: Dict[str, Any],
        current_output: str
    ) -> float:
        """
        Check vocabulary consistency against reference patterns.
        
        Args:
            reference_patterns: Reference voice patterns
            current_output: Current text output
            
        Returns:
            Vocabulary consistency score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    async def aggregate_consistency_scores(
        self,
        individual_scores: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Aggregate individual consistency scores.
        
        Args:
            individual_scores: Individual consistency scores
            weights: Optional weights for aggregation
            
        Returns:
            Overall consistency score
        """
        pass


class DriftDetectionProtocol(ABC):
    """Protocol for voice drift detection systems."""
    
    @abstractmethod
    async def detect_drift(
        self,
        baseline_fingerprint: VoiceFingerprint,
        current_outputs: List[str],
        detection_sensitivity: float = 0.8
    ) -> List[VoiceDriftAlert]:
        """
        Detect voice drift from baseline.
        
        Args:
            baseline_fingerprint: Baseline voice fingerprint
            current_outputs: Recent outputs to analyze
            detection_sensitivity: Drift detection sensitivity
            
        Returns:
            List of drift alerts
        """
        pass
    
    @abstractmethod
    async def analyze_drift_patterns(
        self,
        drift_history: List[VoiceDriftAlert],
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Analyze patterns in voice drift.
        
        Args:
            drift_history: Historical drift alerts
            time_window: Optional time window filter
            
        Returns:
            Drift pattern analysis
        """
        pass
    
    @abstractmethod
    async def predict_drift_risk(
        self,
        voice_fingerprint: VoiceFingerprint,
        recent_patterns: List[Dict[str, Any]],
        prediction_horizon: int = 7  # days
    ) -> Dict[str, float]:
        """
        Predict risk of voice drift.
        
        Args:
            voice_fingerprint: Current voice fingerprint
            recent_patterns: Recent voice patterns
            prediction_horizon: Prediction horizon in days
            
        Returns:
            Drift risk predictions by category
        """
        pass
    
    @abstractmethod
    async def recommend_corrections(
        self,
        drift_alerts: List[VoiceDriftAlert],
        voice_fingerprint: VoiceFingerprint
    ) -> List[Dict[str, Any]]:
        """
        Recommend corrections for detected drift.
        
        Args:
            drift_alerts: Detected drift alerts
            voice_fingerprint: Current voice fingerprint
            
        Returns:
            List of correction recommendations
        """
        pass
