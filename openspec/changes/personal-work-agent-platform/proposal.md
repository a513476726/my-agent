# Proposal

## Why

当前个人工作缺乏统一入口：产品文档分散在本地目录、代码仓库有多个且互不关联、每日代码变更需要手工回顾、需求口径确认只能靠翻找文档。需要一个能在内网自托管的智能体平台，把「文档检索确认需求 → 读取代码确认实现 → 定时产出总结 → 沉淀可复用经验」串成一条闭环。同时平台需要支持多人分区维护，避免成为单人不可持续的黑盒脚本。

## What Changes

- 建立**单仓多包工作空间**（uv workspace + pnpm workspace），按 `apps/`（可部署）、`packages/`（可复用）、`services/`（独立生命周期）划分，配 CODEOWNERS 与路径过滤 CI，支持多人分区维护。
- 后端提供 **BFF + 运营 API**（FastAPI），前端提供**独立管理后台**（Vue 3 + Vite + Ant Design Vue，从既有工程裁剪复用），实现前后端分离。
- 引入**知识库独立服务**（网关封装 RAGFlow），对主应用只暴露稳定契约，主应用不感知 Provider 细节。
- 引入**智能体服务**（AgentScope），支持工具编排、多轮推理与会话持久化，并对 LibreChat 暴露 OpenAI 兼容接口。
- 建立**定时任务与报告体系**：日清抓取 Git 变更并生成总结，周报/季报复用同一流水线；**报告与代码能力沉淀全部落 PostgreSQL**，本地文件仅作导出。
- 建立**多项目隔离机制**：每次对话与任务必须绑定 `project_id`，检索与代码访问限定在该项目范围内。
- 明确**职责边界与依赖方向**，用 `import-linter` 与 ESLint 边界规则在 CI 中强制。

## Capabilities

### New Capabilities

- `project-scoping`: 多项目登记、显式项目上下文绑定、跨项目检索隔离与无上下文时的拒绝行为。
- `knowledge-retrieval`: 文档入库、知识库同步、按项目检索并返回可定位出处（文档 + 章节/页码）。
- `agent-conversation`: 面向 OpenAI 兼容协议的对话接口、工具编排、会话与引用持久化、流式输出。
- `digest-reporting`: 定时触发日清/周报/季报任务，采集 Git 变更并生成报告，报告正文与条目入库，运行幂等与故障隔离。
- `capability-sediment`: 从报告条目提炼代码能力与最佳实践，沉淀为可检索、可回溯来源的知识条目。
- `admin-console`: 管理后台对项目、文档、知识库、报告、沉淀条目、任务的运营与审计能力。

### Modified Capabilities

无（本项目为全新建库，尚无既有 capability）。

## Impact

- **新增代码**：`apps/api`、`apps/worker`、`apps/web`、`services/knowledge`、`packages/{core,data,agent,shared-types}`。
- **外部依赖**：PostgreSQL 16、RAGFlow（`DOC_ENGINE=infinity`）、LibreChat、火山方舟 LLM 与 Embedding API。
- **受影响系统**：需只读挂载本地代码仓库（`zzginfo/work-space`、`zzginfo/hermes-agent`、`haier/dichan/*` 等），不修改被分析仓库。
- **前端来源**：从 `haier/dichan/saleWorkSpace/sales_platform_web` 裁剪复用通用组件与工程配置，**必须清除其硬编码密钥、默认账号与旧内网地址**。
- **部署**：仅在隔离内网可达；8 核 16G 服务器，RAGFlow 约独占 10G 内存。
- **契约约束**：后端沿用 `{code, data, message, success}` 信封与 `{records, total}` 分页，以降低前端改造面。
