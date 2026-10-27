# Design

## Context

当前工作区为空目录，无既有代码。动机与范围见 `proposal.md`。本设计需要同时满足四类约束：多人分区维护、前后端分离、知识库独立、多项目并行。可复用的既有资产有两处：`sales_platform_web`（Vue 3 管理后台工程）与 `sales-platform`（已采用 OpenSpec 的后端仓库，可作为流程参照）。

## Goals / Non-Goals

**Goals:**

- 用单仓多包结构承载多个可独立部署、可独立维护的单元，并在 CI 中强制依赖方向。
- 前后端通过显式契约解耦，前端可复用既有工程而不被旧后端绑架。
- 知识库以独立服务形态存在，主应用不感知其内部实现。
- 所有业务产出（报告、沉淀、运行记录）以数据库为唯一事实来源。
- 多项目并行时，检索、代码访问、任务执行三者都不串味。

**Non-Goals:**

- 不构建通用多租户 SaaS，不做租户计费与配额。
- 不实现公网访问、OAuth 单点登录与跨组织权限体系。
- 不建设可视化工作流编辑器（区别于 Dify 类产品）。
- 不改造、不写回被分析的代码仓库。

## Decisions

### D1. 单仓多包（uv workspace + pnpm workspace）

一个 git 仓库，Python 侧用 uv workspace、前端用 pnpm workspace，各自拥有独立 `pyproject.toml` / `package.json`。

- **为什么**：多项目并行开发需要共享领域模型与接口契约；多仓会导致跨仓版本协调成本远高于收益。
- **替代方案**：多仓独立——契约变更需跨仓 PR 协调，个人维护成本过高；纯单模块——无法表达多人维护边界。
- **后果**：需要 CODEOWNERS 与路径过滤 CI 才能发挥分区维护效果。

### D2. 目录按「可部署 / 可复用 / 独立生命周期」三分

```
apps/        api、worker、web      —— 可独立部署
packages/    core、data、agent、shared-types —— 跨应用复用
services/    knowledge             —— 独立生命周期
deploy/      编排与部署配置
docs/adr/    架构决策记录
```

依赖方向单向且由 `import-linter` 强制：`apps → packages`、`packages/agent → core`、`packages/data → core`、`services/knowledge → core`，`core` 零依赖，`apps` 之间禁止互相 import。

- **为什么**：依赖方向是架构唯一可自动验证的部分；靠人自觉必然腐化。
- **替代方案**：按技术分层（controller/service/repository 各一个目录）——多人维护时改一个功能要横跨所有层，冲突率高。

### D3. 后端按垂直切片组织（modular monolith）

`apps/api/src/api/modules/<feature>/` 每个模块自包含 `router.py`、`service.py`、`schemas.py`、`tests/`，与前端 `apps/web/src/modules/<feature>/` 同名同序。

- **为什么**：一个功能一个负责人，改动局部化；模块间只通过 `packages/core` 中的协议交互。
- **替代方案**：微服务——个人规模下网络调用与运维成本远超收益。

### D4. BFF 与 Worker 拆为两个可部署单元，共享 `packages/agent`

- `api`：同步请求、对外端口、无重计算。
- `worker`：长时间任务、高内存、不占端口。
- **为什么**：日程任务爆发时不能拖垮对话接口；但两者共享智能体装配，走进程内调用而非网络，避免多一跳。
- **替代方案**：单进程——一次日清即可拖垮 API；worker 独立成微服务——多一层网络且需重复装配。

### D5. 前后端分离，前端复用既有工程

- 前端：Vue 3 + Vite + Ant Design Vue，从 `sales_platform_web` 裁剪。
- **保留**：`ProTable`（配置驱动表格）、`DetailView`、`ProUpload`、布局壳、菜单路由引擎、权限指令、请求层、主题与工程配置。
- **丢弃**：全部业务页面（约 4.9 万行）、业务 API 模块、品牌资产、演示残留。
- **必须清除**：AES 密钥、请求签名密钥、OAuth Basic 凭据、默认账号、旧内网地址；接入 secret 扫描。
- **为什么**：`ProTable` 一类组件的成熟度是新工程短期内无法追平的，复用它们能显著压缩 P3 工期。
- **替代方案**：通用 admin 脚手架——组件能力弱于现有工程；服务端渲染后台（SQLAdmin）——不满足前后端分离。

### D6. 沿用既有接口契约以压缩前端改造面

后端提供 `{code, data, message, success}` 信封、`{records, total}` 分页、`Authorization: Bearer`、`/auth/login`、`/admin/user/info`、`/admin/menu/userMenu/{app}`。

- **为什么**：前端 `request.ts`、`ProTable`、`utils/route.ts` 均依赖这些约定；让后端适配前端，改造面收敛到登录与菜单两处。
- **替代方案**：RESTful 风格 + OpenAPI 生成客户端——更规范，但需改动 `ProTable` 与请求层，P3 工期显著拉长。OpenAPI 生成仍保留为 P4 的补充手段，用于新增接口。
- **代价**：后端需要一层统一响应包装，非标准 REST。

### D7. 知识库独立成服务，主应用只依赖 HTTP 契约

`services/knowledge` 暴露 `POST /v1/datasets`、`POST /v1/datasets/{id}/documents`、`POST /v1/retrieval`，内部封装 RAGFlow。

- **为什么**：满足「知识库分离」与独立负责人；`project_id → dataset_id` 映射与结果归一化集中在网关，主应用不出现 RAGFlow 字段。
- **替代方案**：主应用直接调用 RAGFlow REST/MCP——少一个服务，但 Provider 细节会渗透进业务代码，日后替换成本高。
- **实现选择**：RAGFlow 起步使用 `DOC_ENGINE=infinity`，规避 Elasticsearch 的内存占用与 `vm.max_map_count` 依赖。

### D8. 智能体内核采用 AgentScope

- **为什么**：已有使用经验；是框架而非脚手架；支持工具与 MCP；不承担 hermes-agent 体量（约 3500 源文件）带来的上游 fork 维护成本。
- **替代方案**：hermes-agent——现成度最高但接债；自写 tool loop——违背「不从头写」原则。

### D9. 数据库为唯一事实来源

报告正文、报告条目、能力沉淀、任务运行记录、会话与审计全部落 PostgreSQL，本地文件仅作导出。

- **为什么**：多人维护与多端消费要求并发安全与统一查询入口；文件无法承载事务、幂等约束与权限。
- **替代方案**：Markdown 文件 + Git——可读性好，但并发写、幂等与查询能力不足。
- **关键约束**：`job_runs` 上 `run_key = f"{job_id}:{project_id}:{period}"` 唯一，作为幂等基础。

### D10. 多项目隔离依靠显式上下文

每次对话与任务绑定 `project_id`；检索强制带项目过滤；文件与 Git 访问限定在项目登记路径内；无上下文时拒绝而非猜测。

- **为什么**：跨项目串味是多项目平台最常见的正确性事故，且模型自身无法可靠判断归属。
- **替代方案**：全局检索 + 来源标注——召回率高但串味风险不可控，且难以在测试中断言。

### D11. 对话客户端复用 LibreChat，仅做配置

LibreChat 以 OpenAI 兼容端点接入本平台，按项目建立预设以固定项目上下文。

- **为什么**：会话历史、多用户、MCP 客户端等能力成熟，自建成本高。
- **替代方案**：合并进自建前端——少一套 UI，但需要自研对话体验。

### D12. 内网部署，特权面不暴露

仅 `web` 与 `api` 在内网可达；`worker`、`services/knowledge`、RAGFlow 不暴露端口；被分析仓库以只读方式挂载。

- **为什么**：智能体具备命令执行与文件读取能力，暴露面必须最小化。
- **替代方案**：公网 + 2FA——攻击面与运维负担显著上升，且当前需求仅需内网可达。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 依赖方向腐化 | `import-linter` + ESLint 边界规则进 CI，越界即失败 |
| 前后端契约漂移 | 新接口走 OpenAPI 生成；CI 校验生成产物是否与 schema 一致 |
| 前端夹带密钥 | 裁剪首日执行 secret 扫描（gitleaks），命中即阻断合并 |
| 多项目串味 | 显式 `project_id` + 检索过滤 + 交叉提问测试 |
| 单点模型能力不足 | Provider 层可切换；跨文件推理任务单独评估模型 |
| RAGFlow 解析质量不达标 | 20 篇真实文档先验证四项指标，再全量同步 |
| 8 核 16G 内存紧张 | RAGFlow 用 infinity 引擎；各单元设置内存上限；必要时合并部署 |
| 上游依赖升级风险 | 锁定镜像与包版本；升级前在独立环境验证 |

## Migration Plan

全新项目，无存量迁移。按阶段落地，每阶段可独立验收：

1. **基础设施**：git 初始化、workspace 骨架、依赖检查、CODEOWNERS、CI 骨架。
2. **数据层**：领域协议与数据库建模、迁移脚本、幂等约束单测。
3. **后端骨架**：模块结构、鉴权、统一响应包装、健康检查。
4. **前端落地**：裁剪复用、清除密钥、登录与菜单打通。
5. **知识与智能体**：知识库网关与 RAGFlow 验证；智能体装配与会话落库。
6. **任务与沉淀**：调度、报告入库、能力沉淀。
7. **加固**：内网暴露面收敛与备份恢复演练。

回滚策略：各阶段以 feature 分支推进，未合并即回滚；已合并的数据层变更通过 Alembic 降级脚本处理。

## Open Questions

- 当前模型链路（火山方舟 + `doubao-seed-2-1-pro-260628`）在跨文件代码推理上的实际表现，需在阶段 5 实测后决定是否引入更强的模型分级。原计划使用的 DeepSeek 模型在当前账户未开通，已切换到可用的豆包模型。
- RAGFlow 在 1000+ 篇混合文档上的解析耗时与内存峰值，需在阶段 5 用 20 篇样本外推。
- 8 核 16G 下四个自研单元的内存配额具体取值，需在压测后确定。
