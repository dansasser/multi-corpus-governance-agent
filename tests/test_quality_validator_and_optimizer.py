import asyncio

import pytest

from mcg_agent.quality.validators import ToneStyleValidator
from mcg_agent.optimizer.response_optimizer import ResponseOptimizer


def test_tone_style_validator_basic():
    v = ToneStyleValidator(min_tone=0.0, min_style=0.0, min_overall=0.0)
    text = "Therefore, we can conclude. It's great to see progress!"
    scores = v.validate(text, expected_tone="professional", expected_style="concise")
    assert 0.0 <= scores.tone_match <= 1.0
    assert 0.0 <= scores.style_consistency <= 1.0
    assert 0.0 <= scores.overall <= 1.0


@pytest.mark.asyncio
async def test_optimizer_runs_with_punctuation_provider(monkeypatch):
    # Force punctuation_only provider and enable optimizer with quality (no network)
    monkeypatch.setenv("GEN_PROVIDER", "punctuation_only")
    monkeypatch.setenv("FEATURE_RESPONSE_OPTIMIZER", "true")
    monkeypatch.setenv("OPTIMIZATION_STRATEGY", "quality")
    opt = ResponseOptimizer()
    text = "This is test text!!!"
    out, info = await opt.optimize_revise(text, metadata={"expected_tone": "professional", "expected_style": "concise"})
    assert isinstance(out, str)
    assert isinstance(info, dict)
    # When quality mode is on, we expect qa info to be present
    assert "qa" in info

