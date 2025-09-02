from __future__ import annotations


class GovernanceViolationError(Exception):
    """Base class for governance-related errors."""


class UnauthorizedCorpusAccessError(GovernanceViolationError):
    def __init__(self, agent_role: str, corpus: str) -> None:
        super().__init__(f"{agent_role} is not authorized to access corpus '{corpus}'")
        self.agent_role = agent_role
        self.corpus = corpus


class APICallLimitExceededError(GovernanceViolationError):
    def __init__(self, agent_role: str, max_calls: int, attempted: int) -> None:
        super().__init__(
            f"{agent_role} exceeded API call limit: max={max_calls}, attempted={attempted}"
        )
        self.agent_role = agent_role
        self.max_calls = max_calls
        self.attempted = attempted


__all__ = [
    "GovernanceViolationError",
    "UnauthorizedCorpusAccessError",
    "APICallLimitExceededError",
]

