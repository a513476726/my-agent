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

Python 导入包名与目录的对应关系：`apps/api` → `agent_api`、`apps/worker` → `agent_worker`、`packages/core` → `agent_core`、`packages/data` → `agent_data`、`packages/agent` → `agent_runtime`、`services/knowledge` → `agent_knowledge`。

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
uv sync --all-packages       # 安装/同步全部 workspace 依赖
uv run pytest                # 测试
uv run ruff check .          # 静态检查
lint-imports                 # 依赖方向检查

# 需要数据库的测试（先创建 myagent_test 库）
TEST_DATABASE_URL=postgresql+psycopg://myagent:<password>@127.0.0.1:5432/myagent_test uv run pytest

# 前端
pnpm install
pnpm --filter web dev
pnpm --filter web build
pnpm --filter web lint

# 契约
make contracts              # 导出 OpenAPI 并生成共享类型与客户端
make contracts-check        # 校验 schema / 生成产物是否漂移

# 本地编排
docker compose -f deploy/compose/docker-compose.yml up -d
alembic upgrade head

# 受控 RAGFlow（仅 127.0.0.1:9380）
make ragflow-up
make ragflow-smoke

# 知识库网关（需先设置 RAGFLOW_BASE_URL / RAGFLOW_API_KEY）
uv run uvicorn agent_knowledge.main:app --host 127.0.0.1 --port 8001

# 按项目增量同步文档（SOURCE_DIR 是项目内相对目录）
make sync-documents PROJECT_ID=<uuid> SOURCE_DIR=docs
```

### RAGFlow 本地要点

- 密钥放在 `deploy/compose/ragflow/.env`（已忽略、权限 `600`），只把变量名写入 `.env.example`。
- RAGFlow 超级管理员不允许调用 `/api/v1/system/tokens`；需创建一个普通账号，用它登录并生成 API Key，再填入根目录 `.env` 的 `RAGFLOW_API_KEY`。
- 数据集必须配置可用的 Embedding Provider 才能完成分块与向量检索。未配置时文档解析会报 `encoder resolution returned nil`，`/v1/retrieval` 只能返回空结果。
- 火山方舟需先在 Ark 控制台开通模型，再在 RAGFlow 新增 `VolcEngine` Provider 实例和 API Key。配置后设置 `RAGFLOW_EMBEDDING_MODEL` 为完整 ID（形如 `doubao-embedding-vision-251215@volcengine@VolcEngine`）；网关创建数据集时会写入该模型。已有空模型数据集需删除后重建。
- 解析是异步的：网关会在“启动解析请求”失败时尽力删除上游文档，但异步解析失败仍需在后续同步任务中核对文档状态。

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

仓库的本地功能开发已覆盖 P0–P10：uv/pnpm 多包工程、数据层、管理后台、契约生成、RAGFlow 网关与增量同步、AgentScope 智能体、调度报告、能力沉淀、只读挂载与备份恢复。默认模型为火山方舟 `doubao-seed-2-1-pro-260628`，已通过真实工具调用与 SSE 冒烟。RAGFlow 真实文档规模验收（6.4、7.2、7.3）、LibreChat 实例联调（8.6）以及多主机/长期内存压测（11.1、11.3）仍待外部环境。实施进度以 `openspec/changes/personal-work-agent-platform/tasks.md` 为准。
