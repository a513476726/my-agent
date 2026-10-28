# Web 管理后台

Vue 3 + Vite + Ant Design Vue，负责项目、文档、报告与运营入口。接口契约来自 `packages/shared-types`，页面不直接拼后端路径。

## 本地开发

```bash
pnpm install
pnpm --filter @my-agent/web dev
```

开发服务器默认监听 `127.0.0.1:5173`，并把 `/api`、`/auth`、`/admin`、`/health` 代理到 `http://127.0.0.1:8000`。需要指向其他 API 时设置：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 pnpm --filter @my-agent/web dev
```

## 校验

```bash
pnpm --filter @my-agent/web lint
pnpm --filter @my-agent/web build
```

`lint` 与 `build` 都会执行 `vue-tsc --noEmit`；构建产物写入 `dist/`，不作为事实来源提交。

## 目录约定

- `src/modules/`：按业务功能组织的页面与组件。
- `src/api/`：仅保留新平台的请求封装，类型优先引用生成客户端。
- `src/components/`：`ProTable`、`DetailView`、`ProUpload` 等通用组件。
- `src/stores/`：鉴权与标签页状态。

所有请求通过 `src/utils/request.ts` 的统一客户端发出，鉴权失败会清理本地会话并跳转登录。
