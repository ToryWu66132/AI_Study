from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.llm_service import LLMService
from services.retrieval_service import RetrievalService


class QuizService:
    def __init__(
        self,
        *,
        llm_service: LLMService,
        retrieval_service: RetrievalService,
        session_path: Path,
    ) -> None:
        self.llm_service = llm_service
        self.retrieval_service = retrieval_service
        self.session_path = session_path
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_path.exists():
            self._write({})

    async def generate_quiz(
        self,
        *,
        user_id: int,
        topic: str,
        preferred_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        retrieval = await self.retrieval_service.retrieve_with_sources(
            question=topic,
            top_k=6,
            preferred_sources=preferred_sources,
        )
        if not retrieval.has_results:
            raise ValueError(retrieval.message or "No study materials available for quiz generation.")

        quiz = await self.llm_service.generate_quiz(topic=topic, retrieval=retrieval)
        self._validate_quiz(quiz)

        sessions = self._read()
        sessions[str(user_id)] = quiz
        self._write(sessions)
        return quiz

    def get_active_quiz(self, *, user_id: int) -> dict[str, Any] | None:
        return self._read().get(str(user_id))

    def clear_active_quiz(self, *, user_id: int) -> None:
        sessions = self._read()
        sessions.pop(str(user_id), None)
        self._write(sessions)

    def _validate_quiz(self, quiz: dict[str, Any]) -> None:
        if not isinstance(quiz.get("question"), str):
            raise ValueError("Quiz generation failed: missing question.")
        options = quiz.get("options")
        if not isinstance(options, list) or len(options) != 4 or not all(isinstance(item, str) for item in options):
            raise ValueError("Quiz generation failed: expected exactly 4 answer options.")
        answer_index = quiz.get("answer_index")
        if not isinstance(answer_index, int) or not 0 <= answer_index <= 3:
            raise ValueError("Quiz generation failed: answer_index must be between 0 and 3.")
        if not isinstance(quiz.get("explanation"), str):
            raise ValueError("Quiz generation failed: missing explanation.")
        if not isinstance(quiz.get("sources"), list):
            raise ValueError("Quiz generation failed: missing sources.")

    def _read(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.session_path.read_text(encoding="utf-8"))

    def _write(self, sessions: dict[str, dict[str, Any]]) -> None:
        self.session_path.write_text(
            json.dumps(sessions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
