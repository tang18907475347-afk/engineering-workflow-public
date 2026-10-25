#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MR / 评审评论平台后端（占位实现）。

本副本不内置任何专有平台的客户端。`review.py` 的所有远程动作都经由本模块的
`run_tool(name, payload, retry=...)`；接入你自己的平台时，只需要替换这一个函数。

## 契约

`run_tool(name, payload, retry=True) -> dict | list`

- `name`：工具名，见下表。
- `payload`：dict。`retry=False` 表示调用方要求不重试（写操作），后端必须尊重。
- 返回：平台响应解析后的 Python 值；无法解析时抛 `PlatformError`。
- 读操作失败可以重试（限流、超时）；写操作**绝不**自动重试——宁可人工重试，
  不可静默双写一条评论。

|name|payload|返回|
|---|---|---|
|`list_merge_request_ai_comments`|`{repo, mergeRequestId}`|评论数组（字段见 references/feedback.md）|
|`get_merge_request_detail`|`{repo, mergeRequestId}`|MR 详情对象|
|`list_merge_request_changed_files`|`{repo, mergeRequestId}`|变更文件数组|
|`operate_ai_comment`|见 references/feedback.md 的 action / reason code|操作结果|
|`comment_merge_request`|`{repo, mergeRequestId, body, ...}`|新建评论结果|

## 接入示例（GitLab REST）

把下面三行换成一个真正的 HTTP 客户端即可，其余逻辑（解析、指纹、决策信封、
HTML 生成、信封校验）全部与平台无关，不需要改动：

```python
TOKEN = os.environ["GITLAB_TOKEN"]
HOST = os.environ.get("GITLAB_HOST", "gitlab.com")
# GET /api/v4/projects/{quote(repo)}/merge_requests/{id}/discussions
```
"""
from __future__ import annotations


class PlatformError(RuntimeError):
    """平台调用失败或响应无法解析。"""


def run_tool(name: str, payload: dict, retry: bool = True):
    """占位实现：未接入平台时直接失败，且失败模式明确不含糊。"""
    raise PlatformError(
        f"未配置平台后端：{name} 需要 MR/评论平台客户端。"
        f"实现 scripts/mr_backend.py 的 run_tool() 后重试；"
        f"离线子命令（artifact / patch / check-envelope）不受影响。"
    )
