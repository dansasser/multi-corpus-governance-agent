"""Task automation module for executing user tasks with voice consistency."""

from .task_automation_engine import (
    TaskAutomationEngine,
    TaskStatus,
    AutomationLevel,
    TaskExecution
)

__all__ = [
    'TaskAutomationEngine',
    'TaskStatus', 
    'AutomationLevel',
    'TaskExecution'
]
