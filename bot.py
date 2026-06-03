"""Entry point bot Telegram asisten keuangan Hermes.

Menjalankan bot dengan long-polling. Pesan teks pengguna diteruskan ke Hermes
(LLM) yang dapat memanggil tool keuangan, lalu balasannya dikirim ke Telegram.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app import db
from app.llm.client import generate_reply
from config import config

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("hermes-bot")

# Riwayat percakapan per chat (in-memory). {chat_id: [{role, content}, ...]}
_history: dict[int, list[dict]] = {}
MAX_HISTORY_MESSAGES = 20  # 10 giliran terakhir

WELCOME = (
    "👋 Halo! Aku *Hermes*, asisten keuanganmu.\n\n"
    "Aku bisa membantu:\n"
    "💰 *Budgeting pribadi* — catat pengeluaran/pemasukan & ringkasan bulanan\n"
    "🧾 *Pembukuan usaha* — catat transaksi bisnis & laporan laba-rugi\n"
    "💬 *Edukasi keuangan* — tanya konsep keuangan apa pun\n\n"
    "Contoh yang bisa kamu ketik:\n"
    "• _catat jajan 25rb tadi siang_\n"
    "• _set budget makan 1,5jt per bulan_\n"
    "• _ringkasan bulan ini_\n"
    "• _penjualan usaha hari ini 500rb_\n"
    "• _laporan laba rugi bulan ini_\n"
    "• _jelaskan aturan 50/30/20_\n\n"
    "Ketik /help kapan saja untuk melihat panduan ini lagi."
)


def _is_allowed(user_id: int) -> bool:
    if not config.allowed_user_ids:
        return True
    return user_id in config.allowed_user_ids


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _history.pop(update.effective_chat.id, None)
    await update.message.reply_text("🔄 Konteks percakapan direset.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return

    if not _is_allowed(user.id):
        await update.message.reply_text(
            "Maaf, kamu belum diizinkan memakai bot ini. "
            f"Minta admin menambahkan ID kamu: {user.id}"
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    history = _history.setdefault(chat_id, [])
    try:
        reply = await asyncio.to_thread(generate_reply, user.id, list(history), text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gagal memproses pesan")
        await update.message.reply_text(
            "⚠️ Maaf, ada kendala menghubungi mesin AI (Hermes). "
            "Cek apakah backend LLM aktif & konfigurasi .env sudah benar.\n"
            f"Detail: {exc}"
        )
        return

    # Simpan giliran ke riwayat lalu pangkas.
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    del history[:-MAX_HISTORY_MESSAGES]

    await update.message.reply_text(reply)


def main() -> None:
    config.validate()
    db.init_db()

    application = Application.builder().token(config.telegram_token).build()
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot Hermes berjalan (model=%s, backend=%s)...",
                config.llm_model, config.llm_base_url)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
