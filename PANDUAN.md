# Panduan Pemula — Bot Hermes Finance (LLM Gratis)

Panduan ini **tanpa perlu ngoding**. Kamu cukup ikuti langkah & salin-tempel
perintah. Targetnya: bot Telegram asisten keuangan jalan di **VPS** kamu
(6 core / 12GB) memakai **LLM gratis**.

> 💡 **Syarat utama cuma satu: LLM-nya gratis.** Tidak wajib Hermes, tidak wajib
> 9Router. Karena kamu **sudah menjalankan 9Router** di VPS (untuk bot lain
> dengan Claude Sonnet), cara termudah & paling stabil adalah **pakai ulang
> 9Router itu** dengan model gratis. Lihat "Jalur Cepat" di bawah.

> ⚠️ **Penting:** bot ini banyak memakai *function calling* (untuk mencatat
> transaksi & budget). Model yang kuat di tool-use seperti **Claude Sonnet**
> (gratis via provider **Kiro** di 9Router) jauh lebih andal daripada Hermes 8B
> gratis. Disarankan pakai Claude Sonnet gratis; Hermes gratis tetap bisa untuk
> tanya-jawab edukasi.

---

## ⚡ Jalur Cepat (kamu sudah punya 9Router)

Karena 9Router sudah jalan di VPS, kamu bisa lewati instalasi 9Router:

1. Buat bot Telegram → ambil token (**Langkah 1**).
2. Di dashboard 9Router, pastikan ada model gratis (mis. **Kiro** →
   `kr/claude-sonnet-4.5`) dan **salin API key**-nya (**Langkah 5**).
3. Pasang bot ini & isi `.env` (**Langkah 6–7**).
4. Jalankan permanen dengan pm2 (**Langkah 9**).

Selesai. Detail tiap langkah ada di bawah.

---

## Gambaran alurnya

```
Kamu di Telegram
      │
      ▼
  Bot (Python)  ──►  9Router (port 20128)  ──►  Model GRATIS
      │                                         (Kiro Claude Sonnet / Hermes free)
      ▼
  Database SQLite (catatan keuangan)
```

---

## 0. Yang perlu disiapkan

- [ ] Akun **Telegram**
- [ ] **VPS** (akses SSH) — sudah kamu punya
- [ ] **9Router** — sudah jalan di VPS kamu
- [ ] Aplikasi terminal di laptop (Mac/Linux: Terminal; Windows: PowerShell)
- [ ] *(opsional)* Akun **OpenRouter** gratis — hanya jika mau pakai Hermes gratis

---

## 1. Buat bot Telegram & ambil TOKEN

1. Buka Telegram, cari **@BotFather**.
2. Kirim `/newbot`.
3. Beri **nama** dan **username** bot (harus diakhiri `bot`, mis. `keuanganku_bot`).
4. Simpan **token** yang diberikan, contoh:
   `123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 2. Masuk ke VPS (SSH)

Di terminal laptop (ganti `user` dan `IP_VPS`):

```bash
ssh user@IP_VPS
```

Perintah berikutnya dijalankan **di dalam VPS**, kecuali yang ditandai "di laptop".

---

## 3. Pastikan Python ada di VPS

(Node.js & 9Router sudah ada karena bot lamamu sudah pakai.) Bot ini butuh
**Python 3.10+**:

```bash
python3 --version
# kalau belum ada:
sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git
```

---

## 4. (Lewati) Pasang 9Router

9Router sudah jalan di VPS-mu, jadi **langkah ini dilewati**.

> Kalau suatu saat perlu pasang dari nol: `npm install -g 9router` lalu `9router`
> (dashboard di `http://localhost:20128`, password awal `123456`).

---

## 5. Ambil model GRATIS & API key dari dashboard 9Router

Dashboard ada di VPS (`localhost:20128`). Buka dari laptop lewat terowongan SSH.

**5a. Di laptop**, terminal BARU (biarkan terbuka):
```bash
ssh -L 20128:localhost:20128 user@IP_VPS
```

**5b. Di laptop**, buka browser ke `http://localhost:20128` dan login.

**5c. Pilih salah satu sumber model GRATIS:**

- **Disarankan — Kiro (Claude Sonnet gratis, andal untuk catat transaksi):**
  Menu **Providers** → **Connect Kiro** (login AWS Builder ID / Google / GitHub).
  Nama model: `kr/claude-sonnet-4.5`.

- **Alternatif — Hermes gratis:**
  Menu **Providers** → **OpenRouter** → masukkan API key OpenRouter (gratis dari
  https://openrouter.ai/keys). Nama model contoh:
  `or/nousresearch/deephermes-3-llama-3-8b-preview:free`.

**5d. Salin API key 9Router** (menu **API Keys**/**Endpoint**) → untuk `LLM_API_KEY`.

**5e. Pastikan nama model** dengan membuka `http://localhost:20128/v1/models`
dan catat persis nama yang ingin dipakai → untuk `LLM_MODEL`.

---

## 6. Pasang bot Hermes Finance di VPS

```bash
git clone <URL_REPO_INI> hermes-finance-bot
cd hermes-finance-bot

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

---

## 7. Isi konfigurasi (.env)

```bash
cp .env.example .env
nano .env
```

Isi 3 baris ini:

```
TELEGRAM_BOT_TOKEN=token_dari_langkah_1
LLM_API_KEY=api_key_9router_dari_langkah_5d
LLM_MODEL=kr/claude-sonnet-4.5      # atau model gratis pilihanmu dari langkah 5e
```

Biarkan `LLM_BASE_URL=http://localhost:20128/v1`.
Simpan di nano: `Ctrl + O`, `Enter`, lalu `Ctrl + X`.

---

## 8. Tes jalan

```bash
. .venv/bin/activate
python bot.py
```

Buka botmu di Telegram, ketik `/start`, lalu coba:
- `catat jajan 25rb`
- `ringkasan bulan ini`
- `jelaskan aturan 50/30/20`

Kalau lancar, hentikan dengan `Ctrl + C` dan lanjut ke langkah 9.

---

## 9. Jalankan permanen (auto nyala 24 jam)

Kamu mungkin sudah pakai **pm2** untuk bot lama. Tambahkan bot ini:

```bash
cd ~/hermes-finance-bot
pm2 start bot.py --name hermes-bot --interpreter ./.venv/bin/python
pm2 save
```

Perintah berguna:
```bash
pm2 list                 # status semua proses (bot lama + bot ini + 9router)
pm2 logs hermes-bot      # lihat log bot keuangan
pm2 restart hermes-bot   # restart setelah ubah .env
```

🎉 Selesai! Bot keuangan online 24 jam, berdampingan dengan bot lamamu.

---

## 10. Cara pakai botnya

| Ketik di Telegram | Hasil |
|-------------------|-------|
| `catat jajan 25rb tadi siang` | catat pengeluaran pribadi |
| `gaji masuk 7jt` | catat pemasukan pribadi |
| `set budget makan 1,5jt per bulan` | atur budget |
| `ringkasan bulan ini` | ringkasan keuangan pribadi |
| `status budget` | realisasi vs budget |
| `penjualan usaha 500rb hari ini` | catat pemasukan usaha |
| `laporan laba rugi bulan ini` | laporan laba-rugi usaha |
| `jelaskan dana darurat` | edukasi keuangan |

Perintah: `/start` atau `/help`, `/reset` (hapus konteks obrolan).

---

## 11. Troubleshooting

**Bot balas "ada kendala menghubungi mesin AI"**
- Pastikan 9Router `online`: `pm2 list`.
- Cek `LLM_API_KEY` & `LLM_MODEL` di `.env` sama persis dgn dashboard.
- Lihat log: `pm2 logs hermes-bot`.

**Bisa jawab edukasi, tapi GAGAL mencatat transaksi**
- Penyebab umum: model kurang andal untuk *function calling*.
- Solusi: pakai model yang kuat di tool-use, mis. `kr/claude-sonnet-4.5` (gratis
  via Kiro). Ubah `LLM_MODEL`, lalu `pm2 restart hermes-bot`.

**Bot ini bentrok dengan bot lama?**
- Tidak. Keduanya proses pm2 terpisah dan pakai database masing-masing.
  9Router bisa melayani banyak bot/model sekaligus.

**Model gratis kena limit**
- Tier gratis ada batas harian. Ganti ke sumber gratis lain di dashboard, atau
  tunggu reset.

---

### Catatan
- `.env` dan `*.db` berisi rahasia/datamu — jangan dibagikan.
- Edukasi keuangan di bot bersifat informasi umum, bukan nasihat profesional.
