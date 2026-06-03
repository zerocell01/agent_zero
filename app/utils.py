"""Helper format Rupiah dan rentang tanggal."""
from __future__ import annotations

import calendar
from datetime import date

BULAN_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def rupiah(amount: float) -> str:
    """Format angka jadi 'Rp1.250.000'. Tampilkan desimal hanya bila perlu.

    Nilai negatif ditampilkan sebagai '-Rp5.000' (tanda minus di depan).
    """
    amount = float(amount)
    sign = "-" if amount < 0 else ""
    nilai = abs(amount)
    if nilai == int(nilai):
        body = f"{int(nilai):,}".replace(",", ".")
    else:
        body = f"{nilai:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"{sign}Rp{body}"


def month_range(year: int, month: int) -> tuple[str, str]:
    """Tanggal awal & akhir (ISO) untuk bulan tertentu."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()


def current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def nama_bulan(month: int) -> str:
    return BULAN_ID[month] if 1 <= month <= 12 else str(month)
