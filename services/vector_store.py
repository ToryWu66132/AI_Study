from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class JsonVectorStore:
    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._write([])

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        existing = self._read()
        existing.extend(documents)
        self._write(existing)

    def all_documents(self) -> list[dict[str, Any]]:
        return self._read()

    def count(self) -> int:
        return len(self._read())

    def remove_by_source(self, source: str) -> int:
        existing = self._read()
        remaining = [doc for doc in existing if doc.get("source") != source]
        removed = len(existing) - len(remaining)
        if removed:
            self._write(remaining)
        return removed

    def search(self, query_embedding: list[float], top_k: int = 4) -> list[dict[str, Any]]:
        scored = []
        for doc in self._read():
            score = cosine_similarity(query_embedding, doc["embedding"])
            scored.append({**doc, "score": score})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def _read(self) -> list[dict[str, Any]]:
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def _write(self, documents: list[dict[str, Any]]) -> None:
        self.store_path.write_text(
            json.dumps(documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
