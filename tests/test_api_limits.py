import asyncio
import pytest

from mcg_agent.governance.api_limits import APICallGovernance
from mcg_agent.governance.call_tracker import CallTracker


@pytest.mark.asyncio
async def test_api_call_limits_enforced():
    task = "task-1"
    role = "drafter"  # limit = 1 per protocols
    try:
        # First call should pass and increment
        assert await APICallGovernance.validate_api_call(role, task) is True
        # Second call should raise (exceeds 1)
        with pytest.raises(Exception):
            await APICallGovernance.validate_api_call(role, task)
    finally:
        await CallTracker.reset_task(task)


@pytest.mark.asyncio
async def test_api_call_limits_multiple_roles():
    task = "task-2"
    try:
        # ideator -> allowed 2
        assert await APICallGovernance.validate_api_call("ideator", task) is True
        assert await APICallGovernance.validate_api_call("ideator", task) is True
        with pytest.raises(Exception):
            await APICallGovernance.validate_api_call("ideator", task)
    finally:
        await CallTracker.reset_task(task)

