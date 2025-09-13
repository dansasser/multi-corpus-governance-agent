"""
Voice Module

Provides voice fingerprinting and application capabilities for personal voice replication.
Includes voice pattern extraction, fingerprint creation, and voice application systems.
"""

from .voice_fingerprint_extractor import (
    VoicePattern,
    VoiceFingerprint,
    VoiceFingerprintExtractor
)

from .voice_fingerprint_applicator import (
    VoiceFingerprintApplicator,
    VoiceApplicationResult,
    VoiceAdaptationStrategy
)

__all__ = [
    "VoicePattern",
    "VoiceFingerprint",
    "VoiceFingerprintExtractor",
    "VoiceFingerprintApplicator",
    "VoiceApplicationResult",
    "VoiceAdaptationStrategy"
]
