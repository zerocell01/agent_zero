"""Fitur: Hutang (yang kita pinjam) & Piutang (yang dipinjam orang ke kita)."""
from __future__ import annotations

from app import db
from app.utils import rupiah

OWE = "owe"   # hutang: aku berhutang ke orang
LENT = "lent"  # piutang: orang berhutang ke aku


def catat_hutang(user_id: int, amount: float, party: str = "-", note: str = "") -> str:
    tx_id = db.add_debt(user_id, OWE, amount, party, note)
    return f"Tercatat HUTANG {rupiah(amount)} ke {party} (ID #{tx_id})."


def catat_piutang(user_id: int, amount: float, party: str = "-", note: str = "") -> str:
    tx_id = db.add_debt(user_id, LENT, amount, party, note)
    return f"Tercatat PIUTANG {rupiah(amount)} dari {party} (ID #{tx_id})."


def lunasi(user_id: int, debt_id: int) -> str:
    ok = db.pay_debt(user_id, debt_id)
    return f"Hutang/piutang #{debt_id} ditandai LUNAS." if ok else (
        f"Data #{debt_id} tidak ditemukan atau sudah lunas."
    )


def daftar(user_id: int) -> str:
    rows = db.list_debts(user_id, status="open")
    tot = db.debt_totals(user_id)
    if not rows:
        return "Tidak ada hutang/piutang yang aktif. 🎉"

    lines = ["📒 Hutang & Piutang (aktif)", ""]
    hutang = [r for r in rows if r["kind"] == OWE]
    piutang = [r for r in rows if r["kind"] == LENT]

    if hutang:
        lines.append(f"🔴 HUTANG (total {rupiah(tot['owe'])}):")
        for r in hutang:
            note = f" - {r['note']}" if r["note"] else ""
            lines.append(f"   #{r['id']} {rupiah(r['amount'])} ke {r['party']}{note}")
    if piutang:
        lines.append(f"🟢 PIUTANG (total {rupiah(tot['lent'])}):")
        for r in piutang:
            note = f" - {r['note']}" if r["note"] else ""
            lines.append(f"   #{r['id']} {rupiah(r['amount'])} dari {r['party']}{note}")

    lines.append("")
    lines.append("Untuk melunasi: ketik 'lunasi <ID>', mis. 'lunasi 3'.")
    return "\n".join(lines)
