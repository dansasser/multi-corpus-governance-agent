"""
MVLM Module

Provides MVLM integration for personal voice replication including:
- Interchangeable MVLM model management (MVLM-GPT2 vs Enhanced SIM-ONE)
- Voice-aware text generation
- Voice consistency validation
- Model benchmarking for optimization
- Pluggable interface for Revisor/Summarizer MVLM operations
"""

from .personal_voice_mvlm_manager import (
    PersonalVoiceMVLMManager,
    VoiceGenerationRequest,
    VoiceGenerationResult,
    VoiceContext,
    VoiceBenchmarkResults,
    MVLMModelType
)

from .voice_aware_text_generator import (
    VoiceAwareTextGenerator,
    VoiceProfile,
    VoiceValidationResult
)

__all__ = [
    "PersonalVoiceMVLMManager",
    "VoiceGenerationRequest",
    "VoiceGenerationResult",
    "VoiceContext", 
    "VoiceBenchmarkResults",
    "MVLMModelType",
    "VoiceAwareTextGenerator",
    "VoiceProfile",
    "VoiceValidationResult"
]

