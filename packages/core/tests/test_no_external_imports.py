from __future__ import annotations

import ast
import sys
from pathlib import Path

CORE_SOURCE = Path(__file__).parents[1] / "src" / "agent_core"
ALLOWED_ROOTS = set(sys.stdlib_module_names) | {"agent_core"}


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_core_has_no_external_imports() -> None:
    violations: list[str] = []
    for path in sorted(CORE_SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for root in sorted(_import_roots(tree) - ALLOWED_ROOTS):
            violations.append(f"{path.relative_to(CORE_SOURCE)} -> {root}")

    assert not violations, "agent_core 只允许标准库导入：\n" + "\n".join(violations)
