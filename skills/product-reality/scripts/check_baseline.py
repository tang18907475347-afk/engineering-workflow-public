#!/usr/bin/env python3
"""检查 Current Reality（`.engineering/product/`）的结构一致性；不判断语义真伪。

所有检查批量收集问题，最后一次性输出全部 ERROR / WARN，不在中途逐条打印或提前退出
（唯一例外：用法错误、根目录不存在等使后续检查无法进行的前置条件）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = [
    "BASELINE_INDEX.md",
    "product-model/INDEX.md",
    "task-map/INDEX.md",
    "behavior/INDEX.md",
    "evidence/INDEX.md",
    "evidence/questions.md",
    "evidence/claims.md",
    "evidence/unknowns.md",
    "coverage/INDEX.md",
]

# 穷尽性边界声明（负面结论最常挂在这个状态上）
EXHAUSTIVE = "EXHAUSTIVE_WITHIN_SCOPE"

# 必需盘点的 Inventory 类型；权威清单在 references/product/reconnaissance-protocol.md §1，改清单要同步这里。
# 只列本轮真实发生整块缺失的高风险类型，不做全类型穷举。
REQUIRED_INVENTORY_TYPES = (
    "Surface", "Runtime Executor", "Authoritative Docs")


class Report:
    """批量收集问题，统一输出。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def check_required_files(root: Path, report: Report) -> None:
    for rel in REQUIRED:
        if not (root / rel).is_file():
            report.error(f"missing required file: {rel}")


def check_status_consistency(
    index: str, questions: str, unknowns: str, report: Report
) -> None:
    """frontmatter status 与登记册的机械一致性；COMPLETE 时提示未闭合登记项（仅 WARN）。"""
    status_match = re.search(
        r"(?im)^status:\s*(IN_PROGRESS|PARTIAL|COMPLETE|BLOCKED)\s*$", index
    )
    status = status_match.group(1) if status_match else None
    if status is None:
        report.warn("BASELINE_INDEX.md 缺少 frontmatter status")

    if status != "COMPLETE":
        return

    if re.search(r"(?i)\b(OPEN|IN_PROGRESS|PARTIAL|BLOCKED)\b", questions):
        report.warn("Baseline Status=COMPLETE，但 Question Ledger 仍有未闭合状态；请确认均为低影响项")
    if re.search(r"(?i)\b(OPEN|INVESTIGATING|BLOCKED)\b", unknowns):
        report.warn("Baseline Status=COMPLETE，但 Unknown Registry 仍有未解决项；请确认均不影响 P0/P1 与关键 Behavior")


def check_boundary_executed(root: Path, report: Report) -> None:
    """穷尽性边界必须有可重放的 executed 记录。

    治的真实错误：declared 写「web/src 全量」，实际只按一种命名约定检索，
    真实实现是顶层导出 / URL 字面量 → 假阴性，而 Boundary Status 仍是 EXHAUSTIVE。
    只做字段检查，不对 Claim 文本做语义分类。
    """
    targets = [root / "evidence" / "claims.md"]
    cov = root / "coverage"
    if cov.is_dir():
        targets += sorted(cov.glob("*.md"))
    for path in targets:
        text = read(path)
        if EXHAUSTIVE not in text:
            continue
        lines = text.splitlines()
        hits = []
        for i, line in enumerate(lines):
            if EXHAUSTIVE not in line:
                continue
            window = "\n".join(lines[max(0, i - 2):i + 3])
            if not re.search(r"(?i)executed", window):
                hits.append(i + 1)
        if not hits:
            continue
        # 按文件聚合：同一缺陷逐行报会产生几十条同质噪声，淹没可行动信息
        shown = ", ".join(map(str, hits[:8])) + ("…" if len(hits) > 8 else "")
        report.error(
            f"{path.relative_to(root)} 有 {len(hits)} 处 {EXHAUSTIVE} 缺 executed 检索记录"
            f"（行 {shown}）；本检查针对**超出证据能力的表述**，不针对结论本身。"
            "两种合法处置任选：① 补可重放的 executed（工具 + pattern + 范围 + 日期）；"
            "② 把 Boundary Status 降为 PARTIAL/UNKNOWN 并**保留原结论**。"
            "禁止为了清零而批量把结论改写成 UNKNOWN。")


def check_inventory_types(root: Path, report: Report) -> None:
    """Inventory 类型级完整性：必需类型有 item，或显式 zero-result + 检索方式。

    只检查「有没有盘点 / 为 0 有没有解释」，不判断为什么没有、找得够不够深、
    是否应该 COVERED —— 那些留给模型。
    """
    cov = root / "coverage"
    text = "".join(read(p) + "\n" for p in sorted(cov.glob("*.md"))
                   ) if cov.is_dir() else ""
    if "Type Completeness" not in text:
        report.warn("coverage/ 未见 Type Completeness 表；运行期执行器与权威文档两类为空是"
                    "高风险信号，建议按 assets/coverage.template.md 补表")
        return

    block = text.split("Type Completeness", 1)[1]
    block = re.split(r"(?m)^##\s", block, maxsplit=1)[0]
    rows = [r for r in block.splitlines() if r.strip().startswith("|")]
    for want in REQUIRED_INVENTORY_TYPES:
        hits = [r for r in rows if want.lower() in r.lower()]
        if not hits:
            report.error(f"Type Completeness 缺少必需 Inventory 类型：{want}"
                         "（权威清单见 references/product/reconnaissance-protocol.md §1）")
            continue
        for row in hits:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) < 3 or cells[1] not in ("0", "０", "零"):
                continue
            if len(cells[2]) < 2 or cells[2] in ("—", "-", "–", "N/A", "n/a"):
                report.error(f"Inventory 类型「{cells[0]}」为 0 项，但未写明"
                             "「确实不存在」还是「未找到 + 实际检索方式」")


# ── Canonical Information Model（E-* primitive schema）机械校验 ──
# 只检查可机械确定的**记录契约与引用完整性**：字段存在性、ID 合法性、Subject 是否为身份、
# facet/channel 适配、Locator 可重放、深度轴判定完整性与行 J-ID 归属、重复/悬空 ID、
# COMPLETE 零证据。不做语义判断、不做 facet 等级推导、不判断 diagnosis / UX 质量。

E_COLUMNS = 8   # E-ID | Subject | Channel | Reality | Kind | Locator | Observation | Boundary
REALITY_FACETS = ("declared", "implemented", "reachable",
                  "executable", "experienced")
# Subject 只表示被观察对象身份；以下是事实性质，进入 Subject 会让它退化成语义垃圾桶
NON_SUBJECT_WORDS = ("intended", "intent", "historical", "history",
                     "target", "legacy", "planned", "desired", "unknown", "reference-only")
# 只强制两个真实失败过的 facet：其余组合过宽，硬判会产生假 ERROR（runtime 也能证 implemented）
# executable 允许 data-snapshot：真实运行留下的持久化产物即「direct trace」
FACET_CHANNEL_REQUIRED = {
    "experienced": {"runtime"},
    "executable": {"runtime", "test", "data-snapshot"},
}
DISPOSABLE = (".engineering/work/", "/tmp")
# Evidence 的 E-ID + 七字段（8 列）中机械必填的六个内容字段（Kind 允许留空：evidence-standard §2「其余事实留空」）
E_REQUIRED_IDX = {1: "Subject", 2: "Channel", 3: "Reality",
                  5: "Locator", 6: "Observation", 7: "Boundary"}
# 深度轴 facet 列合法取值前缀（md-strip + upper 后判断）
DEPTH_OK = ("PRESENT", "MISSING", "N/A", "NA", "NOT APPLICABLE")

E_ID_RE = re.compile(r"^E-\d+$")
C_ID_RE = re.compile(r"^C-\d+$")
E_TOKEN_RE = re.compile(r"\bE-\d+\b")
C_TOKEN_RE = re.compile(r"\bC-\d+\b")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _strip_md(cell: str) -> str:
    """去掉 backtick / bold / markdown link 包裹取纯文本，用于 ID 与取值比较。

    治的真实误判：模板把值写成 `self` / `PASS` / `runtime`（backtick 包裹），
    旧代码按原文比较 → 合法 Markdown 被误判为非法/空/取值异常。
    """
    c = cell.strip().replace("`", "").replace("*", "")
    m = re.match(r"\[([^\]]+)\]\([^)]*\)", c)
    if m:
        c = m.group(1)
    return c.strip()


def _is_sep_row(cells: list[str]) -> bool:
    """表格分隔行 |---|:--:|。"""
    return bool(cells) and all(
        c == "" or re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells)


def iter_tables(text: str):
    """遍历 markdown 表格块，yield (header_cells, [(lineno, row_cells), ...])。"""
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        block: list[tuple[int, str]] = []
        while i < n and lines[i].strip().startswith("|"):
            block.append((i + 1, lines[i].strip()))
            i += 1
        header = _cells(block[0][1])
        rows = [(ln, _cells(line)) for ln, line in block[1:]
                if not _is_sep_row(_cells(line))]
        yield header, rows


def _col(header: list[str], *needles: str) -> int:
    """按表头文字定位列索引（needles 小写）；找不到返回 -1。"""
    for idx, h in enumerate(header):
        hl = _strip_md(h).lower()
        if any(nd in hl for nd in needles):
            return idx
    return -1


def _evidence_files(root: Path) -> list[Path]:
    ev = root / "evidence"
    if not ev.is_dir():
        return []
    return sorted(ev.rglob("*.md"))


def _canonical_files(root: Path) -> list[Path]:
    """引用扫描范围：evidence + 四张 derived view + spec + BASELINE_INDEX。"""
    files = _evidence_files(root)
    for sub in ("coverage", "task-map", "product-model", "behavior", "spec"):
        d = root / sub
        if d.is_dir():
            files += sorted(d.rglob("*.md"))
    idx = root / "BASELINE_INDEX.md"
    if idx.is_file():
        files.append(idx)
    return files


def _spec_index(root: Path) -> Path | None:
    """Return the spec entry file if a spec deliverable exists, else None."""
    spec_dir = root / "spec"
    if not spec_dir.is_dir():
        return None
    idx = spec_dir / "INDEX.md"
    if idx.is_file():
        return idx
    candidates = sorted(p for p in spec_dir.glob("*.md") if p.is_file())
    return candidates[0] if candidates else None


def check_spec_structure(root: Path, report: Report) -> None:
    """Minimal structural checks for spec/: entry headings and INDEX discipline.

    Only deterministic structure is checked; behavior coverage, acceptance presence
    and spec sufficiency are semantic judgments left to the model.
    """
    spec_dir = root / "spec"
    if not spec_dir.is_dir():
        return
    md_files = sorted(p for p in spec_dir.glob("*.md") if p.is_file())
    if len(md_files) > 1 and not (spec_dir / "INDEX.md").is_file():
        report.error("spec/ has multiple .md files but no INDEX.md")
    idx = _spec_index(root)
    if idx is None:
        return
    text = idx.read_text(encoding="utf-8", errors="replace")
    for heading in ("Spec Target Scope", "Behavior Contracts", "Replica-Ready Judgment"):
        if not re.search(rf"(?im)^##\s+{re.escape(heading)}\s*$", text):
            report.error(
                f"{idx.relative_to(root).as_posix()}: missing '## {heading}' section")


def check_baseline_scope(root: Path, report: Report) -> None:
    """Baseline Scope is structural; Replica-Ready Judgment lives only in spec/INDEX."""
    idx = root / "BASELINE_INDEX.md"
    if not idx.is_file():
        return
    text = idx.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?im)^##\s+Baseline Scope\s*$", text):
        report.error("BASELINE_INDEX.md: missing '## Baseline Scope' section")
    if re.search(r"(?im)^##\s+Replica-Ready Judgment\s*$", text):
        report.error(
            "BASELINE_INDEX.md: Replica-Ready Judgment must live in spec/INDEX.md; "
            "use '## Spec Link' to reference it")


def _status(index: str) -> str:
    m = re.search(r"(?im)^status:\s*([A-Za-z_]+)\s*$", index)
    return (m.group(1) if m else "").upper()


def collect_ids(root: Path):
    """返回 (def_e, def_c, ref_e, ref_c)。

    def_e：evidence/ 全部 canonical 文件里表格首列匹配 E-\\d+ 的行（primitive 定义处）；
    def_c：只认 evidence/claims.md 的 C-* 行（Claim Registry 是唯一 canonical 定义处；
          packets 中的 C 行是历史副本，不再重复计数）；
    ref_*：全部 canonical 文本里出现的 E-\\d+ / C-\\d+ token（含定义处自身）。
    """
    def_e: dict[str, int] = {}
    def_c: dict[str, int] = {}
    for path in _evidence_files(root):
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = _cells(s)
            if not cells:
                continue
            first = _strip_md(cells[0])
            if E_ID_RE.match(first):
                def_e[first] = def_e.get(first, 0) + 1

    claims = root / "evidence" / "claims.md"
    if claims.is_file():
        for line in claims.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = _cells(s)
            if not cells:
                continue
            first = _strip_md(cells[0])
            if C_ID_RE.match(first):
                def_c[first] = def_c.get(first, 0) + 1

    ref_e: set[str] = set()
    ref_c: set[str] = set()
    for path in _canonical_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        ref_e.update(E_TOKEN_RE.findall(text))
        ref_c.update(C_TOKEN_RE.findall(text))
    return def_e, def_c, ref_e, ref_c


def check_evidence_schema(root: Path, report: Report) -> None:
    """每条 canonical E-* 必须符合 E-ID + 七字段（8 列）primitive；六个内容必填项不得为空（Kind 可空）。"""
    hits: list[str] = []
    for path in _evidence_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = _cells(s)
            if not cells or not E_ID_RE.match(_strip_md(cells[0])):
                continue
            if len(cells) != E_COLUMNS:
                hits.append(f"{rel}:{i} 列数 {len(cells)}≠{E_COLUMNS}")
                continue
            vals = [_strip_md(c) for c in cells]
            for idx, name in E_REQUIRED_IDX.items():
                if not vals[idx]:
                    hits.append(f"{rel}:{i} {name} 为空（无隐式默认）")
            subject, channel, reality, locator = vals[1], vals[2], vals[3], vals[5]
            if subject.split(":")[0].strip().lower() in NON_SUBJECT_WORDS:
                hits.append(f"{rel}:{i} Subject={subject} 不是被观察对象的身份")
            fac = reality.lower()
            if fac not in REALITY_FACETS:
                hits.append(f"{rel}:{i} Reality={reality} 不属于五个 facet")
            elif fac in FACET_CHANNEL_REQUIRED and \
                    channel.lower() not in FACET_CHANNEL_REQUIRED[fac]:
                hits.append(
                    f"{rel}:{i} Reality={fac} 但 Channel={channel}（无对应通道支持）")
            if any(d in locator.replace("\\", "/") for d in DISPOSABLE):
                hits.append(f"{rel}:{i} Locator 指向可丢弃位置：{locator[:40]}")
    if hits:
        shown = ", ".join(hits[:8]) + ("…" if len(hits) > 8 else "")
        report.error(f"E-* primitive schema 违规 {len(hits)} 处：{shown}")


def check_evidence_ids(root: Path, report: Report) -> None:
    """Evidence 表里的非法/缺失 E-ID 不再被静默跳过。

    治的真实漏检：旧代码用 `^E-\\d+$` 过滤首列，`E-1a` / `EV-1` / 空 ID 直接 continue，
    schema 校验形同虚设。这里按表头识别 Evidence 表，逐个数据行校验 ID 合法性。
    """
    hits: list[str] = []
    for path in _evidence_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for header, rows in iter_tables(text):
            h0 = _strip_md(header[0]).lower() if header else ""
            if not (h0 == "e-id" or h0.startswith("e-id")):
                continue
            for ln, cells in rows:
                if all(c == "" for c in cells):
                    continue
                first = _strip_md(cells[0]) if cells else ""
                if not E_ID_RE.match(first):
                    raw = cells[0][:24] if cells else ""
                    hits.append(f"{rel}:{ln} 非法/缺失 Evidence ID：{raw!r}")
    if hits:
        shown = ", ".join(hits[:8]) + ("…" if len(hits) > 8 else "")
        report.error(f"非法 Evidence ID {len(hits)} 处（旧行为会静默跳过）：{shown}")


def check_id_integrity(root: Path, report: Report) -> None:
    """重复 ID 与悬空引用：记录契约与引用完整性，任何 Baseline 状态都不允许。"""
    def_e, def_c, ref_e, ref_c = collect_ids(root)
    dup_e = sorted(i for i, c in def_e.items() if c > 1)
    dup_c = sorted(i for i, c in def_c.items() if c > 1)
    if dup_e:
        report.error("重复 Evidence ID（同一 E-* 被定义多次）："
                     + ", ".join(dup_e[:8]) + ("…" if len(dup_e) > 8 else ""))
    if dup_c:
        report.error("重复 Claim ID（同一 C-* 被定义多次）："
                     + ", ".join(dup_c[:8]) + ("…" if len(dup_c) > 8 else ""))
    dangling_e = sorted(ref_e - set(def_e))
    dangling_c = sorted(ref_c - set(def_c))
    if dangling_e:
        report.error("悬空 Evidence 引用（引用了未定义的 E-*，含 Coverage PRESENT 空引用）："
                     + ", ".join(dangling_e[:8]) + ("…" if len(dangling_e) > 8 else ""))
    if dangling_c:
        report.error("悬空 Claim 引用（引用了未定义的 C-*）："
                     + ", ".join(dangling_c[:8]) + ("…" if len(dangling_c) > 8 else ""))


def check_complete_has_evidence(root: Path, report: Report) -> None:
    """COMPLETE 但没有真实 canonical Evidence：调查未诚实收口。"""
    if _status(read(root / "BASELINE_INDEX.md")) != "COMPLETE":
        return
    def_e, _def_c, _ref_e, _ref_c = collect_ids(root)
    if not def_e:
        report.error("status=COMPLETE 但 evidence/ 里没有任何 canonical E-* primitive"
                     "（COMPLETE 表示调查已诚实收口，不能零证据）")


def _p0p1_jids(root: Path) -> set[str]:
    """从 task-map 的 L1 User Jobs 表机械提取 P0/P1 的 J-ID（读 Priority 列，不做语义判断）。"""
    tm = root / "task-map"
    out: set[str] = set()
    if not tm.is_dir():
        return out
    for path in sorted(tm.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for header, rows in iter_tables(text):
            jid_c, pri_c = _col(header, "j-id"), _col(header, "priority")
            if jid_c < 0 or pri_c < 0:
                continue
            for _ln, cells in rows:
                if jid_c >= len(cells) or pri_c >= len(cells):
                    continue
                pri = _strip_md(cells[pri_c]).upper()
                if "P0" in pri or "P1" in pri:
                    jm = re.search(r"J-\d+", _strip_md(cells[jid_c]))
                    if jm:
                        out.add(jm.group(0))
    return out


def check_depth_axis(root: Path, report: Report) -> None:
    """Journey 深度轴：facet 判定完整、PRESENT 引用 E-*、行 J-ID 属 P0/P1、有 MISSING 不得 COMPLETE。

    深度轴只登记 P0/P1 且 UI-bearing 的 Journey（规则见 references/product/coverage-and-readiness.md §3）；
    「UI-bearing」是语义判断，机械无法判定，因此无 UI 的 P0/P1 Journey 缺行不报——
    缺行由收口前的语义判断负责。机械只校验反向：已登记行的 J-ID 必须对应
    task-map 的 P0/P1 Journey。
    """
    status = _status(read(root / "BASELINE_INDEX.md"))
    coverage = root / "coverage"
    missing: list[str] = []
    bad: list[str] = []
    depth_jids: set[str] = set()
    if coverage.is_dir():
        for path in sorted(coverage.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for header, rows in iter_tables(text):
                exp = _col(header, "experience observed")
                if exp < 0:
                    continue
                inter = _col(header, "interaction")
                pres = _col(header, "presentation")
                refs = _col(header, "evidence ref")
                jid_c = _col(header, "j-id")
                if jid_c < 0:
                    jid_c = 0
                facet_idxs = [x for x in (inter, pres, exp) if x >= 0]
                for ln, cells in rows:
                    if all(c == "" for c in cells):
                        continue
                    jidv = _strip_md(cells[jid_c]) if jid_c < len(cells) else ""
                    jm = re.search(r"J-\d+", jidv)
                    if jm:
                        depth_jids.add(jm.group(0))
                    elif not jidv:
                        bad.append(f"{path.name}:{ln} 深度轴缺 J-ID")
                    row_missing = row_present = False
                    for fi in facet_idxs:
                        v = _strip_md(cells[fi]).upper() if fi < len(cells) else ""
                        if not v:
                            bad.append(f"{path.name}:{ln} 深度轴 facet 列为空（未判定）")
                        elif not v.startswith(DEPTH_OK):
                            bad.append(f"{path.name}:{ln} 深度轴取值非法：{cells[fi][:20]!r}")
                        elif v.startswith("MISSING"):
                            row_missing = True
                        elif v.startswith("PRESENT"):
                            row_present = True
                    if row_present:
                        rv = _strip_md(cells[refs]) if 0 <= refs < len(cells) else ""
                        if not re.search(r"E-\d+", rv):
                            bad.append(f"{path.name}:{ln} facet=PRESENT 但 Evidence refs 未引用 E-*")
                    if row_missing:
                        missing.append(f"{path.name}:{jm.group(0) if jm else ln}")
    if bad:
        shown = ", ".join(bad[:8]) + ("…" if len(bad) > 8 else "")
        report.error(f"Journey 深度轴记录契约违规 {len(bad)} 处：{shown}")

    # 深度轴只登记 P0/P1 UI Journey；无 UI 的 P0/P1 Journey 不要求行（语义判断，见 references/product/coverage-and-readiness.md §3）。
    # 机械只校验反向：表中 J-ID 必须对应 task-map 的 P0/P1 Journey（task-map 解析不到 P0/P1 时跳过，避免误报）。
    p0p1 = _p0p1_jids(root)
    strays = sorted(depth_jids - p0p1) if p0p1 else []
    if strays:
        report.error("深度轴包含非 P0/P1 或未定义的 J-ID："
                     + ", ".join(strays[:8]) + ("…" if len(strays) > 8 else ""))

    if missing:
        msg = f"P0/P1 UI Journey 深度轴 MISSING：{', '.join(missing[:8])}"
        if status == "COMPLETE":
            report.error(msg + "——不得 COMPLETE")
        else:
            report.warn(msg + "——可 PARTIAL，但须已登记 Unknown")



def emit(report: Report) -> int:
    """一次性输出全部收集到的问题。"""
    if report.errors:
        print("FAIL")
        for item in report.errors:
            print(f"- ERROR: {item}")
        for item in report.warnings:
            print(f"- WARN: {item}")
        print(f"共 {len(report.errors)} 个 ERROR、{len(report.warnings)} 个 WARN。")
        return 1

    print("PASS")
    for item in report.warnings:
        print(f"- WARN: {item}")
    print("Structural Validation = PASS；不代表语义收口、行为覆盖或规格充分。覆盖与收口判据以 references/product/coverage-and-readiness.md 为准。")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_baseline.py <product-root>")
        return 2

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}")
        return 2

    report = Report()

    has_baseline_index = (root / "BASELINE_INDEX.md").is_file()
    has_spec = _spec_index(root) is not None
    if not has_baseline_index and not has_spec:
        report.error("Missing both BASELINE_INDEX.md and spec/; nothing to validate")
        return emit(report)

    if has_baseline_index:
        index = read(root / "BASELINE_INDEX.md")
        questions = read(root / "evidence/questions.md")
        unknowns = read(root / "evidence/unknowns.md")
        # 逐项检查，全部写入同一个 Report；任何一项失败都不影响其余项继续收集。
        check_required_files(root, report)
        check_baseline_scope(root, report)
        check_status_consistency(index, questions, unknowns, report)
        check_boundary_executed(root, report)
        check_inventory_types(root, report)
        check_evidence_schema(root, report)
        check_evidence_ids(root, report)
        check_complete_has_evidence(root, report)
        check_depth_axis(root, report)

    check_id_integrity(root, report)
    check_spec_structure(root, report)

    return emit(report)


if __name__ == "__main__":
    raise SystemExit(main())
