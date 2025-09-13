"""Personal assistant protocols for core functionality."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class AssistantMode(Enum):
    """Assistant operation modes."""
    PERSONAL = "personal"           # Personal assistance mode
    PROFESSIONAL = "professional"  # Professional assistance mode
    CREATIVE = "creative"          # Creative assistance mode
    ANALYTICAL = "analytical"      # Analytical assistance mode
    ADAPTIVE = "adaptive"          # Adaptive mode based on context


class ResponseStyle(Enum):
    """Response style preferences."""
    CONCISE = "concise"            # Brief, to-the-point responses
    DETAILED = "detailed"          # Comprehensive, detailed responses
    CONVERSATIONAL = "conversational"  # Natural, conversational tone
    FORMAL = "formal"              # Formal, professional tone
    ADAPTIVE = "adaptive"          # Adapt style to context


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AssistantContext:
    """Context information for assistant operations."""
    user_id: str
    session_id: str
    mode: AssistantMode
    response_style: ResponseStyle
    conversation_history: List[Dict[str, Any]]
    current_task: Optional[str] = None
    user_preferences: Dict[str, Any] = None
    platform: Optional[str] = None
    audience: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.user_preferences is None:
            self.user_preferences = {}


@dataclass
class AssistantRequest:
    """Request structure for assistant operations."""
    request_id: str
    user_input: str
    intent: Optional[str] = None
    context: Optional[AssistantContext] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    expected_response_type: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AssistantResponse:
    """Response structure from assistant operations."""
    response_id: str
    request_id: str
    content: str
    response_type: str
    confidence: float
    voice_consistency_score: float
    context_appropriateness: float
    processing_time_ms: int
    sources_used: List[str]
    voice_patterns_applied: List[str]
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskAutomationRequest:
    """Request for task automation."""
    task_id: str
    task_type: str
    task_description: str
    target_platform: Optional[str] = None
    target_audience: Optional[str] = None
    voice_requirements: Dict[str, Any] = None
    automation_level: str = "assisted"  # assisted, semi_automated, fully_automated
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.voice_requirements is None:
            self.voice_requirements = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskAutomationResult:
    """Result from task automation."""
    task_id: str
    status: str  # completed, partial, failed, pending
    generated_content: Optional[str] = None
    actions_taken: List[str] = None
    voice_consistency_score: float = 0.0
    quality_score: float = 0.0
    completion_time_ms: int = 0
    errors: List[str] = None
    recommendations: List[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.actions_taken is None:
            self.actions_taken = []
        if self.errors is None:
            self.errors = []
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}


class PersonalAssistantProtocol(ABC):
    """Protocol for personal assistant core functionality."""
    
    @abstractmethod
    async def process_request(
        self,
        request: AssistantRequest
    ) -> AssistantResponse:
        """
        Process a user request and generate an appropriate response.
        
        Args:
            request: Assistant request with user input and context
            
        Returns:
            Assistant response with generated content
        """
        pass
    
    @abstractmethod
    async def analyze_intent(
        self,
        user_input: str,
        context: Optional[AssistantContext] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent from input.
        
        Args:
            user_input: User's input text
            context: Optional context information
            
        Returns:
            Intent analysis results
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        intent: Dict[str, Any],
        context: AssistantContext
    ) -> str:
        """
        Generate response based on intent and context.
        
        Args:
            intent: Analyzed intent information
            context: Assistant context
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    async def update_context(
        self,
        context: AssistantContext,
        request: AssistantRequest,
        response: AssistantResponse
    ) -> AssistantContext:
        """
        Update context based on interaction.
        
        Args:
            context: Current context
            request: User request
            response: Assistant response
            
        Returns:
            Updated context
        """
        pass


class ContextAwareResponseProtocol(ABC):
    """Protocol for context-aware response generation."""
    
    @abstractmethod
    async def analyze_context(
        self,
        request: AssistantRequest,
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze context for response generation.
        
        Args:
            request: Current request
            conversation_history: Previous conversation
            
        Returns:
            Context analysis results
        """
        pass
    
    @abstractmethod
    async def adapt_response_style(
        self,
        base_response: str,
        context: AssistantContext,
        target_style: ResponseStyle
    ) -> str:
        """
        Adapt response style based on context.
        
        Args:
            base_response: Base response text
            context: Assistant context
            target_style: Target response style
            
        Returns:
            Style-adapted response
        """
        pass
    
    @abstractmethod
    async def validate_context_appropriateness(
        self,
        response: str,
        context: AssistantContext
    ) -> float:
        """
        Validate response appropriateness for context.
        
        Args:
            response: Generated response
            context: Assistant context
            
        Returns:
            Appropriateness score (0.0-1.0)
        """
        pass


class TaskAutomationProtocol(ABC):
    """Protocol for task automation functionality."""
    
    @abstractmethod
    async def automate_task(
        self,
        task_request: TaskAutomationRequest,
        context: AssistantContext
    ) -> TaskAutomationResult:
        """
        Automate a specific task.
        
        Args:
            task_request: Task automation request
            context: Assistant context
            
        Returns:
            Task automation result
        """
        pass
    
    @abstractmethod
    async def get_supported_tasks(self) -> List[str]:
        """
        Get list of supported automation tasks.
        
        Returns:
            List of supported task types
        """
        pass
    
    @abstractmethod
    async def estimate_task_complexity(
        self,
        task_request: TaskAutomationRequest
    ) -> Dict[str, Any]:
        """
        Estimate task complexity and requirements.
        
        Args:
            task_request: Task automation request
            
        Returns:
            Complexity estimation
        """
        pass


class ConversationManagementProtocol(ABC):
    """Protocol for conversation management."""
    
    @abstractmethod
    async def start_conversation(
        self,
        user_id: str,
        initial_context: Optional[AssistantContext] = None
    ) -> str:
        """
        Start a new conversation session.
        
        Args:
            user_id: User identifier
            initial_context: Optional initial context
            
        Returns:
            Session ID
        """
        pass
    
    @abstractmethod
    async def continue_conversation(
        self,
        session_id: str,
        user_input: str,
        context_updates: Optional[Dict[str, Any]] = None
    ) -> AssistantResponse:
        """
        Continue an existing conversation.
        
        Args:
            session_id: Conversation session ID
            user_input: User's input
            context_updates: Optional context updates
            
        Returns:
            Assistant response
        """
        pass
    
    @abstractmethod
    async def end_conversation(
        self,
        session_id: str,
        save_history: bool = True
    ) -> Dict[str, Any]:
        """
        End a conversation session.
        
        Args:
            session_id: Session to end
            save_history: Whether to save conversation history
            
        Returns:
            Conversation summary
        """
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            session_id: Session ID
            limit: Optional limit on number of messages
            
        Returns:
            Conversation history
        """
        pass


class IntentAnalysisProtocol(ABC):
    """Protocol for intent analysis."""
    
    @abstractmethod
    async def classify_intent(
        self,
        user_input: str,
        context: Optional[AssistantContext] = None
    ) -> Dict[str, Any]:
        """
        Classify user intent from input.
        
        Args:
            user_input: User's input text
            context: Optional context
            
        Returns:
            Intent classification results
        """
        pass
    
    @abstractmethod
    async def extract_entities(
        self,
        user_input: str,
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract entities from user input.
        
        Args:
            user_input: User's input text
            intent: Optional intent classification
            
        Returns:
            Extracted entities
        """
        pass
    
    @abstractmethod
    async def determine_response_requirements(
        self,
        intent: Dict[str, Any],
        context: AssistantContext
    ) -> Dict[str, Any]:
        """
        Determine response requirements based on intent.
        
        Args:
            intent: Intent analysis results
            context: Assistant context
            
        Returns:
            Response requirements
        """
        pass
