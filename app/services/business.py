"""Fitur 2: Pembukuan usaha kecil (pemasukan/pengeluaran bisnis)."""
from __future__ import annotations

from app import db
from app.utils import current_year_month, month_range, nama_bulan, rupiah

BOOK = "business"


def catat_transaksi_usaha(
    user_id: int,
    type: str,
    amount: float,
    category: str = "lainnya",
    note: str = "",
    tx_date: str | None = None,
) -> str:
    if type not in ("income", "expense"):
        return "Tipe transaksi harus 'income' (pemasukan) atau 'expense' (pengeluaran)."
    tx_id = db.add_transaction(user_id, BOOK, type, amount, category, note, tx_date)
    label = "pemasukan usaha" if type == "income" else "pengeluaran usaha"
    return f"Tercatat {label} {rupiah(amount)} kategori '{category}' (ID #{tx_id})."


def laporan_laba_rugi(
    user_id: int, year: int | None = None, month: int | None = None
) -> str:
    if year is None or month is None:
        year, month = current_year_month()
    start, end = month_range(year, month)

    tot = db.totals(user_id, BOOK, start, end)
    pendapatan, biaya = tot["income"], tot["expense"]
    laba = pendapatan - biaya

    if pendapatan == 0 and biaya == 0:
        return f"Belum ada transaksi usaha pada {nama_bulan(month)} {year}."

    margin = (laba / pendapatan * 100) if pendapatan > 0 else 0
    status = "LABA" if laba >= 0 else "RUGI"

    lines = [f"📈 Laba-Rugi Usaha {nama_bulan(month)} {year}", ""]
    lines.append(f"Pendapatan : {rupiah(pendapatan)}")
    lines.append(f"Biaya      : {rupiah(biaya)}")
    lines.append(f"{status}    : {rupiah(abs(laba))} (margin {margin:.0f}%)")

    rows = db.summary_by_category(user_id, BOOK, start, end)
    biaya_rows = [r for r in rows if r["type"] == "expense"]
    if biaya_rows:
        lines.append("")
        lines.append("Rincian biaya:")
        for r in biaya_rows:
            lines.append(f"  • {r['category']}: {rupiah(r['total'])} ({r['jumlah']}x)")
    return "\n".join(lines)


def daftar_transaksi_usaha(user_id: int, limit: int = 10) -> str:
    rows = db.list_transactions(user_id, BOOK, limit=limit)
    if not rows:
        return "Belum ada transaksi usaha."
    lines = ["🧾 Transaksi usaha terakhir:"]
    for r in rows:
        tanda = "−" if r["type"] == "expense" else "+"
        lines.append(
            f"#{r['id']} {r['tx_date']} {tanda}{rupiah(r['amount'])} "
            f"[{r['category']}] {r['note']}".rstrip()
        )
    return "\n".join(lines)


def hapus_transaksi_usaha(user_id: int, tx_id: int) -> str:
    ok = db.delete_transaction(user_id, tx_id)
    return f"Transaksi #{tx_id} dihapus." if ok else f"Transaksi #{tx_id} tidak ditemukan."
