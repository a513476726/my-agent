# 部署与运维

## 默认暴露面

`deploy/compose/docker-compose.yml` 默认只发布两个端口：

- `api`: `${API_PORT:-8000}`
- `web`: `${WEB_PORT:-8080}`

`postgres`、`knowledge`、`worker` 只在 Compose 内部网络可达。RAGFlow 使用独立 Compose，仍只绑定回环地址。`api` 与 `worker` 都以只读方式挂载 `${WORKSPACE_HOST_PATH:-../../workspace}` 到 `/workspace`，被分析仓库不可被容器写入。相对路径以 `deploy/compose/` 为基准，建议在生产环境使用绝对路径。

## 启动

1. 将 `.env.example` 复制为 `.env`，设置数据库密码、`AUTH_SECRET`、管理员密码与火山方舟密钥。
2. 把待分析仓库放在 `WORKSPACE_HOST_PATH` 下，并在平台中登记容器内路径（例如 `/workspace/repo-a`）。
3. 启动：

   ```bash
   make up
   ```

4. 管理后台访问 `http://<内网地址>:8080`，API 文档在非生产环境通过 API 端口访问。

## 备份与恢复

```bash
make backup
ALLOW_RESTORE=1 make restore BACKUP=data/backups/myagent-YYYYmmdd-HHMMSS.dump
```

备份文件落在 `data/backups/`，该目录被 `.gitignore` 排除。恢复会覆盖当前数据库，因此脚本要求显式设置 `ALLOW_RESTORE=1`。

## 只读验证

```bash
make verify-readonly
make verify-deploy
```

`verify-readonly` 尝试在只读挂载中创建文件，并验证 Docker 返回失败。`verify-deploy` 解析主栈与 RAGFlow Compose，检查只有 API/Web 对外发布、其余端口仅限于回环、workspace 为只读，以及全部 `mem_limit` 合计不超过 16 GiB。

## 资源上限

默认内存上限：PostgreSQL 2G、API 1G、worker 1G、knowledge 512M、web 128M。RAGFlow 独立编排默认 4G，其余组件按其 Compose 中的 `mem_limit` 生效。可通过对应 `*_MEM_LIMIT` 环境变量调整。
