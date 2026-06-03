"""Konfigurasi aplikasi, dibaca dari environment variables (.env)."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


@dataclass
class Config:
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Backend LLM (OpenAI-compatible: Ollama lokal atau OpenRouter, dsb)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "hermes3")

    db_path: str = os.getenv("DB_PATH", "finance.db")
    timezone: str = os.getenv("TIMEZONE", "Asia/Jakarta")

    allowed_user_ids: set[int] = field(
        default_factory=lambda: _parse_ids(os.getenv("ALLOWED_USER_IDS", ""))
    )

    def validate(self) -> None:
        if not self.telegram_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN belum diisi. Salin .env.example menjadi .env "
                "lalu isi tokennya."
            )


config = Config()
