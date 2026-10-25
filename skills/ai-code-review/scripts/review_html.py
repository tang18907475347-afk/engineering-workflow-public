#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 review.json 渲染为自包含的 review.html。

Builder 只做确定性的结构校验与渲染；不调用 LLM，不改写分析结论。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import review_contract

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "review.html"


class BuildError(RuntimeError):
    """artifact 不完整或模板不可用。"""


def safe_json_for_script(data: dict) -> str:
    """嵌入 <script type="application/json"> 时避免 </script> 与 HTML 实体。"""
    text = json.dumps(data, ensure_ascii=False)
    return (text.replace("<", "\\u003c")
                .replace(">", "\\u003e")
                .replace("&", "\\u0026"))


def build_html(artifact_path: str | Path, out_path: str | Path | None = None,
               template_path: str | Path | None = None) -> tuple[Path, dict]:
    artifact_path = Path(artifact_path)
    if not artifact_path.is_file():
        raise BuildError(f"找不到 artifact：{artifact_path}")
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BuildError(f"artifact 不是合法 JSON：{exc}") from exc
    if not isinstance(artifact, dict):
        raise BuildError("artifact 必须是 JSON 对象")
    errors = review_contract.validate_review_artifact(
        artifact, require_analysis=True)
    if errors:
        raise BuildError("artifact 校验失败：\n" + "\n".join(
            f"- {error}" for error in errors))

    template = Path(template_path or DEFAULT_TEMPLATE)
    if not template.is_file():
        raise BuildError(f"找不到 HTML 模板：{template}")
    html = template.read_text(encoding="utf-8")
    if "__REVIEW_JSON__" not in html:
        raise BuildError("HTML 模板缺少 __REVIEW_JSON__ 占位符")
    html = html.replace("__REVIEW_JSON__", safe_json_for_script(artifact))

    out = Path(out_path) if out_path else artifact_path.with_name("review.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out, artifact


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成 review.html 决策界面")
    parser.add_argument("--artifact", required=True, help="review.json 路径")
    parser.add_argument("--out", help="输出 HTML；默认与 artifact 同目录")
    parser.add_argument("--template", help="自定义 HTML 模板")
    args = parser.parse_args(argv)
    try:
        out, artifact = build_html(args.artifact, args.out, args.template)
    except (BuildError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"html={out}")
    print(f"reviewKey={artifact['reviewKey']}")
    print(f"findings={len(artifact['findings'])}")
    if artifact.get("headMatches") is False:
        print("WARN: headMatches=false；HTML 只提示，不阻断；执行前必须核对"
              " finding 的代码与证据是否仍适用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
