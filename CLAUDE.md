# CLAUDE.md

个人工作助理 Agent 平台。内网自托管，服务于「文档检索确认需求 → 读取代码确认实现 → 定时产出总结 → 沉淀可复用经验」这条闭环。

规格与设计以 `openspec/` 为唯一事实来源。当前架构方案见 `openspec/changes/personal-work-agent-platform/`。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · uv workspace |
| 前端 | Vue 3 · Vite · Ant Design Vue 4 · Tailwind · Pinia · pnpm workspace |
| 智能体 | AgentScope |
| 知识库 | RAGFlow（`DOC_ENGINE=infinity`），由 `services/knowledge` 网关封装 |
| 数据库 | PostgreSQL 16 |
| 对话客户端 | LibreChat（只做配置，不写代码） |
| 部署 | Docker Compose，仅内网可达 |

## 仓库结构与依赖方向

```
apps/       api · worker · web         可独立部署
packages/   core · data · agent · shared-types   跨应用复用
services/   knowledge                  独立生命周期
deploy/     编排与部署配置
docs/adr/   架构决策记录
workspace/  被分析仓库（只读挂载，不入库）
```

依赖方向单向，由 `import-linter` 在 CI 强制：

```
apps/*            → packages/{core, data, agent}
services/knowledge → packages/core
packages/agent    → packages/core
packages/data     → packages/core
packages/core     → （无外部依赖）
```

**禁止**：`apps` 之间互相 import；`packages/knowledge` 依赖 `data`；`core` 引入外部包；前端直接写接口路径（必须用 `packages/shared-types` 生成物）。

## 常用命令

```bash
# Python
uv sync                      # 安装/同步依赖
uv run pytest                # 测试
uv run ruff check .          # 静态检查
lint-imports                 # 依赖方向检查

# 前端
pnpm install
pnpm --filter web dev
pnpm --filter web build
pnpm --filter web lint

# 本地编排
docker compose -f deploy/compose/docker-compose.yml up -d
alembic upgrade head
```

## 开发流程

本项目使用 OpenSpec 驱动开发，产物语言为简体中文（结构标题与 SHALL/MUST 保留英文）。

```bash
openspec list                              # 查看进行中的变更
openspec status --change <name>            # 查看产物完成度
openspec validate <name> --strict          # 提交前校验
```

- 新功能先建 change，补齐 proposal / specs / design / tasks 再实现。
- `tasks.md` 的复选框是进度事实来源；完成后勾选。
- 修改模块边界前，先在 `docs/adr/` 写一条决策记录。

## 项目内置技能

`.claude/skills/` 随仓库版本化，来源与更新方式见 `.claude/skills/NOTICE.md`。

| 技能 | 何时使用 |
|---|---|
| `openspec-propose` / `openspec-apply-change` / `openspec-archive-change` | 变更的提出、实施、归档 |
| `test-driven-development` | 实现任何后端模块、工具或修复缺陷前 |
| `systematic-debugging` | 遇到测试失败、流式中断、MCP 超时等异常时 |
| `verification-before-completion` | 声称任务完成前 |
| `requesting-code-review` | 合并前 |

本机全局还装有 77 个技能（含 `vue3-antd-precheck`、`pyright-lsp` 等插件）。**项目内只内置流程性技能**，通用工具技能依赖本机安装，不复制进仓库。

## 代码约定

- Python：ruff 格式化与检查；类型注解必填；模块内 `router.py` / `service.py` / `schemas.py` / `tests/` 自包含。
- 前端：`apps/web/src/modules/<feature>/` 与后端 `apps/api/src/api/modules/<feature>/` 同名。
- 列表接口统一返回 `{records, total}`；响应统一信封 `{code, data, message, success}`。
- 报告、沉淀、运行记录一律入库，本地文件只作导出。
- 时间统一 `Asia/Shanghai`，存储用 UTC。

## 安全与硬边界

- `workspace/` 下所有仓库**只读挂载**，任何写操作都是缺陷。
- 严禁提交密钥、令牌、内网地址。`.env*` 已在 `.gitignore` 中排除，仅允许 `.env.example`。
- 从既有工程裁剪代码时，必须清除其硬编码密钥与默认账号，并跑 secret 扫描。
- 智能体具备命令执行能力：新增工具必须声明作用域，且默认限定在绑定的 `project_id` 路径内。
- 每个对话与任务必须绑定 `project_id`；缺失时拒绝执行，不得猜测。

## 当前状态

仓库处于脚手架阶段：已完成 git 初始化与 OpenSpec 规划，尚未落地业务代码。实施进度以 `openspec/changes/personal-work-agent-platform/tasks.md` 为准。
