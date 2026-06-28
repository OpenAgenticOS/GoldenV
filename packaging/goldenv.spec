# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 自包含 Windows/Linux onedir 打包。"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "configs"), "configs"),
    (str(ROOT / "assets"), "assets"),
]
binaries = []
hiddenimports = [
    "pydantic",
    "yaml",
    "serial",
    "serial.tools.list_ports",
    "numpy",
    "cv2",
]

for pkg in ("PySide6", "cv2"):
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

hiddenimports += collect_submodules("goldenv")

dahua_import = ROOT / "vendor" / "DahuaMvImport"
if dahua_import.is_dir() and any(dahua_import.iterdir()):
    datas.append((str(dahua_import), "DahuaMvImport"))

dahua_bundle = ROOT / "vendor" / "dahua"
if dahua_bundle.is_dir():
    datas.append((str(dahua_bundle), "dahua"))

dahua_win = ROOT / "vendor" / "dahua" / "win64"
if dahua_win.is_dir():
    for dll in dahua_win.glob("*.dll"):
        binaries.append((str(dll), "dahua/win64"))
        binaries.append((str(dll), "."))

runtime_hooks = [str(ROOT / "packaging" / "runtime_hook_dahua.py")]

a = Analysis(
    [str(ROOT / "goldenv" / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GoldenV",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GoldenV",
)
