from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StudyRecordService:
    def __init__(self, record_path: Path) -> None:
        self.record_path = record_path
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.record_path.exists():
            self._write({})

    def record_quiz_attempt(
        self,
        *,
        user_id: int,
        question: str,
        selected_index: int,
        correct_index: int,
        explanation: str,
        sources: list[str],
    ) -> dict[str, Any]:
        records = self._read()
        user_key = str(user_id)
        attempts = records.setdefault(user_key, [])
        is_correct = selected_index == correct_index
        attempts.append(
            {
                "question": question,
                "selected_index": selected_index,
                "correct_index": correct_index,
                "is_correct": is_correct,
                "explanation": explanation,
                "sources": sources,
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._write(records)
        return {"is_correct": is_correct, "total_attempts": len(attempts)}

    def build_stats_summary(self, *, user_id: int) -> str:
        attempts = self._read().get(str(user_id), [])
        if not attempts:
            return "No quiz attempts recorded yet. Try `/quiz` first."

        total = len(attempts)
        correct = sum(1 for attempt in attempts if attempt["is_correct"])
        accuracy = (correct / total) * 100
        wrong_sources = [
            source
            for attempt in attempts
            if not attempt["is_correct"]
            for source in attempt.get("sources", [])
        ]
        weak_sources = Counter(wrong_sources).most_common(3)
        latest = attempts[-1]["answered_at"]

        lines = [
            f"Quiz attempts: {total}",
            f"Correct answers: {correct}",
            f"Accuracy: {accuracy:.1f}%",
            f"Last activity: {latest}",
        ]
        if weak_sources:
            lines.append("Review these sources:")
            for source, count in weak_sources:
                lines.append(f"- {source} ({count} missed questions)")
        return "\n".join(lines)

    def get_weak_sources(self, *, user_id: int, limit: int = 3) -> list[str]:
        attempts = self._read().get(str(user_id), [])
        wrong_sources = [
            source
            for attempt in attempts
            if not attempt["is_correct"]
            for source in attempt.get("sources", [])
        ]
        return [source for source, _count in Counter(wrong_sources).most_common(limit)]

    def build_review_context(self, *, user_id: int, limit: int = 5) -> str:
        attempts = self._read().get(str(user_id), [])
        if not attempts:
            return "No quiz attempts recorded yet."

        recent_attempts = attempts[-limit:]
        lines = []
        for attempt in recent_attempts:
            result = "correct" if attempt["is_correct"] else "incorrect"
            lines.append(
                f"Question: {attempt['question']}\n"
                f"Result: {result}\n"
                f"Explanation: {attempt['explanation']}\n"
                f"Sources: {', '.join(attempt.get('sources', []))}"
            )
        return "\n\n".join(lines)

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def _write(self, records: dict[str, list[dict[str, Any]]]) -> None:
        self.record_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
