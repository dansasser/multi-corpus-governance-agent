from mcg_agent.protocols.punctuation_protocol import DEFAULT_PUNCTUATION_POLICY
from mcg_agent.utils.punctuation import enforce_punctuation


def test_punctuation_normalization():
    text = "Wow!!! This is great!! Right??! Also… quotes “like this”."
    out, applied = enforce_punctuation(text, DEFAULT_PUNCTUATION_POLICY)
    assert "collapse_repeated_terminators" in applied
    assert "normalize_ellipsis" in applied
    assert "normalize_quotes" in applied
    assert "enforce_space_after_punctuation" in applied
    # Ensure no triples of ! or ? remain
    assert "!!!" not in out and "??" not in out

