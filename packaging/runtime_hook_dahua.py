"""PyInstaller 启动钩子：在任何业务模块加载前准备大华运行时。"""

from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime

prepare_dahua_runtime()
