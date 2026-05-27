from __future__ import annotations

import discord
from discord import app_commands

from services.ingest_service import IngestService
from services.llm_service import LLMService
from services.quiz_service import QuizService
from services.retrieval_service import RetrievalService
from services.study_record_service import StudyRecordService


class StudyAssistantClient(discord.Client):
    def __init__(
        self,
        *,
        llm_service: LLMService,
        ingest_service: IngestService,
        retrieval_service: RetrievalService,
        quiz_service: QuizService,
        study_record_service: StudyRecordService,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.llm_service = llm_service
        self.ingest_service = ingest_service
        self.retrieval_service = retrieval_service
        self.quiz_service = quiz_service
        self.study_record_service = study_record_service
        self._register_commands()

    def _register_commands(self) -> None:
        @self.tree.command(
            name="ask",
            description="Ask the AI study assistant a question.",
        )
        @app_commands.describe(question="The question you want the bot to answer.")
        async def ask(interaction: discord.Interaction, question: str) -> None:
            await interaction.response.defer(thinking=True)
            answer = await self.llm_service.answer_question(question)
            await interaction.followup.send(answer)

        @self.tree.command(
            name="askdoc",
            description="Ask a question against uploaded study materials.",
        )
        @app_commands.describe(question="Question to answer using the study knowledge base.")
        async def askdoc(interaction: discord.Interaction, question: str) -> None:
            await interaction.response.defer(thinking=True)
            result = await self.retrieval_service.retrieve(question)
            if not result.has_results:
                await interaction.followup.send(result.message or "No matching context found.")
                return

            answer = await self.llm_service.answer_with_context(
                question=question,
                context=result.context,
            )
            citations = "\n".join(f"- {item}" for item in result.citations)
            response = f"{answer}\n\nSources:\n{citations}"
            await interaction.followup.send(response[:2000])

        @self.tree.command(
            name="upload_doc",
            description="Upload a PDF, TXT, or MD file into the study knowledge base.",
        )
        @app_commands.describe(file="The study material to index.")
        async def upload_doc(interaction: discord.Interaction, file: discord.Attachment) -> None:
            await interaction.response.defer(thinking=True, ephemeral=True)
            try:
                summary = await self.ingest_service.ingest_attachment(file)
            except ValueError as exc:
                await interaction.followup.send(str(exc), ephemeral=True)
                return
            await interaction.followup.send(summary, ephemeral=True)

        @self.tree.command(
            name="uploadstatus",
            description="Show the current document ingestion status.",
        )
        async def upload_status(interaction: discord.Interaction) -> None:
            summary = self.ingest_service.status_summary()
            await interaction.response.send_message(summary, ephemeral=True)

        @self.tree.command(
            name="list_docs",
            description="List the documents currently indexed in the study knowledge base.",
        )
        async def list_docs(interaction: discord.Interaction) -> None:
            summary = self.ingest_service.list_documents_summary()
            await interaction.response.send_message(summary[:2000], ephemeral=True)

        @self.tree.command(
            name="quiz",
            description="Generate a multiple-choice quiz from your uploaded study materials.",
        )
        @app_commands.describe(topic="What should the quiz focus on?")
        async def quiz(interaction: discord.Interaction, topic: str) -> None:
            await interaction.response.defer(thinking=True)
            weak_sources = self.study_record_service.get_weak_sources(user_id=interaction.user.id)
            try:
                quiz_payload = await self.quiz_service.generate_quiz(
                    user_id=interaction.user.id,
                    topic=topic,
                    preferred_sources=weak_sources,
                )
            except ValueError as exc:
                await interaction.followup.send(str(exc))
                return

            options = quiz_payload["options"]
            focus_note = ""
            if weak_sources:
                focus_note = "Prioritizing your weak sources first.\n"
            message = (
                f"{focus_note}Quiz topic: {topic}\n"
                f"{quiz_payload['question']}\n\n"
                f"A. {options[0]}\n"
                f"B. {options[1]}\n"
                f"C. {options[2]}\n"
                f"D. {options[3]}\n\n"
                "Reply with `/answer_quiz` and choose A, B, C, or D."
            )
            await interaction.followup.send(message[:2000])

        @self.tree.command(
            name="answer_quiz",
            description="Submit your answer to the current active quiz.",
        )
        @app_commands.describe(choice="Choose A, B, C, or D.")
        @app_commands.choices(
            choice=[
                app_commands.Choice(name="A", value="A"),
                app_commands.Choice(name="B", value="B"),
                app_commands.Choice(name="C", value="C"),
                app_commands.Choice(name="D", value="D"),
            ]
        )
        async def answer_quiz(interaction: discord.Interaction, choice: app_commands.Choice[str]) -> None:
            quiz_payload = self.quiz_service.get_active_quiz(user_id=interaction.user.id)
            if not quiz_payload:
                await interaction.response.send_message(
                    "No active quiz found. Run `/quiz` first.",
                    ephemeral=True,
                )
                return

            selected_index = "ABCD".index(choice.value)
            result = self.study_record_service.record_quiz_attempt(
                user_id=interaction.user.id,
                question=quiz_payload["question"],
                selected_index=selected_index,
                correct_index=quiz_payload["answer_index"],
                explanation=quiz_payload["explanation"],
                sources=quiz_payload["sources"],
            )
            self.quiz_service.clear_active_quiz(user_id=interaction.user.id)

            correct_letter = "ABCD"[quiz_payload["answer_index"]]
            if result["is_correct"]:
                feedback = "Correct."
            else:
                feedback = f"Not quite. The correct answer was {correct_letter}."
            response = (
                f"{feedback}\n\n"
                f"Explanation: {quiz_payload['explanation']}\n\n"
                "Sources:\n"
                + "\n".join(f"- {source}" for source in quiz_payload["sources"])
            )
            await interaction.response.send_message(response[:2000], ephemeral=True)

        @self.tree.command(
            name="mystats",
            description="Show your quiz accuracy and review signals.",
        )
        async def mystats(interaction: discord.Interaction) -> None:
            summary = self.study_record_service.build_stats_summary(user_id=interaction.user.id)
            await interaction.response.send_message(summary[:2000], ephemeral=True)

        @self.tree.command(
            name="review",
            description="Get a short review plan based on your recent quiz history.",
        )
        async def review(interaction: discord.Interaction) -> None:
            await interaction.response.defer(thinking=True, ephemeral=True)
            review_context = self.study_record_service.build_review_context(user_id=interaction.user.id)
            if review_context == "No quiz attempts recorded yet.":
                await interaction.followup.send(review_context, ephemeral=True)
                return

            weak_sources = self.study_record_service.get_weak_sources(user_id=interaction.user.id)
            advice = await self.llm_service.generate_review_advice(
                review_context=review_context,
                weak_sources=weak_sources,
            )
            weak_source_block = ""
            if weak_sources:
                weak_source_block = "Priority sources:\n" + "\n".join(
                    f"- {source}" for source in weak_sources
                ) + "\n\n"
            response = f"{weak_source_block}{advice}"
            await interaction.followup.send(response[:2000], ephemeral=True)

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_ready(self) -> None:
        if self.user:
            print(f"Logged in as {self.user} (ID: {self.user.id})")
