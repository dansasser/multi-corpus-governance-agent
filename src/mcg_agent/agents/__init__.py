"""
Agents Module

Contains all agent implementations for the Multi-Corpus Governance Agent system.
Includes both original agents and voice-aware agents for personal voice replication.
"""

# Original agents
from .ideator import IdeatorAgent
from .drafter import DrafterAgent
from .critic import CriticAgent
from .revisor import RevisorAgent
from .summarizer import SummarizerAgent

# Voice-aware agents for personal voice replication
from .voice_aware_ideator import VoiceAwareIdeatorAgent
from .voice_aware_drafter import VoiceAwareDrafterAgent
from .voice_aware_critic import VoiceAwareCriticAgent
from .voice_aware_revisor import VoiceAwareRevisorAgent
from .voice_aware_summarizer import VoiceAwareSummarizerAgent

__all__ = [
    # Original agents
    "IdeatorAgent",
    "DrafterAgent", 
    "CriticAgent",
    "RevisorAgent",
    "SummarizerAgent",
    
    # Voice-aware agents
    "VoiceAwareIdeatorAgent",
    "VoiceAwareDrafterAgent",
    "VoiceAwareCriticAgent", 
    "VoiceAwareRevisorAgent",
    "VoiceAwareSummarizerAgent"
]

