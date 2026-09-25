from copy import deepcopy

import pytest

from src.task7_reranking import rerank_rrf
from src import task9_retrieval_pipeline as pipeline


def item(item_id, score, method='dense'):
    return {
        'id': item_id, 'content': 'Evidence', 'score': score,
        'metadata': {'source': 'policy.md', 'title': 'Policy', 'doc_type': 'legal',
                     'url': None, 'chunk_index': 0},
        'retrieval_method': method,
    }


def test_rrf_copies_inputs_and_fuses_by_rank():
    lists = [[item('a', 0.9), item('b', 0.8)],
             [item('b', 20, 'bm25'), item('c', 10, 'bm25')]]
    original = deepcopy(lists)
    output = rerank_rrf(lists, top_k=2)
    assert [row['id'] for row in output] == ['b', 'a']
    assert output[0]['score'] == pytest.approx(1 / 62 + 1 / 61)
    assert all(row['retrieval_method'] == 'hybrid' for row in output)
    output[0]['metadata']['title'] = 'Changed'
    assert lists == original


def test_rrf_rejects_upstream_duplicates():
    with pytest.raises(ValueError, match='upstream'):
        rerank_rrf([[item('a', 0.9), item('a', 0.8)]])
    assert rerank_rrf([]) == []
    assert rerank_rrf([[item('a', 1)]], top_k=0) == []
    with pytest.raises(ValueError, match='non-negative'):
        rerank_rrf([], k=-1)


def setup_retrievers(monkeypatch, dense, sparse, fallback):
    monkeypatch.setattr(pipeline, 'semantic_search', lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, 'lexical_search', lambda query, top_k: sparse)
    monkeypatch.setattr(pipeline, 'pageindex_search', fallback)


def test_real_fusion_keeps_cosine_confidence(monkeypatch):
    dense = [item('a', 0.9)]
    original = deepcopy(dense)

    def unexpected_fallback(query, top_k):
        pytest.fail('High cosine confidence must not trigger fallback on low RRF score')

    setup_retrievers(monkeypatch, dense, [item('a', 4, 'bm25')], unexpected_fallback)
    output = pipeline.retrieve('policy', score_threshold=0.5)
    assert output[0]['score'] == pytest.approx(2 / 61)
    assert dense == original


@pytest.mark.parametrize('fallback', [[], [item('a', 1, 'dense')]])
def test_empty_or_invalid_fallback_keeps_hybrid(monkeypatch, fallback):
    setup_retrievers(monkeypatch, [item('a', 0.1)], [], lambda query, top_k: fallback)
    output = pipeline.retrieve('policy', score_threshold=0.5)
    assert output[0]['retrieval_method'] == 'hybrid'


def test_no_dense_evidence_attempts_fallback_even_at_zero_threshold(monkeypatch):
    expected = [item('fallback', 1, 'pageindex')]
    setup_retrievers(monkeypatch, [], [], lambda query, top_k: expected)
    assert pipeline.retrieve('policy', score_threshold=0) == expected


def test_threshold_equality_and_dense_baseline(monkeypatch):
    dense = [item('a', 0.5)]

    def unexpected_fallback(query, top_k):
        pytest.fail('Equality is not below threshold')

    setup_retrievers(monkeypatch, dense, [], unexpected_fallback)
    monkeypatch.setattr(pipeline, 'rerank_rrf', lambda *args, **kwargs: pytest.fail('RRF disabled'))
    assert pipeline.retrieve('policy', score_threshold=0.5, use_reranking=False) == dense


def test_no_evidence_and_provider_error_returns_empty(monkeypatch):
    def unavailable(query, top_k):
        raise TimeoutError('provider timed out')

    setup_retrievers(monkeypatch, [], [], unavailable)
    assert pipeline.retrieve('policy') == []
