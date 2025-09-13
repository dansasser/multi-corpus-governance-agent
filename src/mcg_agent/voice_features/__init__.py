"""Advanced voice features for dynamic adaptation, learning, and monitoring.

This module provides sophisticated voice replication capabilities including:
- Dynamic voice adaptation based on context and audience
- Voice learning and evolution tracking
- Voice consistency monitoring and drift detection
- Voice quality assurance and improvement
"""

from .protocols.voice_adaptation_protocol import (
    VoiceAdaptationProtocol,
    ContextAnalysisProtocol,
    AdaptationStrategyProtocol
)
from .protocols.voice_learning_protocol import (
    VoiceLearningProtocol,
    FeedbackProcessingProtocol,
    EvolutionTrackingProtocol
)
from .protocols.voice_monitoring_protocol import (
    VoiceMonitoringProtocol,
    ConsistencyCheckProtocol,
    DriftDetectionProtocol
)

__all__ = [
    # Voice Adaptation Protocols
    "VoiceAdaptationProtocol",
    "ContextAnalysisProtocol", 
    "AdaptationStrategyProtocol",
    
    # Voice Learning Protocols
    "VoiceLearningProtocol",
    "FeedbackProcessingProtocol",
    "EvolutionTrackingProtocol",
    
    # Voice Monitoring Protocols
    "VoiceMonitoringProtocol",
    "ConsistencyCheckProtocol",
    "DriftDetectionProtocol"
]
