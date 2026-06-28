from __future__ import annotations

import argparse
import logging
import sys

from PySide6.QtCore import QLocale
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from goldenv.config import load_config
from goldenv.paths import ensure_user_config, resolve_config_path, user_data_root, user_logs_dir
from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime
from goldenv.ui.main_window import MainWindow


def _setup_logging() -> None:
    log_dir = user_logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "goldenv.log", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _setup_font(app: QApplication) -> None:
    if sys.platform == "win32":
        app.setFont(QFont("Microsoft YaHei UI", 10))
    else:
        app.setFont(QFont("Noto Sans CJK SC", 10))
        for name in ("Noto Sans CJK SC", "WenQuanYi Micro Hei", "Sans Serif"):
            if QFont(name).family():
                app.setFont(QFont(name, 10))
                break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="黄金镯子检测系统")
    parser.add_argument("--config", help="工位配置文件路径")
    parser.add_argument("--simulate", action="store_true", help="模拟相机与电子秤")
    parser.add_argument("--headless-test", action="store_true", help="无 GUI 冒烟测试")
    args = parser.parse_args(argv)

    ensure_user_config()
    _setup_logging()

    dahua_status = prepare_dahua_runtime()
    logging.info("大华运行时: %s", dahua_status.message)

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    base_dir = user_data_root()

    if args.headless_test:
        logging.info("headless 测试通过：配置已加载 %s", config_path)
        logging.info("大华 SDK 就绪: %s", dahua_status.ready)
        return 0

    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Chinese, QLocale.China))
    _setup_font(app)

    window = MainWindow(
        config=config,
        config_path=config_path,
        base_dir=base_dir,
        simulate=args.simulate or config.cameras[0].kind == "simulated",
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
