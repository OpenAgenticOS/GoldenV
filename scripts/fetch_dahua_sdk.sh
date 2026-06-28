#!/usr/bin/env bash
# 从本机已安装的大华 MV Viewer / 工业相机 SDK 复制运行时到 vendor/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STRICT="${STRICT:-0}"

find_sdk_root() {
  if [[ -n "${DAHUA_SDK_PATH:-}" && -d "$DAHUA_SDK_PATH" ]]; then
    echo "$DAHUA_SDK_PATH"
    return 0
  fi
  for base in \
    /opt/HuarayTech/MVviewer \
    /opt/HuarayTech/MVViewer \
    /opt/MVS \
    /usr/local/dahua-mvviewer; do
    if [[ -d "$base" ]]; then
      echo "$base"
      return 0
    fi
  done
  return 1
}

DEST="$ROOT/vendor/dahua/linux64"
PY_DEST="$ROOT/vendor/DahuaMvImport"
mkdir -p "$DEST" "$PY_DEST"

if ! SDK_ROOT="$(find_sdk_root)"; then
  echo "警告: 未找到大华 Linux SDK。请安装 MV Viewer 后设置 DAHUA_SDK_PATH，或继续使用 --simulate"
  exit 0
fi

echo "使用大华 SDK: $SDK_ROOT"

for libdir in "$SDK_ROOT/lib" "$SDK_ROOT/lib64" "$SDK_ROOT/Runtime/x64" "$SDK_ROOT/Runtime/Linux64"; do
  if [[ -d "$libdir" ]]; then
    find "$libdir" -maxdepth 1 -type f \( -name '*.so' -o -name '*.so.*' \) -exec cp -f {} "$DEST/" \;
  fi
done

for pydir in "$SDK_ROOT/Samples/Python" "$SDK_ROOT/Development/Samples/Python"; do
  if [[ -d "$pydir" && -f "$pydir/MVSDK.py" ]]; then
    rm -rf "$PY_DEST"
    cp -a "$pydir" "$PY_DEST"
    echo "已复制 Python MVSDK -> vendor/DahuaMvImport"
    break
  fi
done

cat > "$ROOT/vendor/dahua/manifest.json" <<EOF
{"sdk_path":"$SDK_ROOT","platform":"linux","collected_at":"$(date -Iseconds)"}
EOF

echo "大华 SDK 文件已收集到 vendor/dahua/linux64"
