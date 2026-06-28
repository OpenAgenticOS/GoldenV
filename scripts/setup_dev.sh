#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PIP_CONFIG_FILE="${ROOT}/pip.conf"

if ! command -v python3.11 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python3.11
fi

if [ "${EUID:-$(id -u)}" -eq 0 ] || [ "${SKIP_APT:-0}" = "1" ]; then
  :
else
  echo "如需安装系统依赖: sudo apt install -y python3.11-venv python3-pip libgl1 fonts-noto-cjk"
fi

# 大华 SDK：从本机安装目录复制到 vendor/（若已安装 MV Viewer）
if [ -f "${ROOT}/scripts/fetch_dahua_sdk.sh" ]; then
  bash "${ROOT}/scripts/fetch_dahua_sdk.sh" || true
fi

$PYTHON -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
echo "开发环境就绪。"
echo "  模拟运行: python -m goldenv.app --simulate"
echo "  大华 SDK: 安装 MV Viewer 后重新运行本脚本，或设置 DAHUA_SDK_PATH"
