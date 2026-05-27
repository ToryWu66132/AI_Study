from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    chat_api_key: str
    chat_base_url: str
    chat_model: str
    embedding_model: str
    bot_prefix: str = "!"

    @classmethod
    def from_env(cls) -> "Settings":
        chat_api_key = os.getenv("CHAT_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        chat_base_url = os.getenv("CHAT_BASE_URL") or os.getenv(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1",
        )
        chat_model = os.getenv("CHAT_MODEL") or os.getenv(
            "OPENAI_CHAT_MODEL",
            "gpt-4o-mini",
        )
        embedding_model = os.getenv("EMBEDDING_MODEL") or os.getenv(
            "LOCAL_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        return cls(
            discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            chat_api_key=chat_api_key,
            chat_base_url=chat_base_url,
            chat_model=chat_model,
            embedding_model=embedding_model,
            bot_prefix=os.getenv("BOT_PREFIX", "!"),
        )

    def validate(self) -> None:
        missing = []
        if not self.discord_bot_token:
            missing.append("DISCORD_BOT_TOKEN")
        if not self.chat_api_key:
            missing.append("CHAT_API_KEY or OPENAI_API_KEY")

        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_list}")
