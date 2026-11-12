#!/usr/bin/env python3
"""
Markdown → Academic HTML Report Converter (hardened build).

Converts client-facing omics analysis reports (Markdown) into styled HTML.

Key safety properties:
- {{TITLE}} is HTML-escaped before substitution.
- Raw HTML / JS in the source Markdown is rejected by default (--allow-raw-html overrides).
- Absolute filesystem paths are always rejected for privacy.
- Image references are resolved relative to the input Markdown file's directory,
  not the current working directory. --asset-base overrides.
- Broken image references generate a non-fatal warning summary; --strict-links
  makes them fatal.

Usage:
    python md_to_html.py input.md
    python md_to_html.py input.md -o Report.html --title "Project Report"
    python md_to_html.py input.md -o Report.html --asset-base ./Figures --strict-links
"""

import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup, NavigableString

# Markdown parser extensions
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "toc",
    "nl2br",
]

# Extensions that should be treated as deliverable file paths and linkified
FILE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf",
    ".tsv", ".csv", ".xls", ".xlsx", ".txt",
    ".h5ad", ".rds", ".loom", ".h5", ".hdf5", ".qs2",
    ".md", ".log",
}

TABLE_EXTENSIONS = {".tsv", ".csv", ".xls", ".xlsx"}
TABLE_PREVIEW_DIR = Path("report_assets/table_previews")
LUCKYSHEET_VENDOR_DIR = Path("report_assets/vendor/luckysheet")
SKILL_VENDOR_LUCKYSHEET = Path(__file__).parent / "vendor" / "luckysheet"
SMALL_TABLE_MAX_BYTES = 8 * 1024 * 1024
FULL_TABLE_MAX_CELLS = 200_000
PREVIEW_MAX_ROWS = 5_000
PREVIEW_MAX_COLS = 200

# Raw HTML patterns that should never appear in a client-facing report.
# These get caught BEFORE the markdown library renders, so they cannot inject.
DANGEROUS_HTML_PATTERNS = [
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
    re.compile(r"<\s*object\b", re.IGNORECASE),
    re.compile(r"<\s*embed\b", re.IGNORECASE),
    re.compile(r"<\s*style\b", re.IGNORECASE),
    re.compile(r"<\s*link\b[^>]*\brel\s*=", re.IGNORECASE),
    # inline event handler — require a real HTML tag-open before `on\w+=`
    # so prose like `p_val_adj < 0.05` plus later `ont='BP'` won't false-positive.
    re.compile(r"<\s*[a-zA-Z][\w-]*\b[^>]*?\son\w+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),       # javascript: URLs
]

# Absolute-path patterns: POSIX absolute, Windows drive, UNC, home shortcuts
ABS_PATH_RE = re.compile(r"""
    (?:
        (?<![<\w.-])/(?!/)[^\s`),;，。<>]+
      | ~[/\\][^\s`),;，。]+
      | [A-Za-z]:[/\\][^\s`),;，。]+
      | \\\\[^\s`),;，。]+
    )
""", re.VERBOSE | re.IGNORECASE)


# --------------------------------------------------------------------------
# Pre-scan: reject raw HTML / absolute paths in Markdown source
# --------------------------------------------------------------------------

def find_raw_html_violations(md_text: str) -> list[tuple[int, str]]:
    """Return (line_no, matched_snippet) for raw-HTML violations."""
    violations = []
    # Strip fenced code blocks so legitimate examples don't trigger
    stripped = re.sub(r"```.*?```", "", md_text, flags=re.S)
    stripped = re.sub(r"`[^`\n]+`", "", stripped)
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        for pat in DANGEROUS_HTML_PATTERNS:
            m = pat.search(line)
            if m:
                violations.append((lineno, line.strip()[:120]))
                break
    return violations


def find_abs_path_violations(md_text: str) -> list[tuple[int, str]]:
    """Find absolute filesystem paths anywhere in report markdown."""
    violations = []
    # Drop HTML comments (used for skill/template instructions)
    stripped = re.sub(r"<!--.*?-->", "", md_text, flags=re.S)
    stripped = re.sub(r"https?://[^\s`)]+", "", stripped)

    inline_patterns = [
        re.compile(r"!\[[^\]]*\]\(([^)\s]+)"),  # image
        re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)"),  # plain link
    ]
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        # Inline markdown image/link refs
        for pat in inline_patterns:
            for m in pat.finditer(line):
                target = m.group(1)
                if ABS_PATH_RE.search(target):
                    violations.append((lineno, target))
        # Backtick file references like `/share/foo/bar.tsv`
        for m in re.finditer(r"`([^`]+)`", line):
            target = m.group(1).strip()
            if ABS_PATH_RE.search(target):
                violations.append((lineno, target))
        line_without_inline = line
        for pat in inline_patterns:
            line_without_inline = pat.sub("", line_without_inline)
        line_without_inline = re.sub(r"`[^`\n]+`", "", line_without_inline)
        for m in ABS_PATH_RE.finditer(line_without_inline):
            violations.append((lineno, m.group(0)))
    return violations


# --------------------------------------------------------------------------
# File-path linkification
# --------------------------------------------------------------------------

def is_file_path(text: str) -> bool:
    """Return True if a backtick-quoted token looks like a deliverable file path."""
    text = text.strip().strip("`")
    if not text:
        return False
    ext = Path(text).suffix.lower()
    if ext in FILE_EXTENSIONS:
        return True
    if "/" in text and "." in text.split("/")[-1]:
        return True
    return False


def is_table_path(text: str) -> bool:
    """Return True if a path should open in the table preview drawer."""
    return Path(text.strip().strip("`")).suffix.lower() in TABLE_EXTENSIONS


def make_file_chip(path: str) -> str:
    """Return HTML for a deliverable file chip."""
    safe = html.escape(path, quote=True)
    if is_table_path(path):
        return (
            f'<button class="file-link table-preview-trigger" type="button" '
            f'data-table-path="{safe}" aria-label="预览表格 {safe}">{safe}</button>'
        )
    return (f'<a class="file-link" href="{safe}" '
            f'target="_blank" rel="noopener noreferrer">{safe}</a>')


def linkify_file_paths_in_text(text: str) -> str:
    """Convert backtick-quoted relative file paths into links or preview buttons."""
    def replace_path(match):
        path = match.group(1)
        if is_file_path(path) and not ABS_PATH_RE.search(path):
            return make_file_chip(path)
        return match.group(0)

    return re.sub(r"`([^`]+)`", replace_path, text)


def linkify_file_paths(soup: BeautifulSoup) -> None:
    """Walk the DOM and linkify file paths in text/code nodes."""
    for elem in soup.find_all(string=True):
        if isinstance(elem, NavigableString) and elem.parent.name not in {"a", "code", "pre"}:
            new_text = linkify_file_paths_in_text(str(elem))
            if new_text != str(elem):
                elem.replace_with(BeautifulSoup(new_text, "html.parser"))

    for code in list(soup.find_all("code")):
        text = code.get_text()
        if is_file_path(text) and not ABS_PATH_RE.search(text):
            chip = BeautifulSoup(make_file_chip(text), "html.parser")
            code.replace_with(chip)


# --------------------------------------------------------------------------
# Image sizing (resolves relative to asset_base, not CWD)
# --------------------------------------------------------------------------

def _set_img_display_size(img, img_count: int, asset_base: Path) -> None:
    """Set CSS display size based on the image's actual pixel width."""
    src = img.get("src", "")
    if not src:
        return
    # Resolve relative to asset_base; tolerate absolute or URL-like sources
    if ABS_PATH_RE.search(src) or src.startswith(("http://", "https://", "data:")):
        return
    full = (asset_base / src).resolve()
    if not full.exists():
        return

    try:
        from PIL import Image as PILImage
        with PILImage.open(full) as im:
            orig_w, _ = im.size
    except Exception:
        return

    SINGLE_MAX = 836
    SINGLE_MIN = 550
    MULTI_MIN = 350
    MAX_UPSCALE = 1.5

    if img_count == 1:
        if orig_w < SINGLE_MIN:
            target = min(SINGLE_MIN, int(orig_w * MAX_UPSCALE))
            img["style"] = (f"width: {target}px; height: auto;" if target > orig_w
                            else "height: auto;")
        elif orig_w > SINGLE_MAX:
            img["style"] = f"max-width: {SINGLE_MAX}px; width: 100%; height: auto;"
        else:
            img["style"] = "height: auto;"
    else:
        # Multi-image: lives inside .figure-scroll, which controls layout via
        # CSS (max-height + width:auto). Keep natural width so the user can
        # scroll horizontally instead of seeing every image shrunk to 48%.
        if orig_w < MULTI_MIN:
            target = min(MULTI_MIN, int(orig_w * MAX_UPSCALE))
            img["style"] = f"width: {target}px; height: auto;"
        else:
            img["style"] = "height: auto;"


def source_figure_href(src: str, asset_base: Path) -> str:
    """Return the source figure file to open when the displayed image is clicked.

    The report may display a PNG for browser compatibility, but the source result
    is often a same-stem PDF in the analysis output directory. Prefer that source
    PDF when present; otherwise fall back to the displayed image.
    """
    if not src or ABS_PATH_RE.search(src) or src.startswith(("http://", "https://", "data:")):
        return src
    path = Path(src)
    if path.suffix.lower() == ".pdf":
        return src
    pdf_path = path.with_suffix(".pdf")
    if (asset_base / pdf_path).exists():
        return pdf_path.as_posix()
    return src


# --------------------------------------------------------------------------
# Auto TOC
# --------------------------------------------------------------------------

def generate_toc(soup: BeautifulSoup) -> None:
    """Build a collapsible floating TOC from <h2> and <h3> headings."""
    headings = []
    for h in soup.find_all(["h2", "h3"]):
        text = h.get_text(strip=True)
        if not text:
            continue
        if not h.get("id"):
            slug = re.sub(r"[^\w\s-]", "", text).strip()
            slug = re.sub(r"[-\s]+", "-", slug).lower()
            base_slug = slug or "section"
            counter = 1
            while soup.find(id=slug):
                slug = f"{base_slug}-{counter}"
                counter += 1
            h["id"] = slug
        headings.append((int(h.name[1]), h.get("id"), text))

    if not headings:
        return

    nav = soup.new_tag("nav", **{"class": "report-toc is-expanded", "aria-label": "目录"})

    header = soup.new_tag("div", **{"class": "toc-header"})
    toggle = soup.new_tag(
        "button",
        **{
            "class": "toc-toggle",
            "type": "button",
            "aria-expanded": "true",
            "aria-controls": "report-toc-body",
        },
    )
    toggle.string = "目录"
    header.append(toggle)
    nav.append(header)

    body = soup.new_tag("div", **{"class": "toc-body", "id": "report-toc-body"})
    nav.append(body)

    root_ul = soup.new_tag("ul")
    body.append(root_ul)
    current_h2_li = None

    for level, hid, text in headings:
        li = soup.new_tag("li", **{"class": f"toc-level-{level}"})
        a = soup.new_tag("a", href=f"#{hid}")
        a.string = text
        li.append(a)

        if level == 2 or current_h2_li is None:
            sublist = soup.new_tag("ul", **{"class": "toc-sublist"})
            li.append(sublist)
            root_ul.append(li)
            current_h2_li = li
        else:
            sublist = current_h2_li.find("ul", class_="toc-sublist")
            if sublist is None:
                sublist = soup.new_tag("ul", **{"class": "toc-sublist"})
                current_h2_li.append(sublist)
            sublist.append(li)

    for empty_sublist in list(root_ul.find_all("ul", class_="toc-sublist")):
        if not empty_sublist.find("li", recursive=False):
            empty_sublist.decompose()

    first_li = root_ul.find("li", class_="toc-level-2")
    if first_li:
        first_li["class"] = first_li.get("class", []) + ["is-active-section"]

    container = soup.find("div", class_="report-container")
    if container:
        container.insert(0, nav)
    else:
        h1 = soup.find("h1")
        if h1:
            h1.insert_after(nav)


def panel_label(index: int) -> str:
    """Return spreadsheet-like labels: A, B, ..., Z, AA, AB."""
    label = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


# --------------------------------------------------------------------------
# Figure grouping
# --------------------------------------------------------------------------

def unwrap_image_paragraphs(soup: BeautifulSoup) -> None:
    """Unwrap <p> wrappers around image-only content so img+caption become siblings."""
    for p in list(soup.find_all("p")):
        contents = list(p.contents)
        non_ws = [c for c in contents if not (isinstance(c, NavigableString) and str(c).strip() == "")]
        if not non_ws:
            continue
        allowed = True
        has_figure_element = False
        for c in contents:
            if isinstance(c, NavigableString):
                if str(c).strip() == "":
                    continue
                allowed = False
                break
            if c.name in ("img", "br"):
                if c.name == "img":
                    has_figure_element = True
                continue
            if c.name == "a" and c.get("name"):
                has_figure_element = True
                continue
            allowed = False
            break
        if not allowed or not has_figure_element:
            continue
        for child in list(p.contents):
            p.insert_before(child)
        p.decompose()


def process_figures_v2(soup: BeautifulSoup, asset_base: Path) -> None:
    """Group consecutive <img>s into <figure>, attach next 图N./表N. paragraph as caption."""
    unwrap_image_paragraphs(soup)

    imgs = list(soup.find_all("img"))
    processed = set()

    i = 0
    while i < len(imgs):
        img = imgs[i]
        if id(img) in processed:
            i += 1
            continue

        anchor = None
        prev = img.find_previous_sibling()
        while prev and prev.name == "br":
            prev = prev.find_previous_sibling()
        if prev and prev.name == "a" and prev.get("name"):
            anchor = prev

        img_group = [img]
        processed.add(id(img))
        nxt = img.find_next_sibling()
        while nxt and (nxt.name == "img" or nxt.name == "br" or (nxt.name == "a" and nxt.get("name"))):
            if nxt.name == "img":
                img_group.append(nxt)
                processed.add(id(nxt))
            elif nxt.name == "a" and nxt.get("name"):
                anchor = nxt
            nxt = nxt.find_next_sibling()

        while nxt and nxt.name == "br":
            nxt = nxt.find_next_sibling()

        caption = None
        if nxt and nxt.name == "p":
            text = nxt.get_text(strip=True)
            if re.match(r"^(图|表)\s*\d+[-\d]*[\.\s]", text):
                caption = nxt

        ref = anchor if anchor else img_group[0]
        ref_prev = ref.find_previous_sibling()
        ref_parent = ref.parent
        if ref_prev in img_group:
            ref_prev = img_group[0].find_previous_sibling()

        figure = soup.new_tag("figure", **{"class": "figure"})

        if anchor:
            anchor.extract()
            figure.append(anchor)

        # Multi-image figure groups go inside a horizontally-scrollable div
        # so the figure never overflows the report text column. Single-image
        # figures keep the simpler centered layout (no scroll wrapper).
        if len(img_group) >= 2:
            scroll_div = soup.new_tag("div", **{"class": "figure-scroll"})
            img_container = scroll_div
        else:
            scroll_div = None
            img_container = figure

        for img_in_group in img_group:
            img_in_group.extract()
            img_in_group.attrs.pop("width", None)
            img_in_group.attrs.pop("height", None)
            _set_img_display_size(img_in_group, len(img_group), asset_base)
            src = img_in_group.get("src", "")
            href = source_figure_href(src, asset_base)
            safe_href = html.escape(href, quote=True)
            a_wrapper = BeautifulSoup(
                f'<a class="img-link" href="{safe_href}" target="_blank" rel="noopener noreferrer" aria-label="查看原始图文件"></a>',
                "html.parser",
            )
            a_tag = a_wrapper.find("a")
            if len(img_group) >= 2:
                a_tag["data-panel-label"] = panel_label(len(img_container.find_all("a", recursive=False)))
                a_tag["aria-label"] = f"查看图版 {a_tag['data-panel-label']}"
            a_tag.append(img_in_group)
            img_container.append(a_tag)

        if scroll_div is not None:
            figure.append(scroll_div)

        if caption:
            for stray_img in list(caption.find_all("img")):
                stray_img.extract()
                caption.insert_before(stray_img)
            caption.extract()
            figcaption = soup.new_tag("figcaption")
            for content in list(caption.contents):
                figcaption.append(content)
            figure.append(figcaption)
            number = re.match(r"^(图|表)\s*(\d+)", figcaption.get_text(strip=True))
            if number:
                figure["data-figure-number"] = number.group(2)
        figure["data-panel-count"] = str(len(img_group))

        if ref_prev:
            ref_prev.insert_after(figure)
        elif ref_parent:
            ref_parent.insert(0, figure)

        nxt_after_fig = figure.find_next_sibling()
        while nxt_after_fig and nxt_after_fig.name == "br":
            br = nxt_after_fig
            nxt_after_fig = nxt_after_fig.find_next_sibling()
            br.decompose()

        i += 1


def validate_figure_galleries(soup: BeautifulSoup) -> dict[str, int]:
    """Check the final DOM: one gallery, one figure number, one shared caption."""
    for container in soup.select(".figure-scroll, .content-gallery, .result-rail"):
        if container.find("figure") is not None:
            raise ValueError("A gallery contains separately numbered figures; use one figure with a shared caption.")
    figures = soup.select("figure.figure")
    galleries = panels = 0
    for index, figure in enumerate(figures, start=1):
        images = figure.find_all("img")
        captions = figure.find_all("figcaption")
        if not images or len(captions) != 1 or figure.find("figure") is not None:
            raise ValueError(f"Figure {index} must have images and exactly one shared caption.")
        numbers = re.findall(r"(?:图|表)\s*(\d+)\s*[.．]", captions[0].get_text(" ", strip=True))
        if numbers != [str(index)]:
            raise ValueError(f"Gallery {index} must have one sequential figure number; got {numbers}.")
        if figure.get("data-figure-number", str(index)) != str(index):
            raise ValueError(f"Gallery {index} has inconsistent figure-number metadata.")
        if figure.get("data-panel-count", str(len(images))) != str(len(images)):
            raise ValueError(f"Gallery {index} has inconsistent panel-count metadata.")
        rails = figure.select(".figure-scroll")
        if len(images) > 1:
            if len(rails) != 1 or rails[0].find_all("img") != images:
                raise ValueError(f"Figure {index} must contain one gallery holding all its images.")
            links = rails[0].find_all("a", class_="img-link", recursive=False)
            labels = [link.get("data-panel-label") for link in links]
            expected = [panel_label(i) for i in range(len(images))]
            if labels != expected or any(len(link.find_all("img")) != 1 for link in links):
                raise ValueError(f"Figure {index} panel labels must be {expected}; got {labels}.")
            galleries += 1
        elif rails:
            raise ValueError(f"Standalone figure {index} has an unnecessary gallery wrapper.")
        panels += len(images)
    return {"figures": len(figures), "galleries": galleries, "panels": panels}


# --------------------------------------------------------------------------
# Misc post-processing
# --------------------------------------------------------------------------

def style_tables(soup: BeautifulSoup) -> None:
    for table in soup.find_all("table"):
        table["class"] = table.get("class", []) + ["data-table"]


def process_sample_table(soup: BeautifulSoup) -> None:
    tables = soup.find_all("table")
    if tables:
        tables[0]["class"] = tables[0].get("class", []) + ["sample-info"]


def fold_report_tables(soup: BeautifulSoup, closed_body_rows: int = 12) -> None:
    """Wrap every Markdown table in a collapsible block.

    Short tables stay open by default so core context remains visible. Long
    navigation tables start closed to keep result sections readable.
    """
    for table in list(soup.find_all("table")):
        if table.find_parent("details"):
            continue
        body_rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
        row_count = len(body_rows)

        headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
        header_label = " / ".join(headers[:3]) if headers else "长表格"
        details = soup.new_tag("details")
        is_long = row_count > closed_body_rows
        details["class"] = ["folded-table", "is-long-table" if is_long else "is-short-table"]
        details["data-row-count"] = str(row_count)
        if not is_long:
            details["open"] = ""
        summary = soup.new_tag("summary")
        summary.string = f"表格：{header_label}（{row_count} 行）"
        wrapper = table.wrap(details)
        wrapper.insert(0, summary)


# --------------------------------------------------------------------------
# Table preview sidecars
# --------------------------------------------------------------------------

def normalize_relative_resource_path(ref: str) -> str:
    normalized = ref.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def stable_table_id(path: str) -> str:
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]
    return f"tbl_{digest}"


def js_assignment(var_name: str, value) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"window.{var_name}={payload};\n"


def clean_cell_value(value):
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


COMMON_FIELD_DESCRIPTIONS = {
    "n_genes": "该细胞检测到的基因数量。",
    "n_genes_by_counts": "按 UMI/count 统计得到的检测基因数量。",
    "log1p_n_genes_by_counts": "n_genes_by_counts 经 log1p 转换后的数值。",
    "total_counts": "该细胞的总 UMI/count 数。",
    "log1p_total_counts": "total_counts 经 log1p 转换后的数值。",
    "pct_counts_in_top_20_genes": "表达量最高 20 个基因占该细胞总 counts 的比例。",
    "total_counts_mt": "线粒体基因对应的总 counts。",
    "log1p_total_counts_mt": "total_counts_mt 经 log1p 转换后的数值。",
    "pct_counts_mt": "线粒体基因 counts 占该细胞总 counts 的比例。",
    "total_counts_hb": "血红蛋白基因对应的总 counts。",
    "log1p_total_counts_hb": "total_counts_hb 经 log1p 转换后的数值。",
    "pct_counts_hb": "血红蛋白基因 counts 占该细胞总 counts 的比例。",
    "total_counts_ribo": "核糖体基因对应的总 counts。",
    "log1p_total_counts_ribo": "total_counts_ribo 经 log1p 转换后的数值。",
    "pct_counts_ribo": "核糖体基因 counts 占该细胞总 counts 的比例。",
    "outlier": "是否被整体 QC 指标判定为异常细胞。",
    "mt_outlier": "是否被线粒体比例相关规则判定为异常细胞。",
    "samples": "样本编号或来源样本标签。",
    "groups": "分析比较或样本分组标签。",
    "n_counts": "该细胞的总 counts 数，用于兼容部分单细胞工具字段命名。",
    "doublet_score": "Scrublet 双细胞评分。",
    "predicted_doublet": "Scrublet 是否预测该细胞为潜在双细胞。",
    "S_score": "细胞周期 S 期评分。",
    "G2M_score": "细胞周期 G2/M 期评分。",
    "phase": "根据细胞周期评分得到的细胞周期阶段。",
    "res_0_6": "Leiden resolution=0.6 的 cluster 编号。",
    "res_0_3": "父细胞类型子集内 Leiden resolution=0.3 的 cluster 编号。",
    "cell_types": "细胞类型注释标签。",
    "cells_lv2": "父细胞类型子集内的二级注释或亚型标签。",
    "UMAP1": "UMAP 第一维坐标。",
    "UMAP2": "UMAP 第二维坐标。",
    "tSNE1": "t-SNE 第一维坐标。",
    "tSNE2": "t-SNE 第二维坐标。",
    "cluster": "Leiden cluster 编号或分析使用的 cluster 标识。",
    "Cluster": "cluster 标识；在 SCSA 表中表示被注释的 Leiden cluster。",
    "annotation": "该 cluster 的最终注释类别。",
    "core_markers": "支持该注释的核心 marker 基因集合。",
    "confidence": "注释置信度或注释证据等级。",
    "annotation_basis": "注释依据，包括 marker、工具得分或人工整理信息。",
    "threshold_level": "marker 候选筛选使用的阈值层级。",
    "gene": "基因符号。",
    "group": "差异表达分析中的目标组、cluster、细胞类型或亚型。",
    "names": "差异表达基因名。",
    "scores": "差异表达检验统计量或工具输出评分。",
    "logfoldchanges": "目标组相对于参考组的 log fold change。",
    "pvals": "原始 P 值。",
    "pvals_adj": "多重检验校正后的 P 值。",
    "pct_nz_group": "目标组中该基因表达非零的细胞比例。",
    "pct_nz_reference": "参考组中该基因表达非零的细胞比例。",
    "delta_pct": "目标组与参考组表达非零比例的差值。",
    "Reg": "表达差异方向或调控标记。",
    "cell_types": "细胞类型或亚型标签。",
    "ncells": "对应 cluster 或细胞类型包含的细胞数。",
    "Cell Type": "SCSA 候选细胞类型。",
    "Z-score": "SCSA 输出的细胞类型匹配 Z-score。",
    "n_genes": "细胞数量或计数字段；在组成表中表示对应分组和细胞类型的细胞数。",
    "Cells": "CellChat 通讯矩阵中的发送细胞类型。",
    "from": "CellChat 通讯发送方细胞类型。",
    "to": "CellChat 通讯接收方细胞类型。",
    "pathway": "CellChat 通讯通路名称。",
    "prob": "CellChat 计算得到的通讯概率或通路通讯强度。",
    "Metrics": "Augur 分类评估指标名称。",
    "ONTOLOGY": "GO 本体类别，BP、CC 或 MF。",
    "ID": "富集条目、通路或数据库记录 ID。",
    "Description": "富集条目或通路名称。",
    "GeneRatio": "输入基因集中命中该条目的比例。",
    "BgRatio": "背景基因集中属于该条目的比例。",
    "pvalue": "富集分析原始 P 值。",
    "p.adjust": "多重检验校正后的富集 P 值。",
    "qvalue": "富集分析 q 值。",
    "geneID": "基因符号或基因标识。",
    "Count": "命中该条目的输入基因数量。",
    "category": "KEGG 通路一级分类。",
    "subcategory": "KEGG 通路二级分类。",
    "TF": "转录因子或 regulon 名称。",
    "target": "转录因子共表达网络中的目标基因。",
    "importance": "GRNBoost2 推断的 TF-target 边重要性评分。",
    "MotifID": "cisTarget motif 标识。",
    "AUC": "motif 富集曲线下面积。",
    "NES": "标准化富集分数。",
    "MotifSimilarityQvalue": "motif 相似性对应 q 值。",
    "OrthologousIdentity": "同源基因身份比例。",
    "Annotation": "motif 到转录因子的注释说明。",
    "Context": "regulon 推断使用的 motif 数据库、激活状态或筛选上下文。",
    "TargetGenes": "regulon 包含的目标基因及权重列表。",
    "RankAtMax": "富集曲线达到最大值时的排名位置。",
}


CELL_TYPE_FIELD_RE = re.compile(
    r"^(?:B cell|DC|EC|Fibroblast|Hepatocyte|Macrophage|Mast cell|Monocyte|NK cell|"
    r"Neutrophil|Pericyte|T cell|Tumor cell|Unknown|Mac[0-9]+)$"
)
GENE_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.-]{1,14}$")

PHNET_FIELD_DESCRIPTIONS = {
    "#node": "STRING 网络中的节点名称。",
    "#node1": "STRING 互作边的第一个蛋白节点。",
    "node2": "STRING 互作边的第二个蛋白节点。",
    "identifier": "STRING 节点标识符。",
    "node_degree": "STRING/PPI 网络中该节点的连接数。",
    "node1_string_id": "互作边第一个蛋白的 STRING ID。",
    "node2_string_id": "互作边第二个蛋白的 STRING ID。",
    "combined_score": "STRING 综合互作评分。",
    "neighborhood_on_chromosome": "STRING 染色体邻近证据评分。",
    "gene_fusion": "STRING 基因融合证据评分。",
    "phylogenetic_cooccurrence": "STRING 系统发育共现证据评分。",
    "homology": "STRING 同源性证据评分。",
    "coexpression": "STRING 共表达证据评分。",
    "experimentally_determined_interaction": "STRING 实验证据支持的互作评分。",
    "database_annotated": "STRING 数据库注释证据评分。",
    "automated_textmining": "STRING 文本挖掘证据评分。",
    "AverageShortestPathLength": "平均最短路径长度，节点到网络内其他可达节点的平均步数。",
    "BetweennessCentrality": "介数中心性，衡量节点位于其他节点最短路径上的程度。",
    "ClosenessCentrality": "接近中心性，反映节点到网络中其他节点的距离倒数。",
    "ClusteringCoefficient": "聚类系数，表示节点邻居之间彼此连接的密度。",
    "Degree": "度值，与该节点直接相连的边数量。",
    "degree.layout": "Cytoscape 布局辅助列，记录基于度值生成的布局属性。",
    "Eccentricity": "离心率，节点到网络中最远可达节点的最短路径长度。",
    "IsSingleNode": "是否为孤立节点。",
    "NeighborhoodConnectivity": "邻域连通度，节点邻居的平均连接数。",
    "NumberOfDirectedEdges": "有向边数量。",
    "NumberOfUndirectedEdges": "无向边数量。",
    "PartnerOfMultiEdgedNodePairs": "多重边配对节点数量。",
    "Radiality": "径向性，反映节点相对网络直径的中心程度。",
    "SelfLoops": "自环数量。",
    "Stress": "Stress 中心性，节点参与最短路径的次数。",
    "TopologicalCoefficient": "拓扑系数，衡量节点与邻域共享连接的程度。",
    "name": "网络节点名称或结果对象名称。",
    "shared name": "Cytoscape 共享节点名称。",
    "selected": "Cytoscape 选中状态。",
    "types": "网络节点类型，如中药、化学成分或基因靶点。",
    "node": "弦图或网络节点 ID。",
    "display_name": "图形中展示的节点名称。",
    "class": "节点类别或绘图分组。",
    "community": "网络社区或模块分组。",
    "node_color": "节点绘图颜色。",
    "edge_color": "边绘图颜色。",
    "edge_type": "网络边类型。",
    "source": "网络边的来源节点或来源分组。",
    "target": "网络边的目标节点。",
    "source_class": "来源节点类别。",
    "target_class": "目标节点类别。",
    "source_degree": "来源节点的连接数。",
    "target_degree": "目标节点的连接数。",
    "source_colors": "来源节点或来源分组颜色。",
    "sources": "与该节点相连的来源对象集合。",
    "targets": "与该节点相连的目标对象集合。",
    "n_sources": "来源对象数量。",
    "n_targets": "目标对象数量。",
    "connected_ingredients": "与该节点连接的成分集合。",
    "n_connected_ingredients": "与该节点连接的成分数量。",
    "ingredient_source_degree": "成分作为来源节点时的连接数。",
    "ingredient_target_degree": "成分作为目标节点时的连接数。",
    "class_degree": "同一节点类别内的连接数。",
    "radius": "绘图节点半径。",
    "label_radius": "节点标签绘制半径。",
    "label_shown": "节点标签是否在图中显示。",
    "label_text": "图中显示的节点标签文本。",
    "label_tier": "标签显示层级。",
    "x": "绘图布局 X 坐标。",
    "y": "绘图布局 Y 坐标。",
    "angle_deg": "弦图角度位置，单位为度。",
    "angle_deg_mod360": "转换到 0-360 度范围后的弦图角度。",
    "color": "绘图颜色。",
    "ingredients": "该来源节点连接的成分列表。",
    "n_ingredients": "该来源节点连接的成分数量。",
    "nodes": "网络节点名称集合。",
    "MOL_ID": "中药化学成分数据库 ID。",
    "ingredient": "中药化学成分名称。",
    "molecule_ID": "TCMSP 小分子成分 ID。",
    "molecule_name": "TCMSP 小分子成分名称。",
    "target_name": "成分关联的蛋白或基因名称。",
    "UniProt ID": "UniProt 蛋白 ID。",
    "not_found": "未匹配到 UniProt ID 的目标名称。",
    "Score": "BATMAN-TCM 成分-蛋白关联评分。",
    "herb_name": "中药中文名。",
    "herb_en_name": "中药拉丁名或英文名。",
    "herb_pinyin": "中药拼音名。",
    "ch_name": "中药中文名。",
    "upper": "标准化后的大写名称。",
    "ob": "口服生物利用度 (oral bioavailability)。",
    "dl": "类药性 (drug-likeness) 指标。",
    "caco2": "Caco-2 细胞通透性预测值。",
    "bbb": "血脑屏障通透性预测值。",
    "mw": "分子量。",
    "alogp": "脂水分配系数预测值。",
    "hacc": "氢键受体数量。",
    "hdon": "氢键供体数量。",
    "halflife": "预测半衰期。",
    "file_ID": "来源文件或药材文件标识。",
    "set": "Venn 集合区域名称。",
    "Herbs": "人参相关蛋白节点集合。",
    "chronic_heart_failure": "chronic heart failure 疾病基因集合。",
    "intersection_gene_list": "对应集合区域中的交集基因列表。",
    "count": "该集合区域包含的基因数量。",
    "Name": "分子对接中的小分子成分名称。",
    "Affinity (kcal/mol)": "AutoDock Vina 预测亲和力评分，单位为 kcal/mol。",
    "pdb_id": "受体蛋白结构 ID。",
    "pse_file_name": "PyMOL 会话文件名。",
    "plip_input_pdb_file_name": "PLIP 相互作用解析使用的 PDB 文件名。",
}


# The delivery reports produced by this renderer contain result tables from
# several distinct statistical layers.  A column name such as ``score``,
# ``value`` or ``source`` is therefore not self-describing by itself.  Keep a
# small schema registry for those columns whose meaning changes with the
# table, and use the field-name registry below for stable semantics shared by
# multiple modules.  This registry is intentionally kept in the renderer
# source so a rebuilt report and its preview sidecars always agree.
SCHEMA_FIELD_DESCRIPTIONS = {
    "cohort_summary.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "cohort_role": "该队列在本项目中的分析角色。",
        "platform_scope": "队列所使用的表达平台及数据范围。",
        "input_type": "进入当前分析的表达数据类型。",
        "sample_count": "该队列纳入分析的完整样本数（按样本计）。",
        "group_counts": "该队列各比较分组的样本数汇总。",
        "complete_paired_case_count": "同时具有两种配对分组样本的完整病例数。",
        "sample_exclusion_count": "在样本级 QC 中排除的样本数。",
        "clinical_scope": "该队列是否包含本模块使用的临床变量。",
        "feature_count_before_filter": "特征过滤前的特征数。",
        "feature_count_after_filter_or_gene_collapse": "过滤或基因合并后的特征数。",
        "feature_filter_or_normalization": "特征过滤及归一化所用规则。",
        "normalization": "表达矩阵归一化方法及表达尺度。",
        "processing_scope": "当前表覆盖的数据处理范围。",
    },
    "sample_qc.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "sample_id": "表达样本唯一标识。",
        "sample_order": "样本在 QC 输出中的固定顺序。",
        "group": "样本所属的比较分组。",
        "pair_id": "配对设计中的病例或配对编号。",
        "sample_status": "样本级 QC 保留或排除状态。",
        "sample_exclusion_reason": "样本级 QC 排除原因。",
        "raw_library_size_million": "原始测序文库大小，单位为百万 reads/counts。",
        "detected_feature_count": "该样本检测到的表达特征数。",
        "tmm_norm_factor": "edgeR TMM 归一化因子。",
        "tmm_effective_library_size": "应用 TMM 因子后的有效文库大小。",
        "raw_missing_fraction": "原始表达矩阵中缺失值所占比例。",
        "raw_log2_median": "原始 log2 表达值的样本中位数。",
        "raw_log2_IQR": "原始 log2 表达值的四分位距。",
        "normalized_median": "归一化表达值的样本中位数。",
        "normalized_IQR": "归一化表达值的四分位距。",
        "logCPM_median": "logCPM 表达值的样本中位数。",
        "logCPM_IQR": "logCPM 表达值的四分位距。",
        "detection_pval_le_0.05_count": "检测 P 值不超过 0.05 的特征数。",
        "detection_pval_available_count": "具有可用检测 P 值的特征数。",
    },
    "sample_qc_summary.full.tsv": {
        "dataset": "公共单细胞数据集或队列标识。",
        "sample_id": "单细胞样本唯一标识。",
        "library_id": "单细胞测序文库唯一标识。",
        "patient_id": "样本对应的病例或患者标识。",
        "group": "样本所属的比较分组。",
        "pair_id": "配对设计中的病例或配对编号。",
        "donor_id": "样本对应的供体或病例标识。",
        "donor_replicate": "供体内的样本或技术重复标识。",
        "n_genes_in_library": "该样本文库中可用的基因数。",
        "n_cells_input": "进入该样本 QC 的细胞数。",
        "n_cells_after_fixed_rules": "通过该样本固定 QC 规则后的细胞数。",
        "n_cells_after_mad": "通过该样本 MAD 异常值过滤后的细胞数。",
        "n_cells_scrublet_doublet": "该样本被 Scrublet 判为潜在双细胞的数量。",
        "n_cells_retained": "该样本最终保留的细胞数。",
        "n_cells_removed_total": "该样本 QC 累计移除的细胞数。",
        "retained_fraction": "该样本最终保留细胞占输入细胞的比例。",
        "median_n_genes": "该样本每个细胞检测基因数的中位数。",
        "median_total_counts": "该样本每个细胞总计数的中位数。",
        "median_pct_mt": "该样本每个细胞线粒体转录本比例的中位数。",
        "median_pct_ribo": "该样本每个细胞核糖体转录本比例的中位数。",
        "median_pct_hb": "该样本每个细胞血红蛋白相关转录本比例的中位数。",
        "scrublet_threshold": "该样本使用的 Scrublet 双细胞分数阈值。",
        "scrublet_predicted_doublet_fraction": "该样本被 Scrublet 判为潜在双细胞的比例。",
        "scrublet_expected_doublet_rate": "该样本按文库规模估计的预期双细胞率。",
    },
    "sample_exclusion_audit.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "sample_id": "表达样本唯一标识。",
        "sample_order": "样本在 QC 输出中的固定顺序。",
        "group": "样本所属的比较分组。",
        "pair_id": "配对设计中的病例或配对编号。",
        "candidate_sample": "是否为当前候选样本。",
        "sample_level_decision": "样本级纳入或排除判定。",
        "exclusion_reason": "样本级排除原因。",
        "feature_filtering_scope": "该样本所使用的特征过滤范围。",
    },
    "model.full.tsv": {
        "feature_id": "差异表达模型中的特征或探针编号。",
        "gene_symbol": "特征对应的基因符号。",
        "dataset": "公共表达数据集或队列标识。",
        "contrast_id": "差异比较的唯一标识。",
        "model": "差异表达拟合模型名称。",
        "design_formula": "差异表达模型的设计公式。",
        "contrast_definition": "实验组与对照组的比较定义及方向。",
        "logFC": "实验组相对于对照组的 log2 fold change。",
        "p_value": "差异表达检验的原始 P 值。",
        "FDR": "差异表达检验经多重检验校正后的 FDR（Benjamini–Hochberg 校正 P 值）。",
        "model_logCPM": "edgeR 模型中的平均 logCPM 表达水平。",
        "model_AveExpr": "limma 模型中的平均表达水平。",
        "model_F": "edgeR quasi-likelihood 差异检验的 F 统计量。",
        "model_t": "limma 差异检验的 t 统计量。",
        "model_B": "limma 拟合的 B 统计量（对数优势）。",
        "tested": "该特征是否进入差异检验。",
        "filter_rule": "交付筛选使用的统计阈值与规则。",
        "pass_filter": "该特征是否通过交付筛选。",
        "rank_p": "按原始 P 值从小到大排序的位置。",
    },
    "LDHA_expression.stat.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "contrast_id": "LDHA 表达比较的唯一标识。",
        "role": "该行在 LDHA 表达分析中的分析角色。",
        "gene_symbol": "检验的基因符号（LDHA）。",
        "feature_id": "表达矩阵中的特征或探针编号。",
        "tumor_group": "实验组肿瘤分组标签。",
        "control_group": "对照组分组标签。",
        "paired": "该比较是否按病例配对。",
        "statistical_unit": "效应和检验所使用的统计单位。",
        "test_method": "组间差异检验方法。",
        "n_tumor_samples": "实验组肿瘤样本数。",
        "n_control_samples": "对照组样本数。",
        "n_tumor_units": "实验组统计单位数。",
        "n_control_units": "对照组统计单位数。",
        "n_pairs": "可用于配对检验的完整配对数。",
        "n_units": "该比较实际使用的统计单位总数。",
        "mean_tumor": "实验组的平均表达值。",
        "mean_control": "对照组的平均表达值。",
        "mean_difference_tumor_minus_control": "实验组减对照组的平均表达差值。",
        "effect_type": "效应量的定义或类型。",
        "effect_raw": "原始表达尺度上的效应量。",
        "effect_size": "标准化后的组间效应量。",
        "ci_low": "效应量置信区间下限。",
        "ci_high": "效应量置信区间上限。",
        "p_value_model": "模型检验的原始 P 值。",
        "p_adj_model": "模型检验经多重检验校正后的 P 值。",
        "p_adj_plot_family": "同一绘图结果族内校正后的 P 值。",
        "p_display": "用于图形标注的格式化原始 P 值。",
        "significance": "根据预设阈值标记的显著性状态。",
    },
    "LDHA_standardized_effect.stat.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "contrast_id": "LDHA 表达比较的唯一标识。",
        "role": "该行在标准化效应分析中的分析角色。",
        "gene_symbol": "检验的基因符号（LDHA）。",
        "feature_id": "表达矩阵中的特征或探针编号。",
        "tumor_group": "实验组肿瘤分组标签。",
        "control_group": "对照组分组标签。",
        "paired": "该比较是否按病例配对。",
        "statistical_unit": "效应和检验所使用的统计单位。",
        "test_method": "组间差异检验方法。",
        "n_tumor_samples": "实验组肿瘤样本数。",
        "n_control_samples": "对照组样本数。",
        "n_tumor_units": "实验组统计单位数。",
        "n_control_units": "对照组统计单位数。",
        "n_pairs": "可用于配对检验的完整配对数。",
        "n_units": "该比较实际使用的统计单位总数。",
        "mean_tumor": "实验组的平均表达值。",
        "mean_control": "对照组的平均表达值。",
        "mean_difference_tumor_minus_control": "实验组减对照组的平均表达差值。",
        "effect_type": "效应量的定义或类型。",
        "effect_raw": "原始表达尺度上的效应量。",
        "effect_size": "标准化后的组间效应量。",
        "ci_low": "效应量置信区间下限。",
        "ci_high": "效应量置信区间上限。",
        "p_value_model": "模型检验的原始 P 值。",
        "p_adj_model": "模型检验经多重检验校正后的 P 值。",
        "p_adj_plot_family": "同一绘图结果族内校正后的 P 值。",
        "p_display": "用于图形标注的格式化原始 P 值。",
        "significance": "根据预设阈值标记的显著性状态。",
    },
    "LDHA_sample_expression.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "sample_id": "表达样本唯一标识。",
        "sample_order": "样本在表达图中的固定顺序。",
        "group": "样本所属的比较分组。",
        "group_original": "原始样本分组标签。",
        "patient_id": "病例或患者唯一标识。",
        "pair_id": "配对设计中的病例或配对编号。",
        "statistical_unit": "表达汇总所使用的统计单位。",
        "feature_id": "表达矩阵中的特征或探针编号。",
        "gene_symbol": "表达特征对应的基因符号（LDHA）。",
        "expression_scale": "表达值使用的数值尺度。",
        "expression_value": "该样本在指定尺度上的 LDHA 表达值。",
    },
    "apparent_ROC.stat.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "contrast_id": "ROC 比较的唯一标识。",
        "role": "该行在 ROC 分析中的分析角色。",
        "endpoint": "ROC 分析所区分的结局或分组。",
        "analysis_status": "ROC 分析是否完成及其状态。",
        "roc_method": "ROC 曲线及 AUC 的计算方法。",
        "n": "ROC 分析纳入的样本数。",
        "n_tumor": "ROC 分析中的肿瘤样本数。",
        "n_control": "ROC 分析中的对照样本数。",
        "auc": "ROC 曲线下面积。",
        "auc_ci_low": "AUC 置信区间下限。",
        "auc_ci_high": "AUC 置信区间上限。",
        "auc_ci_method": "AUC 置信区间的计算方法。",
        "direction": "表达值用于 ROC 判别时的方向。",
        "threshold": "ROC 判别阈值。",
        "sensitivity": "ROC 判别灵敏度。",
        "specificity": "ROC 判别特异度。",
        "eligibility": "该 ROC 结果是否满足预设纳入条件。",
    },
    "integration_metrics.full.tsv": {
        "representation": "用于计算整合指标的表示路线（未校正、Harmony 或 scVI）。",
        "metric": "单细胞样本混合或整合质量指标名称。",
        "scope": "该指标的计算范围。",
        "value": "所列整合质量指标的数值。",
        "n_cells": "该指标计算使用的细胞数。",
        "interpretation": "该指标数值的统计解释。",
    },
    "cluster_stability.full.tsv": {
        "representation": "用于聚类稳定性评估的表示路线。",
        "primary_n_neighbors": "主分析邻居图使用的邻居数。",
        "sensitivity_n_neighbors": "敏感性分析邻居图使用的邻居数。",
        "n_cells": "聚类稳定性评估使用的细胞数。",
        "adjusted_rand_index": "两次聚类标签之间的调整 Rand 指数。",
        "normalized_mutual_info": "两次聚类标签之间的标准化互信息。",
    },
    "cluster_sample_support.full.tsv": {
        "representation": "样本来源稳定性评估使用的单细胞表示路线。",
        "cluster": "Leiden cluster 编号。",
        "n_cells": "该 cluster 包含的细胞数。",
        "n_samples_present": "该 cluster 中出现的样本数。",
        "dominant_sample": "该 cluster 中细胞数占比最高的样本。",
        "dominant_sample_fraction": "主导样本占该 cluster 细胞的比例。",
        "sample_entropy": "cluster 细胞样本来源分布的 Shannon 熵。",
        "sample_entropy_normalized": "按样本数归一化后的样本来源 Shannon 熵。",
        "dominant_group": "该 cluster 中细胞数占比最高的比较分组。",
        "n_groups_present": "该 cluster 中出现的比较分组数。",
        "accession": "公共单细胞数据集 accession。",
        "n_donors_present": "该 cluster 中出现的供体数。",
        "dominant_donor": "该 cluster 中细胞数占比最高的供体。",
        "dominant_donor_fraction": "主导供体占该 cluster 细胞的比例。",
    },
    "infercnv_cell_scores.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "infercnv_burden": "该细胞相对于参考细胞的 inferCNV burden 汇总值。",
        "coherent_arm_count": "该细胞具有一致 CNV 信号的染色体臂数量。",
        "coherent_arm_fraction": "具有一致 CNV 信号的染色体臂占比。",
        "infercnv_cluster": "inferCNV 对该细胞分配的表达/CNV profile cluster。",
        "infercnv_status": "该细胞 inferCNV 计算状态。",
    },
    "infercnv_cell_classification.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "sample_id": "单细胞样本唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "source": "细胞注释或 inferCNV 输入的来源对象。",
        "original_annotation": "进入 inferCNV 前的原始细胞注释。",
        "annotation_column": "原始细胞注释所在的元数据列。",
        "annotation_review_excluded": "该细胞是否因注释复核被排除。",
        "infercnv_eligibility": "该细胞是否满足 inferCNV 分析纳入条件。",
        "infercnv_eligibility_reason": "该细胞被纳入或排除 inferCNV 的原因。",
        "representation": "使用的单细胞整合表示路线。",
        "candidate_annotation": "候选细胞的原始注释标签。",
        "reference_lineage": "参考正常谱系的注释标签。",
        "role": "细胞在 inferCNV 分析中的候选或参考角色。",
        "infercnv_group": "inferCNV 分组或分层标签。",
        "infercnv_burden": "该细胞相对于参考细胞的 inferCNV burden 汇总值。",
        "reference_median": "参考细胞 burden 的中位数。",
        "reference_mad": "参考细胞 burden 的 median absolute deviation。",
        "reference_95th_percentile": "参考细胞 burden 的 95% 分位数。",
        "primary_burden_threshold": "主规则使用的 inferCNV burden 阈值。",
        "infercnv_cluster": "inferCNV 对该细胞分配的 profile cluster。",
        "cluster_source": "inferCNV cluster 标签的来源。",
        "coherent_arm_count": "该细胞具有一致 CNV 信号的染色体臂数量。",
        "coherent_arm_fraction": "具有一致 CNV 信号的染色体臂占比。",
        "burden_high": "该细胞 burden 是否超过主规则阈值。",
        "coherent_arm_evidence": "支持一致染色体臂信号的证据状态。",
        "cluster_consistency": "该细胞所在 cluster 的分类一致性状态。",
        "tumor_enrichment": "该 cluster 在候选肿瘤细胞中的富集指标。",
        "infercnv_status": "该细胞 inferCNV 计算状态。",
        "final_class": "inferCNV 纯化后的最终细胞类别。",
        "classification_reason": "最终细胞分类的判定依据。",
        "candidate_or_reference": "该细胞属于候选细胞还是参考细胞。",
    },
    "infercnv_input_cells.full.tsv": {
        "cell_id": "进入 inferCNV 的细胞条形码或细胞唯一标识。",
        "sample_id": "进入 inferCNV 的单细胞样本标识。",
        "donor_id": "进入 inferCNV 的供体或病例标识。",
        "original_annotation": "进入 inferCNV 前的原始细胞注释。",
        "annotation_column": "原始细胞注释所在的元数据列。",
        "annotation_review_excluded": "该细胞是否因注释复核被排除在 inferCNV 输入之外。",
        "infercnv_eligibility": "该细胞是否满足 inferCNV 分析纳入条件。",
        "infercnv_eligibility_reason": "该细胞被纳入或排除 inferCNV 的原因。",
        "candidate_annotation": "候选细胞的原始注释标签。",
        "reference_lineage": "参考正常谱系的注释标签。",
    },
    "malignant_cells.filtered.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "sample_id": "单细胞样本唯一标识。",
        "infercnv_burden": "该细胞相对于参考细胞的 inferCNV burden 汇总值。",
        "infercnv_status": "该细胞 inferCNV 计算状态。",
        "final_class": "inferCNV 纯化后的最终细胞类别。",
    },
    "infercnv_donor_sensitivity.full.tsv": {
        "threshold_id": "inferCNV 敏感性分析阈值方案编号。",
        "k": "阈值方案使用的参考分布倍数参数。",
        "reference_quantile": "参考细胞 burden 使用的分位点。",
        "burden_threshold": "该阈值方案使用的 inferCNV burden 阈值。",
        "donor_id": "供体或病例唯一标识。",
        "n_candidate": "该供体候选细胞数。",
        "n_malignant_high_confidence": "该供体被判为高置信恶性细胞的数量。",
        "n_uncertain": "该供体被判为 uncertain 的细胞数量。",
        "malignant_fraction_of_candidate": "高置信恶性细胞占候选细胞的比例。",
        "uncertain_excluded_from_downstream": "不确定细胞是否从下游分析排除。",
    },
    "infercnv_threshold_sensitivity.full.tsv": {
        "threshold_id": "inferCNV 敏感性分析阈值方案编号。",
        "k": "阈值方案使用的参考分布倍数参数。",
        "reference_quantile": "参考细胞 burden 使用的分位点。",
        "reference_median": "参考细胞 burden 的中位数。",
        "reference_mad": "参考细胞 burden 的 median absolute deviation。",
        "reference_quantile_value": "参考细胞 burden 在指定分位点的数值。",
        "burden_threshold": "该阈值方案使用的 inferCNV burden 阈值。",
        "n_candidate": "候选细胞总数。",
        "n_malignant_high_confidence": "被判为高置信恶性细胞的数量。",
        "n_uncertain": "被判为 uncertain 的细胞数量。",
        "n_normal_like_candidate": "候选细胞中被判为 normal-like 的数量。",
        "cluster_evidence_rule": "用于 cluster 证据判断的规则。",
    },
    "infercnv_statistical_tests.full.tsv": {
        "metric": "inferCNV 统计检验的指标名称。",
        "comparison": "统计检验比较的两类细胞或供体集合。",
        "statistical_unit": "统计检验使用的统计单位。",
        "n_candidate_donors": "候选肿瘤供体数。",
        "n_reference_donors": "参考供体数。",
        "test_method": "统计检验方法。",
        "paired": "该比较是否按供体配对。",
        "raw_p_value": "统计检验的原始 P 值。",
        "adjusted_p_value": "统计检验经多重检验校正后的 P 值。",
        "adjustment_method": "多重检验校正方法。",
        "significance_label": "根据校正 P 值生成的显著性标签。",
        "cell_level_p_values_used": "统计检验是否使用细胞层面 P 值。",
    },
    "target_expression.full.tsv": {
        "sample_id": "表达样本唯一标识。",
        "target": "当前重分析的目标基因或特征名称。",
        "expression": "目标基因在该样本指定表达尺度上的表达值。",
        "group": "样本所属的比较分组。",
        "patient_id": "病例或患者唯一标识。",
        "paired": "该样本是否属于配对比较。",
        "patient_number": "配对病例在当前数据中的顺序编号。",
        "source_probe_count": "映射到该目标基因的探针数量。",
        "expression_scale": "目标表达值使用的数值尺度。",
        "evidence_boundary": "该表结果的证据范围和使用边界。",
    },
    "probe_annotation.full.tsv": {
        "ID_REF": "平台注释中的探针或特征唯一标识。",
        "Database_ID": "平台注释数据库中的探针或特征编号。",
        "gene_symbol": "探针对应的基因符号。",
        "mapping_status": "探针到基因标识的映射状态。",
        "analysis_role": "该探针注释记录在当前重分析中的作用。",
        "evidence_boundary": "该探针注释结果的证据范围和使用边界。",
        "Gene.symbol": "探针对应的基因符号。",
        "Gene.ID": "探针对应的基因数据库编号。",
        "Gene.title": "探针对应的基因功能或注释标题。",
    },
    "pathway_scores.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "sample_id": "通路评分对应的样本唯一标识。",
        "patient_id": "通路评分对应的病例或患者标识。",
        "patient_number": "配对病例在当前通路评分数据中的顺序编号。",
        "group": "样本所属的比较分组。",
        "pathway": "通路或基因集名称。",
        "score": "指定通路的样本级标准化评分。",
        "score_scale": "通路评分所使用的数值尺度。",
    },
    "association_statistics.full.tsv": {
        "association_id": "相关性分析记录编号。",
        "context": "相关性分析的疾病、组织或分层背景。",
        "x_metric": "相关性分析横轴指标名称。",
        "y_metric": "相关性分析纵轴指标名称。",
        "n": "相关性分析纳入的统计单位数。",
        "p_adjust_method": "相关性检验 P 值使用的多重校正方法。",
    },
    "association_pairs.full.tsv": {
        "association_id": "相关性分析记录编号。",
        "context": "相关性分析的疾病、组织或分层背景。",
        "x_metric": "相关性分析横轴指标名称。",
        "y_metric": "相关性分析纵轴指标名称。",
        "n": "相关性分析纳入的统计单位数。",
        "p_adjust_method": "相关性检验 P 值使用的多重校正方法。",
    },
    "candidate_association.full.tsv": {
        "context": "候选关联分析的疾病、组织或分层背景。",
        "n": "候选关联分析纳入的统计单位数。",
        "p_adjust_method": "候选关联检验 P 值使用的多重校正方法。",
    },
    "target_paired_statistics.full.tsv": {
        "p_adjust_method": "配对目标表达检验 P 值使用的多重校正方法。",
    },
    "candidate_paired_statistics.full.tsv": {
        "p_adjust_method": "配对候选表达检验 P 值使用的多重校正方法。",
    },
    "pathway_paired_statistics.full.tsv": {
        "p_adjust_method": "配对通路评分检验 P 值使用的多重校正方法。",
    },
    "paired_statistics.full.tsv": {
        "feature": "配对比较中检验的基因、目标或通路特征。",
        "family": "特征所属的统计分析家族。",
        "contrast": "肿瘤与癌旁样本的配对比较定义。",
        "statistical_unit": "配对效应和检验使用的统计单位。",
        "paired": "该比较是否按病例或供体配对。",
        "n_tumor": "实验组肿瘤样本或统计单位数。",
        "n_adjacent": "对照组癌旁样本或统计单位数。",
        "n_pairs": "可用于配对检验的完整配对数。",
        "mean_tumor": "实验组肿瘤的平均表达或评分。",
        "mean_adjacent": "对照组癌旁的平均表达或评分。",
        "effect": "实验组减对照组的配对效应量。",
        "ci_low": "配对效应量置信区间下限。",
        "ci_high": "配对效应量置信区间上限。",
        "test": "配对比较使用的统计检验。",
        "p_value": "配对比较检验的原始 P 值。",
        "p_adjust": "配对比较经多重检验校正后的 P 值。",
        "p_adjust_method": "配对比较 P 值使用的多重校正方法。",
        "significance": "根据校正 P 值阈值生成的显著性状态。",
        "inference_eligible": "该配对比较是否达到预设样本量并可进行推断。",
        "evidence_boundary": "该配对统计结果的证据范围和使用边界。",
    },
    "filter_counts.full.tsv": {
        "stage_order": "样本级过滤流程中的阶段顺序。",
        "removed_from_previous": "该阶段相对于上一阶段移除的样本或细胞数。",
        "removed_total": "该阶段累计移除的样本或细胞总数。",
    },
    "spatial_centroids.full.tsv": {
        "coordinate_source": "空间坐标的来源对象或坐标文件。",
        "unit_type": "空间质心汇总单位类型（细胞类型或 cluster）。",
        "unit_id": "空间质心汇总单位的唯一标识。",
        "cell_type": "空间质心对应的细胞类型标签。",
        "n_cells": "计算空间质心所使用的细胞数。",
        "centroid_x": "空间质心的 X 坐标。",
        "centroid_y": "空间质心的 Y 坐标。",
        "review_gate": "空间质心是否通过坐标复核门控。",
    },
    "spatial_nearest_neighbors.full.tsv": {
        "coordinate_source": "空间坐标的来源对象或坐标文件。",
        "cell_id": "空间邻居关系中的中心细胞标识。",
        "neighbor_rank": "按空间距离排序的邻居位置。",
        "neighbor_cell_id": "空间邻近关系中的邻居细胞标识。",
        "distance": "中心细胞与邻居细胞之间的空间距离。",
        "review_gate": "空间邻居结果是否通过坐标复核门控。",
    },
    "spatial_review.full.tsv": {
        "coordinate_source": "空间坐标的来源对象或坐标文件。",
        "n_coordinate_cells": "具有可用空间坐标的细胞数。",
        "review_gate": "空间坐标复核门控状态。",
        "review_state": "空间坐标人工复核状态。",
        "reviewer_id": "空间坐标复核人员或复核记录标识。",
        "review_scope": "空间坐标复核覆盖的对象范围。",
        "review_boundary": "空间坐标复核结果的适用边界。",
    },
    "candidate_bulk_evidence.full.tsv": {
        "candidate": "候选基因名称。",
        "dataset": "公共表达数据集或队列标识。",
        "contrast_id": "bulk 差异比较的唯一标识。",
        "analysis_role": "该记录在 bulk 候选证据中的分析角色。",
        "group1": "比较中的实验组标签。",
        "group2": "比较中的对照组标签。",
        "control_role": "对照组在当前比较中的角色。",
        "paired": "该 bulk 比较是否按病例配对。",
        "feature_id": "bulk 表达矩阵中的特征编号。",
        "feature_count": "当前证据记录对应的特征数。",
        "tested": "该候选特征是否进入差异检验。",
        "detection_status": "候选特征的表达检出状态。",
        "effect_value": "候选特征在当前 bulk 比较中的效应量。",
        "p_value": "当前 bulk 检验的原始 P 值。",
        "FDR": "当前 bulk 检验经多重检验校正后的 FDR。",
        "model_expression": "差异模型中的平均表达量。",
        "filter_rule_source": "bulk 筛选规则的来源。",
        "source_model": "产生 bulk 统计量的模型名称。",
        "direction": "候选特征的表达差异方向。",
        "n_group1": "实验组样本或统计单位数。",
        "n_group2": "对照组样本或统计单位数。",
        "n_pairs": "完整配对样本数。",
        "expression_detection_status": "候选表达检出规则的判定状态。",
        "effect_type": "候选效应量的定义或类型。",
        "nominal_pass": "候选是否通过名义 P 值/效应量条件。",
        "fdr_pass": "候选是否通过 FDR 条件。",
        "effect_abs": "候选效应量的绝对值。",
        "effect_threshold_pass": "候选是否通过效应量阈值。",
        "effect_strict_pass": "候选是否通过严格效应量条件。",
        "candidate_class": "候选基因的分类标签。",
        "candidate_source_status": "候选来源记录的状态。",
        "prior_evidence_status": "候选已有证据的状态。",
        "candidate_source": "候选基因进入当前列表的来源。",
        "scrna_evidence_status": "该候选的单细胞证据状态。",
    },
    "endpoint_audit.full.tsv": {
        "endpoint": "生存或临床结局终点名称。",
        "definition": "结局终点的时间和事件定义。",
        "event_label": "事件样本使用的事件标签。",
        "censor_label": "删失样本使用的删失标签。",
        "n": "该临床终点纳入的病例数。",
        "events": "该临床终点发生事件的病例数。",
        "censored": "该临床终点被删失的病例数。",
        "missing_time_or_event": "缺少随访时间或事件状态的病例数。",
        "followup_min_days": "随访时间最小值，单位为天。",
        "followup_median_days": "随访时间中位数，单位为天。",
        "followup_max_days": "随访时间最大值，单位为天。",
        "status": "临床终点数据审计状态。",
        "reason": "临床终点纳入或审计状态的原因。",
    },
    "LDHA_continuous_Cox.full.tsv": {
        "endpoint": "Cox 模型拟合的生存终点名称。",
        "model_type": "Cox 模型类型。",
        "variable": "Cox 模型中的解释变量。",
        "n": "Cox 模型纳入的病例数。",
        "events": "Cox 模型中观察到的事件数。",
        "parameter_count": "Cox 模型估计的参数数量。",
        "events_per_parameter": "每个模型参数对应的事件数。",
        "effect_unit": "模型效应量对应的变量单位。",
        "hazard_ratio": "Cox 模型估计的风险比。",
        "ci_low": "风险比置信区间下限。",
        "ci_high": "风险比置信区间上限。",
        "p_value": "Cox 模型检验的原始 P 值。",
        "status": "Cox 模型拟合状态。",
        "reason": "Cox 模型结果状态的原因。",
    },
    "lncrna2target_atb_ldha.filtered.tsv": {
        "lncrna_name_in_paper": "文献中记录的 lncRNA 名称。",
        "lncrna_official_symbol": "标准化后的 lncRNA 官方符号。",
        "lncrna_entrez_id": "lncRNA 的 Entrez Gene ID。",
        "target_symbol_in_paper": "文献中记录的目标基因符号。",
        "target_official_symbol": "标准化后的目标基因官方符号。",
        "target_entrez_id": "目标基因的 Entrez Gene ID。",
        "disease_state": "文献记录的疾病或处理状态。",
        "lncrna_experiment": "文献中 lncRNA 相关实验描述。",
        "pmid": "支持该记录的 PubMed 文献编号。",
        "is_ldha": "该记录的目标是否为 LDHA。",
        "reference": "该 lncRNA–目标关系的文献引用。",
    },
    "lncrna2target_atb_targets.full.tsv": {
        "lncrna_name_in_paper": "文献中记录的 lncRNA 名称。",
        "lncrna_official_symbol": "标准化后的 lncRNA 官方符号。",
        "lncrna_entrez_id": "lncRNA 的 Entrez Gene ID。",
        "target_symbol_in_paper": "文献中记录的目标基因符号。",
        "target_official_symbol": "标准化后的目标基因官方符号。",
        "target_entrez_id": "目标基因的 Entrez Gene ID。",
        "disease_state": "文献记录的疾病或处理状态。",
        "lncrna_experiment": "文献中 lncRNA 相关实验描述。",
        "pmid": "支持该记录的 PubMed 文献编号。",
        "is_ldha": "该记录的目标是否为 LDHA。",
        "reference": "该 lncRNA–目标关系的文献引用。",
    },
    "lncrna2target_ldha_high_throughput_context.full.tsv": {
        "species_id": "高通量实验使用的物种标识。",
        "experiment_id": "高通量实验的唯一标识。",
        "lncrna_name": "高通量实验中的 lncRNA 名称。",
        "gene_symbol": "高通量实验中的目标基因符号。",
        "entrez_gene_id": "目标基因的 Entrez Gene ID。",
        "log2fc": "高通量实验中的 log2 fold change。",
        "p_value": "高通量实验统计检验的原始 P 值。",
        "adjusted_p_value": "高通量实验经多重检验校正后的 P 值。",
        "direction": "高通量实验的表达变化方向。",
        "is_atb_experiment": "该高通量实验是否为 ATB 相关实验。",
    },
    "candidate_external_evidence_summary.tsv": {
        "gene_symbol": "候选基因符号。",
        "candidate_role": "候选基因在外部证据汇总中的角色。",
        "module11_final_priority": "模块 11 综合证据产生的最终优先级状态。",
        "module11_priority_rank": "模块 11 综合证据优先级的排序位置。",
        "module11_integrated_evidence_score": "模块 11 计算的综合证据评分。",
        "n_evidence_records": "该候选对应的外部证据记录数。",
        "n_cca_iCCA_proteome_records": "CCA/iCCA 蛋白质组证据记录数。",
        "n_hpa_normal_cholangiocyte_records": "HPA 正常胆管细胞证据记录数。",
        "n_cross_cancer_direct_records": "跨癌种直接证据记录数。",
        "n_cross_cancer_family_records": "跨癌种同家族证据记录数。",
        "pdc000356_status": "PDC000356 证据查询状态。",
        "hpa_normal_cholangiocyte_status": "HPA 正常胆管细胞证据状态。",
        "cross_cancer_mechanism_status": "跨癌种机制证据状态。",
        "cca_direct_mechanism_status": "CCA 直接机制证据状态。",
        "evidence_grade_summary": "候选外部证据等级的汇总。",
        "pdc_not_returned_is_not_biological_negative": "PDC 未返回记录是否被标记为非生物学阴性。",
        "external_evidence_used_for_ranking": "外部证据是否用于候选排序。",
        "evidence_boundary": "外部证据汇总的范围和使用边界。",
        "next_experiment": "该候选记录的下一项验证实验描述。",
    },
    "candidate_external_evidence.full.tsv": {
        "candidate": "外部证据对应的候选基因或分子标识。",
        "gene_id": "外部证据记录关联的候选基因或数据库标识。",
        "disease_context": "外部证据涉及的疾病或组织背景。",
        "specimen_or_model": "外部证据使用的样本、标本或模型类型。",
        "assay": "外部证据使用的实验检测或分析方法。",
        "cancer_boundary": "证据是否位于当前癌种或相关癌种范围内。",
        "source_type": "外部证据来源类型。",
        "candidate_role": "该候选在外部证据表中的分子或分析角色。",
        "module11_final_priority": "外部证据模块输出的最终候选优先级。",
        "module11_priority_rank": "外部证据模块中的候选排序位置。",
        "module11_integrated_evidence_score": "外部证据模块计算的综合证据评分。",
        "module11_selection_mode": "外部证据模块采用的候选选择模式。",
        "external_evidence_used_for_ranking": "该外部证据是否用于候选排序。",
    },
    "selected_candidate_evidence_matrix.tsv": {
        "gene_symbol": "候选基因符号。",
        "module11_priority_rank": "模块 11 综合证据优先级的排序位置。",
        "module11_final_priority": "模块 11 综合证据产生的最终优先级状态。",
        "module11_integrated_evidence_score": "模块 11 计算的综合证据评分。",
        "pdc000356_status": "PDC000356 证据查询状态。",
        "hpa_normal_cholangiocyte_status": "HPA 正常胆管细胞证据状态。",
        "cross_cancer_mechanism_status": "跨癌种机制证据状态。",
        "cca_direct_mechanism_status": "CCA 直接机制证据状态。",
        "evidence_grade_summary": "候选外部证据等级的汇总。",
        "pdc_not_returned_is_not_biological_negative": "PDC 未返回记录是否被标记为非生物学阴性。",
        "external_evidence_used_for_ranking": "外部证据是否用于候选排序。",
        "evidence_boundary": "外部证据矩阵的范围和使用边界。",
    },
    "candidate_scoring_rule.full.tsv": {
        "rule_set": "候选评分或筛选使用的规则集名称。",
        "scope": "候选评分规则的适用范围。",
        "min_detected_cohorts": "候选至少需要被检出的队列数阈值。",
        "min_consistent_direction_cohorts": "候选至少需要保持方向一致的队列数阈值。",
        "bulk_p_cut": "bulk 证据使用的原始 P 值阈值。",
        "bulk_fdr_cut": "bulk 证据使用的 FDR 阈值。",
        "bulk_abs_effect_cut": "bulk 证据使用的绝对效应量阈值。",
        "association_p_cut": "相关性证据使用的原始 P 值阈值。",
        "association_fdr_cut": "相关性证据使用的 FDR 阈值。",
        "min_score": "候选进入优先级的最低综合评分。",
        "promotion_allowed": "该规则是否允许候选晋级。",
        "rule_note": "规则集的文字定义或适用说明。",
    },
    "candidate_stability_score.full.tsv": {
        "candidate": "候选基因名称。",
        "rule_set": "候选评分使用的规则集名称。",
        "candidate_source_status": "候选来源记录的状态。",
        "candidate_class": "候选基因的分类标签。",
        "candidate_source": "候选基因进入当前列表的来源。",
        "prior_evidence_status": "候选已有证据的状态。",
        "n_detected_cohorts": "候选被检出的队列数。",
        "n_consistent_direction_cohorts": "候选方向一致的队列数。",
        "bulk_direction": "候选在 bulk 队列中的方向一致性。",
        "n_bulk_supported_cohorts": "提供 bulk 支持的队列数。",
        "detection_score": "候选跨队列检出表现的评分。",
        "direction_score": "候选跨队列方向一致性的评分。",
        "bulk_effect_score": "候选 bulk 效应量证据的评分。",
        "ldha_association_score": "候选与 LDHA 相关性证据的评分。",
        "atb_association_score": "候选与 ATB 表型相关性证据的评分。",
        "pathway_association_score": "候选与通路评分相关性证据的评分。",
        "ldha_target": "候选与 LDHA 相关性证据的目标指标。",
        "ldha_direction": "候选与 LDHA 相关性的方向。",
        "ldha_n_consistent": "候选与 LDHA 相关方向一致的队列数。",
        "atb_target": "候选与 ATB 表型相关性证据的目标指标。",
        "atb_direction": "候选与 ATB 表型相关性的方向。",
        "atb_n_consistent": "候选与 ATB 表型相关方向一致的队列数。",
        "pathway_target": "候选与通路评分相关性证据的目标指标。",
        "pathway_direction": "候选与通路评分相关性的方向。",
        "pathway_n_consistent": "候选与通路评分相关方向一致的队列数。",
        "score_total": "主规则下的候选综合评分。",
        "minimum_score": "主规则要求的最低综合评分。",
        "eligible": "候选是否满足主规则纳入条件。",
        "promotion_allowed": "规则是否允许候选进入后续优先级。",
        "priority_status": "候选在主规则优先级筛选中的状态。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
        "interpretation_status": "候选证据的解释状态。",
        "strict_score_total": "严格规则下的候选综合评分。",
        "strict_eligible": "候选是否满足严格规则纳入条件。",
        "strict_priority_status": "候选在严格规则优先级筛选中的状态。",
        "sensitivity_score_total": "敏感性规则下的候选综合评分。",
        "sensitivity_eligible": "候选是否满足敏感性规则纳入条件。",
        "sensitivity_priority_status": "候选在敏感性规则优先级筛选中的状态。",
        "sensitivity_robust": "候选优先级在敏感性分析中的稳健性状态。",
        "rule_summary": "该候选使用的评分规则汇总。",
    },
    "candidate_stability_priority.filtered.tsv": {
        "candidate": "候选基因名称。",
        "rule_set": "候选评分使用的规则集名称。",
        "candidate_source_status": "候选来源记录的状态。",
        "candidate_class": "候选基因的分类标签。",
        "candidate_source": "候选基因进入当前列表的来源。",
        "prior_evidence_status": "候选已有证据的状态。",
        "n_detected_cohorts": "候选被检出的队列数。",
        "n_consistent_direction_cohorts": "候选方向一致的队列数。",
        "bulk_direction": "候选在 bulk 队列中的方向一致性。",
        "n_bulk_supported_cohorts": "提供 bulk 支持的队列数。",
        "detection_score": "候选跨队列检出表现的评分。",
        "direction_score": "候选跨队列方向一致性的评分。",
        "bulk_effect_score": "候选 bulk 效应量证据的评分。",
        "ldha_association_score": "候选与 LDHA 相关性证据的评分。",
        "atb_association_score": "候选与 ATB 表型相关性证据的评分。",
        "pathway_association_score": "候选与通路评分相关性证据的评分。",
        "ldha_target": "候选与 LDHA 相关性证据的目标指标。",
        "ldha_direction": "候选与 LDHA 相关性的方向。",
        "ldha_n_consistent": "候选与 LDHA 相关方向一致的队列数。",
        "atb_target": "候选与 ATB 表型相关性证据的目标指标。",
        "atb_direction": "候选与 ATB 表型相关性的方向。",
        "atb_n_consistent": "候选与 ATB 表型相关方向一致的队列数。",
        "pathway_target": "候选与通路评分相关性证据的目标指标。",
        "pathway_direction": "候选与通路评分相关性的方向。",
        "pathway_n_consistent": "候选与通路评分相关方向一致的队列数。",
        "score_total": "主规则下的候选综合评分。",
        "minimum_score": "主规则要求的最低综合评分。",
        "eligible": "候选是否满足主规则纳入条件。",
        "promotion_allowed": "规则是否允许候选进入后续优先级。",
        "priority_status": "候选在主规则优先级筛选中的状态。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
        "interpretation_status": "候选证据的解释状态。",
        "strict_score_total": "严格规则下的候选综合评分。",
        "strict_eligible": "候选是否满足严格规则纳入条件。",
        "strict_priority_status": "候选在严格规则优先级筛选中的状态。",
        "sensitivity_score_total": "敏感性规则下的候选综合评分。",
        "sensitivity_eligible": "候选是否满足敏感性规则纳入条件。",
        "sensitivity_priority_status": "候选在敏感性规则优先级筛选中的状态。",
        "sensitivity_robust": "候选优先级在敏感性分析中的稳健性状态。",
        "rule_summary": "该候选使用的评分规则汇总。",
    },
    "candidate_bulk_scrna_intersection.filtered.tsv": {
        "gene_symbol": "候选基因符号。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "bulk_eligible": "候选是否满足 bulk 证据纳入条件。",
        "gene_present": "该基因是否存在于当前单细胞表达矩阵。",
        "n_feature_rows": "该候选在表达矩阵中对应的特征行数。",
        "n_tumor_donors_total": "候选肿瘤供体总数。",
        "n_donors_with_at_least_10_evaluable_cells": "至少具有 10 个可评估细胞的供体数。",
        "n_donors_detection_rate_gt_0": "检测率大于 0 的供体数。",
        "n_donors_detection_rate_ge_5pct": "检测率至少为 5% 的供体数。",
        "main_rule_min_donor_cells": "主规则要求的每个供体最少可评估细胞数。",
        "main_rule_min_donors": "主规则要求的最少支持供体数。",
        "main_rule_detection_threshold": "主规则使用的细胞检测率阈值。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
        "main_scrna_expression_support": "主规则下单细胞表达支持状态。",
        "strict_rule_detection_threshold": "严格规则使用的细胞检测率阈值。",
        "strict_scrna_sensitivity_support": "严格敏感性规则下的单细胞支持状态。",
        "main_rule_reason": "主规则纳入或排除候选的原因。",
        "strict_rule_reason": "严格规则纳入或排除候选的原因。",
        "intersection_main": "候选是否进入 bulk–单细胞主交集。",
        "intersection_strict_sensitivity": "候选是否进入严格敏感性交集。",
        "candidate_status": "候选在交集筛选中的状态。",
        "statistical_unit": "单细胞证据汇总使用的统计单位。",
        "no_unrestricted_gene_search": "是否未进行未限定候选面板的基因搜索。",
    },
    "candidate_bulk_scrna_intersection.strict.filtered.tsv": {
        "gene_symbol": "候选基因符号。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "bulk_eligible": "候选是否满足 bulk 证据纳入条件。",
        "gene_present": "该基因是否存在于当前单细胞表达矩阵。",
        "n_feature_rows": "该候选在表达矩阵中对应的特征行数。",
        "n_tumor_donors_total": "候选肿瘤供体总数。",
        "n_donors_with_at_least_10_evaluable_cells": "至少具有 10 个可评估细胞的供体数。",
        "n_donors_detection_rate_gt_0": "检测率大于 0 的供体数。",
        "n_donors_detection_rate_ge_5pct": "检测率至少为 5% 的供体数。",
        "main_rule_min_donor_cells": "主规则要求的每个供体最少可评估细胞数。",
        "main_rule_min_donors": "主规则要求的最少支持供体数。",
        "main_rule_detection_threshold": "主规则使用的细胞检测率阈值。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
        "main_scrna_expression_support": "主规则下单细胞表达支持状态。",
        "strict_rule_detection_threshold": "严格规则使用的细胞检测率阈值。",
        "strict_scrna_sensitivity_support": "严格敏感性规则下的单细胞支持状态。",
        "main_rule_reason": "主规则纳入或排除候选的原因。",
        "strict_rule_reason": "严格规则纳入或排除候选的原因。",
        "intersection_main": "候选是否进入 bulk–单细胞主交集。",
        "intersection_strict_sensitivity": "候选是否进入严格敏感性交集。",
        "candidate_status": "候选在交集筛选中的状态。",
        "statistical_unit": "单细胞证据汇总使用的统计单位。",
        "no_unrestricted_gene_search": "是否未进行未限定候选面板的基因搜索。",
    },
    "integrated_evidence_priority.full.tsv": {
        "gene_symbol": "候选基因符号。",
        "detection_score": "单细胞或跨队列表达检出的证据评分。",
        "direction_score": "跨队列效应方向一致性的证据评分。",
        "bulk_effect_score": "bulk 差异效应证据评分。",
        "ldha_association_score": "与 LDHA 相关性证据评分。",
        "atb_association_score": "与 ATB 表型相关性证据评分。",
        "pathway_association_score": "与通路评分相关性证据评分。",
        "score_total": "主规则下的综合证据评分。",
        "strict_score_total": "严格规则下的综合证据评分。",
        "bulk_domain_score": "bulk 证据域的汇总评分。",
        "ldha_domain_score": "LDHA 相关性证据域的汇总评分。",
        "atb_domain_score": "ATB 证据域的汇总评分。",
        "pathway_domain_score": "通路相关性证据域的汇总评分。",
        "reconstructed_score_total": "根据单细胞支持状态重建的综合评分。",
        "strict_scrna_support": "严格规则下单细胞证据支持状态。",
        "main_scrna_support": "主规则下单细胞证据支持状态。",
        "priority_pool_member": "该候选是否属于综合优先级候选池。",
        "selection_mode": "综合优先级候选的选择模式。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "n_supported_evidence_domains": "获得支持的证据域数量。",
        "integrated_evidence_score": "综合证据评分。",
        "integrated_priority_rank": "综合证据优先级排序位置。",
        "integrated_priority_selected": "该候选是否被综合优先级规则选中。",
        "integrated_priority_rule": "综合优先级使用的判定规则。",
        "scrna_score_used": "综合评分中是否使用单细胞评分。",
        "scrna_score_value": "综合评分中采用的单细胞评分值。",
        "statistical_unit": "综合证据汇总使用的统计单位。",
    },
    "integrated_evidence_priority.filtered.tsv": {
        "gene_symbol": "候选基因符号。",
        "detection_score": "单细胞或跨队列表达检出的证据评分。",
        "direction_score": "跨队列效应方向一致性的证据评分。",
        "bulk_effect_score": "bulk 差异效应证据评分。",
        "ldha_association_score": "与 LDHA 相关性证据评分。",
        "atb_association_score": "与 ATB 表型相关性证据评分。",
        "pathway_association_score": "与通路评分相关性证据评分。",
        "score_total": "主规则下的综合证据评分。",
        "strict_score_total": "严格规则下的综合证据评分。",
        "bulk_domain_score": "bulk 证据域的汇总评分。",
        "ldha_domain_score": "LDHA 相关性证据域的汇总评分。",
        "atb_domain_score": "ATB 证据域的汇总评分。",
        "pathway_domain_score": "通路相关性证据域的汇总评分。",
        "reconstructed_score_total": "根据单细胞支持状态重建的综合评分。",
        "strict_scrna_support": "严格规则下单细胞证据支持状态。",
        "main_scrna_support": "主规则下单细胞证据支持状态。",
        "priority_pool_member": "该候选是否属于综合优先级候选池。",
        "selection_mode": "综合优先级候选的选择模式。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "n_supported_evidence_domains": "获得支持的证据域数量。",
        "integrated_evidence_score": "综合证据评分。",
        "integrated_priority_rank": "综合证据优先级排序位置。",
        "integrated_priority_selected": "该候选是否被综合优先级规则选中。",
        "integrated_priority_rule": "综合优先级使用的判定规则。",
        "scrna_score_used": "综合评分中是否使用单细胞评分。",
        "scrna_score_value": "综合评分中采用的单细胞评分值。",
        "statistical_unit": "综合证据汇总使用的统计单位。",
    },
    "bulk_eligible_candidates.full.tsv": {
        "gene_symbol": "候选基因符号。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "candidate_panel_member": "该基因是否属于预先指定的候选面板。",
        "bulk_eligible": "候选是否满足 bulk 证据纳入条件。",
        "bulk_priority_status": "候选在 bulk 优先级筛选中的状态。",
        "bulk_input_row": "候选在 bulk 输入表中的行号。",
        "candidate_source": "候选基因进入当前列表的来源。",
        "bulk_source_file": "bulk 候选来源文件的相对路径或名称。",
    },
    "evidence_binary_matrix.full.tsv": {
        "gene_symbol": "候选基因符号。",
        "bulk_evidence": "候选是否具有 bulk 证据支持。",
        "scrna_main_evidence": "候选是否具有主规则单细胞证据支持。",
        "scrna_strict_sensitivity_evidence": "候选是否具有严格敏感性单细胞证据支持。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
    },
    "donor_pseudobulk_detection.full.tsv": {
        "gene_symbol": "候选基因符号。",
        "donor_id": "供体或病例唯一标识。",
        "gene_present": "该基因是否存在于当前表达矩阵。",
        "n_feature_rows": "该候选在表达矩阵中对应的特征行数。",
        "n_cells_evaluable": "该供体中可评估的细胞数。",
        "donor_eligible_min_10_cells": "该供体是否达到至少 10 个可评估细胞。",
        "detected_cells_counts_gt_0": "计数大于 0 的细胞数。",
        "pseudobulk_count_sum": "供体伪 bulk 单位内的计数总和。",
        "mean_count_per_evaluable_cell": "每个可评估细胞的平均计数。",
        "detection_rate": "该供体内达到检出标准的细胞比例。",
        "main_donor_positive_rate_gt_0": "主规则下计数大于 0 的供体阳性比例。",
        "strict_donor_positive_rate_ge_5pct": "严格规则下阳性比例至少为 5% 的供体比例。",
        "statistical_unit": "供体伪 bulk 检测汇总使用的统计单位。",
        "counts_source": "供体伪 bulk 计数的来源矩阵或对象。",
    },
    "candidate_intersection_status.full.tsv": {
        "gene_symbol": "候选基因符号。",
        "candidate_panel_order": "候选面板中的固定排序位置。",
        "bulk_eligible": "候选是否满足 bulk 证据纳入条件。",
        "gene_present": "该基因是否存在于当前单细胞表达矩阵。",
        "n_feature_rows": "该候选在表达矩阵中对应的特征行数。",
        "n_tumor_donors_total": "候选肿瘤供体总数。",
        "n_donors_with_at_least_10_evaluable_cells": "至少具有 10 个可评估细胞的供体数。",
        "n_donors_detection_rate_gt_0": "检测率大于 0 的供体数。",
        "n_donors_detection_rate_ge_5pct": "检测率至少为 5% 的供体数。",
        "main_rule_min_donor_cells": "主规则要求的每个供体最少可评估细胞数。",
        "main_rule_min_donors": "主规则要求的最少支持供体数。",
        "main_rule_detection_threshold": "主规则使用的细胞检测率阈值。",
        "scrna_evidence_status": "候选的单细胞证据状态。",
        "main_scrna_expression_support": "主规则下单细胞表达支持状态。",
        "strict_rule_detection_threshold": "严格规则使用的细胞检测率阈值。",
        "strict_scrna_sensitivity_support": "严格敏感性规则下的单细胞支持状态。",
        "main_rule_reason": "主规则纳入或排除候选的原因。",
        "strict_rule_reason": "严格规则纳入或排除候选的原因。",
        "intersection_main": "候选是否进入 bulk–单细胞主交集。",
        "intersection_strict_sensitivity": "候选是否进入严格敏感性交集。",
        "candidate_status": "候选在交集筛选中的状态。",
        "statistical_unit": "单细胞证据汇总使用的统计单位。",
        "no_unrestricted_gene_search": "是否未进行未限定候选面板的基因搜索。",
        "integrated_evidence_score": "综合证据评分。",
        "integrated_priority_rank": "综合证据优先级排序位置。",
        "integrated_priority_selected": "该候选是否被综合优先级规则选中。",
        "priority_pool_member": "该候选是否属于综合优先级候选池。",
        "selection_mode": "综合优先级候选的选择模式。",
        "strict_scrna_support": "严格规则下单细胞证据支持状态。",
    },
    "pathway_group_stats.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "pathway": "通路或基因集名称。",
        "contrast_id": "通路组间比较的唯一标识。",
        "analysis_role": "该记录在通路组间比较中的分析角色。",
        "group1": "比较中的实验组标签。",
        "group2": "比较中的对照组标签。",
        "test_unit": "通路组间检验使用的统计单位。",
        "paired": "该通路比较是否按病例配对。",
        "n_group1": "实验组统计单位数。",
        "n_group2": "对照组统计单位数。",
        "n_pairs": "完整配对统计单位数。",
        "delta_mean": "实验组减对照组的平均通路评分差值。",
        "standardized_effect": "标准化的通路组间效应量。",
        "effect_ci_low": "通路效应量置信区间下限。",
        "effect_ci_high": "通路效应量置信区间上限。",
        "p_value": "通路组间检验的原始 P 值。",
        "p_display": "用于展示的格式化原始 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "status": "通路组间统计结果状态。",
        "p_adjusted": "通路组间检验经多重检验校正后的 P 值。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
        "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
    },
    "pathway_spearman.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "pathway": "通路或基因集名称。",
        "n_tumor": "相关性分析纳入的肿瘤样本或供体数。",
        "rho": "LDHA 与该通路评分的 Spearman 秩相关系数。",
        "ci_low": "相关系数置信区间下限。",
        "ci_high": "相关系数置信区间上限。",
        "p_value": "相关性检验的原始 P 值。",
        "p_display": "用于展示的格式化原始 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "status": "相关性分析状态。",
        "p_adjusted": "相关性检验经多重检验校正后的 P 值。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
        "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
        "LDHA_source": "LDHA 表达值的来源矩阵或分析表。",
    },
    "preranked_fgsea.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "pathway": "通路或基因集名称。",
        "n_tumor": "预排序富集分析使用的肿瘤样本或统计单位数。",
        "rank_metric": "用于预排序富集的差异或相关性统计量。",
        "NES": "标准化富集分数。",
        "p_value": "GSEA 原始 P 值。",
        "p_adjusted": "GSEA 经多重检验校正后的 P 值。",
        "leading_edge": "达到富集峰值的 leading-edge 基因集合或统计摘要。",
        "status": "GSEA 结果状态。",
        "p_display": "用于展示的格式化原始 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
        "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
    },
    "effect_direction_consistency.full.tsv": {
        "pathway": "通路或基因集名称。",
        "cohorts": "参与方向一致性汇总的队列列表。",
        "n_cohorts": "参与方向一致性汇总的队列数。",
        "positive_direction_n": "效应方向为正的队列数。",
        "negative_direction_n": "效应方向为负的队列数。",
        "same_direction": "各队列效应方向是否一致。",
        "mean_standardized_effect": "各队列标准化效应量的平均值。",
        "fisher_combined_p": "跨队列合并的 Fisher 组合 P 值。",
        "status": "跨队列方向一致性分析状态。",
        "fdr": "方向一致性检验经多重校正后的 FDR。",
    },
    "atb_group_comparison.stat.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "score": "ATB 表型评分。",
        "contrast_id": "ATB 表型比较的唯一标识。",
        "analysis_role": "该记录在 ATB 组间比较中的分析角色。",
        "population": "ATB 评分汇总所使用的样本人群。",
        "group1": "比较中的实验组标签。",
        "group2": "比较中的对照组标签。",
        "test_unit": "ATB 组间检验使用的统计单位。",
        "paired": "该 ATB 比较是否按病例配对。",
        "n_group1": "实验组统计单位数。",
        "n_group2": "对照组统计单位数。",
        "n_pairs": "完整配对统计单位数。",
        "mean_difference": "实验组减对照组的 ATB 平均评分差值。",
        "mean_difference_ci_low": "平均评分差值置信区间下限。",
        "mean_difference_ci_high": "平均评分差值置信区间上限。",
        "effect_type": "ATB 组间效应量的定义或类型。",
        "standardized_effect": "标准化的 ATB 组间效应量。",
        "effect_ci_low": "ATB 效应量置信区间下限。",
        "effect_ci_high": "ATB 效应量置信区间上限。",
        "p_value": "ATB 组间检验的原始 P 值。",
        "p_display": "用于展示的格式化原始 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "status": "ATB 组间统计结果状态。",
        "p_adjusted": "ATB 组间检验经多重检验校正后的 P 值。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
        "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
    },
    "atb_tumor_context_spearman.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "analysis_population": "ATB 相关性分析所使用的肿瘤样本人群。",
        "score": "ATB 表型评分。",
        "correlate_with": "与 ATB 评分进行相关性检验的表达或通路指标。",
        "n_tumor": "相关性分析纳入的肿瘤样本或统计单位数。",
        "rho": "ATB 评分与目标指标的 Spearman 秩相关系数。",
        "ci_low": "相关系数置信区间下限。",
        "ci_high": "相关系数置信区间上限。",
        "p_value": "相关性检验的原始 P 值。",
        "p_display": "用于展示的格式化原始 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "status": "ATB 相关性分析状态。",
        "p_adjusted": "相关性检验经多重检验校正后的 P 值。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
        "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
    },
    "atb_score_definition_audit.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "score": "ATB 表型评分名称。",
        "component_gene": "ATB 评分包含的组成基因。",
        "component_role": "组成基因在 ATB 评分中的方向或功能角色。",
        "definition": "ATB 评分的计算定义。",
        "z_standardization": "组成表达值是否进行了 z-score 标准化。",
        "source": "ATB 评分基因集或定义的来源。",
        "status": "ATB 评分定义审计状态。",
    },
    "atb_adjusted_models_vif.full.tsv": {
        "dataset": "公共表达数据集或队列标识。",
        "analysis_population": "ATB 调整模型所使用的分析人群。",
        "outcome": "调整模型中的结局变量。",
        "model_formula": "调整模型的设计公式。",
        "term": "调整模型中的解释变量或模型项。",
        "n": "调整模型纳入的样本或统计单位数。",
        "estimate": "模型项的估计系数。",
        "std_error": "模型项估计系数的标准误。",
        "ci_low": "模型项效应置信区间下限。",
        "ci_high": "模型项效应置信区间上限。",
        "p_value": "模型项检验的原始 P 值。",
        "p_display": "用于展示的格式化原始 P 值。",
        "vif": "模型项的方差膨胀因子。",
        "status": "调整模型拟合状态。",
        "p_adjusted": "模型项检验经多重检验校正后的 P 值。",
        "p_adjusted_display": "用于展示的格式化校正 P 值。",
    },
    "malignant_vs_adjacent_comparison_stats.full.tsv": {
        "metric": "恶性细胞与癌旁细胞比较的指标名称。",
        "measure": "该比较使用的表达或评分度量。",
        "population": "比较所使用的恶性或癌旁细胞人群。",
        "group_1": "比较中的第一组标签。",
        "group_2": "比较中的第二组标签。",
        "n_group_1_donors": "第一组供体数。",
        "n_group_2_donors": "第二组供体数。",
        "n_complete_pairs": "具有完整两组观测的供体配对数。",
        "statistical_unit": "组间比较使用的统计单位。",
        "effect_group_1_minus_group_2": "第一组减第二组的效应量。",
        "group_1_summary": "第一组的表达或评分汇总值。",
        "group_2_summary": "第二组的表达或评分汇总值。",
        "eligible": "该比较是否满足推断条件。",
        "eligibility_status": "该比较的样本量或推断资格状态。",
        "omitted_reason": "未执行统计检验的具体原因。",
        "test": "组间比较使用的统计检验。",
        "p_value": "组间检验的原始 P 值。",
        "p_adjusted": "组间检验经多重检验校正后的 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "contrast_direction": "组间效应量的方向定义。",
        "effect_group_1_minus_group_2_mean_log1p": "第一组减第二组的 mean log1p 表达差值。",
    },
    "malignant_vs_adjacent_pseudobulk_comparison_stats.full.tsv": {
        "metric": "恶性细胞与癌旁细胞伪 bulk 比较的指标名称。",
        "metric_class": "指标所属的基因表达或通路评分类别。",
        "group_1": "比较中的第一组标签。",
        "group_2": "比较中的第二组标签。",
        "n_group_1_donors": "第一组供体数。",
        "n_group_2_donors": "第二组供体数。",
        "n_complete_pairs": "具有完整两组观测的供体配对数。",
        "statistical_unit": "伪 bulk 组间比较使用的统计单位。",
        "group_1_summary": "第一组的表达或评分汇总值。",
        "group_2_summary": "第二组的表达或评分汇总值。",
        "effect_group_1_minus_group_2": "第一组减第二组的效应量。",
        "eligible": "该比较是否满足推断条件。",
        "eligibility_status": "该比较的样本量或推断资格状态。",
        "omitted_reason": "未执行统计检验的具体原因。",
        "test": "伪 bulk 组间比较使用的统计检验。",
        "p_value": "组间检验的原始 P 值。",
        "p_adjusted": "组间检验经多重检验校正后的 P 值。",
        "significance": "根据预设阈值生成的显著性状态。",
        "contrast_direction": "组间效应量的方向定义。",
    },
    "malignant_vs_adjacent_pseudobulk.full.tsv": {
        "donor_id": "供体或病例唯一标识。",
        "group": "供体所属的比较分组。",
        "population": "伪 bulk 汇总所使用的细胞人群。",
        "n_cells": "供体伪 bulk 单位包含的细胞数。",
        "library_size": "供体伪 bulk 单位的总文库计数。",
        "pseudobulk_unit": "伪 bulk 构建所使用的统计单位。",
        "counts_source": "伪 bulk 计数的来源矩阵或对象。",
        "metric": "表达或通路评分的指标名称。",
        "metric_class": "指标所属的基因表达或通路评分类别。",
        "value": "当前指标的数值。",
        "value_scale": "当前指标使用的数值尺度。",
        "raw_count": "伪 bulk 原始计数总和。",
        "log1p_cpm": "伪 bulk CPM 经 log1p 转换后的表达值。",
        "positive_rate": "伪 bulk 单位内达到检出条件的细胞比例。",
        "score_standardization_population": "通路评分标准化所使用的参考人群。",
        "program_member_genes": "该通路评分包含的成员基因列表。",
        "program_member_log1p_cpm": "成员基因的 log1p(CPM) 值列表。",
        "program_member_z_scores": "成员基因经标准化后的 z-score 列表。",
    },
    "malignant_vs_adjacent_pseudobulk_program_score_audit.full.tsv": {
        "metric": "通路或程序评分的名称。",
        "metric_class": "指标所属的通路评分类别。",
        "gene_symbol": "通路评分使用的成员基因符号。",
        "mean_log1p_cpm": "成员基因 log1p(CPM) 的平均值。",
        "sd_log1p_cpm": "成员基因 log1p(CPM) 的标准差。",
        "n_donor_population_units": "标准化参考人群中的供体统计单位数。",
        "standardization_population": "成员基因标准化所使用的参考人群。",
        "score_method": "通路或程序评分的计算方法。",
    },
    "program_membership.full.tsv": {
        "output_program": "输出通路或程序名称。",
        "component_program": "组成通路或程序名称。",
        "gene_symbol": "程序成员基因符号。",
        "present_in_malignant_object": "该成员基因是否存在于恶性细胞表达对象。",
        "source": "程序成员关系的来源数据库或定义。",
        "db_version": "程序成员来源数据库版本。",
        "coverage": "成员基因在恶性细胞对象中的覆盖比例。",
        "component_eligible": "该组成程序是否满足当前分析纳入条件。",
    },
    "program_score_audit.full.tsv": {
        "output_program": "输出通路或程序名称。",
        "component_program": "组成通路或程序名称。",
        "n_requested_genes": "请求用于评分的成员基因数。",
        "n_present_genes": "在恶性细胞表达对象中实际找到的成员基因数。",
        "coverage": "实际找到的成员基因占请求成员基因的比例。",
        "score_method": "通路或程序评分的计算方法。",
    },
    "LDHA_glycolysis_donor_spearman.full.tsv": {
        "analysis": "LDHA 与糖酵解评分相关性分析的名称。",
        "statistical_unit": "相关性分析使用的统计单位。",
        "n_donors": "相关性分析纳入的供体数。",
        "min_n": "相关性分析允许的最小供体数。",
        "rho": "LDHA 与糖酵解评分的 Spearman 秩相关系数。",
        "ci_low": "相关系数置信区间下限。",
        "ci_high": "相关系数置信区间上限。",
        "p_value": "相关性检验的原始 P 值。",
        "p_adjusted": "相关性检验经多重检验校正后的 P 值。",
        "status": "相关性分析状态。",
        "omitted_reason": "未执行相关性推断的具体原因。",
        "method": "相关性分析使用的方法。",
        "bootstrap_reps": "置信区间 bootstrap 重采样次数。",
        "seed": "随机重采样使用的随机种子。",
    },
    "reviewed_primary_LDHA_by_celltype.full.tsv": {
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "metric": "汇总的表达指标名称（LDHA）。",
        "sample_ids": "该细胞类型汇总包含的样本标识列表。",
        "donor_ids": "该细胞类型汇总包含的供体标识列表。",
        "groups": "该细胞类型汇总涉及的分组标签。",
        "n_samples": "该细胞类型汇总包含的样本数。",
        "n_donors": "该细胞类型汇总包含的供体数。",
        "n_groups": "该细胞类型汇总涉及的分组数。",
        "n_cells": "该细胞类型汇总包含的细胞数。",
        "mean_log1p_cpm": "LDHA log1p(CPM) 表达值的平均值。",
        "positive_rate": "LDHA 表达值大于零的细胞比例。",
        "cell_weighted_mean_log1p_cpm": "按细胞加权的 LDHA mean log1p(CPM)。",
        "cell_weighted_positive_rate": "按细胞加权的 LDHA 阳性比例。",
        "sample_weighting": "样本汇总时使用的加权方式。",
        "statistical_unit": "细胞类型表达汇总使用的统计单位。",
        "plot_order": "细胞类型在图形中的排序位置。",
        "celltype_color": "图形中该细胞类型使用的颜色。",
    },
    "reviewed_primary_candidate_genes_by_celltype.full.tsv": {
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "metric": "汇总的候选基因表达指标名称。",
        "sample_ids": "该细胞类型汇总包含的样本标识列表。",
        "donor_ids": "该细胞类型汇总包含的供体标识列表。",
        "groups": "该细胞类型汇总涉及的分组标签。",
        "n_samples": "该细胞类型汇总包含的样本数。",
        "n_donors": "该细胞类型汇总包含的供体数。",
        "n_groups": "该细胞类型汇总涉及的分组数。",
        "n_cells": "该细胞类型汇总包含的细胞数。",
        "mean_log1p_cpm": "候选基因 log1p(CPM) 表达值的平均值。",
        "positive_rate": "候选基因表达值大于零的细胞比例。",
        "cell_weighted_mean_log1p_cpm": "按细胞加权的候选基因 mean log1p(CPM)。",
        "cell_weighted_positive_rate": "按细胞加权的候选基因阳性比例。",
        "sample_weighting": "样本汇总时使用的加权方式。",
        "statistical_unit": "细胞类型表达汇总使用的统计单位。",
        "plot_order": "细胞类型在图形中的排序位置。",
        "celltype_color": "图形中该细胞类型使用的颜色。",
    },
    "malignant_vs_adjacent_sample_summary.full.tsv": {
        "sample_id": "表达样本唯一标识。",
        "group": "样本所属的比较分组。",
        "population": "表达汇总所使用的细胞人群。",
        "metric": "表达或通路评分的指标名称。",
        "donor_id": "供体或病例唯一标识。",
        "n_cells": "样本中纳入汇总的细胞数。",
        "mean_log1p": "log1p 表达值的平均值。",
        "median_log1p": "log1p 表达值的中位数。",
        "q25_log1p": "log1p 表达值的第 25 百分位数。",
        "q75_log1p": "log1p 表达值的第 75 百分位数。",
        "positive_cells": "表达值大于零的细胞数。",
        "total_cells": "该样本纳入汇总的细胞总数。",
        "positive_rate": "表达值大于零的细胞比例。",
        "statistical_unit": "样本表达汇总使用的统计单位。",
    },
    "malignant_donor_summary.full.tsv": {
        "donor_id": "供体或病例唯一标识。",
        "group": "供体所属的比较分组。",
        "population": "表达汇总所使用的细胞人群。",
        "metric": "表达或通路评分的指标名称。",
        "sample_id": "表达样本唯一标识。",
        "n_samples": "供体汇总包含的样本数。",
        "n_cells": "供体汇总包含的细胞数。",
        "mean_log1p": "log1p 表达值的平均值。",
        "median_log1p": "log1p 表达值的中位数。",
        "q25_log1p": "log1p 表达值的第 25 百分位数。",
        "q75_log1p": "log1p 表达值的第 75 百分位数。",
        "positive_cells": "表达值大于零的细胞数。",
        "total_cells": "该供体纳入汇总的细胞总数。",
        "positive_rate": "表达值大于零的细胞比例。",
        "statistical_unit": "供体表达汇总使用的统计单位。",
        "sample_weighting": "样本汇总时使用的加权方式。",
    },
    "malignant_vs_adjacent_donor_summary.full.tsv": {
        "donor_id": "供体或病例唯一标识。",
        "group": "供体所属的比较分组。",
        "population": "表达汇总所使用的细胞人群。",
        "metric": "表达或通路评分的指标名称。",
        "sample_id": "表达样本唯一标识。",
        "n_samples": "供体汇总包含的样本数。",
        "n_cells": "供体汇总包含的细胞数。",
        "mean_log1p": "log1p 表达值的平均值。",
        "median_log1p": "log1p 表达值的中位数。",
        "q25_log1p": "log1p 表达值的第 25 百分位数。",
        "q75_log1p": "log1p 表达值的第 75 百分位数。",
        "positive_cells": "表达值大于零的细胞数。",
        "total_cells": "该供体纳入汇总的细胞总数。",
        "positive_rate": "表达值大于零的细胞比例。",
        "statistical_unit": "供体表达汇总使用的统计单位。",
        "sample_weighting": "样本汇总时使用的加权方式。",
    },
    "malignant_candidate_donor_summary.full.tsv": {
        "donor_id": "供体或病例唯一标识。",
        "group": "供体所属的比较分组。",
        "population": "表达汇总所使用的细胞人群。",
        "metric": "候选基因表达或评分的指标名称。",
        "sample_id": "表达样本唯一标识。",
        "n_samples": "供体汇总包含的样本数。",
        "n_cells": "供体汇总包含的细胞数。",
        "mean_log1p": "log1p 表达值的平均值。",
        "median_log1p": "log1p 表达值的中位数。",
        "q25_log1p": "log1p 表达值的第 25 百分位数。",
        "q75_log1p": "log1p 表达值的第 75 百分位数。",
        "positive_cells": "表达值大于零的细胞数。",
        "total_cells": "该供体纳入汇总的细胞总数。",
        "positive_rate": "表达值大于零的细胞比例。",
        "statistical_unit": "供体表达汇总使用的统计单位。",
        "sample_weighting": "样本汇总时使用的加权方式。",
        "gene_symbol": "候选基因符号。",
        "candidate_tier": "候选基因在当前结果中的层级。",
        "detected_cells": "达到表达检出条件的细胞数。",
        "detection_fraction": "达到表达检出条件的细胞比例。",
    },
    "malignant_expression_cell_level.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "sample_id": "表达样本唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "group": "样本所属的比较分组。",
        "population": "该细胞所属的表达分析人群。",
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "umap_1": "UMAP 第一维坐标。",
        "umap_2": "UMAP 第二维坐标。",
        "metric": "当前细胞表达或评分的指标名称。",
        "expression": "当前细胞在指定表达尺度上的表达值。",
        "positive": "当前细胞是否达到表达检出条件。",
    },
    "malignant_vs_adjacent_cell_level.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "sample_id": "表达样本唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "group": "样本所属的比较分组。",
        "population": "该细胞所属的表达分析人群。",
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "umap_1": "UMAP 第一维坐标。",
        "umap_2": "UMAP 第二维坐标。",
        "metric": "当前细胞表达或评分的指标名称。",
        "expression": "当前细胞在指定表达尺度上的表达值。",
        "positive": "当前细胞是否达到表达检出条件。",
    },
    "reviewed_primary_LDHA_cell_level.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "sample_id": "表达样本唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "group": "样本所属的比较分组。",
        "population": "该细胞所属的表达分析人群。",
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "umap_1": "UMAP 第一维坐标。",
        "umap_2": "UMAP 第二维坐标。",
        "metric": "当前细胞表达指标名称（LDHA）。",
        "expression": "当前细胞在指定表达尺度上的 LDHA 表达值。",
        "positive": "当前细胞是否达到 LDHA 表达检出条件。",
        "plot_order": "细胞类型在图形中的排序位置。",
        "celltype_color": "图形中该细胞类型使用的颜色。",
    },
    "reviewed_primary_candidate_genes_cell_level.full.tsv": {
        "cell_id": "细胞条形码或细胞唯一标识。",
        "sample_id": "表达样本唯一标识。",
        "donor_id": "供体或病例唯一标识。",
        "group": "样本所属的比较分组。",
        "population": "该细胞所属的表达分析人群。",
        "reviewed_cell_type": "复核后的细胞类型标签。",
        "umap_1": "UMAP 第一维坐标。",
        "umap_2": "UMAP 第二维坐标。",
        "metric": "当前细胞表达指标名称（候选基因）。",
        "expression": "当前细胞在指定表达尺度上的候选基因表达值。",
        "positive": "当前细胞是否达到候选基因表达检出条件。",
        "plot_order": "细胞类型在图形中的排序位置。",
        "celltype_color": "图形中该细胞类型使用的颜色。",
    },
    "cluster_annotation_evidence.full.tsv": {
        "representation": "单细胞注释使用的表示路线。",
        "accession": "公共单细胞数据集 accession。",
        "cluster": "Leiden cluster 编号。",
        "n_cells": "该 cluster 包含的细胞数。",
        "assigned_label": "自动或规则分配的细胞类型标签。",
        "confidence": "cluster 注释置信度。",
        "best_module": "匹配得分最高的 marker 模块。",
        "score": "最佳 marker 模块的匹配评分。",
        "second_best_score": "第二高 marker 模块匹配评分。",
        "score_margin": "最佳与第二高匹配评分之差。",
        "positive_marker_support_count": "获得正向 marker 支持的细胞数。",
        "positive_marker_total_resolved": "已解析的正向 marker 总数。",
        "positive_marker_support_fraction": "正向 marker 支持细胞或条目的比例。",
        "positive_marker_mean_expression": "正向 marker 的平均表达量。",
        "positive_marker_detection_fraction": "正向 marker 达到检出的比例。",
        "negative_marker_conflict_count": "与负向 marker 冲突的细胞或条目数。",
        "negative_marker_total_resolved": "已解析的负向 marker 总数。",
        "negative_marker_conflict_fraction": "负向 marker 冲突比例。",
        "n_top_de_rows": "用于注释的 top 差异表达结果行数。",
        "n_samples_present": "该 cluster 中出现的样本数。",
        "dominant_sample": "该 cluster 的主导样本。",
        "dominant_sample_fraction": "主导样本占该 cluster 细胞的比例。",
        "n_donors_present": "该 cluster 中出现的供体数。",
        "dominant_donor": "该 cluster 的主导供体。",
        "dominant_donor_fraction": "主导供体占该 cluster 细胞的比例。",
        "donor_source": "供体标识的来源字段或映射来源。",
        "doublet_fraction": "该 cluster 中潜在双细胞比例。",
        "doublet_risk": "该 cluster 的双细胞风险等级。",
        "mixed_lineage_fraction": "该 cluster 中混合谱系细胞比例。",
        "mixed_lineage_risk": "该 cluster 的混合谱系风险等级。",
        "doublet_mixed_spectrum_risk": "该 cluster 的双细胞/混合谱系综合风险等级。",
        "annotation_evidence": "支持该 cluster 注释的 marker 或统计证据摘要。",
    },
    "scvi_celltype_composition.full.tsv": {
        "representation": "细胞组成统计使用的单细胞表示路线。",
        "dataset": "公共单细胞数据集或队列标识。",
        "unit_type": "细胞组成统计的单位类型。",
        "unit_id": "细胞组成统计单位的唯一标识。",
        "cell_type": "细胞组成统计对应的细胞类型标签。",
        "sample_id": "细胞组成统计对应的样本标识。",
        "group": "样本所属的比较分组。",
        "n_cells": "该统计单位包含的细胞数。",
        "proportion": "该统计单位中对应细胞类型的细胞比例。",
    },
    "marker_dictionary.full.tsv": {
        "marker_dictionary_version": "marker 字典版本。",
        "module": "marker 所属的细胞类型或谱系模块。",
        "marker_role": "marker 在注释规则中的正向或负向角色。",
        "marker_rank": "marker 在字典模块中的排序位置。",
        "gene": "marker 基因符号。",
    },
    "cluster_review_consensus.full.tsv": {
        "cluster": "Leiden cluster 编号。",
        "reviewed_label": "复核后的 cluster 注释标签。",
        "reviewed_confidence": "复核注释的置信度。",
        "provisional": "该 cluster 注释是否为 provisional 标签。",
        "exclude_from_infercnv": "该 cluster 是否排除出 inferCNV 候选输入。",
        "reviewer_consensus": "复核人员对 cluster 标签的一致性结论。",
        "review_note": "cluster 注释复核备注。",
        "primary_representation": "复核后选定的单细胞表示路线。",
        "n_cells": "该 cluster 包含的细胞数。",
        "automatic_label": "自动注释得到的 cluster 标签。",
        "label_changed": "人工复核是否改变自动标签。",
        "reviewer_count": "参与该 cluster 复核的人员数。",
        "label_source": "最终标签的来源。",
        "review_source": "复核结论的来源记录。",
    },
    "independent_annotation_review.full.tsv": {
        "reviewer_id": "独立注释复核记录或复核人员标识。",
        "reviewed_preferred_route": "独立复核推荐的单细胞表示路线。",
        "review_scope": "独立复核覆盖的对象范围。",
        "review_summary": "独立复核得到的注释总结。",
    },
    "primary_selection_evidence.full.tsv": {
        "primary_representation": "最终选定的单细胞表示路线。",
        "evidence_decision": "主路线选择的证据判定。",
        "n_reviewers": "参与独立复核的人员数。",
        "excluded_clusters": "根据复核从主路线中排除的 cluster 列表。",
        "n_review_excluded_cells": "因复核排除的细胞数。",
        "n_cells": "主路线纳入的细胞数。",
        "counts_hash_unchanged": "主路线选择前后计数矩阵哈希是否保持一致。",
        "source_x_hash_unchanged": "主路线选择前后来源对象哈希是否保持一致。",
        "evidence_basis": "主路线选择所依据的独立复核和稳定性证据。",
    },
    "atb_identifier_crosswalk.full.tsv": {
        "namespace": "ATB 标识符所属的命名空间。",
        "identifier": "ATB 记录中的原始标识符。",
        "status": "ATB 标识符映射状态。",
        "assembly_or_version": "标识符使用的组装版本或数据库版本。",
        "coordinate_or_note": "标识符对应的坐标或映射备注。",
    },
    "interaction_database_query_audit.full.tsv": {
        "resource": "ATB 互作查询所使用的数据库或资源。",
        "query_rule": "ATB 互作记录的检索规则。",
        "exact_current_atb_records": "按当前 ATB 标识符规则检索到的精确记录数。",
        "excluded_collision_records": "因标识符碰撞或非目标匹配而排除的记录数。",
        "cca_records": "检索结果中属于 CCA 的记录数。",
        "interpretation": "查询结果的统计解释。",
    },
    "lnctard_atb_records.full.tsv": {
        "DiseaseName": "数据库记录的疾病名称。",
        "Regulator": "数据库记录的 lncRNA 调控分子。",
        "Target": "数据库记录的目标基因或分子。",
        "RegulationDiretion": "数据库记录的调控方向。",
        "Experimental.method.for.lncRNA.target": "lncRNA–目标关系的实验方法。",
        "ExpressionPattern": "数据库记录的 lncRNA/目标表达模式。",
        "Experimental.method.for.lncRNA.expression": "lncRNA 表达证据使用的实验方法。",
        "Data.accession": "数据库记录对应的数据 accession。",
        "Data.accession2": "数据库记录的第二数据 accession。",
        "influencedFunction": "数据库记录的受影响功能。",
        "regulatoryMechanism": "数据库记录的调控机制。",
        "regulatoryType": "数据库记录的调控类型。",
        "levelOfRegulation": "数据库记录的调控层级。",
        "Drugs": "数据库记录关联的药物信息。",
        "cancerStemCell": "数据库记录的癌症干细胞相关标记。",
        "hallmark": "数据库记录的 Hallmark 标记。",
        "diseaseCategory": "数据库记录的疾病类别。",
        "DiseaseName2": "数据库记录的第二疾病名称。",
        "RegulatorType": "调控分子的类型。",
        "TargetType": "目标分子的类型。",
        "RegulatorEnsembleID": "调控分子的 Ensembl ID。",
        "lncRegulatorPosition": "lncRNA 调控分子在数据库记录中的位置或坐标。",
        "TargetEnsembleID": "目标分子的 Ensembl ID。",
        "lncTargetPosition": "lncRNA–目标关系在数据库记录中的位置或坐标。",
        "RegulatorEntrezID": "调控分子的 Entrez Gene ID。",
        "TargetEntrezID": "目标分子的 Entrez Gene ID。",
        "RegulatorAliases": "调控分子的别名集合。",
        "TargetAliases": "目标分子的别名集合。",
        "Evidence": "数据库记录提供的支持证据。",
        "PubMedID": "数据库记录对应的 PubMed 文献编号。",
        "RID": "数据库记录的内部记录编号。",
        "SearchregulatoryMechanism": "检索到的调控机制文本。",
        "clincal.application": "数据库记录的临床应用描述。",
        "RegulatorCTC": "调控分子的 CTC 标识或注释。",
        "TargetCTC": "目标分子的 CTC 标识或注释。",
    },
    "atb_interaction_evidence.full.tsv": {
        "edge_id": "ATB 互作边的唯一标识。",
        "source_node": "ATB 互作边的来源节点。",
        "target_node": "ATB 互作边的目标节点。",
        "relation": "来源节点与目标节点之间的关系类型。",
        "context": "ATB 互作证据的疾病、组织或实验背景。",
        "evidence_tier": "ATB 互作证据等级。",
        "score": "ATB 互作记录的证据或关联评分。",
        "method": "ATB 互作证据的检索或推断方法。",
        "source": "ATB 互作证据来源。",
        "include_main": "该 ATB 互作记录是否纳入主证据集合。",
        "boundary": "该 ATB 互作证据的纳入边界。",
    },
    "atb_interaction_evidence.filtered.tsv": {
        "edge_id": "ATB 互作边的唯一标识。",
        "source_node": "ATB 互作边的来源节点。",
        "target_node": "ATB 互作边的目标节点。",
        "relation": "来源节点与目标节点之间的关系类型。",
        "context": "ATB 互作证据的疾病、组织或实验背景。",
        "evidence_tier": "ATB 互作证据等级。",
        "score": "ATB 互作记录的证据或关联评分。",
        "method": "ATB 互作证据的检索或推断方法。",
        "source": "ATB 互作证据来源。",
        "include_main": "该 ATB 互作记录是否纳入主证据集合。",
        "boundary": "该 ATB 互作证据的纳入边界。",
    },
    "atb_interaction_evidence_matrix.tsv": {
        "interaction": "ATB 互作矩阵中的互作名称或边标识。",
        "evidence_tier": "ATB 互作证据等级。",
        "score": "ATB 互作记录的证据或关联评分。",
        "context": "ATB 互作证据的疾病、组织或实验背景。",
        "source": "ATB 互作证据来源。",
    },
    "atb_ldha_prediction_summary.full.tsv": {
        "evidence_source": "ATB–LDHA 预测证据的算法或数据库来源。",
        "evidence_type": "ATB–LDHA 预测证据的类型。",
        "query": "预测中的 lncRNA 查询序列 accession。",
        "target": "预测中的 LDHA 目标序列 accession。",
        "observed": "算法输出的观测能量或候选数量摘要。",
        "decision_rule": "判定 ATB–LDHA 支持状态所使用的阈值规则。",
        "result": "ATB–LDHA 预测的支持状态。",
        "interpretation": "ATB–LDHA 预测结果的统计解释。",
    },
    "atb_ldha_sequence_manifest.full.tsv": {
        "molecule": "序列清单中的分子类别。",
        "accession": "序列记录 accession。",
        "entrez_gene_id": "序列对应的 Entrez Gene ID。",
        "length_nt": "核酸序列长度，单位为 nt。",
        "sequence_sha256": "序列内容的 SHA256 校验值。",
        "source_file_sha256": "来源序列文件的 SHA256 校验值。",
        "source": "序列来源数据库或文件。",
    },
    "lnctar_atb_ldha_prediction.full.tsv": {
        "query_accession": "LncTar 查询 lncRNA 序列 accession。",
        "query_length_nt": "查询 lncRNA 序列长度，单位为 nt。",
        "target_accession": "LncTar 目标 LDHA 序列 accession。",
        "target_length_nt": "目标 LDHA 序列长度，单位为 nt。",
        "delta_g_kcal_mol": "LncTar 预测的 RNA–RNA 自由能变化，单位为 kcal/mol。",
        "normalized_delta_g": "按序列长度归一化的自由能指标。",
        "query_start": "查询序列匹配区间起点。",
        "query_end": "查询序列匹配区间终点。",
        "target_start": "目标序列匹配区间起点。",
        "target_end": "目标序列匹配区间终点。",
        "default_cutoff": "LncTar 默认支持判定的自由能阈值。",
        "passes_default_cutoff": "预测结果是否通过 LncTar 默认阈值。",
    },
    "riblast_atb_ldha_local_interactions.full.tsv": {
        "interaction_id": "局部 RNA–RNA 互作候选的唯一标识。",
        "query_accession": "RIblast 查询 lncRNA 序列 accession。",
        "query_length_nt": "查询 lncRNA 序列长度，单位为 nt。",
        "target_accession": "RIblast 目标 LDHA 序列 accession。",
        "target_length_nt": "目标 LDHA 序列长度，单位为 nt。",
        "accessibility_energy_kcal_mol": "RIblast 预测的可及性自由能，单位为 kcal/mol。",
        "hybridization_energy_kcal_mol": "RIblast 预测的杂交自由能，单位为 kcal/mol。",
        "interaction_energy_kcal_mol": "RIblast 预测的局部互作自由能，单位为 kcal/mol。",
        "base_pairs": "局部互作中的碱基配对数。",
        "passes_minus_12": "局部互作能量是否不高于 −12 kcal/mol。",
        "passes_minus_16": "局部互作能量是否不高于 −16 kcal/mol。",
    },
}


def schema_description_for_path(name: str, rel_path: str) -> str | None:
    """Return an exact description for ambiguous fields in known schemas."""
    path = rel_path.replace("\\", "/").lower()
    basename = Path(path).name
    # Longest/most specific filename match wins.  The suffix-based matching
    # keeps the registry usable for both formal and copied report assets.
    matches = [
        (key, mapping)
        for key, mapping in SCHEMA_FIELD_DESCRIPTIONS.items()
        if (
            basename == key.lower()
            or basename.endswith("_" + key.lower())
            or path.endswith("/" + key.lower())
        )
    ]
    if matches:
        matches.sort(key=lambda item: len(item[0]), reverse=True)
        for _, mapping in matches:
            description = mapping.get(name)
            if description is not None:
                return description
    if ".model." in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["model.full.tsv"].get(name)
    if "apparent_roc.stat" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["apparent_ROC.stat.full.tsv"].get(name)
    if "integration_metrics" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["integration_metrics.full.tsv"].get(name)
    if "cluster_stability" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["cluster_stability.full.tsv"].get(name)
    if "infercnv_cell_scores" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["infercnv_cell_scores.full.tsv"].get(name)
    if "infercnv_cell_classification" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["infercnv_cell_classification.full.tsv"].get(name)
    if "malignant_cells" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["malignant_cells.filtered.tsv"].get(name)
    if "infercnv_donor_sensitivity" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["infercnv_donor_sensitivity.full.tsv"].get(name)
    if "infercnv_threshold_sensitivity" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["infercnv_threshold_sensitivity.full.tsv"].get(name)
    if "infercnv_statistical_tests" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["infercnv_statistical_tests.full.tsv"].get(name)
    if "target_expression" in basename:
        return SCHEMA_FIELD_DESCRIPTIONS["target_expression.full.tsv"].get(name)
    return None


FIELD_SEMANTIC_DESCRIPTIONS = {
    # Stable identifiers and labels
    "dataset": "公共表达数据集或队列标识。",
    "sample_id": "样本唯一标识。",
    "sample_ids": "该汇总记录包含的样本标识列表。",
    "library_id": "单细胞测序文库唯一标识。",
    "patient_id": "病例或患者唯一标识。",
    "donor_id": "供体或病例唯一标识。",
    "donor_ids": "该汇总记录包含的供体标识列表。",
    "cell_id": "细胞条形码或细胞唯一标识。",
    "neighbor_cell_id": "空间邻近关系中的邻居细胞标识。",
    "association_id": "相关性分析记录的唯一标识。",
    "candidate": "候选基因或候选分子名称。",
    "gene": "基因符号。",
    "gene_symbol": "基因符号。",
    "feature_id": "表达矩阵中的特征或探针编号。",
    "feature": "当前统计行对应的基因、通路或目标特征名称。",
    "pathway": "通路或基因集名称。",
    "metric": "当前行汇总或检验的指标名称。",
    "metric_class": "指标所属的表达、通路评分或其他统计类别。",
    "group": "样本或细胞所属的比较分组。",
    "group1": "比较中的第一组标签（实验组）。",
    "group2": "比较中的第二组标签（对照组）。",
    "group_1": "比较中的第一组标签。",
    "group_2": "比较中的第二组标签。",
    "reference_group": "统计模型使用的参考组标签。",
    "contrast_id": "差异比较的唯一标识。",
    "contrast": "差异比较的组别及方向定义。",
    "contrast_direction": "差异效应计算的组别方向。",
    "tumor_group": "实验组肿瘤分组标签。",
    "control_group": "对照组分组标签。",
    "analysis_role": "该记录在当前分析中的角色。",
    "role": "该记录或样本在当前分析中的角色。",
    "population": "统计汇总所使用的细胞或样本人群。",
    "analysis_population": "统计分析所使用的细胞或样本人群。",
    "statistical_unit": "效应量或检验使用的统计单位。",
    "test_unit": "组间检验使用的统计单位。",
    "paired": "该比较是否按病例或供体配对。",
    "representation": "当前结果使用的单细胞表示路线。",
    "source": "该记录的来源数据、证据库或输入对象。",
    "source_model": "产生该记录的上游统计模型名称。",
    "source_table": "该结果对应的来源表相对路径或名称。",
    "source_file": "该记录的来源文件名称或相对路径。",
    "source_file_sha256": "来源文件的 SHA256 校验值。",
    "source_url": "外部证据来源的网页或 API 地址。",
    "evidence_boundary": "该结果的证据范围和使用边界。",
    "status": "该记录的计算完成、筛选或质量审计状态。",
    "reason": "该状态或筛选判定的原因。",
    "description": "该记录的文字说明或结果细节。",
    "note": "该记录的审计备注或补充说明。",
    "interpretation": "该结果数值或证据记录的统计解释。",
    "method": "生成该结果所使用的方法名称。",
    "test": "该比较所使用的统计检验名称。",
    "test_method": "该比较所使用的统计检验方法。",
    "model": "拟合该结果的统计模型名称。",
    "model_type": "统计模型的类型。",
    "model_formula": "统计模型的设计公式。",
    "design_formula": "差异表达模型的设计公式。",
    "contrast_definition": "实验组与对照组的比较定义及方向。",
    "filter_rule": "结果筛选使用的阈值与规则。",
    "filter_rule_source": "筛选规则的来源模型或规则集。",
    "rule_set": "候选评分或筛选使用的规则集名称。",
    "rule_note": "规则集的文字定义或适用说明。",
    "rule_summary": "该记录适用的候选评分规则汇总。",
    "selection_mode": "候选或主结果的选择模式。",
    "selection_status": "该记录的选择或纳入状态。",
    "priority_status": "候选在优先级筛选中的状态。",
    "candidate_status": "候选基因在交集或筛选中的状态。",
    "candidate_class": "候选基因的分类标签。",
    "candidate_source": "候选基因进入当前列表的来源。",
    "candidate_source_status": "候选来源记录的状态。",
    "prior_evidence_status": "候选已有证据的状态。",
    "interpretation_status": "该结果的解释状态或证据级别。",
    "evidence_type": "证据记录的类型。",
    "evidence_source": "证据记录的数据库、算法或实验来源。",
    "evidence_domain": "证据所属的分析领域。",
    "evidence_tier": "证据支持等级。",
    "evidence_grade": "外部证据质量等级。",
    "evidence_grade_summary": "候选外部证据等级的汇总。",
    "claim": "外部证据记录所支持的原始主张。",
    "result": "证据查询或预测得到的结果状态。",
    "directness": "证据与当前候选/疾病问题的直接性等级。",
    "validation_status": "外部证据的验证状态。",
    "next_experiment": "外部证据表记录的下一项验证实验描述。",
    "risk_note": "外部证据的风险或适用性备注。",
    # Statistical values
    "logFC": "实验组相对于对照组的 log2 fold change。",
    "logfoldchange": "目标组相对于参考组的 log2 fold change。",
    "log2fc": "实验条件相对于对照条件的 log2 fold change。",
    "p_value": "统计检验的原始 P 值。",
    "pvalue": "统计检验的原始 P 值。",
    "pval": "marker 或差异检验的原始 P 值。",
    "raw_p_value": "统计检验的原始 P 值。",
    "p_value_model": "统计模型检验的原始 P 值。",
    "p_adjust": "经多重检验校正后的 P 值。",
    "p_adjusted": "经多重检验校正后的 P 值。",
    "p_adj_model": "统计模型检验经多重检验校正后的 P 值。",
    "p_adj_plot_family": "同一绘图结果族内校正后的 P 值。",
    "pval_adj": "marker 或差异检验经多重检验校正后的 P 值。",
    "adjusted_p_value": "经多重检验校正后的 P 值。",
    "FDR": "差异表达检验经多重检验校正后的 FDR（Benjamini–Hochberg 校正 P 值）。",
    "fdr": "跨队列或方向一致性分析经校正后的 FDR。",
    "p_display": "用于图形或表格展示的格式化原始 P 值。",
    "p_adjusted_display": "用于图形或表格展示的格式化校正 P 值。",
    "adjusted_significance": "根据校正 P 值阈值生成的显著性状态。",
    "significance": "根据预设显著性阈值生成的状态标签。",
    "significance_label": "根据统计显著性阈值生成的标签。",
    "rank": "marker 在对应 cluster 中按统计量排序的位置。",
    "rank_p": "按原始 P 值从小到大排序的位置。",
    "rank_metric": "用于排序或预排序富集的统计量。",
    "marker_rank": "marker 字典中的优先级排序位置。",
    "score": "当前表定义的统计、marker 匹配或证据评分。",
    "rho": "Spearman 秩相关系数。",
    "fisher_combined_p": "跨队列合并的 Fisher 组合 P 值。",
    "effect": "配对比较中实验组减对照组的效应量。",
    "effect_raw": "原始表达尺度上的效应量。",
    "effect_size": "标准化后的组间效应量。",
    "standardized_effect": "标准化的组间效应量。",
    "mean_standardized_effect": "跨队列标准化效应量的平均值。",
    "ci_low": "效应量或相关系数置信区间下限。",
    "ci_high": "效应量或相关系数置信区间上限。",
    "estimate": "模型中当前项的估计系数。",
    "std_error": "模型估计系数的标准误。",
    "hazard_ratio": "Cox 模型估计的风险比。",
    "vif": "模型项的方差膨胀因子。",
    "auc": "ROC 曲线下面积。",
    "sensitivity": "ROC 判别灵敏度。",
    "specificity": "ROC 判别特异度。",
    "threshold": "判别或筛选使用的数值阈值。",
    # Expression/QC values
    "expression": "指定样本、细胞或目标基因的表达值。",
    "expression_value": "指定表达尺度下的表达值。",
    "expression_scale": "表达值使用的数值尺度。",
    "value": "当前指标或表达汇总的数值。",
    "value_scale": "该数值使用的表达或统计尺度。",
    "mean_tumor": "实验组肿瘤的平均表达或评分。",
    "mean_control": "对照组的平均表达或评分。",
    "mean_adjacent": "癌旁组的平均表达或评分。",
    "mean_difference": "实验组减对照组的平均差值。",
    "mean_difference_tumor_minus_control": "实验组减对照组的平均表达差值。",
    "effect_group_1_minus_group_2": "第一组减第二组的效应量。",
    "effect_group_1_minus_group_2_mean_log1p": "第一组减第二组的 mean log1p 表达差值。",
    "group_1_summary": "第一组的表达或评分汇总值。",
    "group_2_summary": "第二组的表达或评分汇总值。",
    "mean_log1p": "log1p 表达值的平均值。",
    "median_log1p": "log1p 表达值的中位数。",
    "q25_log1p": "log1p 表达值的第 25 百分位数。",
    "q75_log1p": "log1p 表达值的第 75 百分位数。",
    "mean_log1p_cpm": "log1p(CPM) 表达值的平均值。",
    "log1p_cpm": "CPM 经 log1p 转换后的表达值。",
    "raw_count": "原始计数矩阵中的计数总和。",
    "pseudobulk_count_sum": "供体伪 bulk 单位内的计数总和。",
    "mean_count_per_evaluable_cell": "每个可评估细胞的平均计数。",
    "positive_rate": "表达值大于零的细胞或样本比例。",
    "detection_rate": "达到检出标准的供体或细胞比例。",
    "detection_fraction": "达到检出标准的细胞比例。",
    "positive_cells": "表达值大于零的细胞数。",
    "total_cells": "该汇总记录中的细胞总数。",
    "detected_cells": "达到检出标准的细胞数。",
    "positive": "该细胞或样本是否达到表达检出条件。",
    "library_size": "该伪 bulk 单位的总文库计数。",
    "library_n_genes": "单个文库包含的基因数。",
    "merged_n_genes": "外连接合并后表达矩阵的基因数。",
    "genes_missing_from_library_after_outer_merge": "外连接合并后该文库缺失的基因数。",
    "missing_gene_fraction_of_merged_union": "该文库缺失基因占合并基因并集的比例。",
    # Coordinates and spatial/scRNA fields
    "umap_1": "UMAP 第一维坐标。",
    "umap_2": "UMAP 第二维坐标。",
    "centroid_x": "细胞类型或 cluster 空间质心的 X 坐标。",
    "centroid_y": "细胞类型或 cluster 空间质心的 Y 坐标。",
    "distance": "细胞与空间邻居之间的距离。",
    "neighbor_rank": "空间邻居按距离排序的位置。",
    "cluster": "Leiden cluster 编号。",
    "cell_type": "细胞类型标签。",
    "reviewed_cell_type": "复核后的细胞类型标签。",
    "reviewed_label": "复核后的 cluster 或细胞标签。",
    "assigned_label": "自动或规则分配的注释标签。",
    "automatic_label": "自动注释得到的标签。",
    "provisional": "该注释是否为 provisional 标签。",
    "reviewed_confidence": "复核注释的置信度。",
    "confidence": "注释置信度或注释证据等级。",
    "annotation_evidence": "支持该注释的 marker 或统计证据摘要。",
    "annotation_basis": "注释所依据的 marker、工具得分或人工复核信息。",
    "n_cells": "该 cluster、样本或细胞类型包含的细胞数。",
    "n_genes": "该细胞检测到的基因数量。",
    "n_samples_present": "该 cluster 或汇总记录中出现的样本数。",
    "n_donors_present": "该 cluster 或汇总记录中出现的供体数。",
    "dominant_sample": "该 cluster 中细胞数占比最高的样本。",
    "dominant_sample_fraction": "主导样本占该 cluster 细胞的比例。",
    "dominant_donor": "该 cluster 中细胞数占比最高的供体。",
    "dominant_donor_fraction": "主导供体占该 cluster 细胞的比例。",
    "sample_entropy": "cluster 细胞样本来源分布的 Shannon 熵。",
    "sample_entropy_normalized": "按样本数归一化后的样本来源 Shannon 熵。",
    "doublet_fraction": "cluster 中潜在双细胞比例。",
    "doublet_risk": "cluster 的双细胞风险等级。",
    "mixed_lineage_fraction": "cluster 中混合谱系细胞比例。",
    "mixed_lineage_risk": "cluster 的混合谱系风险等级。",
    # Boolean/selection fields
    "tested": "该特征是否进入差异检验。",
    "pass_filter": "该特征是否通过交付筛选。",
    "eligible": "该记录是否满足当前分析的纳入条件。",
    "paired": "该比较是否按病例或供体配对。",
    "gene_present": "该基因是否存在于当前表达矩阵。",
    "bulk_eligible": "该候选是否满足 bulk 证据纳入条件。",
    "promotion_allowed": "规则是否允许该候选进入后续优先级。",
    "include_main": "该记录是否纳入主 ATB 证据集合。",
    "inference_eligible": "该统计行是否满足推断所需的样本量条件。",
    "integrated_priority_selected": "该候选是否被综合证据优先级规则选中。",
    "priority_pool_member": "该记录是否属于综合优先级候选池。",
    "no_unrestricted_gene_search": "是否未进行未限定候选面板的基因搜索。",
    "is_ldha": "该记录的目标是否为 LDHA。",
    "is_atb_experiment": "该实验是否属于 ATB 相关实验。",
    # Files/identifiers/metadata
    "figure_id": "模块内图形的唯一标识。",
    "figure_type": "图形的分析类型。",
    "pdf": "图形 PDF 文件的相对路径。",
    "png": "图形 PNG 文件的相对路径。",
    "year": "外部证据记录的发表或数据年份。",
    "as_of_date": "外部证据检索或核验截止日期。",
    "evidence_as_of_date": "外部证据核验截止日期。",
    "doi": "外部文献的 DOI。",
    "pmid": "PubMed 文献编号。",
    "accession": "公共数据或序列记录的 accession。",
    "accession_or_pmid": "外部证据对应的 accession 或 PubMed 编号。",
    "assembly_or_version": "序列或数据库使用的组装版本/数据库版本。",
    "sequence_sha256": "序列文件或序列内容的 SHA256 校验值。",
    "mapping_status": "探针或特征到基因的映射状态。",
}


def table_context_label(rel_path: str, kind: str) -> str:
    lower = rel_path.lower()
    if "infercnv" in lower:
        return "inferCNV 纯化"
    if "malignant_expression" in lower:
        return "恶性细胞表达"
    if "scrna_qc" in lower:
        return "单细胞 QC"
    if "scrna_dual_integration" in lower:
        return "单细胞整合与聚类"
    if "scrna_dual_annotation" in lower:
        return "单细胞注释"
    if "bulk_candidate_stability" in lower:
        return "bulk 候选稳定性"
    if "bulk_scrna_intersection" in lower:
        return "bulk–单细胞交集"
    if "ldha_expression" in lower:
        return "LDHA 表达"
    if "pathway_scores" in lower:
        return "通路评分"
    if "atb_phenotype" in lower:
        return "ATB 表型"
    if "clinical_progression" in lower:
        return "临床结局"
    if "external_evidence" in lower:
        return "外部证据"
    if "atb_interaction" in lower:
        return "ATB 互作证据"
    if "atb_ldha_prediction" in lower:
        return "ATB–LDHA 预测"
    if "gse103909_reanalysis" in lower:
        return "GSE103909 重分析"
    return "该分析"


def phnet_field_description(name: str, rel_path: str, kind: str) -> str | None:
    if name in PHNET_FIELD_DESCRIPTIONS:
        return PHNET_FIELD_DESCRIPTIONS[name]
    base_name = re.sub(r"_external_.*$", "", name)
    if base_name != name and base_name in PHNET_FIELD_DESCRIPTIONS:
        return PHNET_FIELD_DESCRIPTIONS[base_name] + "（合并外部节点属性表后的对应列。）"
    lower = rel_path.lower()
    if "docking_results" in lower:
        return f"{name}：分子对接结果表中的对象、评分或构象文件信息。"
    if "drug_net" in lower or "ppi" in lower or "string_" in lower:
        return f"{name}：网络节点、边或拓扑属性。"
    if "venn" in lower or "batman" in lower or "tcmsp" in lower:
        return f"{name}：中药成分、蛋白靶点或疾病基因集合相关属性。"
    if "go_kegg" in lower or kind == "enrichment":
        return f"{name}：富集分析条目属性或统计量。"
    return None


def table_kind_for_path(rel_path: str) -> str:
    lower = rel_path.lower()
    name = Path(rel_path).name.lower()
    if name.endswith(".groups.tsv") or ".groups." in name:
        return "sample_group"
    if "pdata" in lower:
        return "sample_metadata"
    if "exprs" in lower:
        return "expression_matrix"
    if "gene_symbol_entrezid" in lower:
        return "gene_mapping"
    if "gsea_enrichment" in lower:
        return "gsea"
    if "wgcna" in lower or "module_membership" in lower:
        return "wgcna"
    if "df.cells_metadata" in lower:
        return "cell_metadata"
    if "cluster_marker_means" in lower:
        return "cluster_marker_means"
    if "cellchat_counts" in lower:
        return "cellchat_counts"
    if "cellchat_weight" in lower:
        return "cellchat_weight"
    if "cellchat_lr_prob_pval" in lower:
        return "cellchat_lr"
    if "cellchat_pathway_prob" in lower:
        return "cellchat_pathway"
    if "summary_metrics" in lower and "augur" in lower:
        return "augur"
    if "cellrss.matrix" in lower:
        return "rss"
    if "scenic.reg.tsv" in lower:
        return "scenic_reg"
    if "scenic.adj.tsv" in lower:
        return "scenic_adj"
    if "regulon.tsv" in lower:
        return "regulon"
    if "go_enrichment" in lower or "kegg_enrichment" in lower or "reactome_enrichment" in lower:
        return "enrichment"
    if "degs" in lower or "marker_genes" in lower or "rank.res" in lower:
        return "deg"
    if "prop.barplot.input" in lower:
        return "composition"
    return "generic"


def first_header_row(sheets: list[dict]) -> list[str]:
    if not sheets:
        return []
    rows = sheets[0].get("rows") or []
    if not rows:
        return []
    return [str(value) for value in rows[0]]


def field_description_for_name(field: str, rel_path: str, kind: str, index: int) -> tuple[str, str]:
    name = field.strip()
    if not name:
        if kind == "cell_metadata":
            return "cell_id", "细胞条形码或细胞唯一标识。"
        if kind == "augur":
            return "index", "指标行索引。"
        return f"index_{index + 1}", "表格行索引或未命名字段。"

    # Resolve exact table schemas first.  This prevents ambiguous names such
    # as score/value/source from being described as if they had one universal
    # meaning across bulk, single-cell, inferCNV and evidence tables.
    schema_description = schema_description_for_path(name, rel_path)
    if schema_description:
        return name, schema_description

    lower_path = rel_path.replace("\\", "/").lower()
    lower_name = name.casefold()

    # Path-aware descriptions for repeated short column names.
    if "markers_scvi" in lower_path:
        marker_descriptions = {
            "representation": "marker 检验使用的单细胞表示路线。",
            "cluster": "marker 检验对应的 Leiden cluster 编号。",
            "rank": "marker 在对应 cluster 中按检验统计量排序的位置。",
            "gene": "候选 marker 的基因符号。",
            "score": "marker 检验输出的统计量或排序评分。",
            "logfoldchange": "该 cluster 相对于其余细胞的 log2 fold change。",
            "pval": "marker 检验的原始 P 值。",
            "pval_adj": "marker 检验经多重检验校正后的 P 值。",
            "positive_marker_modules": "支持该 marker 的正向 marker 模块名称。",
            "negative_marker_modules": "与该 marker 方向相反的 marker 模块名称。",
        }
        if name in marker_descriptions:
            return name, marker_descriptions[name]
    if "pathway_scores.full.tsv" in lower_path:
        if lower_name == "score":
            return name, "该样本在指定通路上的标准化通路评分。"
        if lower_name == "ldha":
            return name, "该样本在指定表达尺度上的 LDHA 表达值。"
        if lower_name == "method":
            return name, "通路评分的计算方法。"
    if "donor_pairs.full.tsv" in lower_path and lower_name == "ldha":
        return name, "供体伪 bulk 单位的 LDHA 表达值。"
    if "donor_pairs.full.tsv" in lower_path and lower_name.startswith("hallmark_"):
        return name, "供体伪 bulk 单位的指定 Hallmark 通路评分。"
    if "atb_interaction_evidence" in lower_path:
        interaction_descriptions = {
            "source_node": "ATB 互作边的来源节点。",
            "target_node": "ATB 互作边的目标节点。",
            "source": "ATB 互作证据来源。",
            "score": "ATB 互作记录的证据或关联评分。",
            "target": "ATB 记录中的目标分子或基因。",
            "context": "ATB 互作证据的疾病、组织或实验背景。",
            "relation": "来源节点与目标节点之间的关系类型。",
            "method": "ATB 互作证据的检索或推断方法。",
            "boundary": "该 ATB 互作证据的纳入边界。",
            "evidence_tier": "ATB 互作证据等级。",
            "interaction": "ATB 互作矩阵中的互作名称或边标识。",
            "include_main": "该 ATB 互作记录是否纳入主证据集合。",
        }
        if lower_name in interaction_descriptions:
            return name, interaction_descriptions[lower_name]
    if "integration_metrics" in lower_path and lower_name == "metric":
        return name, "单细胞整合质量指标名称。"
    if "spatial_centroids" in lower_path and lower_name == "unit_type":
        return name, "空间质心汇总单位类型（细胞类型或 cluster）。"
    if "spatial_review" in lower_path and lower_name in {"review_gate", "review_state", "review_scope", "review_boundary"}:
        return name, "空间坐标人工复核的状态或适用范围。"
    if "association_pairs" in lower_path:
        pair_descriptions = {
            "x_metric": "相关性分析横轴指标名称。",
            "y_metric": "相关性分析纵轴指标名称。",
            "x_value": "相关性分析横轴指标的观测值。",
            "y_value": "相关性分析纵轴指标的观测值。",
            "statistical_unit": "相关性分析的统计单位。",
        }
        if lower_name in pair_descriptions:
            return name, pair_descriptions[lower_name]
    if lower_path.endswith("/association_statistics.full.tsv") or lower_path.endswith("/candidate_association.full.tsv"):
        if lower_name == "rho":
            return name, "候选或指标对之间的 Spearman 秩相关系数。"
        if lower_name == "method":
            return name, "相关性统计所使用的方法。"
    if "paired_statistics" in lower_path:
        paired_descriptions = {
            "feature": "配对比较中检验的基因、目标或通路特征。",
            "family": "特征所属的统计分析家族。",
            "contrast": "肿瘤与癌旁样本的配对比较定义。",
            "mean_tumor": "肿瘤组的平均表达或评分。",
            "mean_adjacent": "癌旁组的平均表达或评分。",
            "effect": "肿瘤组减癌旁组的配对效应量。",
            "test": "配对比较使用的统计检验。",
            "inference_eligible": "该配对比较是否达到预设样本量并可进行推断。",
        }
        if lower_name in paired_descriptions:
            return name, paired_descriptions[lower_name]
    if "candidate_scoring_rule" in lower_path:
        scoring_rule_descriptions = {
            "min_detected_cohorts": "候选至少需要被检出的队列数阈值。",
            "min_consistent_direction_cohorts": "候选至少需要保持方向一致的队列数阈值。",
            "bulk_p_cut": "bulk 证据使用的原始 P 值阈值。",
            "bulk_fdr_cut": "bulk 证据使用的 FDR 阈值。",
            "bulk_abs_effect_cut": "bulk 证据使用的绝对效应量阈值。",
            "association_p_cut": "相关性证据使用的原始 P 值阈值。",
            "association_fdr_cut": "相关性证据使用的 FDR 阈值。",
            "min_score": "候选进入优先级的最低综合评分。",
            "promotion_allowed": "该规则是否允许候选晋级。",
        }
        if lower_name in scoring_rule_descriptions:
            return name, scoring_rule_descriptions[lower_name]

    # Exact field semantics shared by several schemas.
    if name in FIELD_SEMANTIC_DESCRIPTIONS:
        return name, FIELD_SEMANTIC_DESCRIPTIONS[name]
    if lower_name in FIELD_SEMANTIC_DESCRIPTIONS:
        return name, FIELD_SEMANTIC_DESCRIPTIONS[lower_name]

    # InferCNV block columns encode a chromosome/profile block and a proxy
    # statistic.  Handle them before the generic score/p-value patterns.
    if re.fullmatch(r"block_score_[A-Za-z0-9]+\.(?:p|q)_proxy", name):
        block, proxy = name.rsplit(".", 1)
        proxy_label = "p_proxy" if proxy == "p_proxy" else "q_proxy"
        proxy_meaning = "p 值代理统计量" if proxy_label == "p_proxy" else "q 值代理统计量"
        return name, f"inferCNV {block.removeprefix('block_score_')} block 的 {proxy_meaning}。"
    if re.fullmatch(r"arm_chr(?:[1-9]|1\d|2[0-2])_[pq]", lower_name):
        arm = name.rsplit("_", 1)[0].removeprefix("arm_") + name.rsplit("_", 1)[1]
        return name, f"{arm} 染色体臂的参考中心化 inferCNV 信号。"

    # Explicit statistical name families.  These rules are deliberately
    # narrow so that FDR, rank and score cannot fall through to expression
    # descriptions or to a broad "analysis record" placeholder.
    if lower_name in {"fdr", "false_discovery_rate"}:
        return name, "多重检验校正后的错误发现率（FDR）。"
    if lower_name in {"pval", "pvalue", "p_value", "raw_p_value", "p_value_model"}:
        return name, "统计检验的原始 P 值。"
    if lower_name in {"pval_adj", "p_adjust", "p_adjusted", "adjusted_p_value", "p_adj", "p_adj_model"}:
        return name, "统计检验经多重检验校正后的 P 值。"
    if lower_name in {"p_display", "pvalue_display", "p_value_display"}:
        return name, "用于展示的格式化原始 P 值。"
    if lower_name in {"p_adjusted_display", "p_adj_display"}:
        return name, "用于展示的格式化校正 P 值。"
    if lower_name in {"rank"}:
        if "marker" in lower_path:
            return name, "marker 在对应 cluster 中按统计量排序的位置。"
        if "fgsea" in lower_path or "gsea" in lower_path:
            return name, "富集峰值或核心富集条目对应的排序位置。"
        return name, "结果记录按当前排序统计量排列的位置。"
    if lower_name in {"rank_p"}:
        return name, "按原始 P 值从小到大排序的位置。"
    if lower_name in {"rank_metric"}:
        return name, "用于预排序富集或结果排序的统计量。"
    if lower_name in {"score"}:
        if "annotation" in lower_path or "markers" in lower_path:
            return name, "marker 或细胞类型注释匹配的统计评分。"
        if "pathway_scores" in lower_path:
            return name, "指定通路的样本级标准化评分。"
        if "atb_interaction" in lower_path:
            return name, "ATB 互作证据的关联评分。"
        return name, f"{table_context_label(rel_path, kind)}记录的评分值。"
    if lower_name in {"sample_count"}:
        return name, "该队列纳入分析的样本总数。"
    if lower_name in {"group_counts"}:
        return name, "各比较分组的样本数汇总。"
    if lower_name in {"rho"}:
        return name, "Spearman 秩相关系数。"
    if lower_name in {"fisher_combined_p"}:
        return name, "跨队列合并的 Fisher 组合 P 值。"
    if lower_name in {"auc", "auc_ci_low", "auc_ci_high"}:
        return name, {
            "auc": "ROC 曲线下面积。",
            "auc_ci_low": "AUC 置信区间下限。",
            "auc_ci_high": "AUC 置信区间上限。",
        }[lower_name]

    # Specific numeric suffixes retain their denominator/measurement rather
    # than being collapsed into a generic count or proportion phrase.
    count_suffixes = {
        "cells": "细胞数",
        "donors": "供体数",
        "samples": "样本数",
        "pairs": "完整配对数",
        "cohorts": "队列数",
        "features": "特征数",
        "genes": "基因数",
        "records": "记录数",
        "units": "统计单位数",
        "groups": "分组数",
        "parameters": "模型参数数",
    }
    if lower_name.startswith("n_") or lower_name.endswith("_count"):
        pieces = lower_name.removeprefix("n_").split("_")
        suffix = next((key for key in count_suffixes if pieces[-1] == key), None)
        if suffix:
            prefix = "、".join(pieces[:-1])
            prefix_text = f"{prefix}的" if prefix else ""
            return name, f"{prefix_text}{count_suffixes[suffix]}。"
        return name, f"{table_context_label(rel_path, kind)}记录的计数。"
    if lower_name.endswith("_cells"):
        return name, f"{table_context_label(rel_path, kind)}中对应的细胞数。"
    if any(lower_name.endswith(suffix) for suffix in ("_fraction", "_proportion", "_rate", "_coverage")):
        if "positive" in lower_name or "detection" in lower_name:
            return name, "达到表达或检出标准的细胞、样本或供体比例。"
        if "donor" in lower_name:
            return name, "供体层面的比例指标。"
        return name, f"{table_context_label(rel_path, kind)}记录的比例指标。"
    if lower_name in {"proportion"}:
        return name, "对应细胞类型在该统计单位中的细胞比例。"

    # Coordinate, boolean, path and checksum fields are also explicit so
    # they never reach the generic fallback.
    if lower_name in {"umap1", "umap_1", "umap_x"}:
        return name, "UMAP 第一维坐标。"
    if lower_name in {"umap2", "umap_2", "umap_y"}:
        return name, "UMAP 第二维坐标。"
    if lower_name.startswith(("is_", "has_")) or lower_name.endswith(("_bool", "_available", "_supported", "_complete", "_consistent", "_stable")):
        return name, "该记录是否满足对应的可用性、完整性或筛选条件。"
    if lower_name.endswith("_path") or lower_name in {"matrix_path", "features_path", "barcodes_path"}:
        return name, "该输入或结果对象的相对文件路径。"
    if lower_name.endswith("_sha256") or lower_name.endswith("_hash"):
        return name, "对应文件或对象的 SHA256/哈希校验值。"

    if kind == "cluster_marker_means" and name != "cluster":
        return name, f"{name} marker 基因在对应 cluster 中的平均表达值。"
    if kind == "sample_group":
        if name == "samples":
            return name, "GEO 样本编号。"
        if name == "groups":
            return name, "样本所属比较分组。"
    if kind == "sample_metadata":
        if name == "samples":
            return name, "GEO 样本编号。"
        if name in {"title", "geo_accession", "source_name_ch1", "organism_ch1", "characteristics_ch1", "characteristics_ch1.1", "characteristics_ch1.2"}:
            return name, "GEO 样本平台注释或样本来源信息。"
        if name.endswith("_date"):
            return name, "GEO 记录中的日期信息。"
    if kind == "expression_matrix":
        if name in {"geneID", "GeneID"}:
            return name, "表达矩阵中的基因编号或基因标识。"
        if name == "Symbol":
            return name, "表达矩阵中的基因符号。"
        if name == "Length":
            return name, "基因长度注释。"
        if re.match(r"^GSM\d+$", name):
            return name, "该 GEO 样本对应的表达矩阵数值。"
    if kind == "gene_mapping":
        mapping_descriptions = {
            "SYMBOL": "基因符号。",
            "ALIAS": "基因别名或输入基因名。",
            "ENTREZID": "NCBI Entrez Gene ID。",
            "ENSEMBL": "Ensembl 基因 ID。",
        }
        if name in mapping_descriptions:
            return name, mapping_descriptions[name]
    if kind == "enrichment" and name == "geneID":
        return name, "参与该富集条目的输入基因符号集合。"
    if kind == "gsea":
        gsea_descriptions = {
            "ID": "GSEA 基因集或通路 ID。",
            "Description": "GSEA 基因集或通路名称。",
            "setSize": "参与检验的基因集大小。",
            "enrichmentScore": "运行和统计得到的富集分数。",
            "NES": "标准化富集分数。",
            "pvalue": "GSEA 原始 P 值。",
            "p.adjust": "多重检验校正后的 P 值。",
            "qvalue": "GSEA q 值。",
            "rank": "富集峰值对应的排序位置。",
            "leading_edge": "leading edge 统计摘要。",
            "core_enrichment": "核心富集基因集合。",
            "geneID": "参与该 GSEA 条目的基因符号集合。",
        }
        if name in gsea_descriptions:
            return name, gsea_descriptions[name]
    if kind == "wgcna":
        wgcna_descriptions = {
            "geneID": "WGCNA 网络中的基因符号或基因标识。",
            "MM": "模块成员度，与目标模块特征向量的相关性。",
            "gene_sig": "基因与分组性状之间的相关性或显著性指标。",
            "groups": "WGCNA 模块或性状分组标签。",
            "colors": "WGCNA 分配得到的模块颜色。",
            "modules": "WGCNA 模块名称或模块颜色。",
        }
        if name in wgcna_descriptions:
            return name, wgcna_descriptions[name]
    if kind == "cell_metadata" and name == "n_genes":
        return name, "该细胞检测到的基因数量。"
    if kind == "cellchat_counts" and CELL_TYPE_FIELD_RE.match(name):
        return name, f"接收细胞类型为 {name} 时的通讯数量；行 `Cells` 为发送细胞类型。"
    if kind == "cellchat_weight" and CELL_TYPE_FIELD_RE.match(name):
        return name, f"接收细胞类型为 {name} 时的通讯权重；行 `Cells` 为发送细胞类型。"
    if kind == "augur" and CELL_TYPE_FIELD_RE.match(name):
        return name, f"{name} 细胞类型对应的 Augur 指标值。"
    if kind == "rss" and CELL_TYPE_FIELD_RE.match(name):
        return name, f"{name} 亚型对应的 regulon specificity score (RSS)。"
    if kind == "regulon" and name == "geneID":
        return name, "该 regulon 包含的目标基因。"
    phnet_description = phnet_field_description(name, rel_path, kind)
    if phnet_description:
        return name, phnet_description
    if name in COMMON_FIELD_DESCRIPTIONS:
        return name, COMMON_FIELD_DESCRIPTIONS[name]
    # Remaining systematic columns are mapped by their biological/statistical
    # role.  The uppercase-name rule is intentionally limited to expression
    # or score tables; it must never classify FDR, RID, or other identifiers
    # as gene-expression columns.
    if GENE_SYMBOL_RE.match(name) and any(token in lower_path for token in ("expression", "pseudobulk", "scores_long", "exprs")):
        return name, f"{name} 在该表统计单位中的表达或评分值。"
    if CELL_TYPE_FIELD_RE.match(name):
        return name, f"{name} 细胞类型对应的矩阵值。"
    if lower_name in {"pdf", "png"}:
        return name, f"图形 {name.upper()} 文件的相对路径。"
    if lower_name in {"detail", "note", "notes", "clinical_notes", "fragment_notes"}:
        return name, "该记录的文字说明、审计备注或结果细节。"
    if lower_name in {"source_group_effect", "source_donor_composition"}:
        return name, "该结果对应的来源表或来源分析名称。"
    if lower_name == "recommended":
        return name, "该图或结果是否纳入正式交付。"
    if lower_name.endswith("_id"):
        return name, f"{table_context_label(rel_path, kind)}记录的唯一标识。"
    if lower_name in {"cell_type", "celltype", "celltype_broad", "major_cell_type", "target_celltype", "sender", "receiver"}:
        return name, "该记录对应的细胞类型、发送群或接收群标签。"
    if lower_name in {"group", "group_a", "group_b", "reference_group", "contrast_group", "analysis_group", "condition", "stage", "disease_stage", "comparison", "comparison_level", "comparison_column"} or lower_name.endswith("_group"):
        return name, "该记录使用的分组、疾病阶段或比较标签。"
    if lower_name in {"region", "platform", "branch", "database", "tissue", "sex", "diagnosis", "histology_values", "diagnosis_values", "region_provenance"}:
        return name, "该样本或分析记录的来源、平台、组织或分层标签。"
    if lower_name in {"marker", "marker_gene", "tf", "ligand", "receptor", "ligand_complex", "receptor_genes", "regulon", "pathway_name", "term_id", "term_description", "interaction_name", "interaction_name_2"} or lower_name.endswith("_gene"):
        return name, "该记录对应的基因、调控子、配体受体或通路名称。"
    if lower_name in {"status", "validity", "classification", "selection_status", "priority_status", "axis_status", "threshold_status", "inference_status", "metadata_status", "role_audit_status", "annotation_status", "marker_status", "score_status", "coverage_status"} or lower_name.endswith("_status"):
        return name, "该记录的计算完成度、筛选、分类或质量审计状态。"
    if lower_name in {"reason", "decision_reason", "unknown_reason", "cnv_reason", "selection_basis", "evidence_boundary", "causal_inference", "association_claim", "stability_limitation"} or lower_name.endswith("_reason"):
        return name, "该分类、筛选或证据判定的原因与适用边界。"
    if lower_name in {"stars", "significance_star_bh"}:
        return name, "根据多重校正后显著性阈值生成的星号或 ns 标签。"
    if any(token in lower_name for token in ("mean", "median", "min", "max", "q25", "q75", "sd_", "zscore", "distance", "statistic", "lisi", "asw", "delta", "difference", "effect", "prob", "weight", "strength", "degree", "centrality", "importance", "enrichment")):
        return name, f"{table_context_label(rel_path, kind)}记录中的汇总、效应、距离或网络统计量。"
    if any(token in lower_name for token in ("expression", "counts", "detected", "nonzero", "library_total")):
        return name, f"{table_context_label(rel_path, kind)}记录中的表达量、计数、检出或文库规模指标。"
    if lower_name.startswith(("is_", "has_")) or lower_name.endswith(("_bool", "_available", "_supported", "_complete", "_consistent", "_assessed", "_stable")) or lower_name in {"include", "available", "supported", "stable", "selected_for_analysis", "integer_valued", "matrix_member"}:
        return name, "该记录是否满足对应的可用性、完整性、支持或筛选条件。"
    if any(token in lower_name for token in ("annotation", "lineage", "subtype", "cluster", "call", "label", "candidate")):
        return name, "该细胞或记录的聚类、注释、谱系、亚型、候选或分类标签。"
    if any(token in lower_name for token in ("evidence", "support", "direction", "mapping", "configured", "present", "missing")):
        return name, "该候选的证据类型、支持状态、方向一致性或配置/映射信息。"
    # A final lexical fallback is still schema-aware: it names the analysis
    # layer and the column, and never claims an unknown unit or expression
    # value.  It is only reachable for genuinely table-specific text columns.
    return name, f"{table_context_label(rel_path, kind)}记录中的“{name}”列值。"


def field_descriptions_for_table(rel_path: str, sheets: list[dict]) -> list[dict]:
    kind = table_kind_for_path(rel_path)
    if kind == "scenic_reg":
        fields = ["TF", "MotifID", "AUC", "NES", "MotifSimilarityQvalue", "OrthologousIdentity",
                  "Annotation", "Context", "TargetGenes", "RankAtMax"]
    elif kind == "cellchat_lr":
        fields = ["ligand", "receptor", "source", "target", "prob", "pval"]
        descriptions = {
            "ligand": "配体基因或配体复合物名称。",
            "receptor": "受体基因或受体复合物名称。",
            "source": "发送信号的细胞类型。",
            "target": "接收信号的细胞类型。",
            "prob": "CellChat 计算得到的配体-受体通讯概率。",
            "pval": "配体-受体通讯显著性检验 P 值。",
        }
        return [{"field": field, "description": descriptions[field]} for field in fields]
    else:
        fields = first_header_row(sheets)

    seen: set[str] = set()
    descriptions = []
    for index, field in enumerate(fields):
        display, description = field_description_for_name(field, rel_path, kind, index)
        key = display.lower()
        if key in seen:
            continue
        seen.add(key)
        descriptions.append({"field": display, "description": description})
    return descriptions


def table_sidecar_path(table_id: str) -> str:
    return (TABLE_PREVIEW_DIR / f"{table_id}.js").as_posix()


def should_keep_full_table(source: Path, row_count: int, col_count: int) -> bool:
    if source.stat().st_size > SMALL_TABLE_MAX_BYTES:
        return False
    return row_count * max(col_count, 1) <= FULL_TABLE_MAX_CELLS


def trim_rows_for_preview(source: Path, rows: list[list]) -> tuple[list[list], bool]:
    if not rows:
        return rows, False
    row_count = len(rows)
    col_count = max((len(row) for row in rows), default=0)
    keep_full = should_keep_full_table(source, row_count, col_count)
    if keep_full:
        return rows, False
    trimmed = [row[:PREVIEW_MAX_COLS] for row in rows[:PREVIEW_MAX_ROWS]]
    return trimmed, True


def read_delimited_table(source: Path, delimiter: str) -> dict:
    rows: list[list] = []
    row_count = 0
    col_count = 0
    large_source = source.stat().st_size > SMALL_TABLE_MAX_BYTES
    truncated = False
    with source.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            cleaned = [clean_cell_value(cell) for cell in row]
            row_count += 1
            col_count = max(col_count, len(cleaned))
            if large_source:
                if len(rows) < PREVIEW_MAX_ROWS:
                    rows.append(cleaned[:PREVIEW_MAX_COLS])
                    truncated = truncated or len(cleaned) > PREVIEW_MAX_COLS
                else:
                    truncated = True
            else:
                rows.append(cleaned)

    if large_source:
        stored_rows = rows
    else:
        stored_rows, truncated = trim_rows_for_preview(source, rows)
    return {
        "name": "Sheet1",
        "rowCount": row_count,
        "colCount": col_count,
        "storedRowCount": len(stored_rows),
        "storedColCount": max((len(row) for row in stored_rows), default=0),
        "truncated": truncated,
        "rows": stored_rows,
    }


def read_xlsx_table(source: Path) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("XLSX preview requires openpyxl") from exc

    workbook = load_workbook(source, read_only=True, data_only=True)
    sheets = []
    try:
        for worksheet in workbook.worksheets:
            rows: list[list] = []
            row_count = 0
            col_count = 0
            large_source = source.stat().st_size > SMALL_TABLE_MAX_BYTES
            truncated = False
            for row in worksheet.iter_rows(values_only=True):
                cleaned = [clean_cell_value(cell) for cell in row]
                row_count += 1
                col_count = max(col_count, len(cleaned))
                if large_source:
                    if len(rows) < PREVIEW_MAX_ROWS:
                        rows.append(cleaned[:PREVIEW_MAX_COLS])
                        truncated = truncated or len(cleaned) > PREVIEW_MAX_COLS
                    else:
                        truncated = True
                else:
                    rows.append(cleaned)

            if large_source:
                stored_rows = rows
            else:
                stored_rows, truncated = trim_rows_for_preview(source, rows)
            sheets.append({
                "name": worksheet.title,
                "rowCount": row_count,
                "colCount": col_count,
                "storedRowCount": len(stored_rows),
                "storedColCount": max((len(row) for row in stored_rows), default=0),
                "truncated": truncated,
                "rows": stored_rows,
            })
    finally:
        workbook.close()
    return sheets


def build_table_payload(source: Path, rel_path: str, table_id: str) -> dict:
    ext = source.suffix.lower()
    if ext in {".tsv", ".xls"}:
        sheets = [read_delimited_table(source, "\t")]
    elif ext == ".csv":
        sheets = [read_delimited_table(source, ",")]
    elif ext == ".xlsx":
        sheets = read_xlsx_table(source)
    else:
        raise RuntimeError(f"Unsupported table format: {ext}")

    return {
        "id": table_id,
        "path": rel_path,
        "name": Path(rel_path).name,
        "format": ext.lstrip("."),
        "sourceHref": rel_path,
        "sheetCount": len(sheets),
        "fieldDescriptions": field_descriptions_for_table(rel_path, sheets),
        "sheets": sheets,
    }


def copy_luckysheet_vendor(output_dir: Path) -> bool:
    if not SKILL_VENDOR_LUCKYSHEET.exists():
        return False

    dest = output_dir / LUCKYSHEET_VENDOR_DIR
    dest.mkdir(parents=True, exist_ok=True)

    for rel in ["jquery.min.js", "luckysheet.umd.js", "css", "fonts", "plugins"]:
        src = SKILL_VENDOR_LUCKYSHEET / rel
        if not src.exists():
            continue
        target = dest / rel
        if src.is_dir():
            shutil.copytree(
                src,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("*.map", "demoData", "index.html"),
            )
        else:
            if not target.exists() or target.stat().st_size != src.stat().st_size:
                shutil.copy2(src, target)
    return (dest / "jquery.min.js").exists() and (dest / "luckysheet.umd.js").exists()


def write_table_sidecars(
    soup: BeautifulSoup,
    asset_base: Path,
    output_path: Path | None,
) -> dict:
    """Create lazy-loaded table preview sidecars and annotate trigger buttons."""
    triggers = list(soup.find_all("button", class_="table-preview-trigger"))
    if not triggers:
        return {}

    if output_path is None:
        for trigger in triggers:
            trigger["data-table-status"] = "unavailable"
            trigger.attrs.pop("title", None)
            trigger["aria-label"] = f"表格预览未生成 {trigger.get('data-table-path', '')}"
        return {}

    output_dir = output_path.parent
    preview_dir = output_dir / TABLE_PREVIEW_DIR
    preview_dir.mkdir(parents=True, exist_ok=True)
    for stale_sidecar in preview_dir.glob("tbl_*.js"):
        stale_sidecar.unlink()
    vendor_available = copy_luckysheet_vendor(output_dir)

    entries: dict[str, dict] = {}
    paths = []
    for trigger in triggers:
        rel_path = normalize_relative_resource_path(trigger.get("data-table-path", ""))
        if rel_path:
            trigger["data-table-path"] = rel_path
        if rel_path and rel_path not in paths:
            paths.append(rel_path)

    for rel_path in paths:
        table_id = stable_table_id(rel_path)
        source = (asset_base / rel_path).resolve()
        sidecar_rel = table_sidecar_path(table_id)
        entry = {
            "id": table_id,
            "path": rel_path,
            "name": Path(rel_path).name,
            "format": Path(rel_path).suffix.lower().lstrip("."),
            "sourceHref": rel_path,
            "sidecar": sidecar_rel,
            "status": "ready",
            "rowCount": 0,
            "colCount": 0,
            "sheetCount": 0,
            "truncated": False,
        }

        try:
            if not source.exists():
                raise FileNotFoundError(rel_path)
            payload = build_table_payload(source, rel_path, table_id)
            entry["sheetCount"] = payload["sheetCount"]
            entry["fieldDescriptionCount"] = len(payload.get("fieldDescriptions", []))
            if payload["sheets"]:
                first_sheet = payload["sheets"][0]
                entry["rowCount"] = first_sheet["rowCount"]
                entry["colCount"] = first_sheet["colCount"]
                entry["truncated"] = any(sheet["truncated"] for sheet in payload["sheets"])

            sidecar_js = (
                "window.__OMICS_TABLE_PREVIEWS__=window.__OMICS_TABLE_PREVIEWS__||{};\n"
                f"window.__OMICS_TABLE_PREVIEWS__[{json.dumps(table_id)}]="
                f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))};\n"
            )
            (output_dir / sidecar_rel).write_text(sidecar_js, encoding="utf-8")
        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
            error_payload = {
                "id": table_id,
                "path": rel_path,
                "name": Path(rel_path).name,
                "format": entry["format"],
                "sourceHref": rel_path,
                "error": str(exc),
                "sheets": [],
            }
            sidecar_js = (
                "window.__OMICS_TABLE_PREVIEWS__=window.__OMICS_TABLE_PREVIEWS__||{};\n"
                f"window.__OMICS_TABLE_PREVIEWS__[{json.dumps(table_id)}]="
                f"{json.dumps(error_payload, ensure_ascii=False, separators=(',', ':'))};\n"
            )
            (output_dir / sidecar_rel).write_text(sidecar_js, encoding="utf-8")

        entries[rel_path] = entry

    manifest = {
        "version": 1,
        "tables": {entry["id"]: entry for entry in entries.values()},
        "vendor": {
            "available": vendor_available,
            "css": (LUCKYSHEET_VENDOR_DIR / "css/luckysheet.css").as_posix(),
            "pluginsCss": (LUCKYSHEET_VENDOR_DIR / "plugins/css/pluginsCss.css").as_posix(),
            "plugins": (LUCKYSHEET_VENDOR_DIR / "plugins/plugins.css").as_posix(),
            "jquery": (LUCKYSHEET_VENDOR_DIR / "jquery.min.js").as_posix(),
            "js": (LUCKYSHEET_VENDOR_DIR / "luckysheet.umd.js").as_posix(),
        },
    }
    manifest_js = js_assignment("__OMICS_TABLE_MANIFEST__", manifest)
    (preview_dir / "manifest.js").write_text(manifest_js, encoding="utf-8")

    for trigger in triggers:
        rel_path = normalize_relative_resource_path(trigger.get("data-table-path", ""))
        entry = entries.get(rel_path)
        if not entry:
            continue
        trigger["data-table-id"] = entry["id"]
        trigger["data-source-href"] = entry["sourceHref"]
        trigger["data-table-status"] = entry["status"]
        trigger["aria-label"] = f"预览表格 {entry['name']}"
        trigger.attrs.pop("title", None)
        if entry["status"] == "error":
            trigger["data-table-error"] = entry.get("error", "")
        elif entry["truncated"]:
            trigger["data-table-truncated"] = "true"

    return manifest


def table_preview_template_tags(manifest: dict) -> dict[str, str]:
    if not manifest:
        return {
            "manifest": "",
            "vendor_css": "",
            "runtime": "window.__OMICS_TABLE_RUNTIME__={enabled:false};",
        }

    manifest_src = (TABLE_PREVIEW_DIR / "manifest.js").as_posix()
    vendor = manifest.get("vendor", {})
    runtime = {
        "enabled": True,
        "vendorAvailable": bool(vendor.get("available")),
        "luckysheetCss": vendor.get("css", ""),
        "jqueryJs": vendor.get("jquery", ""),
        "luckysheetJs": vendor.get("js", ""),
    }
    css_links = []
    if vendor.get("available"):
        for key in ("pluginsCss", "plugins", "css"):
            href = vendor.get(key, "")
            if href:
                css_links.append(f'<link rel="stylesheet" href="{html.escape(href, quote=True)}">')

    return {
        "manifest": f'<script src="{html.escape(manifest_src, quote=True)}"></script>',
        "vendor_css": "\n".join(css_links),
        "runtime": js_assignment("__OMICS_TABLE_RUNTIME__", runtime),
    }


# --------------------------------------------------------------------------
# Broken link audit
# --------------------------------------------------------------------------

def find_broken_links(soup: BeautifulSoup, asset_base: Path) -> list[str]:
    """Return a list of unresolved image/asset references."""
    broken = []
    seen = set()

    def is_resolvable(ref: str) -> bool:
        if not ref:
            return True
        if ref.startswith(("http://", "https://", "data:", "#", "mailto:")):
            return True
        if ABS_PATH_RE.search(ref):
            return False
        if ref in seen:
            return True
        seen.add(ref)
        return (asset_base / ref).exists()

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not is_resolvable(src):
            broken.append(f"image: {src}")

    for a in soup.find_all("a", class_="file-link"):
        href = a.get("href", "")
        if not is_resolvable(href):
            broken.append(f"file-link: {href}")

    for a in soup.find_all("a", class_="img-link"):
        href = a.get("href", "")
        if not is_resolvable(href):
            broken.append(f"figure-source: {href}")

    for button in soup.find_all("button", class_="table-preview-trigger"):
        href = button.get("data-source-href") or button.get("data-table-path", "")
        if not is_resolvable(href):
            broken.append(f"table-source: {href}")

    return broken


# --------------------------------------------------------------------------
# Main convert pipeline
# --------------------------------------------------------------------------

def convert(
    md_content: str,
    title: str,
    asset_base: Path,
    allow_raw_html: bool,
    output_path: Path | None = None,
) -> tuple[str, list[str]]:
    """
    Convert markdown content to styled HTML.

    Returns (html_string, broken_link_messages).
    Raises ValueError on raw-HTML or absolute-path violations.
    """
    # ----- Pre-scan: privacy + safety -----
    if not allow_raw_html:
        violations = find_raw_html_violations(md_content)
        if violations:
            sample = "\n".join(f"  line {ln}: {snip}" for ln, snip in violations[:5])
            raise ValueError(
                f"Markdown contains disallowed raw HTML / JS "
                f"({len(violations)} issue(s)). Use --allow-raw-html to override.\n{sample}"
            )

    violations = find_abs_path_violations(md_content)
    if violations:
        sample = "\n".join(f"  line {ln}: {snip}" for ln, snip in violations[:5])
        raise ValueError(
            f"Markdown contains absolute filesystem paths "
            f"({len(violations)} issue(s)). BLOCKED privacy leak: absolute paths expose "
            f"local storage details and must be replaced with relative paths.\n{sample}"
        )

    # ----- Render -----
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    html_body = md.convert(md_content)
    soup = BeautifulSoup(html_body, "html.parser")

    # ----- Post-process -----
    process_figures_v2(soup, asset_base)
    style_tables(soup)
    linkify_file_paths(soup)
    table_manifest = write_table_sidecars(soup, asset_base, output_path)
    process_sample_table(soup)
    fold_report_tables(soup)
    generate_toc(soup)
    validate_figure_galleries(soup)

    # Drop empty paragraphs
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()

    broken = find_broken_links(soup, asset_base)

    # ----- Wrap in template -----
    template_path = Path(__file__).parent / "template.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    safe_title = html.escape(title, quote=True)
    table_tags = table_preview_template_tags(table_manifest)
    final_html = (
        template
        .replace("{{TITLE}}", safe_title)
        .replace("{{TABLE_PREVIEW_VENDOR_CSS}}", table_tags["vendor_css"])
        .replace("{{TABLE_PREVIEW_RUNTIME}}", table_tags["runtime"])
        .replace("{{TABLE_PREVIEW_MANIFEST_SCRIPT}}", table_tags["manifest"])
        .replace("{{CONTENT}}", str(soup))
    )

    return final_html, broken


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Render a Markdown report to HTML.")
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("-o", "--output", default=None, help="Output HTML file. Defaults to Report.html in the Markdown directory")
    parser.add_argument("--title", default=None, help="HTML page title (defaults to first H1)")
    parser.add_argument("--asset-base", default=None,
                        help="Directory to resolve image/file paths against. Defaults to the input Markdown's parent directory.")
    parser.add_argument("--allow-raw-html", action="store_true",
                        help="Permit raw HTML / inline event handlers in the Markdown source.")
    parser.add_argument("--strict-links", action="store_true",
                        help="Exit non-zero if any image / file reference fails to resolve under --asset-base.")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    asset_base = Path(args.asset_base).resolve() if args.asset_base else input_path.parent
    md_content = input_path.read_text(encoding="utf-8")
    output_path = Path(args.output).resolve() if args.output else (input_path.parent / "Report.html").resolve()

    if args.title:
        title = args.title
    else:
        m = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
        title = m.group(1).strip() if m else "Analysis Report"

    try:
        rendered, broken = convert(
            md_content,
            title=title,
            asset_base=asset_base,
            allow_raw_html=args.allow_raw_html,
            output_path=output_path,
        )
    except ValueError as e:
        print(f"✗ Render rejected:\n{e}", file=sys.stderr)
        sys.exit(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"✓ Report generated: {output_path}")

    if broken:
        print(f"\n⚠ {len(broken)} unresolved reference(s) under {asset_base}:", file=sys.stderr)
        for b in broken:
            print(f"  {b}", file=sys.stderr)
        if args.strict_links:
            sys.exit(3)


if __name__ == "__main__":
    main()
