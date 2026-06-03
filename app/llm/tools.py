"""Definisi tools (function calling) untuk Hermes + dispatcher ke services.

Format `TOOLS` mengikuti spesifikasi OpenAI-compatible tools, sehingga bisa
dipakai baik oleh Ollama (model Hermes) maupun OpenRouter.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from app.services import business, education, personal, debt

# Tipe handler: fn(user_id, **args) -> str
HANDLERS: dict[str, Callable[..., str]] = {
    # --- Pribadi ---
    "catat_pengeluaran": personal.catat_pengeluaran,
    "catat_pemasukan": personal.catat_pemasukan,
    "ringkasan_bulanan": personal.ringkasan_bulanan,
    "atur_budget": personal.atur_budget,
    "status_budget": personal.status_budget,
    "daftar_transaksi": personal.daftar_transaksi,
    "hapus_transaksi": personal.hapus_transaksi,
    # --- Usaha ---
    "catat_transaksi_usaha": business.catat_transaksi_usaha,
    "laporan_laba_rugi": business.laporan_laba_rugi,
    "daftar_transaksi_usaha": business.daftar_transaksi_usaha,
    "hapus_transaksi_usaha": business.hapus_transaksi_usaha,
    # --- Edukasi ---
    "daftar_topik_edukasi": lambda user_id: education.daftar_topik(),
    # --- Hutang/Piutang ---
    "catat_hutang": debt.catat_hutang,
    "catat_piutang": debt.catat_piutang,
    "lunasi_hutang": debt.lunasi,
    "daftar_hutang": lambda user_id: debt.daftar(user_id),
}


def _amount() -> dict:
    return {"type": "number", "description": "Nominal dalam Rupiah (angka, tanpa titik/koma). Contoh 50000."}


def _category(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _date() -> dict:
    return {
        "type": "string",
        "description": "Tanggal transaksi format YYYY-MM-DD. Kosongkan untuk hari ini.",
    }


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


TOOLS: list[dict] = [
    # ---------------- Pribadi ----------------
    _tool(
        "catat_pengeluaran",
        "Catat satu pengeluaran pribadi pengguna.",
        {
            "amount": _amount(),
            "category": _category("Kategori, mis. makan, transport, belanja."),
            "note": {"type": "string", "description": "Catatan opsional."},
            "tx_date": _date(),
        },
        ["amount"],
    ),
    _tool(
        "catat_pemasukan",
        "Catat satu pemasukan pribadi (gaji, bonus, dll).",
        {
            "amount": _amount(),
            "category": _category("Kategori, mis. gaji, bonus, hadiah."),
            "note": {"type": "string", "description": "Catatan opsional."},
            "tx_date": _date(),
        },
        ["amount"],
    ),
    _tool(
        "ringkasan_bulanan",
        "Ringkasan keuangan pribadi (pemasukan, pengeluaran, per kategori) untuk satu bulan.",
        {
            "year": {"type": "integer", "description": "Tahun. Kosongkan = tahun ini."},
            "month": {"type": "integer", "description": "Bulan 1-12. Kosongkan = bulan ini."},
        },
        [],
    ),
    _tool(
        "atur_budget",
        "Setel/ubah batas budget bulanan untuk satu kategori pengeluaran pribadi.",
        {
            "category": _category("Kategori budget, mis. makan, hiburan."),
            "monthly_limit": _amount(),
        },
        ["category", "monthly_limit"],
    ),
    _tool(
        "status_budget",
        "Lihat realisasi pengeluaran vs budget per kategori untuk satu bulan.",
        {
            "year": {"type": "integer", "description": "Tahun. Kosongkan = tahun ini."},
            "month": {"type": "integer", "description": "Bulan 1-12. Kosongkan = bulan ini."},
        },
        [],
    ),
    _tool(
        "daftar_transaksi",
        "Tampilkan daftar transaksi pribadi terakhir.",
        {"limit": {"type": "integer", "description": "Jumlah maksimum, default 10."}},
        [],
    ),
    _tool(
        "hapus_transaksi",
        "Hapus satu transaksi pribadi berdasarkan ID.",
        {"tx_id": {"type": "integer", "description": "ID transaksi (mis. 12)."}},
        ["tx_id"],
    ),
    # ---------------- Usaha ----------------
    _tool(
        "catat_transaksi_usaha",
        "Catat pemasukan atau pengeluaran untuk pembukuan usaha.",
        {
            "type": {
                "type": "string",
                "enum": ["income", "expense"],
                "description": "income = pemasukan/penjualan, expense = biaya/pengeluaran.",
            },
            "amount": _amount(),
            "category": _category("Kategori, mis. penjualan, bahan baku, gaji, sewa."),
            "note": {"type": "string", "description": "Catatan opsional."},
            "tx_date": _date(),
        },
        ["type", "amount"],
    ),
    _tool(
        "laporan_laba_rugi",
        "Laporan laba-rugi usaha (pendapatan, biaya, laba/rugi, margin) untuk satu bulan.",
        {
            "year": {"type": "integer", "description": "Tahun. Kosongkan = tahun ini."},
            "month": {"type": "integer", "description": "Bulan 1-12. Kosongkan = bulan ini."},
        },
        [],
    ),
    _tool(
        "daftar_transaksi_usaha",
        "Tampilkan daftar transaksi usaha terakhir.",
        {"limit": {"type": "integer", "description": "Jumlah maksimum, default 10."}},
        [],
    ),
    _tool(
        "hapus_transaksi_usaha",
        "Hapus satu transaksi usaha berdasarkan ID.",
        {"tx_id": {"type": "integer", "description": "ID transaksi."}},
        ["tx_id"],
    ),
    # ---------------- Edukasi ----------------
    _tool(
        "daftar_topik_edukasi",
        "Tampilkan daftar topik edukasi keuangan yang bisa ditanyakan pengguna.",
        {},
        [],
    ),
    # ---------------- Hutang/Piutang ----------------
    _tool(
        "catat_hutang",
        "Catat hutang baru (uang yang DIPINJAM pengguna dari orang lain).",
        {
            "amount": _amount(),
            "party": {"type": "string", "description": "Kepada siapa berhutang (nama)."},
            "note": {"type": "string", "description": "Catatan opsional."},
        },
        ["amount"],
    ),
    _tool(
        "catat_piutang",
        "Catat piutang baru (uang yang DIPINJAMKAN pengguna ke orang lain).",
        {
            "amount": _amount(),
            "party": {"type": "string", "description": "Siapa yang berhutang ke pengguna (nama)."},
            "note": {"type": "string", "description": "Catatan opsional."},
        },
        ["amount"],
    ),
    _tool(
        "lunasi_hutang",
        "Tandai satu hutang/piutang sebagai lunas berdasarkan ID.",
        {"debt_id": {"type": "integer", "description": "ID hutang/piutang."}},
        ["debt_id"],
    ),
    _tool(
        "daftar_hutang",
        "Tampilkan daftar hutang & piutang yang masih aktif beserta totalnya.",
        {},
        [],
    ),
]


def dispatch(name: str, arguments: str | dict[str, Any], user_id: int) -> str:
    """Jalankan tool sesuai nama dengan argumen dari LLM."""
    handler = HANDLERS.get(name)
    if handler is None:
        return f"(Tool '{name}' tidak dikenal.)"

    if isinstance(arguments, str):
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return f"(Argumen tool '{name}' tidak valid: {arguments!r})"
    else:
        args = dict(arguments or {})

    # Buang argumen kosong agar default pada service yang dipakai.
    args = {k: v for k, v in args.items() if v not in (None, "")}

    try:
        return handler(user_id=user_id, **args)
    except TypeError as exc:
        return f"(Argumen tidak sesuai untuk '{name}': {exc})"
    except Exception as exc:  # noqa: BLE001 - kembalikan error ke LLM agar bisa dijelaskan
        return f"(Terjadi kesalahan saat menjalankan '{name}': {exc})"
