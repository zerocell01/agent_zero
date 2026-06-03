"""Klien Hermes (OpenAI-compatible) dengan loop function-calling.

Mendukung Ollama lokal maupun API seperti OpenRouter, ditentukan lewat
LLM_BASE_URL / LLM_API_KEY / LLM_MODEL di .env.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.llm.tools import TOOLS, dispatch
from config import config

_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

MAX_TOOL_ROUNDS = 5


def _today_str() -> str:
    try:
        now = datetime.now(ZoneInfo(config.timezone))
    except Exception:
        now = datetime.now()
    return now.strftime("%Y-%m-%d (%A)")


def system_prompt() -> str:
    return (
        "Kamu adalah 'Hermes', asisten keuangan pribadi & usaha berbahasa Indonesia "
        "di dalam bot Telegram. Kamu ramah, ringkas, dan jujur.\n\n"
        f"Tanggal hari ini: {_today_str()}. Mata uang: Rupiah (IDR).\n\n"
        "Kamu punya TIGA peran:\n"
        "1. Budgeting pribadi: catat pemasukan/pengeluaran, atur budget, beri ringkasan bulanan.\n"
        "2. Pembukuan usaha: catat transaksi usaha, buat laporan laba-rugi.\n"
        "3. Edukasi keuangan: jawab pertanyaan konsep keuangan dengan bahasa sederhana.\n\n"
        "Aturan penting:\n"
        "- Untuk MENCATAT, MENGUBAH, atau MELIHAT data keuangan, SELALU gunakan tool yang tersedia. "
        "Jangan mengarang angka atau saldo.\n"
        "- Saat pengguna menyebut nominal seperti '50rb', '1,5jt', 'Rp200.000', konversikan ke angka "
        "polos (50000, 1500000, 200000) sebelum memanggil tool.\n"
        "- Jika maksud pengguna ambigu (mis. tidak jelas pribadi atau usaha), tanyakan singkat dulu.\n"
        "- Untuk pertanyaan edukasi, jawab langsung tanpa tool, singkat dan mudah dipahami.\n"
        "- Jangan memberi nasihat investasi spesifik yang menjanjikan keuntungan; beri edukasi umum "
        "dan ingatkan adanya risiko.\n"
        "- Setelah tool dijalankan, sampaikan hasilnya kembali ke pengguna dengan bahasa natural."
    )


def _serialize_tool_calls(tool_calls) -> list[dict]:
    return [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }
        for tc in tool_calls
    ]


def generate_reply(user_id: int, history: list[dict], user_text: str) -> str:
    """Hasilkan balasan asisten untuk satu pesan pengguna.

    `history` berisi giliran sebelumnya berupa {role, content} (user/assistant).
    Mengembalikan teks balasan final.
    """
    messages: list[dict] = [{"role": "system", "content": system_prompt()}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        resp = _client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip() or "(maaf, aku tidak punya jawaban)"

        # Simpan pesan assistant yang meminta tool, lalu jalankan tiap tool.
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": _serialize_tool_calls(msg.tool_calls),
            }
        )
        for tc in msg.tool_calls:
            result = dispatch(tc.function.name, tc.function.arguments, user_id)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

    # Bila loop tool habis, minta jawaban final tanpa tool.
    resp = _client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip() or "(maaf, terjadi kendala)"
