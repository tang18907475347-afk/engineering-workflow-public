# 来源采集（按需）
采集层只是获取「需求文本 / 设计证据」的一种途径：用户已直接给出原文、截图或节点说明时，跳过采集、直接进 [资料阅读](source-reading.md)，不为走流程重采。

在目标项目的 git worktree 内调用；脚本路径以本 Skill 的安装位置为准。尖括号须替换为真实参数，方括号表示可选项（执行时去掉括号或整个选项），含空格的路径须加引号。

**PRD / 需求文档采集不随本副本提供**：原实现依赖专有的文档桥接客户端，已移除。按同样的落位契约自己接一个采集入口即可——输出 `<out>/<slug>.md`（frontmatter：`source_url` / `title` / `node_id` / `fetched_at` / `content_hash`）+ 原文正文，资源清单放 `assets/<slug>/manifest.json`，历史版本与远端哈希记在 `<out>/manifest.json`；`--main` 只标记 `sources/prd/manifest.json` 的 primary 文档、不复制正文。

```text
# PRD / 需求文档（占位：本副本不含该脚本，按上面的落位契约自备）
<文档采集入口> <url> --req <需求slug> [--main]

# 设计稿（随副本提供；默认 auto：先试本地 MCP，不可达且有 token 转 REST）
python3 <本 Skill 所在目录>/scripts/fetch_figma_design.py "<figma-url?node-id=..>" --req <需求slug> [--transport auto|mcp|rest] [--figma-token "$FIGMA_TOKEN"]
```

采集是确定性动作：环境不可用（采集入口缺失/鉴权失败、MCP 不可达且无 token、token 401/403、非 git worktree）一律 `[BLOCKED]` 停下、只读诊断并报用户，不自动安装/登录/启动 Figma/猜 token。分流见 [environment-boundary.md](environment-boundary.md)。
