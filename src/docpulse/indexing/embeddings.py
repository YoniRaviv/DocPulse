import json
from pathlib import Path

import litellm
import numpy as np


class Embedder:
    """Embeds texts keyed by content hash; hash -> vector cached in a JSON file."""

    def __init__(self, model: str, cache_path: Path) -> None:
        self.model = model
        self.cache_path = cache_path
        self._cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text())

    def embed(self, texts_by_hash: dict[str, str]) -> dict[str, np.ndarray]:
        missing = [h for h in texts_by_hash if h not in self._cache]
        if missing:
            response = litellm.embedding(
                model=self.model, input=[texts_by_hash[h] for h in missing]
            )
            for position, item in enumerate(response.data):
                self._cache[missing[item.get("index", position)]] = item["embedding"]
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache))
        return {h: np.array(self._cache[h]) for h in texts_by_hash}
