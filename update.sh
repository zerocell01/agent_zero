#!/usr/bin/env bash
#
# Update bot ke versi terbaru: tarik perubahan dari GitHub, perbarui dependency,
# lalu restart proses pm2. Jalankan dari dalam folder repo:
#
#   bash update.sh
#
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Menarik perubahan terbaru (git pull)..."
git pull --ff-only || { echo "Gagal git pull. Selesaikan konflik dulu."; exit 1; }

echo "==> Memperbarui dependency..."
if [ ! -d ".venv" ]; then
  echo "Virtualenv belum ada. Jalankan: bash install.sh"
  exit 1
fi
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -r requirements.txt -q

echo "==> Restart bot..."
if command -v pm2 >/dev/null 2>&1 && pm2 describe hermes-bot >/dev/null 2>&1; then
  pm2 restart hermes-bot
  echo "OK. Lihat log: pm2 logs hermes-bot"
else
  echo "pm2/hermes-bot tidak ditemukan. Jalankan manual: . .venv/bin/activate && python bot.py"
fi
echo "Selesai."
