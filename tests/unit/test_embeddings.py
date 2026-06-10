from unittest.mock import patch

import numpy as np

from docpulse.indexing.embeddings import Embedder


def fake_response(inputs):
    class R:
        data = [{"embedding": [float(len(t)), 1.0]} for t in inputs]

    return R()


def test_embeds_and_caches(tmp_path):
    embedder = Embedder(model="openai/text-embedding-3-small", cache_path=tmp_path / "emb.json")
    with patch("docpulse.indexing.embeddings.litellm.embedding") as mock_embed:
        mock_embed.side_effect = lambda model, input: fake_response(input)
        first = embedder.embed({"h1": "hello", "h2": "worlds!"})
        assert np.allclose(first["h1"], [5.0, 1.0])
        assert mock_embed.call_count == 1

        # second call: everything cached, no API hit
        second = embedder.embed({"h1": "hello", "h2": "worlds!"})
        assert mock_embed.call_count == 1
        assert np.allclose(second["h2"], first["h2"])


def test_cache_persists_across_instances(tmp_path):
    cache = tmp_path / "emb.json"
    with patch("docpulse.indexing.embeddings.litellm.embedding") as mock_embed:
        mock_embed.side_effect = lambda model, input: fake_response(input)
        Embedder(model="m", cache_path=cache).embed({"h1": "hello"})
        Embedder(model="m", cache_path=cache).embed({"h1": "hello"})
        assert mock_embed.call_count == 1
