# Tasks

## 1. 基础设施（P0）

- [x] 1.1 初始化 git 仓库并提交 `.gitignore`（排除 `node_modules/`、`.venv/`、`dist/`、`data/`、`workspace/`），验证 `git status` 干净
- [x] 1.2 建立 uv workspace 根 `pyproject.toml` 与 `apps/`、`packages/`、`services/` 目录骨架，验证 `uv sync` 成功
- [x] 1.3 建立 pnpm workspace 根 `pnpm-workspace.yaml`，验证 `pnpm install` 成功
- [x] 1.4 配置 `import-linter` 的依赖方向规则（`core` 零依赖、`apps` 互不 import、`knowledge` 不依赖 `data`），验证故意越界时 `lint-imports` 失败
- [x] 1.5 编写 `CODEOWNERS`，验证 GitHub 能识别各目录负责人（文件位于 `.github/CODEOWNERS`，owner `a513476726` 已确认推送权限，远程 `main` 已包含该文件）
- [x] 1.6 建立 GitHub Actions：Python lint/test 与前端 lint/build 按 `paths:` 过滤，验证仅改 `apps/web` 时只触发前端任务（首次推送 Backend/Frontend/Contracts 全成功；仅改 `apps/web` 的提交只触发 Frontend 并成功）
- [x] 1.7 添加 `Makefile`（`sync`、`lint`、`test`、`up`、`down`），验证每条目标可独立执行

## 2. 数据层（P1）

- [x] 2.1 在 `packages/core` 定义领域模型与协议接口（无外部依赖），验证 `import-linter` 报告 `core` 无外部依赖
- [x] 2.2 在 `packages/data` 实现全部表模型（projects、documents、knowledge_bases、reports、report_items、capability_notes、agents、jobs、job_runs、conversations、messages、audit_logs），验证 `alembic revision --autogenerate` 生成完整迁移
- [x] 2.3 初始化 Alembic 并执行 `alembic upgrade head`，验证 12 张表全部创建
- [x] 2.4 为 `job_runs` 增加 `run_key` 唯一约束，验证插入重复 `run_key` 时数据库拒绝
- [x] 2.5 实现 repository 层（含分页返回 `{records, total}`），验证单测覆盖分页与事务回滚

## 3. 后端骨架（P2）

- [x] 3.1 建立 FastAPI 应用与 `/health`，验证返回数据库连通状态
- [x] 3.2 实现统一响应信封 `{code, data, message, success}` 与全局异常处理，验证成功与失败两类响应结构一致
- [x] 3.3 实现分页响应封装，验证列表接口返回 `records` 与 `total`
- [x] 3.4 实现鉴权接口 `/auth/login`、`/admin/user/info`、`/admin/menu/userMenu/{app}`，验证登录后可用 Bearer 访问受保护接口
- [x] 3.5 建立 `modules/{project,document,report,capability,job,chat}` 骨架与依赖注入，验证各模块路由可访问且互不 import
- [x] 3.6 实现审计日志写入（操作者、动作、资源、时间），验证写操作后 `audit_logs` 有记录

## 4. 前端落地（P3）

- [x] 4.1 从 `sales_platform_web` 复制可复用目录（`components/ProTable`、`DetailView`、`ProUpload`、`layouts`、`utils`、`hooks`、`directives`、`stores/theme|tags`、工程配置），验证 `pnpm build` 通过
- [x] 4.2 删除全部旧销售业务页面与业务 API 模块；新接入的项目、文档、报告列表由 4.6 实现，验证 `src/views` 不含旧业务页面且 `src/api` 仅保留新后端契约模块
- [x] 4.3 **清除硬编码密钥与旧地址**（AES 密钥、签名密钥、OAuth Basic、默认账号、旧内网 IP、生产跳转），验证 `gitleaks detect` 无命中
- [x] 4.4 改造 `stores/auth.ts`、`views/Login.vue`、路由守卫对接新后端，验证登录后可进入工作台
- [x] 4.5 对接菜单接口与 `utils/route.ts`，验证服务端菜单能渲染出侧边栏并正确跳转
- [x] 4.6 用 `ProTable` 实现项目、文档、报告三个列表页，验证分页与筛选可用
- [x] 4.7 新增面包屑组件，验证多级路由下正确显示路径

## 5. 契约生成（P4）

- [x] 5.1 导出 FastAPI OpenAPI schema，验证 schema 文件可稳定生成
- [x] 5.2 在 `packages/shared-types` 生成 TS 类型与客户端，验证生成产物可被前端 import
- [x] 5.3 CI 增加契约校验：schema 变更后重新生成，验证未提交生成产物时任务失败

## 6. 知识库（P5）

- [x] 6.1 建立 `services/knowledge` 网关与 `/v1/datasets`、`/v1/datasets/{id}/documents`、`/v1/retrieval`，验证三个接口可访问且返回统一结构（真实 RAGFlow 冒烟通过）
- [x] 6.2 编写 RAGFlow 编排（`DOC_ENGINE=infinity`），验证 RAGFlow 服务与 API 可用（v1.0.0-rc2，`healthz` 全项 ok）
- [x] 6.3 实现 `project_id → dataset_id` 映射与结果归一化（`source_path`、`heading_path`、`score`），验证不同项目检索互不串数据（双项目映射与过滤测试通过）
- [ ] 6.4 用 20 篇真实文档（含扫描件与复杂表格）完成验证，记录召回命中率、出处可定位性、解析耗时与失败率四项指标
- [x] 6.5 实现文档入库与 `documents` 表映射（含内容摘要去重），验证重复入库不产生新记录

## 7. 全量同步（P6）

- [x] 7.1 实现增量同步命令（新增/变更/跳过三种结果分别计数），验证重复执行第二次无新增
- [ ] 7.2 同步 1000+ 篇文档，验证失败文档可列出且不阻断其余文档
- [ ] 7.3 验证按项目检索能返回带出处的结果，且跨项目不串味

## 8. 智能体（P7）

- [x] 8.1 在 `packages/agent` 完成 AgentScope 装配（模型配置、工具注册、项目上下文注入），验证最小单轮对话可返回结果（真实 Ark 模型冒烟通过，默认模型 `doubao-seed-2-1-pro-260628`）
- [x] 8.2 实现工具：`search_knowledge`、`fs_read`、`fs_search`、`git_log`、`git_diff`，验证每个工具有独立单测（五个工具单测通过，真实模型调用 `fs_read` 成功）
- [x] 8.3 实现 `GET /v1/models` 与 `POST /v1/chat/completions`（含 SSE），验证流式响应可被客户端消费（真实 Ark 非流式与 SSE 冒烟通过，终止标识为 `[DONE]`）
- [x] 8.4 实现会话与引用落库，验证查询历史会话时能看到引用信息（假知识库引用持久化与真实模型工具调用落库测试通过）
- [x] 8.5 实现缺上下文拒绝逻辑，验证未绑定项目时不执行任何工具（无 `project_id` 时不创建会话、不调用工具）
- [ ] 8.6 配置 LibreChat 自定义端点与按项目预设，验证对话经本平台产生且带引用（配置生成器已实现；LibreChat 实例联调未做）
- [x] 8.7 执行交叉提问测试（同一问题在项目 A 与项目 B 分别提问），验证回答范围不串项目（双项目 `fs_read` 交叉测试通过）

## 9. 调度与报告（P8）

- [x] 9.1 实现 APScheduler 从数据库加载任务并执行，验证启用/停用任务状态生效（启用任务被加载、停用任务被移除的测试通过）
- [x] 9.2 实现 `daily_git` 处理逻辑（采集 `git log --numstat` 与关键差异），验证单项目产出结构化摘要（提交、文件统计与差异解析测试通过）
- [x] 9.3 实现 `run_key` 幂等，验证同日重复触发被跳过并返回已有报告引用（重复触发复用已有成功运行与报告）
- [x] 9.4 实现故障隔离，验证单项目失败只标记该次运行失败且其他项目正常完成（失败隔离与同键重试测试通过）
- [x] 9.5 实现报告入库与后台展示，验证报告正文与条目来自数据库且可按项目与周期筛选（详情与周期筛选 API 测试通过）
- [x] 9.6 实现报告导出，验证导出文件生成后数据库记录不受影响（Markdown 导出前后记录一致性测试通过）

## 10. 能力沉淀（P9）

- [x] 10.1 实现 `capability_sediment` 任务从报告条目提炼沉淀条目，验证每条都带来源报告与项目（沉淀任务入库与来源字段测试通过）
- [x] 10.2 实现主题去重与合并，验证重复主题不新增条目且来源被追加（同主题来源与标签合并测试通过）
- [x] 10.3 实现状态管理（草稿/已确认/已归档），验证草稿默认不出现在检索结果中（默认隐藏与状态更新 API 测试通过）
- [x] 10.4 实现按项目、主题、标签检索，验证各维度过滤正确（多维过滤测试通过）
- [x] 10.5 实现已确认条目回灌知识库，验证同步后可在对话中检索到（确认后同步、幂等与假知识库 E2E 检索通过）

## 11. 加固与交付（P10）

- [ ] 11.1 收敛暴露面：仅 `api` 与 `web` 在内网可达，验证其余端口从其他主机不可访问（Compose 静态校验通过；真实多主机访问验证未做）
- [x] 11.2 校验只读挂载：在 worker 内对 `/workspace` 写入必须失败（Docker 只读挂载写入失败实测通过）
- [ ] 11.3 配置各单元内存上限，验证 8 核 16G 下全栈稳定运行且无 OOM（内存上限静态校验通过；长期稳定运行与 OOM 压测未做）
- [x] 11.4 完成数据库备份与恢复演练，验证可从备份重建并查询到历史报告（临时数据库备份恢复演练通过）
- [x] 11.5 执行端到端验收：登录 → 提问带引用 → 手动触发日清 → 报告入库 → 沉淀生成（本地 E2E 通过；另完成真实 Ark 工具调用与 SSE 冒烟）
