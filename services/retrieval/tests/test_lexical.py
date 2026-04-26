"""Tests for the lexical retriever."""

from __future__ import annotations

from civic_retrieval import LexicalEvidence, LexicalRetriever, MockLexicalRetriever


class _FakeClient:
    def __init__(self, response):
        self.response = response
        self.seen_body: dict | None = None
        self.seen_index: str | None = None

    def search(self, index, body):
        self.seen_index = index
        self.seen_body = body
        return self.response


def test_bm25_body_is_built_with_filters() -> None:
    client = _FakeClient(
        {
            "hits": {
                "hits": [
                    {
                        "_id": "s1",
                        "_score": 1.5,
                        "_source": {
                            "span_id": "s1",
                            "document_id": "d1",
                            "text": "the excerpt",
                            "source_tier": 1,
                        },
                    }
                ]
            }
        }
    )
    r = LexicalRetriever(client)
    out = r.search("voted for reform", filters={"source_tier": 1})
    assert client.seen_index == "evidence_spans"
    assert "multi_match" in client.seen_body["query"]["bool"]["must"][0]
    assert client.seen_body["query"]["bool"]["filter"] == [{"term": {"source_tier": 1}}]
    assert len(out) == 1
    assert out[0].span_id == "s1"
    assert out[0].source_tier == 1


def test_empty_query_becomes_match_all() -> None:
    client = _FakeClient({"hits": {"hits": []}})
    r = LexicalRetriever(client)
    r.search("")
    assert client.seen_body["query"]["bool"]["must"] == [{"match_all": {}}]


def test_vector_path_activates_with_embedder_and_flag() -> None:
    class _Embed:
        def embed(self, text: str) -> list[float]:
            return [0.1] * 384

    client = _FakeClient({"hits": {"hits": []}})
    r = LexicalRetriever(client, embedder=_Embed(), vector_enabled=True)
    r.search("anything")
    assert "knn" in client.seen_body
    assert client.seen_body["knn"]["field"] == "embedding"


def test_vector_path_stays_off_without_flag() -> None:
    class _Embed:
        def embed(self, text: str) -> list[float]:
            return [0.1] * 384

    client = _FakeClient({"hits": {"hits": []}})
    r = LexicalRetriever(client, embedder=_Embed(), vector_enabled=False)
    r.search("anything")
    assert "knn" not in client.seen_body


def test_mock_retriever_returns_what_it_was_given() -> None:
    r = MockLexicalRetriever(
        [
            LexicalEvidence("s1", "d1", "t1", 1, 1.0),
            LexicalEvidence("s2", "d2", "t2", 2, 0.8),
        ]
    )
    assert len(r.search("any")) == 2
    assert len(r.search("any", top_k=1)) == 1
