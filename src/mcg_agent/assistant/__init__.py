"""Personal assistant core functionality."""

from .protocols import (
    PersonalAssistantProtocol,
    ContextAwareResponseProtocol,
    TaskAutomationProtocol,
    ConversationManagementProtocol,
    IntentAnalysisProtocol,
    AssistantContext,
    AssistantRequest,
    AssistantResponse,
    AssistantMode,
    ResponseStyle
)

from .personal_assistant_core import PersonalAssistantCore
from .context_aware_responder import ContextAwareResponder
from .intent_analyzer import AdvancedIntentAnalyzer
from .conversation_manager import ConversationManager
from .complete_assistant_integration import CompleteAssistantIntegration, AssistantCapability, AssistantPerformanceMetrics

# Task automation
from .task_automation import (
    TaskAutomationEngine,
    TaskAutomationRequest,
    TaskAutomationResult,
    TaskType,
    TaskPriority,
    AutomationLevel
)

__all__ = [
    # Protocols
    'PersonalAssistantProtocol',
    'ContextAwareResponseProtocol', 
    'TaskAutomationProtocol',
    'ConversationManagementProtocol',
    'IntentAnalysisProtocol',
    'AssistantContext',
    'AssistantRequest',
    'AssistantResponse',
    'AssistantMode',
    'ResponseStyle',
    
    # Core components
    'PersonalAssistantCore',
    'ContextAwareResponder',
    'AdvancedIntentAnalyzer',
    'ConversationManager',
    'CompleteAssistantIntegration',
    'AssistantCapability',
    'AssistantPerformanceMetrics',
    
    # Task automation
    'TaskAutomationEngine',
    'TaskAutomationRequest',
    'TaskAutomationResult',
    'TaskType',
    'TaskPriority',
    'AutomationLevel'
]
