"""Entry point bot Telegram asisten keuangan Hermes.

Mendukung menu tombol interaktif (inline keyboard) + pemrosesan bahasa natural
lewat Hermes (LLM). Tombol pencatatan & info bekerja tanpa LLM (langsung ke
service), sedangkan teks bebas, edukasi, dan tombol kustom memakai LLM.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app import db, keyboards
from app.llm.client import generate_reply
from app.services import business, debt, education, personal
from app.utils import parse_entry
from config import config

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("hermes-bot")

# Riwayat percakapan AI per chat. {chat_id: [{role, content}, ...]}
_history: dict[int, list[dict]] = {}
MAX_HISTORY_MESSAGES = 20

WELCOME = (
    "👋 Halo! Aku *Hermes*, asisten keuanganmu.\n\n"
    "Gunakan tombol di bawah untuk catat cepat, atau cukup *ketik bebas* seperti:\n"
    "• _catat jajan 25rb_\n"
    "• _ringkasan bulan ini_\n"
    "• _jelaskan dana darurat_\n\n"
    "Pilih menu:"
)

HELP = (
    "*Panduan singkat*\n\n"
    "📋 /menu — tampilkan tombol menu\n"
    "⭐ /addbutton — buat tombol sendiri\n"
    "   Format: `/addbutton Label | teks yang dikirim`\n"
    "   Contoh: `/addbutton Kopi harian | catat kopi 20rb`\n"
    "🗑 /buttons — kelola/hapus tombol kustom\n"
    "🔄 /reset — hapus konteks obrolan AI\n\n"
    "Kamu juga bisa ketik bebas, mis. _catat gaji 7jt_, _laporan laba rugi_, "
    "_hutang 500rb ke budi_, atau tanya edukasi keuangan."
)

# Prompt untuk aksi yang butuh input. key -> (pending, pesan)
INPUT_ACTIONS: dict[str, tuple[str, str]] = {
    "a:inc": ("inc", "💰 *Catat Pemasukan*\nKirim: `<jumlah> <kategori> <catatan>`\nContoh: `7jt gaji bulanan`"),
    "a:exp": ("exp", "💸 *Catat Pengeluaran*\nKirim: `<jumlah> <kategori> <catatan>`\nContoh: `50rb makan nasi padang`"),
    "a:debt": ("debt", "🔴 *Catat Hutang* (kamu pinjam)\nKirim: `<jumlah> <nama> <catatan>`\nContoh: `500rb budi modal usaha`"),
    "a:lent": ("lent", "🟢 *Catat Piutang* (kamu memberi pinjam)\nKirim: `<jumlah> <nama> <catatan>`\nContoh: `200rb andi`"),
    "a:bizin": ("bizin", "💰 *Pemasukan Usaha*\nKirim: `<jumlah> <kategori> <catatan>`\nContoh: `500rb penjualan`"),
    "a:bizex": ("bizex", "💸 *Pengeluaran Usaha*\nKirim: `<jumlah> <kategori> <catatan>`\nContoh: `200rb bahan-baku`"),
}

CUSTOM_INFO = (
    "⭐ *Tombol Saya*\n\n"
    "Buat tombol pintasmu sendiri dengan:\n"
    "`/addbutton Label | teks yang dikirim`\n\n"
    "Contoh: `/addbutton Kopi | catat kopi 20rb`\n"
    "Saat ditekan, tombol mengirim teks itu ke bot. Tekan 🗑 untuk menghapus."
)


def _is_allowed(user_id: int) -> bool:
    return not config.allowed_user_ids or user_id in config.allowed_user_ids


async def _safe_edit(query, text: str, **kwargs) -> None:
    """edit_message_text yang mengabaikan error 'message is not modified'."""
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not _is_allowed(uid):
        await update.message.reply_text(
            f"Maaf, kamu belum diizinkan memakai bot ini. ID kamu: {uid}"
        )
        return
    await update.message.reply_text(
        WELCOME, parse_mode="Markdown", reply_markup=keyboards.main_menu(uid)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP, parse_mode="Markdown")


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    await update.message.reply_text("📋 Menu:", reply_markup=keyboards.main_menu(uid))


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _history.pop(update.effective_chat.id, None)
    context.user_data.pop("pending", None)
    await update.message.reply_text("🔄 Konteks percakapan direset.")


async def addbutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    arg = " ".join(context.args) if context.args else ""
    if "|" in arg:
        label, payload = arg.split("|", 1)
        label, payload = label.strip(), payload.strip()
        if label and payload:
            db.add_custom_button(uid, label[:40], payload)
            await update.message.reply_text(
                f"✅ Tombol '{label[:40]}' dibuat.",
                reply_markup=keyboards.main_menu(uid),
            )
            return
    # tidak ada argumen valid -> mode tuntun
    context.user_data["pending"] = "addbtn"
    await update.message.reply_text(
        "Kirim tombol baru dengan format:\n`Label | teks yang dikirim`\n"
        "Contoh: `Kopi harian | catat kopi 20rb`",
        parse_mode="Markdown",
        reply_markup=keyboards.cancel_menu(),
    )


async def buttons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    await update.message.reply_text(
        CUSTOM_INFO, parse_mode="Markdown",
        reply_markup=keyboards.custom_buttons_menu(uid),
    )


# ---------------------------------------------------------------------------
# Callback tombol
# ---------------------------------------------------------------------------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = update.effective_user.id
    await query.answer()
    if not _is_allowed(uid):
        await query.answer("Tidak diizinkan.", show_alert=True)
        return

    data = query.data or ""

    if data == "a:menu":
        context.user_data.pop("pending", None)
        await _safe_edit(query, "📋 Menu:", reply_markup=keyboards.main_menu(uid))
        return
    if data == "a:cancel":
        context.user_data.pop("pending", None)
        await _safe_edit(query, "Dibatalkan.", reply_markup=keyboards.main_menu(uid))
        return

    # aksi input -> set pending lalu minta detail
    if data in INPUT_ACTIONS:
        pending, msg = INPUT_ACTIONS[data]
        context.user_data["pending"] = pending
        await _safe_edit(query, msg, parse_mode="Markdown", reply_markup=keyboards.cancel_menu())
        return

    # aksi info -> langsung tampilkan (tanpa LLM)
    info = {
        "a:sum": lambda: personal.ringkasan_bulanan(uid),
        "a:bud": lambda: personal.status_budget(uid),
        "a:debts": lambda: debt.daftar(uid),
        "a:edu": lambda: education.daftar_topik(),
        "a:bizrep": lambda: business.laporan_laba_rugi(uid),
    }
    if data in info:
        await _safe_edit(query, info[data](), reply_markup=keyboards.back_menu())
        return

    if data == "a:biz":
        await _safe_edit(query, "🧾 Menu Usaha:", reply_markup=keyboards.business_menu())
        return
    if data == "a:cust":
        await _safe_edit(query, CUSTOM_INFO, parse_mode="Markdown",
                         reply_markup=keyboards.custom_buttons_menu(uid))
        return

    if data.startswith("c:"):  # jalankan tombol kustom
        b = db.get_custom_button(uid, int(data[2:]))
        if not b:
            await query.answer("Tombol tidak ditemukan.", show_alert=True)
            return
        await _safe_edit(query, f"⏳ Menjalankan: {b['label']}")
        await _process_text(uid, update.effective_chat.id, b["payload"],
                            reply_target=query.message, context=context)
        return

    if data.startswith("d:"):  # hapus tombol kustom
        db.delete_custom_button(uid, int(data[2:]))
        await _safe_edit(query, "🗑 Tombol dihapus.\n\n" + CUSTOM_INFO,
                         parse_mode="Markdown",
                         reply_markup=keyboards.custom_buttons_menu(uid))
        return


# ---------------------------------------------------------------------------
# Pesan teks
# ---------------------------------------------------------------------------
async def _handle_pending(uid: int, pending: str, text: str, message, context) -> None:
    """Tangani input setelah tombol input ditekan. Mengembalikan True bila selesai."""
    if pending == "addbtn":
        if "|" in text:
            label, payload = text.split("|", 1)
            label, payload = label.strip()[:40], payload.strip()
            if label and payload:
                db.add_custom_button(uid, label, payload)
                context.user_data.pop("pending", None)
                await message.reply_text(
                    f"✅ Tombol '{label}' dibuat.",
                    reply_markup=keyboards.main_menu(uid),
                )
                return
        await message.reply_text(
            "Format salah. Kirim: `Label | teks`", parse_mode="Markdown",
            reply_markup=keyboards.cancel_menu(),
        )
        return

    amount, cat, note = parse_entry(text)
    if amount is None:
        await message.reply_text(
            "⚠️ Aku tidak menemukan nominal. Contoh: `50rb makan`",
            parse_mode="Markdown", reply_markup=keyboards.cancel_menu(),
        )
        return  # tetap di mode input agar bisa coba lagi

    if pending == "exp":
        res = personal.catat_pengeluaran(uid, amount, cat, note)
    elif pending == "inc":
        res = personal.catat_pemasukan(uid, amount, cat, note)
    elif pending == "debt":
        res = debt.catat_hutang(uid, amount, party=cat, note=note)
    elif pending == "lent":
        res = debt.catat_piutang(uid, amount, party=cat, note=note)
    elif pending == "bizin":
        res = business.catat_transaksi_usaha(uid, "income", amount, cat, note)
    elif pending == "bizex":
        res = business.catat_transaksi_usaha(uid, "expense", amount, cat, note)
    else:
        res = "(aksi tidak dikenal)"

    context.user_data.pop("pending", None)
    await message.reply_text(res, reply_markup=keyboards.main_menu(uid))


async def _process_text(uid: int, chat_id: int, text: str, reply_target, context) -> None:
    """Kirim teks ke LLM (Hermes) dan balas hasilnya."""
    history = _history.setdefault(chat_id, [])
    try:
        reply = await asyncio.to_thread(generate_reply, uid, list(history), text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gagal memproses pesan")
        await reply_target.reply_text(
            "⚠️ Maaf, ada kendala menghubungi mesin AI (Hermes). "
            "Cek backend LLM & konfigurasi .env (LLM_API_KEY / LLM_MODEL).\n"
            f"Detail: {exc}",
            reply_markup=keyboards.menu_button(),
        )
        return
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    del history[:-MAX_HISTORY_MESSAGES]
    await reply_target.reply_text(reply, reply_markup=keyboards.menu_button())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return
    if not _is_allowed(uid):
        await update.message.reply_text(
            f"Maaf, kamu belum diizinkan memakai bot ini. ID kamu: {uid}"
        )
        return

    pending = context.user_data.get("pending")
    if pending:
        await _handle_pending(uid, pending, text, update.message, context)
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await _process_text(uid, chat_id, text, update.message, context)


def main() -> None:
    config.validate()
    db.init_db()

    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(CommandHandler(["start"], start))
    app.add_handler(CommandHandler(["help"], help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("addbutton", addbutton_cmd))
    app.add_handler(CommandHandler("buttons", buttons_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot Hermes berjalan (model=%s, backend=%s)...",
                config.llm_model, config.llm_base_url)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
