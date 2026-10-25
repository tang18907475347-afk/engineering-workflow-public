import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import figma_rest as fr

NODES = {"nodes": {"12:34": {"document": {
    "id": "12:34", "name": "登录页", "type": "FRAME",
    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 375, "height": 812},
    "children": [{"id": "12:35", "name": "标题", "type": "TEXT"}],
}}}}
IMAGES = {"images": {"12:34": "https://figma-cdn/x.png"}}


def _fake_get(nodes, images):
    def _g(url, token, timeout=60):
        return nodes if "/nodes?" in url else images
    return _g


def test_fetch_nodes_produces_mcp_shaped_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_get", _fake_get(NODES, IMAGES))
    monkeypatch.setattr(fr, "_download_bytes", lambda url, timeout=60: b"PNGDATA")
    out_root = tmp_path / "figma"
    entries, failures = fr.fetch_nodes("FILEKEY", ["12:34"], "tok", out_root, scale=2, concurrency=1)
    assert failures == []
    assert len(entries) == 1
    node_dir = out_root / "FILEKEY" / "12-34"
    md = (node_dir / "get_metadata.md").read_text(encoding="utf-8")
    assert "<frame" in md and 'name="登录页"' in md
    assert "12:34" not in md and "width" not in md      # sanitize_outline 去 id/尺寸
    assert (node_dir / "get_screenshot.png").read_bytes() == b"PNGDATA"
    e = entries[0]
    assert e["node_id"] == "12:34" and e["slug"] == "FILEKEY/12-34"
    assert e["tools"] == ["get_metadata", "get_screenshot"]
    assert e["outline_hash"] and e["screenshot_hash"]


def test_missing_document_is_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_get", _fake_get({"nodes": {}}, {"images": {}}))
    monkeypatch.setattr(fr, "_download_bytes", lambda url, timeout=60: b"x")
    entries, failures = fr.fetch_nodes("FILEKEY", ["99:99"], "tok", tmp_path / "figma", 2, 1)
    assert entries == [] and any(x.startswith("[FAIL]") for x in failures)


def test_auth_error_is_blocked(tmp_path, monkeypatch):
    def _blocked(url, token, timeout=60):
        raise fr.EnvironmentBlocked("Figma REST 鉴权失败（HTTP 403）")
    monkeypatch.setattr(fr, "_get", _blocked)
    entries, failures = fr.fetch_nodes("FILEKEY", ["12:34"], "bad", tmp_path / "figma", 2, 1)
    assert entries == [] and any(x.startswith("[BLOCKED]") for x in failures)


def test_run_targets_requires_token(tmp_path):
    entries, failures = fr.run_targets(
        [("https://www.figma.com/design/FK/x?node-id=12-34", "12:34", "")], tmp_path, "", 2, 1)
    assert entries == [] and any("BLOCKED" in x for x in failures)


def test_run_targets_selection_mode_unsupported(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_get", lambda *a, **k: {})
    entries, failures = fr.run_targets([(None, None, "FK")], tmp_path, "tok", 2, 1)
    assert entries == [] and any("node-id" in x for x in failures)
