# LibreChat 接入

LibreChat 通过 OpenAI 兼容端点接入本平台，不在本仓库内改写其业务代码。平台侧仍是唯一的会话、工具调用与引用事实来源。

## 配置步骤

1. 在平台根目录 `.env` 设置 `OPENAI_API_KEY`，作为 LibreChat 访问本平台的长期令牌。
2. 启动 API 后生成按项目预设的配置。API 运行在宿主机时使用：

   ```bash
   uv run python deploy/librechat/render_config.py \
     --database-url "$DATABASE_URL" \
     --base-url "http://host.docker.internal:8000/v1" \
     --model "$AGENT_MODEL"
   ```

   如果 LibreChat 与 `api` 位于同一 Docker 网络，则把 `--base-url` 改为 `http://api:8000/v1`。
3. 复制 LibreChat 环境变量并生成密钥：

   ```bash
   cp deploy/librechat/.env.example deploy/librechat/.env
   openssl rand -hex 32  # LIBRECHAT_CREDS_KEY
   openssl rand -hex 16  # LIBRECHAT_CREDS_IV
   openssl rand -hex 32  # LIBRECHAT_JWT_SECRET
   openssl rand -hex 32  # LIBRECHAT_JWT_REFRESH_SECRET
   ```

   `MY_AGENT_API_KEY` 必须与平台 `OPENAI_API_KEY` 相同。首次注册账号时把 `LIBRECHAT_ALLOW_REGISTRATION` 临时设为 `true`，创建账号后改回 `false` 并重新执行启动命令使环境变量生效。
4. 启动：

   ```bash
   docker compose --env-file deploy/librechat/.env \
     -f deploy/librechat/docker-compose.yml up -d
   ```

   默认只绑定 `127.0.0.1:3080`，不会额外暴露到其他主机。若需要内网访问，显式修改 `LIBRECHAT_PORT` 或在前置反向代理后发布。

生成器为每个启用项目写入一个独立端点，并通过 `X-Project-Id` 固定项目上下文。用户在 LibreChat 中选择「项目名 · 项目助理」时，工具、检索与代码访问都只能作用于该项目。

## 引用展示

平台在非流式响应的 `citations` 字段和流式结束时返回引用数组；同时把「参考来源」追加到回答正文，因此即使客户端忽略扩展字段，用户仍能看到文档标题与章节路径。工具失败也会以「工具调用失败」段落显式展示。

## 配置更新

项目新增、改名或停用后重新执行 `render_config.py` 并重启 LibreChat：

```bash
docker compose --env-file deploy/librechat/.env \
  -f deploy/librechat/docker-compose.yml restart librechat
```
