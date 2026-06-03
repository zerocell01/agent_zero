"""Fitur 3: Edukasi keuangan.

Jawaban edukasi diberikan langsung oleh Hermes (LLM) lewat system prompt.
Modul ini menyediakan daftar topik dan disclaimer agar konsisten.
"""
from __future__ import annotations

TOPIK = [
    "Menyusun anggaran 50/30/20",
    "Membangun dana darurat",
    "Mengelola & melunasi utang",
    "Dasar-dasar menabung vs investasi",
    "Mengenal reksa dana, saham, obligasi",
    "Inflasi dan nilai uang",
    "Tips mengatur arus kas usaha kecil",
    "Memisahkan keuangan pribadi & usaha",
]

DISCLAIMER = (
    "Catatan: ini edukasi umum, bukan nasihat keuangan profesional. "
    "Untuk keputusan besar, pertimbangkan konsultasi dengan penasihat berlisensi."
)


def daftar_topik() -> str:
    lines = ["📚 Topik edukasi keuangan yang bisa kamu tanyakan:", ""]
    lines += [f"  • {t}" for t in TOPIK]
    lines.append("")
    lines.append("Tanyakan apa saja, mis. 'jelaskan aturan 50/30/20'.")
    return "\n".join(lines)
