from mcg_agent.protocols.governance_protocol import CORPUS_ACCESS, RAG_POLICY


def test_corpus_access_matrix():
    assert CORPUS_ACCESS.is_allowed("ideator", "personal") is True
    assert CORPUS_ACCESS.is_allowed("drafter", "personal") is False
    assert CORPUS_ACCESS.is_allowed("critic", "social") is True
    assert CORPUS_ACCESS.is_allowed("revisor", "published") is False


def test_rag_policy():
    assert RAG_POLICY.is_rag_allowed("critic", "social") is True
    assert RAG_POLICY.is_rag_allowed("ideator", "published") is True
    assert RAG_POLICY.is_rag_allowed("drafter", "published") is False
    assert RAG_POLICY.is_rag_allowed("summarizer", "social") is False

