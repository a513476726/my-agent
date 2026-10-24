# Spec Delta

## Purpose

为平台的日常运营提供统一入口，覆盖项目与文档管理、知识库同步、报告阅读、能力沉淀维护、任务编排与操作审计。

## ADDED Requirements

### Requirement: 登录鉴权

管理后台 MUST 要求登录后才能访问任何管理功能。未通过鉴权的请求 SHALL 被拒绝并重定向到登录入口。

#### Scenario: 未登录访问
- **WHEN** 未携带有效凭证访问管理页面或接口
- **THEN** 系统拒绝访问并跳转登录

#### Scenario: 登录成功
- **WHEN** 用户提交正确的账号与密码
- **THEN** 系统建立会话并进入工作台

### Requirement: 数据管理

管理后台 SHALL 支持对项目、文档、知识库、报告、沉淀条目与任务的创建、查看、修改与删除。

#### Scenario: 编辑项目
- **WHEN** 管理员修改项目名称或启用状态
- **THEN** 系统保存修改并在列表中反映

#### Scenario: 删除沉淀条目
- **WHEN** 管理员删除某条沉淀记录
- **THEN** 该条目从列表与检索中移除，且操作被审计记录

### Requirement: 任务管理与手动触发

管理后台 SHALL 展示任务列表与运行历史，并 MUST 支持手动触发任务。

#### Scenario: 查看运行记录
- **WHEN** 管理员打开某任务的运行历史
- **THEN** 系统展示每次运行的开始时间、状态、耗时与错误信息

#### Scenario: 手动触发
- **WHEN** 管理员点击手动触发
- **THEN** 系统立即创建一次运行并在历史中可见

### Requirement: 报告阅读

管理后台 SHALL 支持阅读报告正文与条目，并 MUST 支持按项目与周期筛选。

#### Scenario: 按周期筛选
- **WHEN** 用户选择项目与日期区间
- **THEN** 系统只返回区间内的报告

### Requirement: 操作审计

所有写操作 MUST 记录审计日志，至少包含操作者、动作、目标资源与时间。

#### Scenario: 审计可查
- **WHEN** 管理员查询审计日志
- **THEN** 系统按时间倒序返回记录，并可定位到具体资源

### Requirement: 角色区分

管理后台 SHALL 至少区分只读角色与管理员角色。只读角色 MUST 无法执行写操作。

#### Scenario: 只读角色被拒绝写入
- **WHEN** 只读角色尝试提交写操作
- **THEN** 系统拒绝并返回权限不足

### Requirement: 接口契约一致

管理后台所依赖的列表接口 MUST 返回 `{records, total}` 结构，所有接口响应 MUST 使用 `{code, data, message, success}` 信封。

#### Scenario: 列表分页
- **WHEN** 前端请求任一列表且指定页码
- **THEN** 响应包含当前页记录与总数

#### Scenario: 业务错误表达
- **WHEN** 请求处理失败
- **THEN** 响应信封中 `code` 非零，且 `message` 给出可读原因
