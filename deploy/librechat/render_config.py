from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text


@dataclass(frozen=True, slots=True)
class ProjectRef:
    id: str
    name: str


def build_config(
    projects: list[ProjectRef],
    *,
    base_url: str,
    model: str,
    api_key_variable: str = "${MY_AGENT_API_KEY}",
) -> dict[str, object]:
    endpoints: list[dict[str, object]] = [
        {
            "name": "个人工作助理",
            "apiKey": api_key_variable,
            "baseURL": base_url,
            "models": {"default": [model], "fetch": True},
            "titleConvo": True,
            "titleModel": "current_model",
            "modelDisplayLabel": "个人工作助理",
        }
    ]
    for project in projects:
        endpoints.append(
            {
                "name": f"{project.name} · 项目助理",
                "apiKey": api_key_variable,
                "baseURL": base_url,
                "models": {"default": [model], "fetch": False},
                "titleConvo": True,
                "titleModel": "current_model",
                "modelDisplayLabel": project.name,
                "headers": {"X-Project-Id": project.id},
            }
        )
    return {
        "version": "1.2.8",
        "cache": True,
        "fileStrategy": "local",
        "endpoints": {"custom": endpoints},
    }


def load_enabled_projects(database_url: str) -> list[ProjectRef]:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT id, name FROM projects WHERE enabled = true ORDER BY created_at, id")
            ).all()
    finally:
        engine.dispose()
    return [ProjectRef(id=str(row.id), name=str(row.name)) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 LibreChat 项目预设配置")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="项目数据库连接串，默认读取 DATABASE_URL",
    )
    parser.add_argument("--base-url", default="http://api:8000/v1")
    parser.add_argument(
        "--model",
        default=os.environ.get("AGENT_MODEL", "doubao-seed-2-1-pro-260628"),
    )
    parser.add_argument("--output", default="deploy/librechat/librechat.yaml")
    args = parser.parse_args()

    if not args.database_url:
        parser.error("必须提供 --database-url 或 DATABASE_URL")
    projects = load_enabled_projects(args.database_url)
    config = build_config(projects, base_url=args.base_url, model=args.model)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已写入 {output}，包含 {len(projects)} 个项目预设")


if __name__ == "__main__":
    main()
