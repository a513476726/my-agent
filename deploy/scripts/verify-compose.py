from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAIN_COMPOSE = ROOT / "deploy/compose/docker-compose.yml"
RAGFLOW_COMPOSE = ROOT / "deploy/compose/ragflow/docker-compose.yml"
PUBLIC_SERVICES = frozenset({"api", "web"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
MAX_TOTAL_MEMORY = 16 * 1024**3


def _compose_config(path: Path, defaults: dict[str, str]) -> dict[str, Any]:
    environment = {**defaults, **os.environ}
    output = subprocess.check_output(
        ["docker", "compose", "-f", str(path), "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        text=True,
    )
    return json.loads(output)


def _published_ports(service: dict[str, Any]) -> list[dict[str, Any]]:
    return service.get("ports") or []


def _check_ports(name: str, config: dict[str, Any]) -> int:
    failures = 0
    for service_name, service in config.get("services", {}).items():
        for port in _published_ports(service):
            host_ip = port.get("host_ip") or "0.0.0.0"
            if service_name in PUBLIC_SERVICES:
                continue
            if host_ip not in LOOPBACK_HOSTS:
                print(
                    f"FAIL {name}/{service_name}: 非 API/Web 端口发布在 {host_ip}",
                    file=sys.stderr,
                )
                failures += 1
    return failures


def _check_workspace_mounts(config: dict[str, Any]) -> int:
    failures = 0
    for service_name in ("api", "worker"):
        service = config.get("services", {}).get(service_name, {})
        workspaces = [
            volume for volume in service.get("volumes", []) if volume.get("target") == "/workspace"
        ]
        if len(workspaces) != 1 or workspaces[0].get("read_only") is not True:
            print(f"FAIL {service_name}: /workspace 未以只读方式挂载", file=sys.stderr)
            failures += 1
    return failures


def _memory_bytes(services: dict[str, Any]) -> int:
    total = 0
    for service in services.values():
        value = service.get("mem_limit")
        if isinstance(value, int):
            total += value
        elif isinstance(value, str) and value.isdigit():
            total += int(value)
    return total


def main() -> int:
    main_config = _compose_config(
        MAIN_COMPOSE,
        {
            "POSTGRES_PASSWORD": "verify-password",
            "AUTH_SECRET": "verify-secret-" + "x" * 32,
            "ADMIN_PASSWORD": "verify-admin-password",
        },
    )
    ragflow_config = _compose_config(
        RAGFLOW_COMPOSE,
        {
            "MYSQL_PASSWORD": "verify-mysql-password",
            "MINIO_USER": "verify-minio-user",
            "MINIO_PASSWORD": "verify-minio-password",
            "REDIS_PASSWORD": "verify-redis-password",
            "RAGFLOW_ADMIN_PASSWORD": "verify-ragflow-password",
        },
    )

    failures = _check_ports("main", main_config)
    failures += _check_ports("ragflow", ragflow_config)
    failures += _check_workspace_mounts(main_config)

    total_memory = _memory_bytes(main_config.get("services", {})) + _memory_bytes(
        ragflow_config.get("services", {})
    )
    if total_memory > MAX_TOTAL_MEMORY:
        print(
            f"FAIL 内存上限合计 {total_memory / 1024**3:.2f} GiB，超过 16 GiB",
            file=sys.stderr,
        )
        failures += 1

    if failures:
        return 1
    print(f"OK 暴露面与只读挂载符合约束，内存上限合计 {total_memory / 1024**3:.2f} GiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
