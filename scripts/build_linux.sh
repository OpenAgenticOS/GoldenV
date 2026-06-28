#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PIP_CONFIG_FILE="${ROOT}/pip.conf"
source .venv/bin/activate 2>/dev/null || true
pip install pyinstaller -q
pyinstaller packaging/goldenv.spec --noconfirm
echo "Linux 演示包: dist/GoldenV/"
