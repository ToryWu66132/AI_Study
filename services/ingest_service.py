from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from pypdf import PdfReader

from services.llm_service import LLMService
from services.vector_store import JsonVectorStore


class IngestService:
    def __init__(
        self,
        *,
        upload_dir: Path,
        vector_store: JsonVectorStore,
        llm_service: LLMService,
    ) -> None:
        self.upload_dir = upload_dir
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.upload_dir / "documents.json"
        if not self.registry_path.exists():
            self._write_registry([])

    async def ingest_attachment(self, attachment: discord.Attachment) -> str:
        suffix = Path(attachment.filename).suffix.lower()
        if suffix not in {".pdf", ".txt", ".md"}:
            raise ValueError("Only PDF, TXT, and MD files are supported right now.")

        saved_path = self.upload_dir / attachment.filename
        await attachment.save(saved_path)
        file_hash = self._hash_file(saved_path)
        registry = self._read_registry()

        duplicate = next((item for item in registry if item["sha256"] == file_hash), None)
        if duplicate:
            saved_path.unlink(missing_ok=True)
            return (
                f"`{attachment.filename}` was already indexed as `{duplicate['filename']}`. "
                "Skipped duplicate upload."
            )

        replaced_entry = next((item for item in registry if item["filename"] == attachment.filename), None)
        if replaced_entry:
            self.vector_store.remove_by_source(attachment.filename)
            registry = [item for item in registry if item["filename"] != attachment.filename]

        document_pages = self._extract_document_pages(saved_path)
        chunks = self._chunk_pages(document_pages)
        if not chunks:
            saved_path.unlink(missing_ok=True)
            raise ValueError("The uploaded file did not contain readable text.")

        embeddings = await self.llm_service.embed_texts([chunk["text"] for chunk in chunks])
        indexed_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            indexed_chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "source": attachment.filename,
                    "page": chunk["page"],
                    "text": chunk["text"],
                    "embedding": embedding,
                }
            )

        self.vector_store.add_documents(indexed_chunks)
        registry.append(
            {
                "filename": attachment.filename,
                "sha256": file_hash,
                "chunk_count": len(indexed_chunks),
                "page_count": len(document_pages),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._write_registry(registry)

        replacement_note = ""
        if replaced_entry:
            replacement_note = " Replaced the previous indexed version with the same filename."
        return (
            f"Indexed `{attachment.filename}` with {len(indexed_chunks)} chunks. "
            f"The knowledge base now has {self.vector_store.count()} chunks."
            f"{replacement_note}"
        )

    def status_summary(self) -> str:
        registry = self._read_registry()
        file_count = len(registry)
        chunk_count = self.vector_store.count()
        return (
            "RAG ingestion pipeline is ready.\n"
            f"Upload directory: {self.upload_dir}\n"
            f"Files stored: {file_count}\n"
            f"Indexed chunks: {chunk_count}"
        )

    def list_documents_summary(self) -> str:
        registry = self._read_registry()
        if not registry:
            return "No study documents have been indexed yet."

        lines = ["Indexed documents:"]
        for item in sorted(registry, key=lambda row: row["uploaded_at"], reverse=True):
            lines.append(
                f"- {item['filename']} | pages: {item['page_count']} | chunks: {item['chunk_count']}"
            )
        return "\n".join(lines)

    def _extract_document_pages(self, path: Path) -> list[dict[str, int | str]]:
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf_pages(path)
        text = path.read_text(encoding="utf-8")
        return [{"page": 1, "text": text}]

    def _extract_pdf_pages(self, path: Path) -> list[dict[str, int | str]]:
        reader = PdfReader(str(path))
        pages: list[dict[str, int | str]] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": index, "text": text})
        return pages

    def _chunk_pages(
        self,
        pages: list[dict[str, int | str]],
        *,
        chunk_size: int = 900,
        overlap: int = 150,
    ) -> list[dict[str, int | str]]:
        chunks: list[dict[str, int | str]] = []
        for page in pages:
            page_number = int(page["page"])
            cleaned_text = self._clean_text(str(page["text"]))
            if not cleaned_text:
                continue

            start = 0
            while start < len(cleaned_text):
                end = start + chunk_size
                chunk_text = cleaned_text[start:end].strip()
                if chunk_text:
                    chunks.append({"page": page_number, "text": chunk_text})
                if end >= len(cleaned_text):
                    break
                start = max(end - overlap, start + 1)
        return chunks

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _read_registry(self) -> list[dict[str, Any]]:
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _write_registry(self, documents: list[dict[str, Any]]) -> None:
        self.registry_path.write_text(
            json.dumps(documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
