import pytest

from mcg_agent.routing.pipeline import GovernedAgentPipeline


@pytest.mark.asyncio
async def test_punctuation_enforced_in_pipeline_final_output():
    pipeline = GovernedAgentPipeline()
    text = 'Wow!!! This is “great”… right??!'
    result = await pipeline.process_request(text)
    # Final content should be normalized: no smart quotes, no triple exclamations
    assert '“' not in result.content and '”' not in result.content
    assert '!!!' not in result.content
    # Ellipsis normalized to three dots
    assert '...' in result.content
    # Metadata should reflect that normalization occurred at summarizer or revisor
    assert (
        result.metadata.get('punctuation_normalization', {}).get('applied')
        or any(
            isinstance(cl, dict) and cl.get('reason') == 'punctuation_normalization'
            for cl in result.metadata.get('change_log', [])
        )
    )

