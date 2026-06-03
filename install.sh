#!/usr/bin/env bash
#
# Installer Bot Hermes Finance untuk VPS.
# Jalankan dari dalam folder repo (yang sudah di-clone):
#
#   bash install.sh
#
# Skrip ini akan:
#   1) Cek & pasang prasyarat (python3, venv, pip)
#   2) Membuat virtualenv + install dependency
#   3) Wizard mengisi file .env (tinggal jawab pertanyaan)
#   4) Menjalankan bot dengan pm2 (otomatis nyala 24 jam + restart)
#
set -uo pipefail

# ---------- tampilan ----------
if [ -t 1 ]; then
  C_RESET="\033[0m"; C_B="\033[1m"; C_G="\033[32m"; C_Y="\033[33m"; C_R="\033[31m"; C_C="\033[36m"
else
  C_RESET=""; C_B=""; C_G=""; C_Y=""; C_R=""; C_C=""
fi
info()  { printf "${C_C}==>${C_RESET} %s\n" "$*"; }
ok()    { printf "${C_G}OK :${C_RESET} %s\n" "$*"; }
warn()  { printf "${C_Y}!! :${C_RESET} %s\n" "$*"; }
err()   { printf "${C_R}ERR:${C_RESET} %s\n" "$*" >&2; }
title() { printf "\n${C_B}== %s ==${C_RESET}\n" "$*"; }

# ---------- pindah ke folder skrip ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "bot.py" ]; then
  err "File bot.py tidak ditemukan. Jalankan skrip ini DI DALAM folder repo (mis. ~/agent_zero)."
  exit 1
fi

title "Bot Hermes Finance - Installer"
info "Folder: $SCRIPT_DIR"

# ---------- sudo ----------
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ---------- deteksi package manager ----------
PKG=""
if command -v apt-get >/dev/null 2>&1; then PKG="apt"; fi
if command -v dnf     >/dev/null 2>&1; then PKG="dnf"; fi
if command -v yum     >/dev/null 2>&1; then PKG="yum"; fi

pkg_install() {
  case "$PKG" in
    apt) $SUDO apt-get update -y && $SUDO apt-get install -y "$@" ;;
    dnf) $SUDO dnf install -y "$@" ;;
    yum) $SUDO yum install -y "$@" ;;
    *)   warn "Package manager tidak dikenal. Pasang manual: $*" ; return 1 ;;
  esac
}

# ---------- 1. Prasyarat Python ----------
title "1/4 Cek prasyarat Python"
PY=""
for c in python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  warn "Python3 belum ada, mencoba memasang..."
  pkg_install python3 python3-venv python3-pip || { err "Gagal pasang Python."; exit 1; }
  PY="python3"
fi

PYVER="$($PY -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
info "Python terdeteksi: $PY ($PYVER)"
$PY -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,9) else 1)' || {
  err "Butuh Python 3.9+ (disarankan 3.10+). Versi sekarang: $PYVER"; exit 1; }

# pastikan venv + ensurepip tersedia.
# Di Debian/Ubuntu butuh paket python3.X-venv (mis. python3.12-venv) yang berisi ensurepip.
if ! $PY -c 'import ensurepip, venv' >/dev/null 2>&1; then
  warn "Paket venv/ensurepip belum lengkap, mencoba memasang python${PYVER}-venv..."
  pkg_install "python${PYVER}-venv" || pkg_install python3-venv || warn "Tidak bisa pasang otomatis; akan dicoba lagi saat membuat venv."
fi
# pastikan git ada (untuk update nanti)
command -v git >/dev/null 2>&1 || pkg_install git || true
ok "Prasyarat Python siap."

# ---------- 2. Virtualenv + dependency ----------
title "2/4 Virtualenv & dependency"
# bersihkan venv parsial (mis. sisa percobaan gagal sebelumnya)
if [ -d ".venv" ] && [ ! -x ".venv/bin/python" ]; then
  warn "Menemukan .venv tidak lengkap, menghapusnya..."
  rm -rf .venv
fi
if [ ! -d ".venv" ]; then
  info "Membuat virtualenv (.venv)..."
  if ! $PY -m venv .venv; then
    warn "Gagal membuat venv. Memasang python${PYVER}-venv lalu mencoba lagi..."
    pkg_install "python${PYVER}-venv" || pkg_install python3-venv || true
    rm -rf .venv
    $PY -m venv .venv || {
      err "Tetap gagal membuat virtualenv. Jalankan manual: $SUDO apt-get install -y python${PYVER}-venv"
      exit 1
    }
  fi
fi
# shellcheck disable=SC1091
. .venv/bin/activate
info "Memasang dependency (pip install)..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q || { err "Gagal install requirements."; exit 1; }
ok "Dependency terpasang."

# ---------- 3. Wizard .env ----------
title "3/4 Konfigurasi (.env)"

# ambil nilai lama bila .env sudah ada
get_old() { [ -f .env ] && grep -E "^$1=" .env | head -n1 | cut -d= -f2- || true; }

if [ -f .env ]; then
  warn "File .env sudah ada. Tekan Enter untuk mempertahankan nilai lama di tiap pertanyaan."
fi

DEF_TOKEN="$(get_old TELEGRAM_BOT_TOKEN)"
DEF_BASE="$(get_old LLM_BASE_URL)";   DEF_BASE="${DEF_BASE:-http://localhost:20128/v1}"
DEF_KEY="$(get_old LLM_API_KEY)"
DEF_MODEL="$(get_old LLM_MODEL)";     DEF_MODEL="${DEF_MODEL:-kr/claude-sonnet-4.5}"
DEF_TZ="$(get_old TIMEZONE)";         DEF_TZ="${DEF_TZ:-Asia/Jakarta}"
DEF_DB="$(get_old DB_PATH)";          DEF_DB="${DEF_DB:-finance.db}"
DEF_IDS="$(get_old ALLOWED_USER_IDS)"

ask() { # ask <prompt> <default> -> echo hasil ke stdout
  local prompt="$1" def="$2" ans=""
  if [ -n "$def" ]; then
    printf "%s [%s]: " "$prompt" "$def" >&2
  else
    printf "%s: " "$prompt" >&2
  fi
  read -r ans
  echo "${ans:-$def}"
}

echo
info "Token Telegram dari @BotFather (wajib)."
TOKEN="$(ask 'TELEGRAM_BOT_TOKEN' "$DEF_TOKEN")"
while [ -z "$TOKEN" ]; do warn "Tidak boleh kosong."; TOKEN="$(ask 'TELEGRAM_BOT_TOKEN' "$DEF_TOKEN")"; done

echo
info "Backend LLM. Default = pakai 9Router yang sudah jalan di VPS (port 20128)."
BASE="$(ask 'LLM_BASE_URL' "$DEF_BASE")"
info "API key dari dashboard 9Router (http://localhost:20128). Wajib bila pakai 9Router."
KEY="$(ask 'LLM_API_KEY' "$DEF_KEY")"
info "Nama model GRATIS (andal utk catat transaksi): kr/claude-sonnet-4.5"
MODEL="$(ask 'LLM_MODEL' "$DEF_MODEL")"

echo
TZ_="$(ask 'TIMEZONE' "$DEF_TZ")"
DB_="$(ask 'DB_PATH' "$DEF_DB")"
info "Batasi akses ke ID Telegram tertentu (pisah koma). Kosongkan = semua boleh."
IDS="$(ask 'ALLOWED_USER_IDS' "$DEF_IDS")"

# tulis .env
{
  echo "TELEGRAM_BOT_TOKEN=$TOKEN"
  echo "LLM_BASE_URL=$BASE"
  echo "LLM_API_KEY=$KEY"
  echo "LLM_MODEL=$MODEL"
  echo "DB_PATH=$DB_"
  echo "TIMEZONE=$TZ_"
  echo "ALLOWED_USER_IDS=$IDS"
} > .env
chmod 600 .env
ok "File .env tersimpan (permission 600)."

# ---------- 4. Jalankan dengan pm2 ----------
title "4/4 Menjalankan bot"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"

# uji impor cepat agar error konfigurasi ketahuan lebih awal
if ! "$VENV_PY" -c "import config, app.db, app.llm.client" >/dev/null 2>&1; then
  warn "Uji impor modul gagal — cek lagi dependency. Bot mungkin tetap bisa dijalankan manual."
fi

USE_PM2="y"
printf "Jalankan otomatis 24 jam dengan pm2? [Y/n]: " >&2; read -r USE_PM2
USE_PM2="${USE_PM2:-y}"

if printf '%s' "$USE_PM2" | grep -qiE '^y'; then
  if ! command -v node >/dev/null 2>&1; then
    warn "Node.js belum ada (biasanya sudah ada karena 9Router). Memasang..."
    if [ "$PKG" = "apt" ]; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash - && $SUDO apt-get install -y nodejs
    else
      pkg_install nodejs || true
    fi
  fi
  if ! command -v pm2 >/dev/null 2>&1; then
    info "Memasang pm2..."
    $SUDO npm install -g pm2 || { err "Gagal pasang pm2."; USE_PM2="n"; }
  fi
fi

if printf '%s' "$USE_PM2" | grep -qiE '^y' && command -v pm2 >/dev/null 2>&1; then
  info "Mendaftarkan proses 'hermes-bot' di pm2..."
  pm2 delete hermes-bot >/dev/null 2>&1 || true
  pm2 start "$SCRIPT_DIR/bot.py" --name hermes-bot --interpreter "$VENV_PY" --cwd "$SCRIPT_DIR"
  pm2 save
  echo
  ok "Bot berjalan! Beberapa detik lagi cek di Telegram dengan /start."
  echo
  info "Agar tetap nyala setelah VPS reboot, jalankan perintah yang ditampilkan oleh:"
  printf "    ${C_B}pm2 startup${C_RESET}\n"
  echo
  info "Perintah berguna:"
  echo "    pm2 logs hermes-bot     # lihat log"
  echo "    pm2 restart hermes-bot  # restart setelah ubah .env"
  echo "    pm2 list                # status semua proses"
else
  echo
  ok "Setup selesai. Untuk menjalankan manual:"
  echo "    . .venv/bin/activate && python bot.py"
fi

title "Selesai 🎉"
