"""Fitur 1: Pencatat & budgeting pribadi.

Semua fungsi mengembalikan teks ringkas (bahasa Indonesia) yang akan
disampaikan kembali ke pengguna oleh Hermes.
"""
from __future__ import annotations

from app import db
from app.utils import current_year_month, month_range, nama_bulan, rupiah

BOOK = "personal"


def catat_pengeluaran(
    user_id: int,
    amount: float,
    category: str = "lainnya",
    note: str = "",
    tx_date: str | None = None,
) -> str:
    tx_id = db.add_transaction(user_id, BOOK, "expense", amount, category, note, tx_date)
    pesan = f"Tercatat pengeluaran {rupiah(amount)} kategori '{category}' (ID #{tx_id})."
    return pesan + _peringatan_budget(user_id, category)


def catat_pemasukan(
    user_id: int,
    amount: float,
    category: str = "lainnya",
    note: str = "",
    tx_date: str | None = None,
) -> str:
    tx_id = db.add_transaction(user_id, BOOK, "income", amount, category, note, tx_date)
    return f"Tercatat pemasukan {rupiah(amount)} kategori '{category}' (ID #{tx_id})."


def ringkasan_bulanan(
    user_id: int, year: int | None = None, month: int | None = None
) -> str:
    if year is None or month is None:
        year, month = current_year_month()
    start, end = month_range(year, month)

    tot = db.totals(user_id, BOOK, start, end)
    pemasukan, pengeluaran = tot["income"], tot["expense"]
    saldo = pemasukan - pengeluaran

    lines = [f"📊 Ringkasan Pribadi {nama_bulan(month)} {year}", ""]
    lines.append(f"Pemasukan : {rupiah(pemasukan)}")
    lines.append(f"Pengeluaran: {rupiah(pengeluaran)}")
    lines.append(f"Selisih   : {rupiah(saldo)}")

    rows = db.summary_by_category(user_id, BOOK, start, end)
    pengeluaran_rows = [r for r in rows if r["type"] == "expense"]
    if pengeluaran_rows:
        lines.append("")
        lines.append("Pengeluaran per kategori:")
        for r in pengeluaran_rows:
            lines.append(f"  • {r['category']}: {rupiah(r['total'])} ({r['jumlah']}x)")

    if pemasukan == 0 and pengeluaran == 0:
        return f"Belum ada transaksi pribadi pada {nama_bulan(month)} {year}."
    return "\n".join(lines)


def atur_budget(user_id: int, category: str, monthly_limit: float) -> str:
    db.set_budget(user_id, category, monthly_limit)
    return f"Budget bulanan kategori '{category}' disetel ke {rupiah(monthly_limit)}."


def status_budget(
    user_id: int, year: int | None = None, month: int | None = None
) -> str:
    if year is None or month is None:
        year, month = current_year_month()
    start, end = month_range(year, month)

    budgets = db.get_budgets(user_id)
    if not budgets:
        return (
            "Belum ada budget yang disetel. Contoh: 'set budget makan 1,5 juta per bulan'."
        )

    spent = db.spent_by_category(user_id, start, end)
    lines = [f"🎯 Status Budget {nama_bulan(month)} {year}", ""]
    for b in budgets:
        cat = b["category"]
        limit = float(b["monthly_limit"])
        used = spent.get(cat, 0.0)
        sisa = limit - used
        persen = (used / limit * 100) if limit > 0 else 0
        ikon = "🟢" if persen < 80 else ("🟡" if persen <= 100 else "🔴")
        lines.append(
            f"{ikon} {cat}: {rupiah(used)} / {rupiah(limit)} "
            f"({persen:.0f}%) — sisa {rupiah(sisa)}"
        )
    return "\n".join(lines)


def daftar_transaksi(user_id: int, limit: int = 10) -> str:
    rows = db.list_transactions(user_id, BOOK, limit=limit)
    if not rows:
        return "Belum ada transaksi pribadi."
    lines = ["🧾 Transaksi pribadi terakhir:"]
    for r in rows:
        tanda = "−" if r["type"] == "expense" else "+"
        lines.append(
            f"#{r['id']} {r['tx_date']} {tanda}{rupiah(r['amount'])} "
            f"[{r['category']}] {r['note']}".rstrip()
        )
    return "\n".join(lines)


def hapus_transaksi(user_id: int, tx_id: int) -> str:
    ok = db.delete_transaction(user_id, tx_id)
    return f"Transaksi #{tx_id} dihapus." if ok else f"Transaksi #{tx_id} tidak ditemukan."


def _peringatan_budget(user_id: int, category: str) -> str:
    """Tambahkan peringatan bila budget kategori terlampaui bulan ini."""
    budgets = {b["category"]: float(b["monthly_limit"]) for b in db.get_budgets(user_id)}
    limit = budgets.get(category.lower())
    if not limit:
        return ""
    year, month = current_year_month()
    start, end = month_range(year, month)
    used = db.spent_by_category(user_id, start, end).get(category.lower(), 0.0)
    persen = (used / limit * 100) if limit > 0 else 0
    if persen > 100:
        return f"\n⚠️ Budget '{category}' sudah terlampaui ({persen:.0f}% dari {rupiah(limit)})!"
    if persen >= 80:
        return f"\n🟡 Budget '{category}' sudah {persen:.0f}% terpakai ({rupiah(used)}/{rupiah(limit)})."
    return ""
