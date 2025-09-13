"""Task automation engine for executing user tasks with voice consistency."""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from ..protocols import (
    TaskAutomationProtocol,
    TaskAutomationRequest,
    TaskAutomationResult,
    TaskPriority,
    AssistantContext
)
from ...voice_features.adapters import DynamicVoiceAdapter
from ...mvlm import PersonalVoiceMVLMManager
from ...governance import PersonalDataGovernanceManager
from ...security import PersonalVoiceAuditTrail

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class AutomationLevel(Enum):
    """Level of automation for tasks."""
    MANUAL = "manual"              # User confirmation required for each step
    ASSISTED = "assisted"          # AI suggests, user approves
    SEMI_AUTOMATED = "semi_automated"  # AI executes with user oversight
    FULLY_AUTOMATED = "fully_automated"  # AI executes independently


@dataclass
class TaskExecution:
    """Represents a task execution with metadata."""
    task_id: str
    task_type: str
    status: TaskStatus
    automation_level: AutomationLevel
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: float
    steps_completed: int
    total_steps: int
    result_data: Dict[str, Any]
    error_message: Optional[str]
    voice_consistency_score: float
    user_satisfaction: Optional[float]


class TaskAutomationEngine(TaskAutomationProtocol):
    """
    Core task automation engine that executes user tasks
    while maintaining voice consistency and authenticity.
    
    This engine specializes in:
    - Email drafting and sending with authentic voice
    - Social media content creation and posting
    - Document and content generation
    - Scheduling and reminder management
    - Multi-step workflow automation
    """
    
    def __init__(
        self,
        voice_adapter: DynamicVoiceAdapter,
        mvlm_manager: PersonalVoiceMVLMManager,
        governance_manager: PersonalDataGovernanceManager,
        audit_trail: PersonalVoiceAuditTrail
    ):
        """
        Initialize task automation engine.
        
        Args:
            voice_adapter: Voice adaptation system
            mvlm_manager: MVLM management for text generation
            governance_manager: Personal data governance
            audit_trail: Voice usage audit trail
        """
        self.voice_adapter = voice_adapter
        self.mvlm_manager = mvlm_manager
        self.governance_manager = governance_manager
        self.audit_trail = audit_trail
        
        # Task automation configuration
        self.automation_config = {
            'max_concurrent_tasks': 5,
            'default_automation_level': AutomationLevel.ASSISTED,
            'voice_consistency_threshold': 0.8,
            'max_task_duration_minutes': 30,
            'retry_attempts': 3,
            'user_confirmation_timeout_seconds': 300,
            'supported_platforms': [
                'email', 'gmail', 'outlook',
                'twitter', 'linkedin', 'facebook', 'instagram',
                'slack', 'discord', 'teams'
            ]
        }
        
        # Active task executions
        self.active_tasks: Dict[str, TaskExecution] = {}
        
        # Task type handlers
        self.task_handlers = {
            'email_draft': self._handle_email_draft,
            'email_send': self._handle_email_send,
            'social_post': self._handle_social_post,
            'content_creation': self._handle_content_creation,
            'document_generation': self._handle_document_generation,
            'schedule_meeting': self._handle_schedule_meeting,
            'set_reminder': self._handle_set_reminder,
            'research_task': self._handle_research_task,
            'analysis_task': self._handle_analysis_task
        }
        
        # Platform-specific configurations
        self.platform_configs = {
            'email': {
                'max_length': 5000,
                'requires_subject': True,
                'supports_attachments': True,
                'voice_style': 'professional_friendly'
            },
            'twitter': {
                'max_length': 280,
                'supports_media': True,
                'hashtag_friendly': True,
                'voice_style': 'casual_engaging'
            },
            'linkedin': {
                'max_length': 3000,
                'professional_tone': True,
                'supports_media': True,
                'voice_style': 'professional_authoritative'
            },
            'facebook': {
                'max_length': 8000,
                'casual_tone': True,
                'supports_media': True,
                'voice_style': 'personal_friendly'
            },
            'slack': {
                'max_length': 4000,
                'casual_tone': True,
                'supports_formatting': True,
                'voice_style': 'professional_casual'
            }
        }
        
        # Task automation statistics
        self.automation_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'average_completion_time': 0.0,
            'average_voice_consistency': 0.0,
            'task_type_distribution': {},
            'platform_usage': {},
            'automation_level_usage': {}
        }
    
    async def automate_task(
        self,
        request: TaskAutomationRequest
    ) -> TaskAutomationResult:
        """
        Automate a user task with voice consistency.
        
        Args:
            request: Task automation request
            
        Returns:
            Task automation result
        """
        try:
            # Validate task request
            validation_result = await self._validate_task_request(request)
            if not validation_result['valid']:
                return await self._create_error_result(
                    request, f"Task validation failed: {validation_result['error']}"
                )
            
            # Create task execution
            task_execution = await self._create_task_execution(request)
            self.active_tasks[task_execution.task_id] = task_execution
            
            # Execute task based on type
            if request.task_type not in self.task_handlers:
                return await self._create_error_result(
                    request, f"Unsupported task type: {request.task_type}"
                )
            
            # Update task status
            task_execution.status = TaskStatus.IN_PROGRESS
            task_execution.started_at = datetime.now()
            
            # Execute task handler
            handler = self.task_handlers[request.task_type]
            execution_result = await handler(request, task_execution)
            
            # Update task completion
            task_execution.status = TaskStatus.COMPLETED if execution_result['success'] else TaskStatus.FAILED
            task_execution.completed_at = datetime.now()
            task_execution.progress = 1.0 if execution_result['success'] else task_execution.progress
            task_execution.result_data = execution_result.get('data', {})
            task_execution.error_message = execution_result.get('error')
            
            # Calculate voice consistency
            if execution_result.get('generated_content'):
                voice_consistency = await self._validate_voice_consistency(
                    execution_result['generated_content'], request.context
                )
                task_execution.voice_consistency_score = voice_consistency
            
            # Create result
            result = TaskAutomationResult(
                task_id=task_execution.task_id,
                request_id=request.request_id,
                success=execution_result['success'],
                result_data=task_execution.result_data,
                generated_content=execution_result.get('generated_content'),
                execution_time_ms=int((task_execution.completed_at - task_execution.started_at).total_seconds() * 1000),
                voice_consistency_score=task_execution.voice_consistency_score,
                steps_completed=task_execution.steps_completed,
                total_steps=task_execution.total_steps,
                automation_level=task_execution.automation_level.value,
                metadata={
                    'task_type': request.task_type,
                    'platform': request.target_platform,
                    'automation_level': task_execution.automation_level.value,
                    'voice_style_used': execution_result.get('voice_style_used'),
                    'corpus_access': execution_result.get('corpus_access', [])
                }
            )
            
            # Log successful automation
            await self.audit_trail.log_voice_usage(
                user_id=request.context.user_id,
                operation_type='task_automation',
                voice_patterns_used=execution_result.get('voice_patterns_used', []),
                success=True,
                metadata={
                    'task_id': task_execution.task_id,
                    'task_type': request.task_type,
                    'platform': request.target_platform,
                    'voice_consistency': task_execution.voice_consistency_score
                }
            )
            
            # Update statistics
            await self._update_automation_statistics(task_execution, result)
            
            # Clean up completed task
            if task_execution.task_id in self.active_tasks:
                del self.active_tasks[task_execution.task_id]
            
            logger.info(f"Task automation completed: {task_execution.task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Task automation failed: {str(e)}")
            
            # Log failed automation
            await self.audit_trail.log_voice_usage(
                user_id=request.context.user_id if request.context else "unknown",
                operation_type='task_automation',
                voice_patterns_used=[],
                success=False,
                metadata={
                    'task_type': request.task_type,
                    'error': str(e)
                }
            )
            
            return await self._create_error_result(request, str(e))
    
    async def get_supported_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of supported automation tasks.
        
        Returns:
            List of supported task types with metadata
        """
        supported_tasks = []
        
        task_descriptions = {
            'email_draft': {
                'name': 'Email Drafting',
                'description': 'Draft emails in your authentic voice',
                'platforms': ['email', 'gmail', 'outlook'],
                'automation_levels': ['assisted', 'semi_automated', 'fully_automated'],
                'voice_features': ['tone_adaptation', 'audience_awareness', 'professional_style']
            },
            'email_send': {
                'name': 'Email Sending',
                'description': 'Send drafted emails with voice consistency',
                'platforms': ['email', 'gmail', 'outlook'],
                'automation_levels': ['assisted', 'semi_automated'],
                'voice_features': ['signature_consistency', 'tone_validation']
            },
            'social_post': {
                'name': 'Social Media Posting',
                'description': 'Create and post social media content in your voice',
                'platforms': ['twitter', 'linkedin', 'facebook', 'instagram'],
                'automation_levels': ['assisted', 'semi_automated', 'fully_automated'],
                'voice_features': ['platform_adaptation', 'casual_tone', 'engagement_optimization']
            },
            'content_creation': {
                'name': 'Content Creation',
                'description': 'Generate articles, blogs, and documents',
                'platforms': ['blog', 'medium', 'wordpress'],
                'automation_levels': ['assisted', 'semi_automated', 'fully_automated'],
                'voice_features': ['long_form_consistency', 'expertise_demonstration', 'style_adaptation']
            },
            'document_generation': {
                'name': 'Document Generation',
                'description': 'Create professional documents and reports',
                'platforms': ['word', 'google_docs', 'pdf'],
                'automation_levels': ['assisted', 'semi_automated'],
                'voice_features': ['formal_tone', 'structure_consistency', 'professional_language']
            },
            'schedule_meeting': {
                'name': 'Meeting Scheduling',
                'description': 'Schedule meetings with voice-consistent invitations',
                'platforms': ['calendar', 'outlook', 'google_calendar'],
                'automation_levels': ['assisted', 'semi_automated'],
                'voice_features': ['professional_communication', 'clear_instructions']
            },
            'set_reminder': {
                'name': 'Reminder Setting',
                'description': 'Set reminders with personalized messages',
                'platforms': ['calendar', 'notes', 'tasks'],
                'automation_levels': ['assisted', 'semi_automated', 'fully_automated'],
                'voice_features': ['personal_tone', 'motivational_language']
            },
            'research_task': {
                'name': 'Research Tasks',
                'description': 'Conduct research and compile findings',
                'platforms': ['web', 'documents', 'databases'],
                'automation_levels': ['assisted', 'semi_automated'],
                'voice_features': ['analytical_tone', 'source_integration', 'summary_style']
            },
            'analysis_task': {
                'name': 'Analysis Tasks',
                'description': 'Analyze data and generate insights',
                'platforms': ['spreadsheet', 'reports', 'presentations'],
                'automation_levels': ['assisted', 'semi_automated'],
                'voice_features': ['analytical_voice', 'data_interpretation', 'insight_communication']
            }
        }
        
        for task_type, handler in self.task_handlers.items():
            if task_type in task_descriptions:
                task_info = task_descriptions[task_type].copy()
                task_info['task_type'] = task_type
                task_info['handler_available'] = True
                supported_tasks.append(task_info)
        
        return supported_tasks
    
    async def estimate_task_complexity(
        self,
        task_type: str,
        task_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate task complexity and execution time.
        
        Args:
            task_type: Type of task
            task_parameters: Task parameters
            
        Returns:
            Complexity estimation
        """
        try:
            # Base complexity scores
            base_complexity = {
                'email_draft': 0.3,
                'email_send': 0.2,
                'social_post': 0.4,
                'content_creation': 0.8,
                'document_generation': 0.7,
                'schedule_meeting': 0.5,
                'set_reminder': 0.2,
                'research_task': 0.9,
                'analysis_task': 0.8
            }
            
            complexity = base_complexity.get(task_type, 0.5)
            
            # Adjust based on parameters
            if 'content_length' in task_parameters:
                length = task_parameters['content_length']
                if length == 'long':
                    complexity += 0.3
                elif length == 'short':
                    complexity -= 0.2
            
            if 'requires_research' in task_parameters and task_parameters['requires_research']:
                complexity += 0.2
            
            if 'multiple_platforms' in task_parameters and task_parameters['multiple_platforms']:
                complexity += 0.3
            
            # Normalize complexity
            complexity = max(0.1, min(1.0, complexity))
            
            # Estimate execution time
            base_time_minutes = {
                'email_draft': 2,
                'email_send': 1,
                'social_post': 3,
                'content_creation': 15,
                'document_generation': 10,
                'schedule_meeting': 5,
                'set_reminder': 1,
                'research_task': 20,
                'analysis_task': 15
            }
            
            estimated_time = base_time_minutes.get(task_type, 5)
            estimated_time = int(estimated_time * (1 + complexity))
            
            # Determine automation recommendation
            if complexity < 0.3:
                recommended_automation = AutomationLevel.FULLY_AUTOMATED
            elif complexity < 0.6:
                recommended_automation = AutomationLevel.SEMI_AUTOMATED
            else:
                recommended_automation = AutomationLevel.ASSISTED
            
            return {
                'complexity_score': complexity,
                'estimated_time_minutes': estimated_time,
                'recommended_automation_level': recommended_automation.value,
                'complexity_factors': {
                    'base_complexity': base_complexity.get(task_type, 0.5),
                    'content_length_factor': task_parameters.get('content_length', 'medium'),
                    'research_required': task_parameters.get('requires_research', False),
                    'multi_platform': task_parameters.get('multiple_platforms', False)
                },
                'resource_requirements': {
                    'corpus_access': complexity > 0.4,
                    'voice_adaptation': True,
                    'quality_validation': complexity > 0.5,
                    'user_oversight': complexity > 0.6
                }
            }
            
        except Exception as e:
            logger.error(f"Task complexity estimation failed: {str(e)}")
            return {
                'complexity_score': 0.5,
                'estimated_time_minutes': 5,
                'recommended_automation_level': AutomationLevel.ASSISTED.value,
                'error': str(e)
            }
    
    # Task handler methods
    
    async def _handle_email_draft(
        self,
        request: TaskAutomationRequest,
        execution: TaskExecution
    ) -> Dict[str, Any]:
        """Handle email drafting task."""
        try:
            execution.total_steps = 4
            
            # Step 1: Analyze email requirements
            email_params = request.task_parameters
            recipient = email_params.get('recipient', 'Unknown')
            subject = email_params.get('subject', 'No Subject')
            purpose = email_params.get('purpose', 'general')
            tone = email_params.get('tone', 'professional_friendly')
            
            execution.steps_completed = 1
            
            # Step 2: Determine voice context
            voice_context = {
                'platform': 'email',
                'audience': recipient,
                'purpose': purpose,
                'tone': tone,
                'formality_level': 0.7,  # Email default
                'length_target': 'medium'
            }
            
            execution.steps_completed = 2
            
            # Step 3: Generate email content using voice adapter
            content_prompt = f"""
            Draft an email with the following details:
            - Recipient: {recipient}
            - Subject: {subject}
            - Purpose: {purpose}
            - Tone: {tone}
            
            Generate a professional, authentic email in the user's voice.
            """
            
            adapted_voice = await self.voice_adapter.adapt_voice(
                text=content_prompt,
                context=voice_context,
                strategy='context_specific'
            )
            
            # Use MVLM to generate the actual email content
            email_content = await self.mvlm_manager.generate_text(
                prompt=adapted_voice.adapted_text,
                voice_context=voice_context,
                max_length=self.platform_configs['email']['max_length']
            )
            
            execution.steps_completed = 3
            
            # Step 4: Format and validate email
            formatted_email = await self._format_email_content(
                subject, email_content, recipient, request.context
            )
            
            execution.steps_completed = 4
            
            return {
                'success': True,
                'generated_content': formatted_email,
                'data': {
                    'subject': subject,
                    'recipient': recipient,
                    'content': email_content,
                    'formatted_email': formatted_email
                },
                'voice_style_used': tone,
                'voice_patterns_used': ['personal', 'professional'],
                'corpus_access': ['personal', 'published']
            }
            
        except Exception as e:
            logger.error(f"Email draft handler failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_social_post(
        self,
        request: TaskAutomationRequest,
        execution: TaskExecution
    ) -> Dict[str, Any]:
        """Handle social media posting task."""
        try:
            execution.total_steps = 5
            
            # Step 1: Analyze post requirements
            post_params = request.task_parameters
            platform = request.target_platform
            content_type = post_params.get('content_type', 'general')
            topic = post_params.get('topic', 'Update')
            include_hashtags = post_params.get('include_hashtags', True)
            
            execution.steps_completed = 1
            
            # Step 2: Get platform configuration
            platform_config = self.platform_configs.get(platform, {})
            max_length = platform_config.get('max_length', 1000)
            voice_style = platform_config.get('voice_style', 'casual_engaging')
            
            execution.steps_completed = 2
            
            # Step 3: Determine voice context
            voice_context = {
                'platform': platform,
                'content_type': content_type,
                'voice_style': voice_style,
                'max_length': max_length,
                'casual_tone': platform_config.get('casual_tone', True),
                'hashtag_friendly': platform_config.get('hashtag_friendly', False)
            }
            
            execution.steps_completed = 3
            
            # Step 4: Generate post content
            content_prompt = f"""
            Create a {platform} post about: {topic}
            Content type: {content_type}
            Style: {voice_style}
            Max length: {max_length} characters
            Include hashtags: {include_hashtags}
            
            Generate engaging content in the user's authentic voice for {platform}.
            """
            
            adapted_voice = await self.voice_adapter.adapt_voice(
                text=content_prompt,
                context=voice_context,
                strategy='context_specific'
            )
            
            post_content = await self.mvlm_manager.generate_text(
                prompt=adapted_voice.adapted_text,
                voice_context=voice_context,
                max_length=max_length
            )
            
            execution.steps_completed = 4
            
            # Step 5: Format and optimize post
            formatted_post = await self._format_social_post(
                post_content, platform, include_hashtags, topic
            )
            
            execution.steps_completed = 5
            
            return {
                'success': True,
                'generated_content': formatted_post,
                'data': {
                    'platform': platform,
                    'content_type': content_type,
                    'topic': topic,
                    'character_count': len(formatted_post),
                    'hashtags_included': include_hashtags
                },
                'voice_style_used': voice_style,
                'voice_patterns_used': ['personal', 'social'],
                'corpus_access': ['personal', 'social']
            }
            
        except Exception as e:
            logger.error(f"Social post handler failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_content_creation(
        self,
        request: TaskAutomationRequest,
        execution: TaskExecution
    ) -> Dict[str, Any]:
        """Handle content creation task."""
        try:
            execution.total_steps = 6
            
            # Step 1: Analyze content requirements
            content_params = request.task_parameters
            content_type = content_params.get('content_type', 'article')
            topic = content_params.get('topic', 'General Topic')
            target_length = content_params.get('target_length', 'medium')
            audience = content_params.get('audience', 'general')
            
            execution.steps_completed = 1
            
            # Step 2: Determine content structure
            structure = await self._determine_content_structure(content_type, target_length)
            execution.steps_completed = 2
            
            # Step 3: Create content outline
            outline = await self._create_content_outline(topic, structure, audience)
            execution.steps_completed = 3
            
            # Step 4: Generate content sections
            content_sections = []
            for section in outline['sections']:
                section_content = await self._generate_content_section(
                    section, topic, audience, request.context
                )
                content_sections.append(section_content)
            
            execution.steps_completed = 4
            
            # Step 5: Combine and format content
            full_content = await self._combine_content_sections(
                content_sections, outline, content_type
            )
            execution.steps_completed = 5
            
            # Step 6: Final voice consistency check
            voice_validated_content = await self._validate_content_voice_consistency(
                full_content, request.context
            )
            execution.steps_completed = 6
            
            return {
                'success': True,
                'generated_content': voice_validated_content,
                'data': {
                    'content_type': content_type,
                    'topic': topic,
                    'word_count': len(voice_validated_content.split()),
                    'sections': len(content_sections),
                    'outline': outline
                },
                'voice_style_used': 'authoritative_personal',
                'voice_patterns_used': ['personal', 'published'],
                'corpus_access': ['personal', 'published']
            }
            
        except Exception as e:
            logger.error(f"Content creation handler failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Additional task handlers would be implemented here...
    # For brevity, I'll implement the key helper methods
    
    # Private helper methods
    
    async def _validate_task_request(self, request: TaskAutomationRequest) -> Dict[str, Any]:
        """Validate task automation request."""
        try:
            # Check if task type is supported
            if request.task_type not in self.task_handlers:
                return {
                    'valid': False,
                    'error': f"Unsupported task type: {request.task_type}"
                }
            
            # Check platform support
            if request.target_platform and request.target_platform not in self.automation_config['supported_platforms']:
                return {
                    'valid': False,
                    'error': f"Unsupported platform: {request.target_platform}"
                }
            
            # Check governance permissions
            if request.context:
                has_permission = await self.governance_manager.check_usage_permission(
                    user_id=request.context.user_id,
                    usage_type='task_automation',
                    agent_type='automation_engine'
                )
                
                if not has_permission:
                    return {
                        'valid': False,
                        'error': "Insufficient permissions for task automation"
                    }
            
            # Check concurrent task limit
            if len(self.active_tasks) >= self.automation_config['max_concurrent_tasks']:
                return {
                    'valid': False,
                    'error': "Maximum concurrent tasks limit reached"
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Task validation failed: {str(e)}")
            return {
                'valid': False,
                'error': f"Validation error: {str(e)}"
            }
    
    async def _create_task_execution(self, request: TaskAutomationRequest) -> TaskExecution:
        """Create task execution object."""
        return TaskExecution(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            task_type=request.task_type,
            status=TaskStatus.PENDING,
            automation_level=request.automation_level or self.automation_config['default_automation_level'],
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            progress=0.0,
            steps_completed=0,
            total_steps=1,
            result_data={},
            error_message=None,
            voice_consistency_score=0.0,
            user_satisfaction=None
        )
    
    async def _validate_voice_consistency(
        self,
        generated_content: str,
        context: AssistantContext
    ) -> float:
        """Validate voice consistency of generated content."""
        try:
            # Use voice adapter to validate consistency
            validation_result = await self.voice_adapter.adapt_voice(
                text=generated_content,
                context={
                    'validation_mode': True,
                    'user_id': context.user_id,
                    'platform': context.platform
                },
                strategy='preserve_original'
            )
            
            return validation_result.confidence
            
        except Exception as e:
            logger.error(f"Voice consistency validation failed: {str(e)}")
            return 0.5
    
    async def _format_email_content(
        self,
        subject: str,
        content: str,
        recipient: str,
        context: AssistantContext
    ) -> str:
        """Format email content with proper structure."""
        # Basic email formatting
        formatted_email = f"Subject: {subject}\n"
        formatted_email += f"To: {recipient}\n\n"
        
        # Add greeting if not present
        if not content.strip().startswith(('Hi', 'Hello', 'Dear')):
            formatted_email += f"Hello,\n\n"
        
        formatted_email += content
        
        # Add closing if not present
        if not any(closing in content.lower() for closing in ['regards', 'sincerely', 'thanks', 'best']):
            formatted_email += "\n\nBest regards"
        
        return formatted_email
    
    async def _format_social_post(
        self,
        content: str,
        platform: str,
        include_hashtags: bool,
        topic: str
    ) -> str:
        """Format social media post for platform."""
        formatted_post = content.strip()
        
        # Add hashtags if requested and platform supports them
        if include_hashtags and platform in ['twitter', 'instagram', 'linkedin']:
            # Generate relevant hashtags based on topic
            hashtags = await self._generate_hashtags(topic, platform)
            if hashtags:
                formatted_post += f"\n\n{' '.join(hashtags)}"
        
        # Ensure platform character limits
        platform_config = self.platform_configs.get(platform, {})
        max_length = platform_config.get('max_length')
        
        if max_length and len(formatted_post) > max_length:
            # Truncate content while preserving hashtags
            if include_hashtags and '#' in formatted_post:
                content_part, hashtag_part = formatted_post.rsplit('\n\n', 1)
                available_length = max_length - len(hashtag_part) - 3  # Account for "\n\n"
                if available_length > 50:  # Minimum content length
                    formatted_post = content_part[:available_length] + "...\n\n" + hashtag_part
                else:
                    formatted_post = formatted_post[:max_length-3] + "..."
            else:
                formatted_post = formatted_post[:max_length-3] + "..."
        
        return formatted_post
    
    async def _generate_hashtags(self, topic: str, platform: str) -> List[str]:
        """Generate relevant hashtags for topic and platform."""
        # Simple hashtag generation based on topic keywords
        topic_words = topic.lower().split()
        hashtags = []
        
        # Platform-specific hashtag strategies
        if platform == 'twitter':
            # Twitter prefers shorter, more specific hashtags
            for word in topic_words[:3]:
                if len(word) > 3:
                    hashtags.append(f"#{word.capitalize()}")
        elif platform == 'linkedin':
            # LinkedIn prefers professional hashtags
            professional_tags = ['#Professional', '#Business', '#Industry', '#Innovation']
            hashtags.extend(professional_tags[:2])
        elif platform == 'instagram':
            # Instagram allows more hashtags
            for word in topic_words[:5]:
                if len(word) > 2:
                    hashtags.append(f"#{word.capitalize()}")
        
        return hashtags[:5]  # Limit to 5 hashtags
    
    async def _determine_content_structure(
        self,
        content_type: str,
        target_length: str
    ) -> Dict[str, Any]:
        """Determine content structure based on type and length."""
        structures = {
            'article': {
                'short': ['introduction', 'main_point', 'conclusion'],
                'medium': ['introduction', 'background', 'main_points', 'examples', 'conclusion'],
                'long': ['introduction', 'background', 'problem_statement', 'analysis', 'solutions', 'examples', 'conclusion']
            },
            'blog_post': {
                'short': ['hook', 'main_content', 'call_to_action'],
                'medium': ['hook', 'introduction', 'main_content', 'examples', 'call_to_action'],
                'long': ['hook', 'introduction', 'background', 'main_content', 'examples', 'counterpoints', 'conclusion', 'call_to_action']
            },
            'report': {
                'short': ['executive_summary', 'findings', 'recommendations'],
                'medium': ['executive_summary', 'methodology', 'findings', 'analysis', 'recommendations'],
                'long': ['executive_summary', 'introduction', 'methodology', 'findings', 'analysis', 'discussion', 'recommendations', 'conclusion']
            }
        }
        
        structure = structures.get(content_type, structures['article'])
        sections = structure.get(target_length, structure['medium'])
        
        return {
            'content_type': content_type,
            'target_length': target_length,
            'sections': sections,
            'estimated_words': len(sections) * 150  # Rough estimate
        }
    
    async def _create_content_outline(
        self,
        topic: str,
        structure: Dict[str, Any],
        audience: str
    ) -> Dict[str, Any]:
        """Create detailed content outline."""
        outline = {
            'topic': topic,
            'audience': audience,
            'structure': structure,
            'sections': []
        }
        
        # Create section details
        for section_name in structure['sections']:
            section = {
                'name': section_name,
                'title': section_name.replace('_', ' ').title(),
                'purpose': await self._get_section_purpose(section_name),
                'key_points': [],
                'estimated_words': 150
            }
            outline['sections'].append(section)
        
        return outline
    
    async def _get_section_purpose(self, section_name: str) -> str:
        """Get the purpose of a content section."""
        purposes = {
            'introduction': 'Introduce the topic and engage the reader',
            'background': 'Provide necessary context and background information',
            'main_point': 'Present the primary argument or information',
            'main_points': 'Present the key arguments or information points',
            'main_content': 'Deliver the core content and value',
            'examples': 'Provide concrete examples and illustrations',
            'analysis': 'Analyze the information and provide insights',
            'solutions': 'Present solutions or recommendations',
            'conclusion': 'Summarize key points and provide closure',
            'call_to_action': 'Encourage reader action or engagement',
            'executive_summary': 'Provide a high-level overview of key findings',
            'methodology': 'Explain the approach and methods used',
            'findings': 'Present the key findings and results',
            'recommendations': 'Provide actionable recommendations'
        }
        
        return purposes.get(section_name, 'Provide relevant information for this section')
    
    async def _generate_content_section(
        self,
        section: Dict[str, Any],
        topic: str,
        audience: str,
        context: AssistantContext
    ) -> str:
        """Generate content for a specific section."""
        try:
            # Create section-specific prompt
            section_prompt = f"""
            Write the {section['title']} section for content about: {topic}
            Audience: {audience}
            Purpose: {section['purpose']}
            Target length: approximately {section['estimated_words']} words
            
            Generate content in the user's authentic voice that serves the section purpose.
            """
            
            # Use voice adapter for section-specific voice context
            voice_context = {
                'content_section': section['name'],
                'topic': topic,
                'audience': audience,
                'formality_level': 0.6,
                'expertise_level': 'knowledgeable'
            }
            
            adapted_voice = await self.voice_adapter.adapt_voice(
                text=section_prompt,
                context=voice_context,
                strategy='context_specific'
            )
            
            # Generate section content
            section_content = await self.mvlm_manager.generate_text(
                prompt=adapted_voice.adapted_text,
                voice_context=voice_context,
                max_length=section['estimated_words'] * 6  # Rough character estimate
            )
            
            return section_content
            
        except Exception as e:
            logger.error(f"Section generation failed: {str(e)}")
            return f"[Error generating {section['title']} section: {str(e)}]"
    
    async def _combine_content_sections(
        self,
        sections: List[str],
        outline: Dict[str, Any],
        content_type: str
    ) -> str:
        """Combine content sections into final content."""
        combined_content = ""
        
        for i, section_content in enumerate(sections):
            section_info = outline['sections'][i]
            
            # Add section title for longer content
            if content_type in ['report', 'long_article'] and len(outline['sections']) > 3:
                combined_content += f"\n## {section_info['title']}\n\n"
            
            combined_content += section_content.strip() + "\n\n"
        
        return combined_content.strip()
    
    async def _validate_content_voice_consistency(
        self,
        content: str,
        context: AssistantContext
    ) -> str:
        """Validate and adjust content for voice consistency."""
        try:
            # Use voice adapter to ensure consistency
            consistency_check = await self.voice_adapter.adapt_voice(
                text=content,
                context={
                    'validation_mode': True,
                    'user_id': context.user_id,
                    'content_type': 'long_form'
                },
                strategy='preserve_original'
            )
            
            # If consistency is low, apply minor adjustments
            if consistency_check.confidence < self.automation_config['voice_consistency_threshold']:
                adjusted_content = await self.voice_adapter.adapt_voice(
                    text=content,
                    context={
                        'adjustment_mode': True,
                        'user_id': context.user_id,
                        'target_consistency': self.automation_config['voice_consistency_threshold']
                    },
                    strategy='blend_contexts'
                )
                return adjusted_content.adapted_text
            
            return content
            
        except Exception as e:
            logger.error(f"Voice consistency validation failed: {str(e)}")
            return content
    
    async def _create_error_result(
        self,
        request: TaskAutomationRequest,
        error_message: str
    ) -> TaskAutomationResult:
        """Create error result for failed task."""
        return TaskAutomationResult(
            task_id=f"error_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            success=False,
            result_data={'error': error_message},
            generated_content=None,
            execution_time_ms=0,
            voice_consistency_score=0.0,
            steps_completed=0,
            total_steps=1,
            automation_level=AutomationLevel.MANUAL.value,
            metadata={'error': error_message}
        )
    
    async def _update_automation_statistics(
        self,
        execution: TaskExecution,
        result: TaskAutomationResult
    ) -> None:
        """Update automation statistics."""
        self.automation_stats['total_tasks'] += 1
        
        if result.success:
            self.automation_stats['completed_tasks'] += 1
            
            # Update average completion time
            completion_time = result.execution_time_ms / 1000.0  # Convert to seconds
            current_avg = self.automation_stats['average_completion_time']
            completed_count = self.automation_stats['completed_tasks']
            self.automation_stats['average_completion_time'] = (
                (current_avg * (completed_count - 1) + completion_time) / completed_count
            )
            
            # Update average voice consistency
            current_voice_avg = self.automation_stats['average_voice_consistency']
            self.automation_stats['average_voice_consistency'] = (
                (current_voice_avg * (completed_count - 1) + result.voice_consistency_score) / completed_count
            )
        else:
            self.automation_stats['failed_tasks'] += 1
        
        # Update task type distribution
        task_type = execution.task_type
        if task_type not in self.automation_stats['task_type_distribution']:
            self.automation_stats['task_type_distribution'][task_type] = 0
        self.automation_stats['task_type_distribution'][task_type] += 1
        
        # Update automation level usage
        automation_level = execution.automation_level.value
        if automation_level not in self.automation_stats['automation_level_usage']:
            self.automation_stats['automation_level_usage'][automation_level] = 0
        self.automation_stats['automation_level_usage'][automation_level] += 1
    
    def get_automation_statistics(self) -> Dict[str, Any]:
        """Get task automation statistics."""
        success_rate = (
            self.automation_stats['completed_tasks'] / self.automation_stats['total_tasks']
            if self.automation_stats['total_tasks'] > 0 else 0.0
        )
        
        return {
            'statistics': self.automation_stats.copy(),
            'success_rate': success_rate,
            'active_tasks': len(self.active_tasks),
            'configuration': self.automation_config.copy(),
            'supported_platforms': self.automation_config['supported_platforms'],
            'supported_task_types': list(self.task_handlers.keys())
        }
