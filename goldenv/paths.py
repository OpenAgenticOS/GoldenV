from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def internal_root() -> Path:
    root = app_root()
    internal = root / "_internal"
    return internal if internal.is_dir() else root


def bundled_configs_dir() -> Path:
    return internal_root() / "configs"


def user_data_root() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        return Path(base) / "GoldenV"
    return Path.home() / ".local" / "share" / "GoldenV"


def user_configs_dir() -> Path:
    return user_data_root() / "configs"


def user_logs_dir() -> Path:
    return user_data_root() / "logs"


def resolve_config_path(cli_path: str | None = None) -> Path:
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    user_cfg = user_configs_dir() / "station.yaml"
    if user_cfg.is_file():
        return user_cfg
    bundled = bundled_configs_dir() / "station.yaml"
    if bundled.is_file():
        ensure_user_config()
        return user_configs_dir() / "station.yaml"
    return app_root() / "configs" / "station.yaml"


def user_storage_dir() -> Path:
    """检测数据根目录（数据库、图像、导出 CSV）。"""
    root = user_data_root() / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def first_run_marker() -> Path:
    return user_data_root() / ".first_run_done"


def gige_driver_ack_marker() -> Path:
    return user_data_root() / ".gige_driver_ack"


def mv_viewer_ack_marker() -> Path:
    return user_data_root() / ".mv_viewer_ack"


def ensure_user_config() -> None:
    user_dir = user_configs_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    user_logs_dir().mkdir(parents=True, exist_ok=True)
    target = user_dir / "station.yaml"
    if target.is_file():
        return
    bundled = bundled_configs_dir() / "station.yaml"
    if bundled.is_file():
        shutil.copy2(bundled, target)
    protocols_src = bundled_configs_dir() / "scale_protocols"
    protocols_dst = user_dir / "scale_protocols"
    if protocols_src.is_dir() and not protocols_dst.exists():
        shutil.copytree(protocols_src, protocols_dst)
    user_storage_dir()
