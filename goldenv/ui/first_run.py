from __future__ import annotations

import sys

from PySide6.QtWidgets import QMessageBox

from goldenv.config import AppConfig
from goldenv.paths import mv_viewer_ack_marker
from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime
from goldenv.ui import strings as S


def maybe_prompt_mv_viewer(parent, config: AppConfig) -> None:
    """配置为大华相机且本机未检测到 MVSDK 时，提示用户安装 MV Viewer。"""
    if sys.platform != "win32":
        return
    if mv_viewer_ack_marker().is_file():
        return
    cam = config.cameras[0] if config.cameras else None
    if not cam or cam.kind != "dahua":
        return
    status = prepare_dahua_runtime()
    mv_viewer_ack_marker().touch()
    if status.ready:
        return
    QMessageBox.warning(
        parent,
        S.MV_VIEWER_TITLE,
        S.MV_VIEWER_PROMPT,
    )
