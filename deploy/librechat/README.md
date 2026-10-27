# LibreChat 接入

LibreChat 通过 OpenAI 兼容端点接入本平台，不在本仓库内改写其业务代码。

## 配置步骤

1. 在根目录 `.env` 设置 `OPENAI_API_KEY`，作为 LibreChat 访问本平台的长期令牌；不要把该值写入 `librechat.yaml`。
2. 启动 API 后生成按项目预设的配置：

   ```bash
   uv run python deploy/librechat/render_config.py \
     --database-url "$DATABASE_URL" \
     --base-url "http://api:8000/v1" \
     --model "$AGENT_MODEL"
   ```

3. 将生成的 `deploy/librechat/librechat.yaml` 挂载到 LibreChat 容器的 `/app/librechat.yaml`，并在 LibreChat 的 `.env` 中设置：

   ```dotenv
   CONFIG_PATH=/app/librechat.yaml
   MY_AGENT_API_KEY=<与平台 OPENAI_API_KEY 相同>
   ```

生成器为每个启用项目写入一个独立端点，并通过 `X-Project-Id` 固定项目上下文。用户在 LibreChat 中选择「项目名 · 项目助理」时，工具、检索与代码访问都只能作用于该项目。

## 引用展示

平台在非流式响应的 `citations` 字段和流式结束时返回引用数组；同时把「参考来源」追加到回答正文，因此即使客户端忽略扩展字段，用户仍能看到文档标题与章节路径。工具失败也会以「工具调用失败」段落显式展示。
