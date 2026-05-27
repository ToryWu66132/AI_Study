from __future__ import annotations

from pathlib import Path

from app.config import Settings
from bot.discord_client import StudyAssistantClient
from services.ingest_service import IngestService
from services.llm_service import LLMService
from services.quiz_service import QuizService
from services.retrieval_service import RetrievalService
from services.study_record_service import StudyRecordService
from services.vector_store import JsonVectorStore


def main() -> None:
    settings = Settings.from_env()
    settings.validate()

    project_root = Path(__file__).resolve().parent
    llm_service = LLMService(settings)
    vector_store = JsonVectorStore(project_root / "data" / "vector_store" / "index.json")
    ingest_service = IngestService(
        upload_dir=project_root / "data" / "uploads",
        vector_store=vector_store,
        llm_service=llm_service,
    )
    retrieval_service = RetrievalService(
        vector_store=vector_store,
        llm_service=llm_service,
    )
    quiz_service = QuizService(
        llm_service=llm_service,
        retrieval_service=retrieval_service,
        session_path=project_root / "data" / "quiz_sessions.json",
    )
    study_record_service = StudyRecordService(
        project_root / "data" / "study_records.json"
    )

    client = StudyAssistantClient(
        llm_service=llm_service,
        ingest_service=ingest_service,
        retrieval_service=retrieval_service,
        quiz_service=quiz_service,
        study_record_service=study_record_service,
    )
    client.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
