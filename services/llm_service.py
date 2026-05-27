from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from app.config import Settings

if TYPE_CHECKING:
    from services.retrieval_service import RetrievalResult


SYSTEM_PROMPT = (
    "You are an AI study assistant inside Discord. "
    "Give concise, accurate, student-friendly explanations. "
    "If the question is ambiguous, state your assumption clearly."
)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chat_client = AsyncOpenAI(
            api_key=settings.chat_api_key,
            base_url=settings.chat_base_url,
        )
        self.embedding_model = SentenceTransformer(settings.embedding_model)

    async def answer_question(self, question: str) -> str:
        completion = await self.chat_client.chat.completions.create(
            model=self.settings.chat_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        return completion.choices[0].message.content or "I couldn't generate a response."

    async def answer_with_context(self, *, question: str, context: str) -> str:
        prompt = (
            "Answer the question using the study material context below. "
            "Prefer the retrieved notes over general knowledge. "
            "If the context is insufficient, say so clearly. "
            "Do not invent sources or page numbers.\n\n"
            f"Study material:\n{context}\n\nQuestion:\n{question}"
        )
        return await self.answer_question(prompt)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = await asyncio.to_thread(
            self.embedding_model.encode,
            texts,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    async def embed_text(self, text: str) -> list[float]:
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def generate_quiz(self, *, topic: str, retrieval: "RetrievalResult") -> dict:
        prompt = (
            "Create one multiple-choice quiz question for a student using the study material below. "
            "Return valid JSON with keys: question, options, answer_index, explanation, sources. "
            "options must contain exactly 4 strings. answer_index must be an integer from 0 to 3. "
            "sources must be a short list copied from the provided citations.\n\n"
            f"Topic request: {topic}\n\n"
            f"Study material:\n{retrieval.context}\n\n"
            f"Available citations:\n{chr(10).join(retrieval.citations)}"
        )
        completion = await self.chat_client.chat.completions.create(
            model=self.settings.chat_model,
            temperature=0.4,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        return json.loads(content)

    async def generate_review_advice(
        self,
        *,
        review_context: str,
        weak_sources: list[str],
    ) -> str:
        prompt = (
            "You are helping a student review weak spots from recent quiz attempts. "
            "Based on the attempt history below, give a short review plan with: "
            "1) the top weak concepts, 2) what to revisit first, and 3) one concrete next action. "
            "Keep it concise and actionable.\n\n"
            f"Weak sources: {', '.join(weak_sources) if weak_sources else 'None identified'}\n\n"
            f"Recent attempt history:\n{review_context}"
        )
        return await self.answer_question(prompt)
