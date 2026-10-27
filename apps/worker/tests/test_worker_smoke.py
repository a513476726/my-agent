from agent_worker import __version__


def test_worker_package_is_importable() -> None:
    assert __version__ == "0.1.0"
