from agent_data import __version__


def test_data_package_is_importable() -> None:
    assert __version__ == "0.1.0"
