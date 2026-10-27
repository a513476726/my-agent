from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_api.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "packages" / "shared-types" / "openapi.json"


def render_schema() -> str:
    schema = app.openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 FastAPI OpenAPI schema")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="仅在文件过期时返回非零退出码")
    args = parser.parse_args()

    expected = render_schema()
    output = args.output.resolve()
    if args.check:
        actual = output.read_text(encoding="utf-8") if output.exists() else ""
        if actual != expected:
            print(f"OpenAPI schema 已过期：{output}")
            return 1
        print(f"OpenAPI schema 一致：{output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8")
    print(f"OpenAPI schema 已导出：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
