from __future__ import annotations

from dataclasses import dataclass

from services.llm_service import LLMService
from services.vector_store import JsonVectorStore


@dataclass(frozen=True)
class RetrievalResult:
    context: str
    citations: list[str]
    has_results: bool
    message: str | None = None


class RetrievalService:
    def __init__(
        self,
        *,
        vector_store: JsonVectorStore,
        llm_service: LLMService,
    ) -> None:
        self.vector_store = vector_store
        self.llm_service = llm_service

    async def retrieve(self, question: str, top_k: int = 4) -> RetrievalResult:
        return await self.retrieve_with_sources(question=question, top_k=top_k)

    async def retrieve_with_sources(
        self,
        *,
        question: str,
        top_k: int = 4,
        preferred_sources: list[str] | None = None,
    ) -> RetrievalResult:
        if self.vector_store.count() == 0:
            return RetrievalResult(
                context="",
                citations=[],
                has_results=False,
                message="No study documents have been indexed yet.",
            )

        query_embedding = await self.llm_service.embed_text(question)
        matches = self.vector_store.search(query_embedding, top_k=top_k)
        if preferred_sources:
            preferred = [match for match in matches if match["source"] in preferred_sources]
            others = [match for match in matches if match["source"] not in preferred_sources]
            matches = preferred + others
        if not matches:
            return RetrievalResult(
                context="",
                citations=[],
                has_results=False,
                message="No relevant study chunks were found.",
            )

        context_sections = []
        citations = []
        for match in matches:
            context_sections.append(
                f"Source: {match['source']} | Page: {match['page']} | Score: {match['score']:.3f}\n"
                f"{match['text']}"
            )
            citations.append(
                f"{match['source']} (page {match['page']}, score {match['score']:.3f})"
            )
        return RetrievalResult(
            context="\n\n".join(context_sections),
            citations=citations,
            has_results=True,
        )
