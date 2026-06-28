from __future__ import annotations

import sys

from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime


def _sdk_search_paths():
    from goldenv.runtime.dahua_bootstrap import _candidate_python_dirs

    return _candidate_python_dirs()


def is_dahua_sdk_available() -> bool:
    prepare_dahua_runtime()
    for path in _sdk_search_paths():
        if path.is_dir() and (path / "MVSDK.py").is_file():
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
            try:
                import MVSDK  # type: ignore  # noqa: F401
                import ImageConvert  # type: ignore  # noqa: F401

                return True
            except ImportError:
                continue
    return False


def _load_mvsdk():
    prepare_dahua_runtime()
    for path in _sdk_search_paths():
        if not path.is_dir() or not (path / "MVSDK.py").is_file():
            continue
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
        try:
            import MVSDK  # type: ignore
            import ImageConvert  # type: ignore

            return {"MVSDK": MVSDK, "ImageConvert": ImageConvert, "path": path}
        except ImportError:
            continue
    return None
