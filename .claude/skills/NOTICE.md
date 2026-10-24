# 项目内置技能来源说明

本目录中的以下技能复制自 **obra/superpowers**（MIT License，Copyright © 2025 Jesse Vincent），仅做了落地到本仓库的整理，未修改工作流内容：

| 技能 | 用途 |
|---|---|
| `test-driven-development` | 先写测试再实现，红/绿循环 |
| `systematic-debugging` | 先定位根因再修复，禁止症状式补丁 |
| `verification-before-completion` | 声称完成前必须提供验证证据 |
| `requesting-code-review` | 提交前请求独立评审 |

其余技能（`openspec-*`）由 `openspec init` 生成，不属于上述来源。

## 为什么复制而不是只装全局

仓库自带技能可以保证：克隆即用、CI 与本地行为一致、多人维护时流程不走样。代价是**不会自动跟随上游更新**。

## 更新方式

```bash
# 上游：https://github.com/obra/superpowers
rm -rf .claude/skills/<name>
cp -R ~/.claude/skills/omc-learned/<name> .claude/skills/<name>
git diff --stat .claude/skills/<name>
```

更新前先确认上游 LICENSE 未变更。若需修改某个技能以适配本项目，请在对应目录内新增 `PROJECT-NOTES.md` 说明改了什么，避免下次覆盖时丢失。
