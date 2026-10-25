#!/usr/bin/env python3
"""通过本地 Figma Dev Mode MCP server 获取设计稿数据（脚本直连，不经 IDE MCP 注册）。

前置条件：
1. Figma 桌面端已启动并打开目标文件（浏览器版不支持本地 MCP）。
2. 已启用 Dev Mode MCP Server：菜单 Preferences → Enable Dev Mode MCP Server，
   本地端点默认 http://127.0.0.1:3845/mcp，无需认证。
3. 使用的 Figma 席位需要支持 Dev Mode MCP。
若本地 MCP 无法握手，脚本输出 `[BLOCKED]` 后停止，不自动启动、安装或改写 Figma 环境。

用法示例：
  # 列出当前服务器提供的工具及入参 schema（确认 MCP 已握手与可用能力范围）
  python fetch_figma_design.py --list-tools

  # 单个节点：从 Figma 链接提取 node-id，拉取节点大纲与截图
  python fetch_figma_design.py "https://www.figma.com/design/<file>/<name>?node-id=12-34" --req <req>

  # 多个设计稿并发拉取（位置参数或 --url 重复传入，互不覆盖）
  python fetch_figma_design.py "<url1>" "<url2>" "<url3>" --req <req> --concurrency 4

  # 在 Figma 中多选若干设计稿后运行（需显式提供 fileKey，支持多选批量）
  python fetch_figma_design.py --file-key <fileKey> --req <req>

输出固定写入 `.engineering/requirements/<req>/sources/design/`（`--req` 必填）；
`--out` 仅可显式指定同一目录。按 **fileKey / node-id 两级分目录**：
URL 会自动提取 fileKey；node-id 或当前选区模式必须显式传 `--file-key`，否则停止并报告输入错误。

  .engineering/requirements/<req>/sources/design/
  ├── manifest.json          ← 全局索引：fileKey/node-id → 名称/来源 URL/拉取时间/产物目录
  ├── <fileKey>/             ← Figma fileKey 层（跨文件资产不混层）
  │   └── <node-id>/         ← 设计稿单元：子树大纲 + 截图
  └── <另一 fileKey>/
      └── ...

**多 canvas 自动拆分**：metadata 响应中包含多个 canvas/frame 根结构时逐个资产化；
canvas（页面级 URL）只作为拆分入口：拉取大纲后**并发拆分**顶层设计稿单元
（frame/section/component/instance/symbol），每个单元获得独立资产（子树大纲 + 单元级
清晰截图）；页面级节点本身（全量大纲/全景拼贴图）无意义，不落盘、不进 manifest。
拆分时同步计算顶层单元间的覆盖关联（如全屏遮罩层）写入 manifest 的 overlays 字段。
--no-split 时页面节点按普通节点处理。text/vector/基础图形等素材不拆。
落盘大纲过滤 id/x/y/width/height 噪音属性（node-id 回源一律走 manifest 索引）。
超长 name 截断（MAX_NAME_LEN，默认 120 字符）：大纲仅作布局辅助参考不是绝对权威，
name 只承载文案预览，正文全文需回源或看截图。
重复拉取同一节点时覆盖更新该节点目录；manifest.json 始终保留全量索引。
资产分层哈希：outline_hash（大纲文本，确定性）与 screenshot_hash（截图字节）
分开写入 manifest；截图字节变化时自动保留一代旧图 get_screenshot.prev.png 供运行时 freshness
判断时视觉比对。
默认只拉节点大纲与截图；需要视觉规格/设计 token 时可 --tools 附加 get_design_context 等工具。
本地 Desktop MCP 绑定当前活动文件/选区；访问本地端点时脚本自动将并发降为单通道，并在 canvas 拆分中复用一次握手会话。
默认的 get_metadata 与 get_screenshot 都是必需输入：任一调用失败、返回 MCP isError、空响应或空图片，
该节点不会作为成功资产落盘；若本批次没有任何设计单元产出，命令以非零状态结束，避免空跑。
附加工具失败只产生显式警告，不伪装成已获取。
"""
import argparse
import base64
import binascii
import concurrent.futures
import copy
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worktree_paths import (  # noqa: E402
    WorktreePathError,
    current_worktree_root,
    ensure_inside,
    requirement_source_dir,
)

DEFAULT_ENDPOINT = "http://127.0.0.1:3845/mcp"
DEFAULT_TOOLS = ["get_metadata", "get_screenshot"]
DEFAULT_CONCURRENCY = 4
# canvas（页面）自动拆分时的设计稿单元类型；text/vector/基础图形等素材不拆
SPLIT_TAGS = {"frame", "section", "component", "instance", "symbol"}
XML_ROOT_TAGS = ("canvas", "frame", "section", "instance", "component", "symbol")


def is_local_mcp_endpoint(endpoint: str) -> bool:
    """本地 Figma Desktop MCP 绑定活动文档/选区，默认按单通道访问。"""
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"} and port == 3845


class EnvironmentBlocked(RuntimeError):
    """Figma MCP 不可用：交给用户恢复，不在拉取流程内自修。"""


class McpCallError(RuntimeError):
    """MCP 工具调用失败；保留工具、节点和失败类别，禁止静默降级为空结果。"""

    def __init__(self, endpoint: str, tool: str, node_id, message: str, *, category="tool"):
        self.endpoint = endpoint
        self.tool = tool
        self.node_id = node_id
        self.category = category
        subject = node_id or "<selection>"
        detail = re.sub(r"\s+", " ", str(message)).strip()
        if len(detail) > 400:
            detail = detail[:397] + "..."
        super().__init__(f"{tool}({subject}) at {endpoint}: {detail}")


MCP_ENV_ERRORS = (urllib.error.URLError, ConnectionError, OSError, RuntimeError, ValueError)


class McpClient:
    """极简 MCP Streamable HTTP 客户端（JSON-RPC 2.0，纯标准库）。
    非线程安全：并发场景下每个 worker 使用独立实例（各自握手建立会话）。"""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.session_id = None
        self._next_id = 1

    def _post(self, payload: dict):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self.session_id = sid
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8", "replace")
        if "text/event-stream" in ctype:
            return self._last_sse_result(raw)
        if not raw.strip():
            return None
        return json.loads(raw)

    @staticmethod
    def _last_sse_result(raw: str):
        """解析 SSE 流，返回最后一个含 JSON-RPC result/error 的 event。

        只按 \\n 切行（SSE 规范行边界），不用 str.splitlines()：
        Figma XML 文本里可能携带 U+2028 等字符，splitlines 会把它们当行边界，
        把超长单行 JSON（页面级大纲可达数百 KB）切断导致解析失败。
        同一 event 的多个 data: 行按规范用 \\n 拼接。
        """
        result = None
        blocks = []
        current = []
        for line in raw.split("\n"):
            line = line.rstrip("\r")
            if line.startswith("data:"):
                current.append(line[len("data:"):])
            else:
                if current:
                    blocks.append(current)
                    current = []
        if current:
            blocks.append(current)
        for block in blocks:
            try:
                obj = json.loads("\n".join(block))
            except json.JSONDecodeError:
                continue
            if "result" in obj or "error" in obj:
                result = obj
        if result is None:
            raise RuntimeError("SSE stream contains no JSON-RPC result")
        return result

    def request(self, method: str, params=None):
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        self._next_id += 1
        if params is not None:
            payload["params"] = params
        resp = self._post(payload)
        if resp is None:
            raise RuntimeError(f"no response for {method}")
        if not isinstance(resp, dict):
            raise RuntimeError(f"{method} returned a non-object response")
        if "error" in resp:
            err = resp["error"]
            if not isinstance(err, dict):
                raise RuntimeError(f"{method} failed: malformed error response")
            raise RuntimeError(f"{method} failed: {err.get('message')} (code {err.get('code')})")
        return resp.get("result")

    def notify(self, method: str):
        self._post({"jsonrpc": "2.0", "method": method})

    def initialize(self):
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "product-engineering", "version": "0.2.0"},
            },
        )
        self.notify("notifications/initialized")


def connect_client(client: McpClient):
    """把握手/协议异常统一标成环境阻断，供主流程和并发 worker 分流。"""
    try:
        client.initialize()
    except MCP_ENV_ERRORS as exc:
        raise EnvironmentBlocked(
            f"cannot connect to {client.endpoint}: {exc}"
        ) from None


def list_tools(client: McpClient):
    """tools/list 失败同样属于 MCP 环境阻断，不返回半成品工具表。"""
    try:
        result = client.request("tools/list") or {}
    except MCP_ENV_ERRORS as exc:
        raise EnvironmentBlocked(
            f"tools/list failed at {client.endpoint}: {exc}"
        ) from None
    if not isinstance(result, dict):
        raise EnvironmentBlocked(f"tools/list failed at {client.endpoint}: non-object response")
    tools = result.get("tools") or []
    if not isinstance(tools, list):
        raise EnvironmentBlocked(f"tools/list failed at {client.endpoint}: tools 不是列表")
    return [tool for tool in tools if isinstance(tool, dict) and isinstance(tool.get("name"), str)]


def node_id_from_url(url: str):
    match = re.search(r"[?&]node-id=([0-9A-Za-z_-]+)", url)
    if not match:
        return None
    # Figma URL 用 12-34，工具入参一般用 12:34
    return match.group(1).replace("-", ":")


def file_key_from_url(url: str):
    match = re.search(r"/(?:design|board|slides|proto)/([0-9A-Za-z_-]+)", url or "")
    return match.group(1) if match else None


def canonical_file_key(file_key: str) -> str:
    """返回可安全作为目录名的 Figma fileKey。"""
    value = str(file_key or "")
    if not re.fullmatch(r"[0-9A-Za-z_-]+", value):
        raise ValueError(f"fileKey 不是规范的单层标识：{file_key!r}")
    return value


def canonical_node_id(node_id: str) -> str:
    """返回 manifest 使用的冒号 node-id；拒绝无法形成稳定坐标的值。"""
    value = str(node_id or "")
    if not re.fullmatch(r"\d+(?:[-:]\d+)", value):
        raise ValueError(f"node-id 不是规范的数字坐标：{node_id!r}")
    return value.replace("-", ":")


def tool_accepts(tool, key: str) -> bool:
    if not isinstance(tool, dict):
        return False
    schema = tool.get("inputSchema") or {}
    if not isinstance(schema, dict):
        return False
    props = schema.get("properties") or {}
    if not isinstance(props, dict):
        return False
    return key in props


def tool_accepts_node_id(tool) -> bool:
    return any(tool_accepts(tool, k) for k in ("nodeId", "node_id", "nodeID", "node-id"))


# 客户端栈提示（main 从 CLI 填）：call_tool 按工具 schema 透传给接受这些字段的工具
# （如 get_design_context / get_variable_defs 的 clientLanguages / clientFrameworks）
_CLIENT_HINTS: dict = {}


def selected_nodes_from_result(result):
    """解析 get_metadata 响应中 "Currently selected nodes" 列出的全部节点（支持多选）。"""
    nodes = []
    if not isinstance(result, dict):
        return nodes
    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text", "")
        if not isinstance(text, str):
            continue
        for match in re.finditer(r"^\s*-\s*(\d+:\d+)\s*:\s*(.+?)\s*$", text, re.MULTILINE):
            nodes.append((match.group(1), match.group(2)))
    return nodes


def extract_root_elements(result):
    """提取 metadata 响应中的全部顶层 XML 根元素。

    单个响应可能包含多个 canvas/frame 根结构（多选选区、跨页面节点等场景），
    按行首（第 0 列）的开标签切分顶层块，逐块解析。
    """
    roots = []
    if not isinstance(result, dict):
        return roots
    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text", "")
        if not isinstance(text, str):
            continue
        lines = text.split("\n")
        blocks, current = [], None
        for line in lines:
            if re.match(r"<[a-zA-Z]", line):
                if current:
                    blocks.append(current)
                current = [line]
            elif current is not None:
                current.append(line)
        if current:
            blocks.append(current)
        for block in blocks:
            xml_text = "\n".join(block).strip()
            if not xml_text:
                continue
            try:
                roots.append(safe_fromstring(xml_text))
            except ET.ParseError:
                continue
    return roots


def safe_fromstring(xml_text: str):
    """硬化版 ET.fromstring：拒绝 DTD/ENTITY 声明（防实体展开/XXE；数据源为本地 Figma，仍做防御）。"""
    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise ET.ParseError("DTD/ENTITY declarations are not allowed")
    return ET.fromstring(xml_text)


def element_to_xml(el) -> str:
    """序列化 Element 为带缩进的 XML 文本。"""
    try:
        ET.indent(el)
    except AttributeError:  # Python < 3.9
        pass
    return ET.tostring(el, encoding="unicode")


def save_result(result, out_dir: Path, tool_name: str):
    files = []
    if not isinstance(result, dict):
        return files
    def output(path: Path) -> Path:
        return ensure_inside(path, out_dir, "Figma asset output")

    contents = result.get("content") or []
    if not isinstance(contents, list):
        return files
    # 同一工具的多个 text 块合并写入一个文件（后端可能返回提示文本 + 正文多个块）
    texts = [item.get("text", "") for item in contents
             if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text", ""), str)]
    if texts:
        joined = "\n".join(texts)
        try:
            parsed = json.loads(joined)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            # JSON 文本（get_variable_defs 等）→ .json 格式化落盘，不套 md 壳
            path = output(out_dir / f"{tool_name}.json")
            path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(path)
        elif tool_name == "get_design_context" and re.search(r"^SUPER CRITICAL:", joined, re.M):
            # React 代码体 与 尾部转换提示（SUPER CRITICAL 段）拆分落盘
            m = re.search(r"^SUPER CRITICAL:", joined, re.M)
            code = joined[: m.start()].rstrip() + "\n"
            code_path = output(out_dir / f"{tool_name}.tsx")
            prompt_path = output(out_dir / f"{tool_name}_prompt.md")
            code_path.write_text(code, encoding="utf-8")
            prompt_path.write_text(joined[m.start():], encoding="utf-8")
            files += [code_path, prompt_path]
        else:
            path = output(out_dir / f"{tool_name}.md")
            path.write_text(joined, encoding="utf-8")
            files.append(path)
    img_idx = 0
    for idx, item in enumerate(contents):
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "image":
            # get_design_context 响应附带的参考图与 get_screenshot 内容重复——不重复落盘，
            # 视觉真值单源 = get_screenshot.png
            if tool_name == "get_design_context":
                continue
            data = item.get("data", "")
            if not isinstance(data, str) or not data.strip():
                raise ValueError(f"{tool_name} 返回了空图片数据")
            ext = "png"
            mime = item.get("mimeType", "") if isinstance(item.get("mimeType", ""), str) else ""
            if "svg" in mime:
                ext = "svg"
            path = output(out_dir / f"{tool_name}.{ext}" if img_idx == 0 else out_dir / f"{tool_name}-{img_idx}.{ext}")
            try:
                data_bytes = base64.b64decode(data)
            except (binascii.Error, TypeError, ValueError) as exc:
                raise ValueError(f"{tool_name} 返回了无法解码的图片数据：{exc}") from None
            if path.exists():
                old_bytes = path.read_bytes()
                if (old_bytes != data_bytes and tool_name == "get_screenshot"
                        and img_idx == 0 and ext == "png"):
                    # 截图字节变化：保留一代旧图，供运行时 freshness 判断时视觉比对
                    output(out_dir / "get_screenshot.prev.png").write_bytes(old_bytes)
            path.write_bytes(data_bytes)
            files.append(path)
            img_idx += 1
        elif kind not in ("text", "image"):
            path = output(out_dir / f"{tool_name}-{idx}.json")
            path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(path)
    if not files and result.get("structuredContent"):
        path = output(out_dir / f"{tool_name}.json")
        path.write_text(json.dumps(result["structuredContent"], ensure_ascii=False, indent=2), encoding="utf-8")
        files.append(path)
    return files


def _has_valid_image_payload(result) -> bool:
    """在写盘前确认截图响应至少包含可解码的非空图片。"""
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        return False
    for item in result["content"]:
        if not isinstance(item, dict) or item.get("type") != "image":
            continue
        data = item.get("data")
        if not isinstance(data, str) or not data.strip():
            continue
        try:
            if base64.b64decode(data):
                return True
        except (binascii.Error, TypeError, ValueError):
            continue
    return False


def _mcp_error_category(message: str) -> str:
    """把工具错误粗分为输入错误或运行阻断；不把业务错误伪装成成功。"""
    text = str(message).lower()
    if any(token in text for token in (
        "invalid params", "invalid parameter", "invalid node", "unknown node",
        "node not found", "node is not found", "malformed url", "bad request", "code -32602",
    )):
        return "input"
    return "tool"


def _tool_error_text(result) -> str:
    """提取 MCP isError 的短诊断文本；只保留错误摘要，不写入原始响应。"""
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            texts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            if texts:
                return " ".join(texts)
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            for key in ("message", "error", "detail"):
                if isinstance(structured.get(key), str):
                    return structured[key]
    return "MCP tool returned isError"


def call_tool(client, available, name, node_id, *, required=False):
    """按 node-id 调用工具；必需工具失败必须显式抛错，不能退化成空资产。"""
    if name not in available:
        if required:
            raise McpCallError(
                client.endpoint, name, node_id,
                "tool is not advertised by the MCP server", category="capability",
            )
        return None
    arguments = {}
    if node_id and tool_accepts_node_id(available[name]):
        arguments["nodeId"] = node_id
    for k, v in _CLIENT_HINTS.items():
        if v and tool_accepts(available[name], k):
            arguments[k] = v
    try:
        result = client.request("tools/call", {"name": name, "arguments": arguments})
    except MCP_ENV_ERRORS as exc:
        failure = McpCallError(
            client.endpoint, name, node_id, exc, category=_mcp_error_category(exc),
        )
        if required:
            raise failure from None
        print(f"[WARN] optional {failure}", file=sys.stderr)
        return None
    if not isinstance(result, dict):
        failure = McpCallError(
            client.endpoint, name, node_id,
            f"returned a non-object response ({type(result).__name__})",
            category="protocol",
        )
        if required:
            raise failure
        print(f"[WARN] optional {failure}", file=sys.stderr)
        return None
    if result.get("isError"):
        message = _tool_error_text(result)
        failure = McpCallError(
            client.endpoint, name, node_id, message,
            category=_mcp_error_category(message),
        )
        if required:
            raise failure
        print(f"[WARN] optional {failure}", file=sys.stderr)
        return None
    return result


# 落盘大纲过滤的噪音属性：id/坐标/尺寸保留在处理过程与 manifest 中，不进文件
DROPPED_OUTLINE_ATTRS = ("id", "x", "y", "width", "height")
# 大纲仅作布局参考，name 只是文案预览非全文；超长（如把 md/正文塞进 name 的节点）截断
MAX_NAME_LEN = 120


def sanitize_outline(el):
    """大纲降噪：递归移除噪音属性（id/坐标/尺寸）并截断超长 name（超出 MAX_NAME_LEN
    保留前缀 + '...'）。大纲只是布局辅助参考不是绝对权威，文本全文需回源或看截图。"""
    for e in el.iter():
        for attr in DROPPED_OUTLINE_ATTRS:
            if attr in e.attrib:
                del e.attrib[attr]
        name = e.get("name")
        if name is not None and len(name) > MAX_NAME_LEN:
            e.set("name", name[:MAX_NAME_LEN - 3] + "...")
    return el


def asset_hashes(node_dir: Path):
    """单元资产分层内容哈希：outline（确定性文本）与 screenshot 分开记录。

    哈希只报告资产字节变化，不判断结构 / 产品语义失效。
    运行时可比较 get_screenshot.prev.png 与新图及大纲，再决定是否更新下游。"""
    def h(name):
        p = node_dir / name
        return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None
    return {"outline_hash": h("get_metadata.md"), "screenshot_hash": h("get_screenshot.png")}


def save_node_asset(node_dir: Path, root, shot_result, *, require_screenshot=False):
    """保存单节点资产；要求截图时没有有效图片就拒绝提交节点。"""
    if require_screenshot:
        if shot_result is None:
            raise ValueError("get_screenshot 未返回结果；拒绝写入无视觉证据的节点")
        if not _has_valid_image_payload(shot_result):
            raise ValueError("get_screenshot 返回成功但没有可解码的图片内容；拒绝写入空视觉资产")
    node_dir = ensure_inside(node_dir, node_dir.parent.parent, "Figma node directory")
    node_dir.mkdir(parents=True, exist_ok=True)
    clean = sanitize_outline(copy.deepcopy(root))
    metadata_path = ensure_inside(node_dir / "get_metadata.md", node_dir, "Figma outline output")
    metadata_path.write_text(element_to_xml(clean) + "\n", encoding="utf-8")
    tools = ["get_metadata"]
    if shot_result is not None:
        files = save_result(shot_result, node_dir, "get_screenshot")
        screenshot_files = [
            path for path in files
            if path.suffix.lower() in {".png", ".svg"} and path.exists() and path.stat().st_size > 0
        ]
        if require_screenshot and not screenshot_files:
            raise ValueError("get_screenshot 返回成功但没有有效图片内容；拒绝写入空视觉资产")
        if screenshot_files:
            tools.append("get_screenshot")
    return node_dir, tools


def node_dir_for(out_root: Path, file_key, slug: str) -> Path:
    """资产目录 = out / fileKey / node-id；fileKey 缺失时拒绝写入。"""
    if not file_key:
        raise ValueError("Figma 资产写入需要 file_key；请提供包含 fileKey 的 URL 或 --file-key")
    canonical_file_key(file_key)
    if not slug or Path(slug).name != slug or slug in {".", ".."}:
        raise ValueError(f"node-id 不能作为安全目录名：{slug!r}")
    return ensure_inside(out_root / file_key / slug, out_root, "Figma node output")


def compute_overlays(units):
    """计算 canvas 顶层单元间的覆盖关联（如全屏遮罩层整层叠于另一单元之上）。
    判定：交叠面积占前者面积 ≥ 80% 时记为前者覆盖后者；无重叠不记录。"""
    overlays = {}

    def rect(el):
        try:
            return (float(el.get("x") or 0), float(el.get("y") or 0),
                    float(el.get("width") or 0), float(el.get("height") or 0))
        except (TypeError, ValueError):
            return (0.0, 0.0, 0.0, 0.0)

    for a in units:
        ax, ay, aw, ah = rect(a)
        if aw <= 0 or ah <= 0:
            continue
        for b in units:
            if a is b:
                continue
            bx, by, bw, bh = rect(b)
            if bw <= 0 or bh <= 0:
                continue
            ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
            iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
            if ix * iy / (aw * ah) >= 0.8:
                overlays.setdefault(a.get("id"), []).append(b.get("id"))
    return overlays


def process_canvas_units(root, endpoint, out_root, file_key, base_url, wanted, concurrency):
    """拆分 canvas 顶层设计稿单元；本地端点串行复用一个 MCP 会话。"""
    units = [c for c in root if c.tag in SPLIT_TAGS and c.get("id")]
    overlays = compute_overlays(units)
    print(f"  canvas split: '{root.get('name')}' -> {len(units)} design units (concurrency {min(concurrency, len(units) or 1)})")

    if not units:
        return [], [f"[FAIL] canvas {root.get('name') or '<unnamed>'}: 没有可拆分的设计单元"]

    def process_unit(child, client, available):
        try:
            cid = child.get("id")
            cslug = cid.replace(":", "-")
            cdir = node_dir_for(out_root, file_key, cslug)
            cshot = (
                call_tool(client, available, "get_screenshot", cid, required=True)
                if "get_screenshot" in wanted else None
            )
            _, ctools = save_node_asset(
                cdir, child, cshot, require_screenshot=("get_screenshot" in wanted)
            )
            curl = f"{base_url}?node-id={cslug}" if base_url else None
            return {
                "node_id": cid, "slug": f"{file_key}/{cslug}", "name": child.get("name"),
                "file_key": file_key, "source_url": curl, "tools": ctools,
                "overlays": overlays.get(cid), **asset_hashes(cdir),
            }
        except McpCallError as exc:
            prefix = "[FAIL]" if exc.category == "input" else "[BLOCKED]"
            return {"error": f"{prefix} unit {child.get('id')}: {exc}"}
        except EnvironmentBlocked as exc:
            return {"error": f"[BLOCKED] unit {child.get('id')}: {exc}"}
        except ValueError as exc:
            return {"error": f"[FAIL] unit {child.get('id')}: {exc}"}
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            return {"error": f"[BLOCKED] unit {child.get('id')}: {exc}"}

    def worker(child):
        try:
            client = McpClient(endpoint)
            connect_client(client)
            tools = list_tools(client)
            available = {t.get("name"): t for t in tools}
            return process_unit(child, client, available)
        except McpCallError as exc:
            prefix = "[FAIL]" if exc.category == "input" else "[BLOCKED]"
            return {"error": f"{prefix} unit {child.get('id')}: {exc}"}
        except EnvironmentBlocked as exc:
            return {"error": f"[BLOCKED] unit {child.get('id')}: {exc}"}
        except ValueError as exc:
            return {"error": f"[FAIL] unit {child.get('id')}: {exc}"}
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            return {"error": f"[BLOCKED] unit {child.get('id')}: {exc}"}

    entries, failures = [], []
    if concurrency <= 1:
        # Desktop MCP 的活动文件/选区是共享上下文；复用同一会话也避免每个单元重复握手。
        client = McpClient(endpoint)
        connect_client(client)
        available = {t.get("name"): t for t in list_tools(client)}
        results = [process_unit(child, client, available) for child in units]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(worker, units))
    for result in results:
        if "error" in result:
            failures.append(result["error"])
        else:
            entries.append(result)
            print(f"  - unit {result['slug']} '{result['name']}': {', '.join(result['tools'])}")
    return entries, failures


def process_target(target, endpoint, out_root, wanted, no_split, concurrency):
    """处理一个目标（URL / node-id / 选区）；返回 (manifest 条目列表, 失败信息列表)。

    条目字段：node_id/slug/name/file_key/source_url/tools，
    manifest 由主线程统一写入（避免并发写冲突）。
    """
    url, node_id, file_key_override = target
    file_key = file_key_override or file_key_from_url(url)
    if not file_key:
        return [], [f"[FAIL] {node_id or url or '<selection>'}: 缺少 file_key；请提供包含 fileKey 的 URL 或 --file-key"]
    file_key = canonical_file_key(file_key)
    if node_id is not None:
        node_id = canonical_node_id(node_id)
    client = McpClient(endpoint)
    connect_client(client)
    tools = list_tools(client)
    available = {t.get("name"): t for t in tools}
    base_url = url.split("?")[0] if url else None

    entries = []
    failures = []

    metadata_result = call_tool(client, available, "get_metadata", node_id, required=True)
    if metadata_result is None:
        failures.append(f"{node_id or url or '<selection>'}: get_metadata failed")
        return entries, failures

    # 选区模式：解析全部选中节点（支持多选批量）
    if node_id is None:
        selected = selected_nodes_from_result(metadata_result)
        if selected:
            node_id = selected[0][0]

    roots = extract_root_elements(metadata_result)
    if not roots:
        failures.append(f"{node_id or url or '<selection>'}: no parsable XML outline")
        return entries, failures

    # 单个响应包含多个 canvas/frame 根结构时逐个资产化（目录按 fileKey/node-id 两级）
    target_shot = None
    for root in roots:
        rid = root.get("id") or ""
        slug = rid.replace(":", "-") if rid else "selection"

        # canvas（页面级）仅作为拆分入口：并发拆单元，页面级资产不落盘不进 manifest
        if root.tag == "canvas":
            if no_split:
                if "get_screenshot" in wanted:
                    target_shot = call_tool(client, available, "get_screenshot", rid, required=True)
                node_dir, tools_done = save_node_asset(
                    node_dir_for(out_root, file_key, slug), root, target_shot,
                    require_screenshot=("get_screenshot" in wanted),
                )
                entries.append({
                    "node_id": rid or slug, "slug": f"{file_key}/{slug}", "name": root.get("name"),
                    "file_key": file_key, "source_url": url, "tools": tools_done,
                    **asset_hashes(node_dir),
                })
                print(f"- {slug} '{root.get('name')}': {', '.join(tools_done)} (no-split, kept as-is)")
            else:
                unit_entries, unit_failures = process_canvas_units(root, endpoint, out_root, file_key, base_url, wanted, concurrency)
                entries.extend(unit_entries)
                failures.extend(unit_failures)
            continue

        shot = None
        if "get_screenshot" in wanted:
            if rid == node_id:
                if target_shot is None:
                    target_shot = call_tool(client, available, "get_screenshot", node_id, required=True)
                shot = target_shot
            else:
                shot = call_tool(client, available, "get_screenshot", rid, required=True)
        node_dir, tools_done = save_node_asset(
            node_dir_for(out_root, file_key, slug), root, shot,
            require_screenshot=("get_screenshot" in wanted),
        )

        # 目标 root 上按需拉取附加工具（get_design_context 等）
        if rid == node_id:
            for extra in wanted:
                if extra in ("get_metadata", "get_screenshot") or extra not in available:
                    continue
                extra_result = call_tool(client, available, extra, rid)
                if extra_result is not None:
                    files = save_result(extra_result, node_dir, extra)
                    if files:
                        tools_done.append(extra)

        name = root.get("name")
        source_url = url if rid == node_id else (f"{base_url}?node-id={slug}" if base_url else None)
        entries.append({
            "node_id": rid or slug, "slug": f"{file_key}/{slug}", "name": name, "file_key": file_key,
            "source_url": source_url, "tools": tools_done,
            **asset_hashes(node_dir),
        })
        print(f"- {slug} '{name}': {', '.join(tools_done)}")
    return entries, failures


def run_target(target, endpoint, out_root, wanted, no_split, concurrency):
    try:
        return process_target(target, endpoint, out_root, wanted, no_split, concurrency)
    except McpCallError as exc:
        prefix = "[FAIL]" if exc.category == "input" else "[BLOCKED]"
        return [], [f"{prefix} {target[1] or target[0] or '<selection>'}: {exc}"]
    except EnvironmentBlocked as exc:
        return [], [f"[BLOCKED] {exc}"]
    except ValueError as exc:
        return [], [f"[FAIL] {target[1] or target[0] or '<selection>'}: {exc}"]
    except (urllib.error.URLError, ConnectionError, OSError) as exc:
        return [], [f"[BLOCKED] connection error ({target[1] or target[0] or '<selection>'}): {exc}"]


ASSET_REF_RE = re.compile(r"(https?://localhost:\d+/assets/[\w.-]+|file://figma/image/[\w.-]+)")


def fetch_asset_bytes(ref: str, client):
    """图片/SVG 下载双通道：localhost 资产服务走 HTTP；file://figma/image 走 MCP resources/read。"""
    if ref.startswith("http"):
        with urllib.request.urlopen(ref, timeout=30) as r:
            return r.read()
    result = client.request("resources/read", {"uri": ref})
    if not isinstance(result, dict):
        raise ValueError("resources/read 返回了非对象响应")
    contents = result.get("contents") or []
    if not isinstance(contents, list):
        raise ValueError("resources/read 的 contents 不是列表")
    for c in contents:
        if not isinstance(c, dict):
            continue
        if c.get("blob"):
            try:
                return base64.b64decode(c["blob"])
            except (binascii.Error, TypeError, ValueError) as exc:
                raise ValueError(f"resources/read 返回了无法解码的 blob：{exc}") from None
        if isinstance(c.get("text"), str) and c["text"]:
            return c["text"].encode()
    return None


def load_assets_manifest(path: Path) -> dict:
    """读取按 fileKey 隔离的资产索引；损坏输入必须显式失败而不是 traceback。"""
    if not path.exists():
        return {"urls": {}, "shas": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"资产 manifest 无法读取或解析：{path}（{exc}）") from None
    if not isinstance(value, dict):
        raise ValueError(f"资产 manifest 顶层必须是 JSON 对象：{path}")
    for key in ("urls", "shas"):
        if key in value and not isinstance(value[key], dict):
            raise ValueError(f"资产 manifest 的 {key} 必须是对象：{path}")
    value.setdefault("urls", {})
    value.setdefault("shas", {})
    for ref, record in value["urls"].items():
        local = record.get("local") if isinstance(record, dict) else None
        if (not isinstance(local, str) or not local
                or Path(local).name != local or local in {".", ".."}):
            raise ValueError(f"资产 manifest 的 urls[{ref!r}] 缺少有效 local：{path}")
    for digest, local in value["shas"].items():
        if (not isinstance(local, str) or not local
                or Path(local).name != local or local in {".", ".."}):
            raise ValueError(f"资产 manifest 的 shas[{digest!r}] 缺少有效文件名：{path}")
    return value


def collect_assets(node_dirs, client):
    """工具产物引用的图片/SVG 统一落盘 <fileKey>/assets/：内容哈希去重。

    扫描节点目录下 .md/.json/.tsx 产物中的 localhost 资产 URL 与 file://figma/image URI
    （tsx 必须入扫描集：get_design_context 的图片常量是 tsx 独有引用，不扫则无映射、
    本地化重写空转）；
    同字节只存一份（多 URL 共享 local）；SVG 只落 .svg 源文件（XML 结构消费侧按需解析，
    不造冗余衍生物）；shards（get_code_connect_suggestions-<n>.json）在其引用全部落盘后
    清理（失败 shard 保留供重试）；原始产物不改写，url→local 映射记 assets/manifest.json。
    """
    stats = {}
    if not node_dirs:
        return stats
    out_root = node_dirs[0].parent.parent
    by_filekey: dict = {}
    for nd in node_dirs:
        ensure_inside(nd, out_root, "Figma node directory")
        by_filekey.setdefault(nd.parent, []).append(nd)
    for fk_dir, dirs in by_filekey.items():
        stats = {"refs": 0, "downloaded": 0, "dedup": 0, "cleaned": 0, "failed": 0}
        assets_dir = ensure_inside(fk_dir / "assets", out_root, "Figma assets directory")
        assets_dir.mkdir(parents=True, exist_ok=True)
        mpath = ensure_inside(assets_dir / "manifest.json", out_root, "Figma assets manifest")
        manifest = load_assets_manifest(mpath)
        urls, shas = manifest.setdefault("urls", {}), manifest.setdefault("shas", {})
        refs = []
        for nd in dirs:
            for f in sorted(list(nd.glob("*.md")) + list(nd.glob("*.json")) + list(nd.glob("*.tsx"))):
                ensure_inside(f, out_root, "Figma asset reference source")
                refs += ASSET_REF_RE.findall(f.read_text(errors="ignore"))
        for ref in dict.fromkeys(refs):
            stats["refs"] += 1
            if ref in urls:
                continue
            try:
                data = fetch_asset_bytes(ref, client)
            except (urllib.error.URLError, OSError, RuntimeError, ValueError) as exc:
                stats["failed"] += 1
                print(f"  [asset WARN] {ref}: {exc}", file=sys.stderr)
                continue
            if not data:
                stats["failed"] += 1
                print(f"  [asset WARN] {ref}: 空响应", file=sys.stderr)
                continue
            sha = "sha256:" + hashlib.sha256(data).hexdigest()[:16]
            ext = Path(urllib.parse.urlsplit(ref).path).suffix or ".bin"
            if sha in shas:
                local = shas[sha]
                stats["dedup"] += 1
            else:
                local = f"{sha.split(':')[1]}.{ext.lstrip('.')}"
                asset_path = ensure_inside(assets_dir / local, out_root, "Figma collected asset")
                asset_path.write_bytes(data)
                shas[sha] = local
                stats["downloaded"] += 1
            urls[ref] = {"local": local, "sha256": sha, "bytes": len(data)}
        # shards 清理：引用全部落盘的 get_code_connect_suggestions-<n>.json 删除
        for nd in dirs:
            for shard in nd.glob("get_code_connect_suggestions-*.json"):
                ensure_inside(shard, out_root, "Figma shard")
                shard_refs = ASSET_REF_RE.findall(shard.read_text(errors="ignore"))
                if shard_refs and all(r in urls for r in shard_refs):
                    shard.unlink()
                    stats["cleaned"] += 1
        # tsx 代码产物引用本地化：localhost/file:// 引用重写为 ../assets/<local>（.md raw 保留原 URL）
        for nd in dirs:
            for tsx in nd.glob("*.tsx"):
                ensure_inside(tsx, out_root, "Figma code asset")
                text = tsx.read_text(encoding="utf-8")

                def _rw(m, _urls=urls):
                    rec = _urls.get(m.group(0))
                    return f"../assets/{rec['local']}" if rec else m.group(0)

                new = ASSET_REF_RE.sub(_rw, text)
                if new != text:
                    tsx.write_text(new, encoding="utf-8")
                    stats["rewritten"] = stats.get("rewritten", 0) + 1
        ensure_inside(mpath, out_root, "Figma assets manifest")
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(f"  [assets] {fk_dir.name}: refs {stats['refs']} / 新落 {stats['downloaded']}"
              f" / 去重 {stats['dedup']} / shards清理 {stats['cleaned']}"
              f" / tsx本地化 {stats.get('rewritten', 0)} / 失败 {stats['failed']}")
    return stats

def write_manifest(out_root: Path, all_entries):
    manifest_path = ensure_inside(out_root / "manifest.json", out_root, "Figma manifest output")
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeError) as exc:
            raise ValueError(f"已有 manifest 无法读取或解析：{exc}；请先修复后再拉取") from None
    if not isinstance(manifest, dict):
        raise ValueError("已有 manifest 顶层不是对象，不能继续写入")
    nodes = manifest.setdefault("nodes", {})
    if not isinstance(nodes, dict):
        raise ValueError("已有 manifest.nodes 不是对象，不能继续写入")
    invalid_existing = []
    for raw_key in nodes:
        key = str(raw_key)
        parts = key.split("/", 1)
        try:
            valid = (len(parts) == 2
                     and canonical_file_key(parts[0]) == parts[0]
                     and canonical_node_id(parts[1]) == parts[1])
        except ValueError:
            valid = False
        if not valid:
            invalid_existing.append(key)
    if invalid_existing:
        raise ValueError(
            "已有 manifest 含非规范 node key（必须是 <fileKey>/<冒号 node-id> 复合键）："
            + ", ".join(sorted(invalid_existing))
        )
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for e in all_entries:
        file_key = e.get("file_key")
        node_id = canonical_node_id(e["node_id"])
        if not file_key:
            raise ValueError(f"node {node_id} 缺少 file_key，不能写入 manifest")
        file_key = canonical_file_key(file_key)
        manifest_key = f"{file_key}/{node_id}"
        entry = {
            "name": e["name"],
            "file_key": e["file_key"],
            "source_url": e["source_url"],
            "fetched_at": now,
            "tools": e["tools"],
            "dir": e["slug"],
        }
        for hk in ("outline_hash", "screenshot_hash"):
            if e.get(hk):
                entry[hk] = e[hk]
        if e.get("overlays"):
            entry["overlays"] = e["overlays"]
        nodes[manifest_key] = entry
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize_client(client: McpClient, endpoint: str):
    """握手失败属于环境阻断：明确停下，不在拉取流程内修复 Figma。"""
    try:
        connect_client(client)
    except EnvironmentBlocked as exc:
        print(
            f"[BLOCKED] {exc}\n"
            "Check that the Figma DESKTOP app is running with the target file open and that\n"
            "Preferences -> Enable Dev Mode MCP Server is turned on. Browser-only Figma does not\n"
            "expose the local MCP endpoint. The script will not start, install, or reconfigure Figma;\n"
            "report this environment blocker to the user and resume after it is restored.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch design outlines/screenshots from local Figma Dev Mode MCP server (batch & concurrent)"
    )
    parser.add_argument("urls", nargs="*", help="Figma URLs (multiple allowed)")
    parser.add_argument("--url", action="append", default=[], dest="url_flags", help="Figma URL; repeatable")
    parser.add_argument("--node-id", action="append", default=[], dest="node_ids", help="Figma node id (e.g. 12:34); repeatable")
    parser.add_argument("--file-key", default="", help="Figma fileKey；用于 node-id 或当前选区模式的规范坐标")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"MCP endpoint (default {DEFAULT_ENDPOINT})")
    parser.add_argument("--tools", default=",".join(DEFAULT_TOOLS), help=f"comma separated tool names (default {','.join(DEFAULT_TOOLS)})")
    parser.add_argument("--req", help="需求 slug；设计资产归属的 requirement")
    parser.add_argument("--out", help="可选显式目录；必须等于该需求的 sources/design")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help=f"parallel workers (default {DEFAULT_CONCURRENCY})")
    parser.add_argument("--no-split", action="store_true", help="do not auto-split canvas (page) metadata into per-design-unit assets")
    parser.add_argument("--list-tools", action="store_true", help="only initialize, list tools and their schemas, then exit")
    parser.add_argument("--client-languages", default="", help="e.g. typescript；按 schema 透传给接受 clientLanguages 的工具（get_design_context 等）")
    parser.add_argument("--client-frameworks", default="", help="e.g. react,tailwind；同上透传 clientFrameworks")
    parser.add_argument("--collect-assets", action="store_true",
                        help="把产物引用的图片/SVG 统一落盘 <fileKey>/assets/（内容哈希去重，已落盘 shards 清理）；"
                             "不带 urls 时扫描 --out 下全部节点目录")
    parser.add_argument("--transport", choices=["auto", "mcp", "rest"], default="auto",
                        help="设计稿传输：auto=先试本地 MCP，不可达且有 token 转 REST；mcp=仅本地；rest=仅 REST")
    parser.add_argument("--figma-token", default="",
                        help="Figma REST personal access token（或 env FIGMA_TOKEN）；rest/auto 兜底用")
    parser.add_argument("--scale", type=int, default=2, help="REST 截图倍率（默认 2）")
    args = parser.parse_args()
    if not args.list_tools:
        if not args.req:
            parser.error("采集设计资产时必须提供 --req；不能写入无归属的全局目录")
        try:
            root = current_worktree_root()
            expected_out = requirement_source_dir(args.req, "design", root)
            out_root = expected_out if not args.out else ensure_inside(args.out, expected_out, "Figma output directory")
            if out_root.resolve() != expected_out.resolve():
                raise WorktreePathError(
                    "--out 只能是当前 worktree 的 .engineering/requirements/<req>/sources/design"
                )
            args.out = str(out_root.resolve())
        except WorktreePathError as exc:
            print(f"[BLOCKED] {exc}", file=sys.stderr)
            raise SystemExit(2)
    global _CLIENT_HINTS
    _CLIENT_HINTS = {
        "clientLanguages": args.client_languages,
        "clientFrameworks": args.client_frameworks,
    }

    # 独立 collect 模式：不跑 fetch 流程（避免回退到当前选区意外拉取）
    if args.collect_assets and not args.urls and not args.url_flags and not args.node_ids:
        node_dirs = sorted(p.parent for p in Path(args.out).glob("*/*/get_metadata.md"))
        if not node_dirs:
            raise SystemExit("collect-assets: 无节点目录可扫")
        client = McpClient(args.endpoint)
        initialize_client(client, args.endpoint)
        try:
            collect_assets(node_dirs, client)
        except ValueError as exc:
            print(f"[FAIL] collect-assets: {exc}", file=sys.stderr)
            raise SystemExit(1)
        except OSError as exc:
            print(f"[BLOCKED] 无法读写 Figma 资产 {args.out}: {exc}", file=sys.stderr)
            raise SystemExit(2)
        return

    wanted = list(dict.fromkeys(t.strip() for t in args.tools.split(",") if t.strip()))

    # 输入坐标先于 MCP 握手校验，避免缺 file_key 时被无关的环境错误遮蔽。
    targets = []
    for u in list(args.urls) + list(args.url_flags):
        if u:
            targets.append((u, node_id_from_url(u), args.file_key.strip()))
    for nid in args.node_ids:
        if nid:
            targets.append((None, nid, args.file_key.strip()))
    if not targets:
        targets.append((None, None, args.file_key.strip()))
    # 重复目标会让并发 worker 写同一节点目录；按首次出现顺序去重，避免竞态。
    targets = list(dict.fromkeys(targets))
    if args.concurrency < 1:
        parser.error("--concurrency 必须是正整数")
    input_errors = []
    for url, nid, override in targets:
        file_key = override or file_key_from_url(url)
        if not file_key:
            input_errors.append(
                f"{nid or '<selection>'}: 缺少 file_key；请提供包含 fileKey 的 URL 或 --file-key"
            )
            continue
        try:
            canonical_file_key(file_key)
            if nid is not None:
                canonical_node_id(nid)
        except ValueError as exc:
            input_errors.append(f"{nid or url or '<selection>'}: {exc}")
    if not args.list_tools and input_errors:
        for message in input_errors:
            print(f"[FAIL] {message}", file=sys.stderr)
        raise SystemExit(1)

    token = args.figma_token or os.environ.get("FIGMA_TOKEN", "")
    transport = args.transport
    if transport == "auto" and not args.list_tools:
        probe = McpClient(args.endpoint)
        try:
            connect_client(probe)
            transport = "mcp"
        except EnvironmentBlocked:
            if token:
                transport = "rest"
                print("[INFO] 本地 Figma MCP 不可达，转 REST 兜底。", file=sys.stderr)
            else:
                print(
                    "[BLOCKED] 本地 Figma MCP 不可达且未提供 FIGMA_TOKEN。\n"
                    "恢复选项：1) 启动 Figma 桌面端并启用 Dev Mode MCP Server；\n"
                    "         2) 提供 --figma-token 或设置环境变量 FIGMA_TOKEN 走 REST 兜底。",
                    file=sys.stderr,
                )
                raise SystemExit(2)

    client = None
    if transport == "mcp" or args.list_tools:
        client = McpClient(args.endpoint)
        initialize_client(client, args.endpoint)

    if args.list_tools:
        try:
            tools = list_tools(client)
        except EnvironmentBlocked as exc:
            print(f"[BLOCKED] {exc}", file=sys.stderr)
            raise SystemExit(2)
        print(f"{len(tools)} tools available:")
        for tool in tools:
            description = tool.get("description") if isinstance(tool.get("description"), str) else ""
            print(f"- {tool.get('name')}: {description.splitlines()[0] if description else ''}")
            schema = tool.get("inputSchema") or {}
            props = schema.get("properties") if isinstance(schema, dict) else {}
            if not isinstance(props, dict):
                props = {}
            if props:
                arg_list = ", ".join(
                    "%s(%s)" % (k, v.get("type", "?") if isinstance(v, dict) else "?")
                    for k, v in props.items()
                )
                print(f"    args: {arg_list}")
        return

    out_root = Path(args.out)
    try:
        out_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[BLOCKED] 无法写入 Figma 输出目录 {out_root}: {exc}", file=sys.stderr)
        raise SystemExit(2)

    if transport == "rest":
        import figma_rest
        all_entries, all_failures = figma_rest.run_targets(
            targets, out_root, token, args.scale, args.concurrency)
        all_entries.sort(key=lambda e: (str(e.get("file_key", "")), str(e.get("node_id", ""))))
        all_failures.sort()
        if not all_entries:
            print("[FAIL] REST 未产出任何设计单元；请检查 node-id、file_key 与 token。", file=sys.stderr)
            for failure in all_failures:
                print(f"- {failure}", file=sys.stderr)
            raise SystemExit(2 if any(x.startswith("[BLOCKED]") for x in all_failures) else 1)
        try:
            write_manifest(out_root, all_entries)
        except ValueError as exc:
            print(f"[FAIL] Figma manifest 输入不完整：{exc}", file=sys.stderr)
            raise SystemExit(1)
        print(f"- manifest: {out_root / 'manifest.json'} (REST 本批 {len(all_entries)} 条)")
        if all_failures:
            print("warning: failures:", file=sys.stderr)
            for failure in all_failures:
                print(f"- {failure}", file=sys.stderr)
            raise SystemExit(2 if any(x.startswith("[BLOCKED]") for x in all_failures) else 1)
        return

    effective_concurrency = args.concurrency
    if is_local_mcp_endpoint(args.endpoint) and effective_concurrency > 1:
        effective_concurrency = 1
        print(
            "[INFO] local Figma MCP 绑定活动文件/选区，本次强制串行访问以避免上下文竞争。",
            file=sys.stderr,
        )
    print(f"Figma MCP connected: {args.endpoint}")
    print(f"targets: {len(targets)} | concurrency: {min(effective_concurrency, len(targets))} | out: {out_root}")

    all_entries, all_failures = [], []
    # 本地 MCP 使用单通道；其他端点保留显式并发参数。
    with concurrent.futures.ThreadPoolExecutor(max_workers=effective_concurrency) as pool:
        futures = [
            pool.submit(run_target, t, args.endpoint, out_root, wanted, args.no_split, effective_concurrency)
            for t in targets
        ]
        for fut in concurrent.futures.as_completed(futures):
            entries, failures = fut.result()
            all_entries.extend(entries)
            all_failures.extend(failures)

    # worker 完成顺序不稳定；排序后再写 manifest，避免同一批输入产生无语义 diff。
    all_entries.sort(key=lambda entry: (str(entry.get("file_key", "")), str(entry.get("node_id", ""))))
    all_failures.sort()
    if not all_entries:
        print(
            "[FAIL] 本次没有产出任何设计单元，拒绝把空跑视为成功；请检查 get_metadata 响应、选区和目标 node-id。",
            file=sys.stderr,
        )
        for failure in all_failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(2 if any(f.startswith("[BLOCKED]") for f in all_failures) else 1)
    try:
        write_manifest(out_root, all_entries)
        total = len((json.loads((out_root / "manifest.json").read_text(encoding="utf-8")).get("nodes") or {}))
    except ValueError as exc:
        print(f"[FAIL] Figma manifest 输入不完整：{exc}", file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(f"[BLOCKED] 无法读写 Figma manifest {out_root / 'manifest.json'}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    print(f"- manifest: {out_root / 'manifest.json'} (本批 {len(all_entries)} 条，索引全量 {total} 条)")

    if all_failures:
        print("warning: failures:", file=sys.stderr)
        for f in all_failures:
            print(f"- {f}", file=sys.stderr)
        print(
            "Tip: open the target file in the Figma desktop app and SELECT the frame you need,\n"
            "then rerun without URL args; or pass URLs that contain node-id.",
            file=sys.stderr,
        )
        if any(f.startswith("[BLOCKED]") for f in all_failures):
            raise SystemExit(2)
        raise SystemExit(1)

    if args.collect_assets:
        if args.urls or args.url_flags or args.node_ids:
            node_dirs = [Path(args.out) / e["slug"] for e in all_entries]   # slug = <fileKey>/<node-slug>
        else:
            node_dirs = sorted(p.parent for p in Path(args.out).glob("*/*/get_metadata.md"))
        if node_dirs:
            client = McpClient(args.endpoint)
            initialize_client(client, args.endpoint)
            try:
                collect_assets(node_dirs, client)
            except ValueError as exc:
                print(f"[FAIL] Figma 资产索引输入不完整：{exc}", file=sys.stderr)
                raise SystemExit(1)
            except OSError as exc:
                print(f"[BLOCKED] 无法读写 Figma 资产 {args.out}: {exc}", file=sys.stderr)
                raise SystemExit(2)
        else:
            print("collect-assets: 无节点目录可扫", file=sys.stderr)


if __name__ == "__main__":
    main()
