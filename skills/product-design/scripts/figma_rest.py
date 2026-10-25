#!/usr/bin/env python3
"""Figma REST API 兜底通道：无桌面端 MCP 时，用 personal access token 拉指定节点的
outline + screenshot，归一化成与本地 MCP 完全同形的产物（复用 fetch_figma_design 的写入 helper）。

纯 Python 3 标准库。token 走 --figma-token 或 env FIGMA_TOKEN，绝不硬编码/打日志/写产物。
v1 范围：按显式 node-id（或含 node-id 的 URL）抓指定单元；选区模式、canvas 页面级自动拆分、
overlays、collect-assets 仍以 MCP 为主，REST 侧为 phase-2。
"""
import base64
import concurrent.futures
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_figma_design import (  # noqa: E402
    EnvironmentBlocked,
    asset_hashes,
    canonical_file_key,
    canonical_node_id,
    file_key_from_url,
    node_dir_for,
    node_id_from_url,
    save_node_asset,
)

REST_BASE = "https://api.figma.com"
# REST node type → MCP outline 标签的已知映射；未列出的回退通用标签
TYPE_TAG = {
    "DOCUMENT": "document", "CANVAS": "canvas", "FRAME": "frame", "GROUP": "group",
    "SECTION": "section", "COMPONENT": "component", "COMPONENT_SET": "component",
    "INSTANCE": "instance", "TEXT": "text", "VECTOR": "vector", "RECTANGLE": "rect",
    "ELLIPSE": "ellipse", "LINE": "line", "BOOLEAN_OPERATION": "boolean",
}
FALLBACK_TAG = "node"


def _get(url, token, timeout=60):
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise EnvironmentBlocked(f"Figma REST 鉴权失败（HTTP {exc.code}）：检查 FIGMA_TOKEN") from None
        if exc.code == 429:
            raise EnvironmentBlocked("Figma REST 限流（HTTP 429）：稍后重试，不循环重试") from None
        if exc.code == 404:
            raise ValueError(f"HTTP 404 文件/节点不存在：{url}") from None
        raise EnvironmentBlocked(f"Figma REST HTTP {exc.code}：{url}") from None
    except (urllib.error.URLError, OSError) as exc:
        raise EnvironmentBlocked(f"Figma REST 网络不可达：{exc}") from None
    except json.JSONDecodeError as exc:
        raise EnvironmentBlocked(f"Figma REST 响应非 JSON：{exc}") from None


def _download_bytes(url, timeout=60):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError) as exc:
        raise EnvironmentBlocked(f"Figma 截图下载失败：{exc}") from None


def json_to_element(node):
    """REST 节点 JSON → 与 MCP get_metadata 同形的 XML Element（递归）。

    tag = 已知类型映射（未识别回退 'node'）；保留 name 与 boundingBox 的 id/x/y/width/height
    （供 save_node_asset→sanitize_outline 落盘时去除噪音；overlays 为 phase-2）。
    """
    ntype = str(node.get("type") or "").upper()
    el = ET.Element(TYPE_TAG.get(ntype, FALLBACK_TAG))
    if isinstance(node.get("name"), str):
        el.set("name", node["name"])
    if isinstance(node.get("id"), str):
        el.set("id", node["id"])
    bb = node.get("absoluteBoundingBox") or node.get("boundingBox") or {}
    if isinstance(bb, dict):
        for k in ("x", "y", "width", "height"):
            if isinstance(bb.get(k), (int, float)):
                el.set(k, str(bb[k]))
    for child in node.get("children") or []:
        if isinstance(child, dict):
            el.append(json_to_element(child))
    return el


def _shot_result(png_bytes):
    return {"content": [{"type": "image",
                         "data": base64.b64encode(png_bytes).decode("ascii"),
                         "mimeType": "image/png"}]}


def fetch_nodes(file_key, node_ids, token, out_root, scale=2, concurrency=4):
    """按 node-id 列表经 REST 拉 outline+截图，落与 MCP 同形产物；返回 (entries, failures)。"""
    file_key = canonical_file_key(file_key)
    node_ids = [canonical_node_id(n) for n in dict.fromkeys(node_ids)]
    q = urllib.parse.quote(",".join(node_ids), safe=":,")
    nodes_url = f"{REST_BASE}/v1/files/{file_key}/nodes?ids={q}"
    images_url = f"{REST_BASE}/v1/images/{file_key}?ids={q}&format=png&scale={scale}"
    try:
        nodes_resp = _get(nodes_url, token)
        images_resp = _get(images_url, token)
    except EnvironmentBlocked as exc:
        return [], [f"[BLOCKED] {file_key}: {exc}"]
    except ValueError as exc:
        return [], [f"[FAIL] {file_key}: {exc}"]
    images = (images_resp or {}).get("images") or {}
    doc_nodes = (nodes_resp or {}).get("nodes") or {}
    out_root = Path(out_root)

    def one(nid):
        wrapper = doc_nodes.get(nid) or {}
        node = wrapper.get("document") if isinstance(wrapper, dict) else None
        if not isinstance(node, dict):
            return None, f"[FAIL] {file_key}/{nid}: REST 未返回该节点 document"
        img_url = images.get(nid)
        if not isinstance(img_url, str) or not img_url:
            return None, f"[FAIL] {file_key}/{nid}: REST 未返回截图 URL"
        try:
            png = _download_bytes(img_url)
            root = json_to_element(node)
            slug = nid.replace(":", "-")
            node_dir = node_dir_for(out_root, file_key, slug)
            _, tools = save_node_asset(node_dir, root, _shot_result(png), require_screenshot=True)
            entry = {
                "node_id": nid, "slug": f"{file_key}/{slug}", "name": node.get("name"),
                "file_key": file_key,
                "source_url": f"https://www.figma.com/design/{file_key}?node-id={slug}",
                "tools": tools, **asset_hashes(node_dir),
            }
            return entry, None
        except EnvironmentBlocked as exc:
            return None, f"[BLOCKED] {file_key}/{nid}: {exc}"
        except ValueError as exc:
            return None, f"[FAIL] {file_key}/{nid}: {exc}"

    entries, failures = [], []
    workers = max(1, min(concurrency, len(node_ids) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for entry, failure in pool.map(one, node_ids):
            if entry:
                entries.append(entry)
            if failure:
                failures.append(failure)
    entries.sort(key=lambda e: (e["file_key"], e["node_id"]))
    failures.sort()
    return entries, failures


def run_targets(targets, out_root, token, scale=2, concurrency=4):
    """消费 fetch_figma_design 的 targets=[(url, node_id, file_key_override), ...]；
    按 file_key 归并 node-id 后调 fetch_nodes。选区/缺 node-id → FAIL（REST 不支持选区）。"""
    if not token:
        return [], ["[BLOCKED] REST 需要 --figma-token 或 env FIGMA_TOKEN"]
    by_key, failures = {}, []
    for url, node_id, override in targets:
        file_key = override or file_key_from_url(url)
        if not file_key:
            failures.append(f"[FAIL] {url or node_id or '<selection>'}: 缺少 file_key（REST 需含 fileKey 的 URL 或 --file-key）")
            continue
        try:
            file_key = canonical_file_key(file_key)
        except ValueError as exc:
            failures.append(f"[FAIL] {url or node_id}: {exc}")
            continue
        nid = node_id or (node_id_from_url(url) if url else None)
        if not nid:
            failures.append(f"[FAIL] {url or '<selection>'}: REST 需显式 node-id（用含 node-id 的 URL 或 --node-id）；选区/页面级请改用 MCP")
            continue
        try:
            nid = canonical_node_id(nid)
        except ValueError as exc:
            failures.append(f"[FAIL] {url or node_id}: {exc}")
            continue
        by_key.setdefault(file_key, []).append(nid)
    entries = []
    for file_key, nids in sorted(by_key.items()):
        e, f = fetch_nodes(file_key, nids, token, out_root, scale, concurrency)
        entries.extend(e)
        failures.extend(f)
    return entries, failures
