import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_figma_design as f


def test_sanitize_outline_drops_noise_and_truncates():
    el = ET.fromstring(
        '<frame id="1:2" x="0" y="0" width="10" height="20" name="%s">'
        '<text name="hi"/></frame>' % ("A" * 200)
    )
    clean = f.sanitize_outline(el)
    assert clean.get("id") is None and clean.get("width") is None
    assert len(clean.get("name")) <= f.MAX_NAME_LEN
    assert clean.find("text").get("name") == "hi"


def test_save_node_asset_refuses_empty_screenshot(tmp_path):
    out_root = tmp_path / "figma"
    node_dir = f.node_dir_for(out_root, "FILEKEY", "1-2")
    root = ET.fromstring('<frame name="F"><text name="t"/></frame>')
    try:
        f.save_node_asset(node_dir, root, None, require_screenshot=True)
        assert False, "should refuse node without screenshot"
    except ValueError:
        pass


def test_save_node_asset_writes_outline_and_manifest_hashes(tmp_path):
    out_root = tmp_path / "figma"
    node_dir = f.node_dir_for(out_root, "FILEKEY", "1-2")
    root = ET.fromstring('<frame id="1:2" name="F"><text name="t"/></frame>')
    shot = {"content": [{"type": "image", "data": "aGVsbG8=", "mimeType": "image/png"}]}
    _, tools = f.save_node_asset(node_dir, root, shot, require_screenshot=True)
    assert (node_dir / "get_metadata.md").exists()
    assert (node_dir / "get_screenshot.png").read_bytes() == b"hello"
    assert tools == ["get_metadata", "get_screenshot"]
    hashes = f.asset_hashes(node_dir)
    assert hashes["outline_hash"] and hashes["screenshot_hash"]
