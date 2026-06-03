# Hermes Finance Bot 🤖💸

Bot Telegram asisten keuangan berbasis **Hermes** (LLM). Tiga fitur utama:

1. 💰 **Budgeting pribadi** — catat pengeluaran/pemasukan, atur budget per kategori, ringkasan bulanan, peringatan budget otomatis.
2. 🧾 **Pembukuan usaha** — catat transaksi bisnis, laporan laba-rugi bulanan.
3. 💬 **Edukasi keuangan** — tanya-jawab konsep keuangan dalam bahasa sederhana.

Hermes memahami bahasa natural (mis. _"catat jajan 25rb"_) dan memanggil
fungsi keuangan (function calling) untuk menyimpan/menghitung data — jadi angka
selalu akurat, bukan dikarang oleh model.

## Arsitektur

```
Telegram  ──►  bot.py  ──►  Hermes (LLM)  ──► tools (function calling)
                                   │                 │
                                   ▼                 ▼
                          jawaban natural      services ──► SQLite
```

- `bot.py` — entry point bot (long-polling).
- `app/llm/` — klien Hermes + definisi tools + dispatcher.
- `app/services/` — logika keuangan (personal, business, education).
- `app/db.py` — penyimpanan SQLite.
- `config.py` — konfigurasi dari `.env`.

## Prasyarat

- Python 3.10+
- Token bot Telegram dari [@BotFather](https://t.me/BotFather)
- Backend Hermes, pilih salah satu:
  - **Ollama** di VPS (gratis): `ollama pull hermes3` — butuh RAM cukup besar.
  - **API OpenAI-compatible** seperti OpenRouter (mis. model `nousresearch/hermes-3-llama-3.1-70b`).

## Setup

```bash
git clone <repo-ini> hermes-finance-bot
cd hermes-finance-bot

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: isi TELEGRAM_BOT_TOKEN dan konfigurasi LLM (Ollama / OpenRouter)
```

Jalankan:

```bash
python bot.py
```

Buka bot kamu di Telegram, ketik `/start`.

## Contoh perintah di chat

| Ketik | Hasil |
|-------|-------|
| `catat jajan 25rb tadi siang` | mencatat pengeluaran pribadi |
| `gaji masuk 7jt` | mencatat pemasukan pribadi |
| `set budget makan 1,5jt per bulan` | mengatur budget |
| `ringkasan bulan ini` | ringkasan keuangan pribadi |
| `status budget` | realisasi vs budget |
| `penjualan usaha 500rb hari ini` | mencatat pemasukan usaha |
| `bayar bahan baku 200rb` (konteks usaha) | mencatat biaya usaha |
| `laporan laba rugi bulan ini` | laporan laba-rugi usaha |
| `jelaskan aturan 50/30/20` | edukasi keuangan |

Perintah bot: `/start` atau `/help` (panduan), `/reset` (hapus konteks percakapan).

## Deploy di VPS (systemd)

Agar bot tetap berjalan dan auto-restart, gunakan service systemd
(`deploy/hermes-bot.service`). Sesuaikan path & user, lalu:

```bash
sudo cp deploy/hermes-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-bot
sudo systemctl status hermes-bot
journalctl -u hermes-bot -f          # lihat log
```

### Menjalankan Hermes via Ollama di VPS

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull hermes3:8b
# pastikan LLM_BASE_URL=http://localhost:11434/v1 dan LLM_MODEL=hermes3:8b di .env
```

> **VPS 6 core / 12GB RAM (tanpa GPU)**: pakai model **8B** (`hermes3:8b`,
> kuantisasi Q4 ~5-6GB RAM). Inferensi CPU-only: balasan muncul beberapa detik —
> wajar untuk pemakaian chat. Model 70B/405B **tidak muat** di RAM 12GB; kalau
> butuh kualitas lebih tinggi/instan, pakai opsi API (OpenRouter) di `.env`.

## Keamanan

- `.env` dan file `*.db` sudah masuk `.gitignore` — jangan commit token/datamu.
- Set `ALLOWED_USER_IDS` di `.env` untuk membatasi siapa yang boleh memakai bot
  (isi dengan ID Telegram, pisahkan koma). Kosong = semua orang boleh.

## Catatan teknis

- Nominal disimpan sebagai angka; format Rupiah ditangani saat ditampilkan.
- Data per pengguna dipisah berdasarkan ID Telegram.
- Edukasi keuangan bersifat informasi umum, bukan nasihat keuangan profesional.
