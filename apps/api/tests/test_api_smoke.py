from agent_api import __version__


def test_api_package_is_importable() -> None:
    assert __version__ == "0.1.0"
