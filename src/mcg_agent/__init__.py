"""
Multi-Corpus Governance Agent

A governed AI assistant that connects to multiple corpora (personal, social, published)
and routes them through a five-agent pipeline: Ideator → Drafter → Critic → Revisor → Summarizer.

Unlike prompt-tuned chatbots, reasoning and validation are handled in the governance layer.
Heavy lifting (idea generation, drafting, validation) uses API backends, while Minimum Viable
Language Models (MVLMs) act as firebreaks at the end of the chain to enforce tone, reduce
noise, and package results.
"""

__version__ = "0.1.0"
__author__ = "Multi-Corpus Governance Agent Team"
__email__ = "team@mcg-agent.com"
__license__ = "AGPL-3.0"
__description__ = "A governed AI assistant with multi-corpus integration and five-agent pipeline"

# Core exports
from mcg_agent.config import settings

# Agent exports
from mcg_agent.pydantic_ai.agent_base import (
    AgentRole,
    AgentInput, 
    AgentOutput,
    GovernanceContext
)

# Protocol exports
from mcg_agent.protocols.context_protocol import (
    ContextSnippet,
    ContextPack
)

from mcg_agent.protocols.governance_protocol import (
    API_CALL_LIMITS,
    CORPUS_ACCESS,
    RAG_POLICY
)

# Search exports
from mcg_agent.search.models import (
    PersonalSearchFilters,
    PersonalSearchResult,
    SocialSearchFilters,
    SocialSearchResult,
    PublishedSearchFilters,
    PublishedSearchResult
)

__all__ = [
    # Package metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    
    # Core
    "settings",
    
    # Agent types
    "AgentRole",
    "AgentInput",
    "AgentOutput", 
    "GovernanceContext",
    
    # Context types
    "ContextSnippet",
    "ContextPack",
    
    # Governance
    "API_CALL_LIMITS",
    "CORPUS_ACCESS",
    "RAG_POLICY",
    
    # Search types
    "PersonalSearchFilters",
    "PersonalSearchResult",
    "SocialSearchFilters", 
    "SocialSearchResult",
    "PublishedSearchFilters",
    "PublishedSearchResult",
]
