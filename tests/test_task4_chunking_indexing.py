import numpy as np
import pytest

from src import task4_chunking_indexing as task4
from src.contracts import validate_document


def test_load_and_chunk_preserve_frontmatter(tmp_path, monkeypatch):
    folder = tmp_path / 'legal'
    folder.mkdir()
    (folder / 'policy.md').write_text(
        '---\nid: POLICY\nsource: original.pdf\ntitle: Policy\n'
        'doc_type: legal\nurl: https://example.org/policy\nhistorical: false\n---\n'
        + 'Policy content. ' * 100, encoding='utf-8',
    )
    monkeypatch.setattr(task4, 'STANDARDIZED_DIR', tmp_path)
    documents = task4.load_documents()
    assert documents[0]['id'] == 'POLICY'
    chunks = task4.chunk_documents(documents)
    assert chunks == task4.chunk_documents(task4.load_documents())
    assert len(chunks) > 1
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        assert chunk['metadata']['source'] == 'original.pdf'
        assert chunk['metadata']['url'] == 'https://example.org/policy'
        assert chunk['metadata']['historical'] is False
        assert len(chunk['content']) <= task4.CHUNK_SIZE
        assert 'source: original.pdf' not in chunk['content']


def test_local_embedding_batches_and_checks_dimension(monkeypatch):
    class Model:
        def get_sentence_embedding_dimension(self):
            return 2

        def encode(self, texts, **kwargs):
            assert kwargs['normalize_embeddings'] is True
            assert kwargs['batch_size'] == task4.BATCH_SIZE
            return np.array([[0.6, 0.8] for _ in texts])

    monkeypatch.setattr(task4, 'EMBEDDING_PROVIDER', 'sentence_transformers')
    monkeypatch.setattr(task4, 'EMBEDDING_DIM', 2)
    monkeypatch.setattr(task4, '_local_model', lambda name: Model())
    assert task4.embed_texts(['document', 'query']) == [[0.6, 0.8], [0.6, 0.8]]
    assert task4.embed_texts([]) == []
    monkeypatch.setattr(task4, 'EMBEDDING_DIM', 3)
    with pytest.raises(ValueError, match='dimension'):
        task4.embed_texts(['query'])


def test_index_is_persistent_idempotent_and_cosine(tmp_path, monkeypatch):
    monkeypatch.setattr(task4, 'CHROMA_DIR', tmp_path / 'chroma')
    monkeypatch.setattr(task4, 'EMBEDDING_DIM', 2)
    monkeypatch.setattr(task4, 'embed_texts', lambda texts: [[1.0, 0.0] for _ in texts])
    chunks = [{
        'id': 'policy::chunk-0', 'content': 'Policy content',
        'metadata': {'source': 'policy.pdf', 'title': 'Policy', 'doc_type': 'legal',
                     'url': None, 'chunk_index': 0},
    }]
    embedded = task4.embed_chunks(chunks)
    assert 'embedding' not in chunks[0]
    task4.index_to_vectorstore(embedded)
    task4.index_to_vectorstore(embedded)
    collection = task4.get_collection()
    assert collection.count() == 1
    result = collection.query(query_embeddings=[[1.0, 0.0]], n_results=1)
    assert result['ids'] == [['policy::chunk-0']]
    assert result['distances'][0][0] == pytest.approx(0.0)
    assert result['metadatas'][0][0]['url'] == ''
    monkeypatch.setattr(task4, 'EMBEDDING_MODEL', 'different-model')
    with pytest.raises(ValueError, match='configuration differs'):
        task4.get_collection()
