from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from goldenv.paths import app_root, internal_root, is_frozen

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DahuaRuntimeStatus:
    ready: bool
    python_module_dir: Optional[Path]
    dll_dirs: List[Path]
    message: str


def _candidate_python_dirs() -> List[Path]:
    root = app_root()
    internal = internal_root()
    dirs = [
        internal / "DahuaMvImport",
        root / "DahuaMvImport",
        root / "vendor" / "DahuaMvImport",
        Path(__file__).resolve().parent.parent.parent / "vendor" / "DahuaMvImport",
    ]
    for env_key in ("DAHUA_SDK_PATH", "MVSDK_PATH", "HUARAY_SDK_PATH"):
        env = os.environ.get(env_key)
        if not env:
            continue
        base = Path(env)
        dirs.extend(
            [
                base,
                base / "Development" / "Samples" / "Python",
                base / "Samples" / "Python",
            ]
        )
    if sys.platform == "win32":
        for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if not pf:
                continue
            for name in ("HuarayTech/MV Viewer", "DaHuaTech/MV Viewer", "Industrial Camera/MV Viewer"):
                dirs.append(Path(pf) / name / "Development" / "Samples" / "Python")
    elif sys.platform.startswith("linux"):
        for base in ("/opt/HuarayTech/MVviewer", "/opt/MVS", "/opt/dahua-mvviewer"):
            dirs.extend([Path(base) / "Samples" / "Python", Path(base)])
    unique: List[Path] = []
    seen = set()
    for path in dirs:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _candidate_dll_dirs() -> List[Path]:
    root = app_root()
    internal = internal_root()
    dirs = [
        root,
        internal,
        root / "dahua" / "win64",
        internal / "dahua" / "win64",
        root / "vendor" / "dahua" / "win64",
    ]
    if sys.platform.startswith("linux"):
        dirs.extend(
            [
                root / "dahua" / "linux64",
                internal / "dahua" / "linux64",
                root / "vendor" / "dahua" / "linux64",
            ]
        )
    for env_key in ("DAHUA_SDK_PATH", "MVSDK_PATH"):
        env = os.environ.get(env_key)
        if not env:
            continue
        base = Path(env)
        dirs.extend(
            [
                base,
                base / "Runtime" / "x64",
                base / "Runtime" / "Win64",
                base / "lib64",
                base / "lib",
            ]
        )
    unique: List[Path] = []
    seen = set()
    for path in dirs:
        if path.is_dir():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                unique.append(path)
    return unique


def _has_mvsdk_module(path: Path) -> bool:
    return path.is_dir() and (path / "MVSDK.py").is_file()


def _register_dll_directories(dll_dirs: List[Path]) -> None:
    if sys.platform != "win32":
        return
    if hasattr(os, "add_dll_directory"):
        for directory in dll_dirs:
            try:
                os.add_dll_directory(str(directory))
            except OSError as exc:
                logger.debug("无法注册 DLL 目录 %s: %s", directory, exc)
    else:
        path_value = os.environ.get("PATH", "")
        prepend = ";".join(str(d) for d in dll_dirs)
        os.environ["PATH"] = f"{prepend};{path_value}" if path_value else prepend


def prepare_dahua_runtime() -> DahuaRuntimeStatus:
    """启动或安装后调用：注册大华 SDK 搜索路径与 DLL 目录。"""
    python_dir: Optional[Path] = None
    for directory in _candidate_python_dirs():
        if _has_mvsdk_module(directory):
            python_dir = directory
            if str(directory) not in sys.path:
                sys.path.insert(0, str(directory))
            break

    dll_dirs = _candidate_dll_dirs()
    _register_dll_directories(dll_dirs)

    if python_dir and not os.environ.get("DAHUA_SDK_PATH"):
        os.environ["DAHUA_SDK_PATH"] = str(python_dir.parent.parent.parent if "Samples" in str(python_dir) else python_dir)

    ready = python_dir is not None
    if ready:
        message = f"大华 MVSDK 已就绪: {python_dir}"
    elif is_frozen():
        message = "安装包内未找到大华 MVSDK，请重新运行安装程序或联系管理员"
    else:
        message = "未检测到大华 SDK，开发模式将使用模拟相机。可运行 scripts/fetch_dahua_sdk.ps1 或 .sh"

    logger.info(message)
    return DahuaRuntimeStatus(ready=ready, python_module_dir=python_dir, dll_dirs=dll_dirs, message=message)


def read_bundled_manifest() -> dict:
    for base in (internal_root(), app_root()):
        manifest = base / "dahua" / "manifest.json"
        if manifest.is_file():
            with manifest.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    return {}
