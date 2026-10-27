from agent_knowledge import __version__


def test_knowledge_package_is_importable() -> None:
    assert __version__ == "0.1.0"
