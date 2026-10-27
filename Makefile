SHELL := /bin/bash
COMPOSE_FILE := deploy/compose/docker-compose.yml
RAGFLOW_COMPOSE_FILE := deploy/compose/ragflow/docker-compose.yml

.PHONY: help sync lint test contracts contracts-check up down ragflow-up ragflow-down ragflow-smoke sync-documents backup restore verify-readonly verify-deploy

help:
	@printf '%s\n' \
		'make sync  - 安装/同步 Python 与前端依赖' \
		'make lint  - Ruff、依赖方向与前端类型检查' \
		'make test  - 运行 Python 测试与前端测试' \
		'make contracts - 导出 OpenAPI 并生成共享 TS 类型与客户端' \
		'make contracts-check - 校验 OpenAPI 与共享类型生成产物未漂移' \
		'make up    - 启动本地依赖服务' \
		'make down  - 停止本地依赖服务' \
		'make ragflow-up - 启动受控 RAGFlow' \
		'make ragflow-down - 停止受控 RAGFlow' \
		'make ragflow-smoke - 检查 RAGFlow 依赖健康状态' \
		'make sync-documents PROJECT_ID=<uuid> [SOURCE_DIR=docs] - 增量同步项目文档' \
		'make backup - 备份 PostgreSQL' \
		'make restore BACKUP=<file> - 恢复 PostgreSQL（需 ALLOW_RESTORE=1）' \
		'make verify-readonly - 验证 workspace 只读挂载' \
		'make verify-deploy - 校验端口暴露、只读挂载与内存上限'

sync:
	uv sync --all-packages
	pnpm install

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run lint-imports
	pnpm run lint

test:
	uv run pytest
	pnpm run test

contracts:
	uv run python apps/api/scripts/export_openapi.py
	pnpm --filter @my-agent/shared-types generate

contracts-check:
	uv run python apps/api/scripts/export_openapi.py --check
	pnpm --filter @my-agent/shared-types generate:check

up:
	docker compose -f $(COMPOSE_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) down

ragflow-up:
	docker compose -f $(RAGFLOW_COMPOSE_FILE) up -d

ragflow-down:
	docker compose -f $(RAGFLOW_COMPOSE_FILE) down

ragflow-smoke:
	curl -fsS http://127.0.0.1:$${RAGFLOW_HTTP_PORT:-9380}/api/v1/system/healthz

sync-documents:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID 不能为空" >&2; exit 1)
	uv run python -m agent_worker.sync --project-id "$(PROJECT_ID)" --source-dir "$(or $(SOURCE_DIR),.)"

backup:
	bash deploy/scripts/backup-postgres.sh

restore:
	@test -n "$(BACKUP)" || (echo "BACKUP 不能为空" >&2; exit 1)
	bash deploy/scripts/restore-postgres.sh "$(BACKUP)"

verify-readonly:
	docker run --rm -v "$(CURDIR):/workspace:ro" alpine:3.20 sh -c '! touch /workspace/.readonly-check'

verify-deploy:
	uv run python deploy/scripts/verify-compose.py
