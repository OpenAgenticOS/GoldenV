from goldenv.runtime.dahua_bootstrap import prepare_dahua_runtime


def test_prepare_dahua_runtime_returns_status():
    status = prepare_dahua_runtime()
    assert status.message
    assert isinstance(status.dll_dirs, list)
