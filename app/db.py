"""Layer database SQLite untuk transaksi keuangan & budget.

Skema:
- transactions : catatan pemasukan/pengeluaran. Kolom `book` membedakan
                 'personal' (pribadi) vs 'business' (usaha).
- budgets      : batas pengeluaran bulanan per kategori (khusus pribadi).

Catatan: setiap operasi membuka koneksi baru agar aman dipakai dari beberapa
thread (handler bot berjalan async + panggilan LLM dijalankan di executor).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Iterator

from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    book      TEXT    NOT NULL CHECK (book IN ('personal', 'business')),
    type      TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    amount    REAL    NOT NULL CHECK (amount >= 0),
    category  TEXT    NOT NULL DEFAULT 'lainnya',
    note      TEXT    DEFAULT '',
    tx_date   TEXT    NOT NULL,           -- format YYYY-MM-DD
    created_at TEXT   NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tx_user_book_date
    ON transactions (user_id, book, tx_date);

CREATE TABLE IF NOT EXISTS budgets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    category      TEXT    NOT NULL,
    monthly_limit REAL    NOT NULL CHECK (monthly_limit >= 0),
    UNIQUE (user_id, category)
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ----------------------------------------------------------------------------
# Transaksi
# ----------------------------------------------------------------------------
def add_transaction(
    user_id: int,
    book: str,
    type: str,
    amount: float,
    category: str = "lainnya",
    note: str = "",
    tx_date: str | None = None,
) -> int:
    tx_date = tx_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO transactions (user_id, book, type, amount, category, note, tx_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, book, type, float(amount), category.lower(), note, tx_date),
        )
        return int(cur.lastrowid)


def list_transactions(
    user_id: int,
    book: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM transactions WHERE user_id = ? AND book = ?"
    params: list = [user_id, book]
    if start:
        query += " AND tx_date >= ?"
        params.append(start)
    if end:
        query += " AND tx_date <= ?"
        params.append(end)
    query += " ORDER BY tx_date DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def delete_transaction(user_id: int, tx_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
        )
        return cur.rowcount > 0


def summary_by_category(
    user_id: int, book: str, start: str, end: str
) -> list[sqlite3.Row]:
    """Total per (type, category) dalam rentang tanggal [start, end]."""
    with get_conn() as conn:
        return conn.execute(
            """SELECT type, category, SUM(amount) AS total, COUNT(*) AS jumlah
               FROM transactions
               WHERE user_id = ? AND book = ? AND tx_date BETWEEN ? AND ?
               GROUP BY type, category
               ORDER BY total DESC""",
            (user_id, book, start, end),
        ).fetchall()


def totals(user_id: int, book: str, start: str, end: str) -> dict[str, float]:
    """Total pemasukan & pengeluaran dalam rentang tanggal."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT type, SUM(amount) AS total
               FROM transactions
               WHERE user_id = ? AND book = ? AND tx_date BETWEEN ? AND ?
               GROUP BY type""",
            (user_id, book, start, end),
        ).fetchall()
    result = {"income": 0.0, "expense": 0.0}
    for r in rows:
        result[r["type"]] = float(r["total"] or 0.0)
    return result


# ----------------------------------------------------------------------------
# Budget
# ----------------------------------------------------------------------------
def set_budget(user_id: int, category: str, monthly_limit: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO budgets (user_id, category, monthly_limit)
               VALUES (?, ?, ?)
               ON CONFLICT (user_id, category)
               DO UPDATE SET monthly_limit = excluded.monthly_limit""",
            (user_id, category.lower(), float(monthly_limit)),
        )


def get_budgets(user_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id = ? ORDER BY category",
            (user_id,),
        ).fetchall()


def spent_by_category(user_id: int, start: str, end: str) -> dict[str, float]:
    """Total pengeluaran pribadi per kategori dalam rentang tanggal."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT category, SUM(amount) AS total
               FROM transactions
               WHERE user_id = ? AND book = 'personal' AND type = 'expense'
                     AND tx_date BETWEEN ? AND ?
               GROUP BY category""",
            (user_id, start, end),
        ).fetchall()
    return {r["category"]: float(r["total"] or 0.0) for r in rows}
