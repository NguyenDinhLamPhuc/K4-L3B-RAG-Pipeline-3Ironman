from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src import task10_generation as generation
from src.contracts import validate_generation_result


def chunks(method='hybrid'):
    return [{'id': f'chunk-{i}', 'content': f'Evidence {i}', 'score': 1 - i / 10,
             'metadata': {'source': 'policy.md', 'title': 'Policy', 'doc_type': 'legal',
                          'url': None, 'chunk_index': i}, 'retrieval_method': method}
            for i in range(5)]


@pytest.mark.parametrize('method', ['hybrid', 'pageindex'])
def test_generation_citations_survive_reorder(monkeypatch, method):
    source = chunks(method)
    original = deepcopy(source)
    monkeypatch.setattr(generation, 'retrieve', lambda query, top_k: source)

    def llm(system, message):
        assert message.index('[Source: chunk-4]') < message.index('[Source: chunk-1]')
        assert 'Title: Policy' in message and 'Source: policy.md' in message
        return 'Evidence 1 [Source: chunk-1]'

    monkeypatch.setattr(generation, 'call_llm', llm)
    result = generation.generate_with_citation('Question')
    validate_generation_result(result)
    assert result['retrieval_source'] == method
    assert result['sources'] == source == original


@pytest.mark.parametrize('answer', ['', 'Unsupported answer', 'Claim [Source: invented]', generation.SAFE_REFUSAL])
def test_invalid_or_refused_answer_has_no_sources(monkeypatch, answer):
    monkeypatch.setattr(generation, 'retrieve', lambda query, top_k: chunks())
    monkeypatch.setattr(generation, 'call_llm', lambda *args: answer)
    result = generation.generate_with_citation('Question')
    assert result == {'answer': generation.SAFE_REFUSAL, 'sources': [], 'retrieval_source': 'none'}


def test_no_evidence_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(generation, 'retrieve', lambda query, top_k: [])
    monkeypatch.setattr(generation, 'call_llm', lambda *args: pytest.fail('No evidence'))
    validate_generation_result(generation.generate_with_citation('Question'))


def test_provider_error_is_safe(monkeypatch):
    monkeypatch.setattr(generation, 'retrieve', lambda query, top_k: chunks())

    def unavailable(*args):
        raise TimeoutError('Unavailable')

    monkeypatch.setattr(generation, 'call_llm', unavailable)
    result = generation.generate_with_citation('Question')
    assert result['sources'] == [] and result['retrieval_source'] == 'none'


def test_gemini_dispatch_returns_plain_text(monkeypatch):
    from google import genai

    monkeypatch.setattr(generation, 'LLM_PROVIDER', 'gemini')
    monkeypatch.setattr(generation, 'LLM_MODEL', 'test-model')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value = SimpleNamespace(text='  Answer  ')
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(genai, 'Client', factory)
    assert generation.call_llm('System', 'Question') == 'Answer'
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs['model'] == 'test-model'
    assert kwargs['contents'] == 'Question'
    assert kwargs['config'].system_instruction == 'System'
    assert factory.call_args.kwargs['http_options'].timeout == 30000
