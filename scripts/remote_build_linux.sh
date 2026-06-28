#!/usr/bin/env bash
# 在 Ubuntu 远程机上执行：PyInstaller 打 Linux onedir 包（非 .exe）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== GoldenV Linux 远程打包 ==="

if ! command -v python3 >/dev/null; then
  echo "未找到 python3" >&2
  exit 1
fi

export PIP_CONFIG_FILE="${PIP_CONFIG_FILE:-$ROOT/pip.conf}"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt pyinstaller

rm -rf dist/GoldenV build
pyinstaller packaging/goldenv.spec --noconfirm --distpath dist --workpath build

python -m goldenv.app --headless-test --simulate

cd dist
rm -f GoldenV-linux.tar.gz
tar -czf GoldenV-linux.tar.gz GoldenV
echo "已生成 dist/GoldenV-linux.tar.gz"
