"""Voice features protocols defining clean interfaces for all voice functionality."""

from .voice_adaptation_protocol import (
    VoiceAdaptationProtocol,
    ContextAnalysisProtocol,
    AdaptationStrategyProtocol,
    AdaptationStrategy,
    ContextType,
    AdaptationContext,
    AdaptationResult
)

from .voice_learning_protocol import (
    VoiceLearningProtocol,
    FeedbackProcessingProtocol,
    EvolutionTrackingProtocol,
    FeedbackType,
    LearningMode,
    VoiceFeedback,
    VoiceEvolutionRecord,
    LearningSession
)

from .voice_monitoring_protocol import (
    VoiceMonitoringProtocol,
    ConsistencyCheckProtocol,
    DriftDetectionProtocol,
    MonitoringLevel,
    AlertSeverity,
    DriftType,
    ConsistencyMetrics,
    VoiceDriftAlert,
    MonitoringReport
)

__all__ = [
    # Voice Adaptation
    "VoiceAdaptationProtocol",
    "ContextAnalysisProtocol",
    "AdaptationStrategyProtocol",
    "AdaptationStrategy",
    "ContextType",
    "AdaptationContext",
    "AdaptationResult",
    
    # Voice Learning
    "VoiceLearningProtocol",
    "FeedbackProcessingProtocol",
    "EvolutionTrackingProtocol",
    "FeedbackType",
    "LearningMode",
    "VoiceFeedback",
    "VoiceEvolutionRecord",
    "LearningSession",
    
    # Voice Monitoring
    "VoiceMonitoringProtocol",
    "ConsistencyCheckProtocol",
    "DriftDetectionProtocol",
    "MonitoringLevel",
    "AlertSeverity",
    "DriftType",
    "ConsistencyMetrics",
    "VoiceDriftAlert",
    "MonitoringReport"
]
