from agent_runtime import __version__


def test_runtime_package_is_importable() -> None:
    assert __version__ == "0.1.0"
