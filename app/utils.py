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



import re

_SUFFIX = {
    "rb": 1_000, "ribu": 1_000, "k": 1_000, "ratus ribu": 100_000,
    "jt": 1_000_000, "juta": 1_000_000, "jeti": 1_000_000, "m": 1_000_000,
    "miliar": 1_000_000_000, "milyar": 1_000_000_000, "b": 1_000_000_000,
}
# urutkan suffix terpanjang dulu agar 'ratus ribu' cocok sebelum 'ribu'
_SUFFIX_PATTERN = "|".join(sorted(_SUFFIX, key=len, reverse=True))
_AMOUNT_RE = re.compile(
    rf"(\d+(?:[.,]\d+)*)\s*({_SUFFIX_PATTERN})?(?![A-Za-z])", re.IGNORECASE
)


def parse_amount(text: str) -> float | None:
    """Ubah teks nominal Indonesia jadi angka.

    Contoh: '50rb'->50000, '1,5jt'->1500000, '2 juta'->2000000,
    'Rp50.000'->50000, '50000'->50000.
    """
    if not text:
        return None
    m = _AMOUNT_RE.search(text.replace("Rp", " ").replace("rp", " "))
    if not m:
        return None
    num_raw, suffix = m.group(1), (m.group(2) or "").lower()
    if suffix:
        # dengan suffix: titik/koma = pemisah desimal (mis. 1,5jt)
        num = float(num_raw.replace(".", "").replace(",", "."))
        return num * _SUFFIX[suffix]
    # tanpa suffix: titik/koma = pemisah ribuan (mis. 50.000)
    return float(num_raw.replace(".", "").replace(",", ""))


def parse_entry(text: str) -> tuple[float | None, str, str]:
    """Pisah teks '<jumlah> <kategori> <catatan>' jadi (amount, category, note).

    Contoh: '50rb makan nasi padang' -> (50000, 'makan', 'nasi padang').
    """
    text = (text or "").strip()
    m = _AMOUNT_RE.search(text.replace("Rp", " ").replace("rp", " "))
    amount = parse_amount(text)
    if amount is None or not m:
        return None, "lainnya", text
    sisa = (text[: m.start()] + " " + text[m.end():]).strip()
    parts = sisa.split()
    if not parts:
        return amount, "lainnya", ""
    category = parts[0]
    note = " ".join(parts[1:])
    return amount, category, note
