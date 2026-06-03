"""Susunan tombol (inline keyboard) untuk bot Telegram."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app import db


def _grid(buttons: list[InlineKeyboardButton], cols: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = _grid([
        InlineKeyboardButton("💰 Pemasukan", callback_data="a:inc"),
        InlineKeyboardButton("💸 Pengeluaran", callback_data="a:exp"),
        InlineKeyboardButton("🔴 Hutang", callback_data="a:debt"),
        InlineKeyboardButton("🟢 Piutang", callback_data="a:lent"),
        InlineKeyboardButton("📊 Ringkasan", callback_data="a:sum"),
        InlineKeyboardButton("🎯 Budget", callback_data="a:bud"),
        InlineKeyboardButton("📒 Daftar Hutang", callback_data="a:debts"),
        InlineKeyboardButton("🧾 Usaha", callback_data="a:biz"),
        InlineKeyboardButton("📚 Edukasi", callback_data="a:edu"),
        InlineKeyboardButton("⭐ Tombol Saya", callback_data="a:cust"),
    ])

    # tambahkan tombol kustom milik pengguna (maks 6 ditampilkan di menu utama)
    custom = db.list_custom_buttons(user_id)[:6]
    if custom:
        rows += _grid([
            InlineKeyboardButton(f"• {b['label']}", callback_data=f"c:{b['id']}")
            for b in custom
        ])
    return InlineKeyboardMarkup(rows)


def business_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_grid([
        InlineKeyboardButton("💰 Pemasukan Usaha", callback_data="a:bizin"),
        InlineKeyboardButton("💸 Pengeluaran Usaha", callback_data="a:bizex"),
        InlineKeyboardButton("📈 Laba-Rugi", callback_data="a:bizrep"),
        InlineKeyboardButton("⬅️ Menu Utama", callback_data="a:menu"),
    ]))


def cancel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✖️ Batal", callback_data="a:cancel"),
    ]])


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Menu Utama", callback_data="a:menu"),
    ]])


def custom_buttons_menu(user_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for b in db.list_custom_buttons(user_id):
        rows.append([
            InlineKeyboardButton(f"• {b['label']}", callback_data=f"c:{b['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"d:{b['id']}"),
        ])
    rows.append([InlineKeyboardButton("⬅️ Menu Utama", callback_data="a:menu")])
    return InlineKeyboardMarkup(rows)



def menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Menu", callback_data="a:menu"),
    ]])
