"""Personal assistant protocols for core functionality."""

from .assistant_protocol import (
    # Enums
    AssistantMode,
    ResponseStyle,
    TaskPriority,
    
    # Data structures
    AssistantContext,
    AssistantRequest,
    AssistantResponse,
    TaskAutomationRequest,
    TaskAutomationResult,
    
    # Protocols
    PersonalAssistantProtocol,
    ContextAwareResponseProtocol,
    TaskAutomationProtocol,
    ConversationManagementProtocol,
    IntentAnalysisProtocol
)

__all__ = [
    # Enums
    "AssistantMode",
    "ResponseStyle", 
    "TaskPriority",
    
    # Data structures
    "AssistantContext",
    "AssistantRequest",
    "AssistantResponse",
    "TaskAutomationRequest",
    "TaskAutomationResult",
    
    # Protocols
    "PersonalAssistantProtocol",
    "ContextAwareResponseProtocol",
    "TaskAutomationProtocol",
    "ConversationManagementProtocol",
    "IntentAnalysisProtocol"
]
