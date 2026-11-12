#!/usr/bin/env python3
"""Build a path-free, self-contained thumbnail gallery from a figure manifest."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


MIME_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}
ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s\"'=(])(?:/(?:Users|private|tmp|share|data|home)/|~[/\\]|[A-Za-z]:[/\\]|\\\\[^\\\s]+\\)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Figure:
    module: str
    figure_type: str
    note: str
    filename: str
    data_uri: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Report_thumbnails.html with all display images embedded as data URIs."
    )
    parser.add_argument("manifest", type=Path, help="TSV figure manifest")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--asset-base", type=Path, required=True)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--title")
    parser.add_argument(
        "--subtitle",
        default="所有图片均已嵌入本 HTML 文件；点击缩略图可查看完整尺寸。",
    )
    return parser.parse_args()


def title_from_markdown(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.is_file():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def normalize_relative_path(raw_path: str) -> PurePosixPath:
    value = raw_path.strip().replace("\\", "/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Figure path must be a normalized relative path: {raw_path!r}")
    if re.match(r"^[A-Za-z]:/", value):
        raise ValueError(f"Figure path must not use a drive prefix: {raw_path!r}")
    return path


def infer_module(path: PurePosixPath, explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    parts = list(path.parts)
    lower = [part.casefold() for part in parts]
    if "figures" in lower:
        index = lower.index("figures")
        if index > 0:
            return parts[index - 1]
    return parts[0] if len(parts) > 1 else "结果图"


def display_module(value: str) -> str:
    match = re.match(r"^(\d+)[._-](.+)$", value)
    if match:
        return f"{match.group(1)} · {match.group(2).replace('_', ' ').replace('.', ' ')}"
    return value.replace("_", " ")


def load_figures(manifest: Path, asset_base: Path) -> list[Figure]:
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    asset_base = asset_base.resolve()
    figures: list[Figure] = []
    seen: set[str] = set()
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"figure_type", "representative_path", "note"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            for raw_path in row["representative_path"].split(";"):
                relative = normalize_relative_path(raw_path)
                relative_key = relative.as_posix()
                if relative_key in seen:
                    continue
                source = (asset_base / Path(*relative.parts)).resolve()
                try:
                    source.relative_to(asset_base)
                except ValueError as exc:
                    raise ValueError(f"Figure path escapes asset base: {relative_key}") from exc
                if not source.is_file():
                    raise FileNotFoundError(source)
                mime = MIME_TYPES.get(source.suffix.casefold())
                if mime is None:
                    raise ValueError(f"Unsupported browser image format: {relative_key}")
                encoded = base64.b64encode(source.read_bytes()).decode("ascii")
                figures.append(
                    Figure(
                        module=infer_module(relative, row.get("module", "")),
                        figure_type=row["figure_type"].strip(),
                        note=row["note"].strip(),
                        filename=source.name,
                        data_uri=f"data:{mime};base64,{encoded}",
                    )
                )
                seen.add(relative_key)
    return figures


def render(title: str, subtitle: str, figures: list[Figure]) -> str:
    grouped: OrderedDict[str, list[Figure]] = OrderedDict()
    for figure in figures:
        grouped.setdefault(figure.module, []).append(figure)

    sections: list[str] = []
    figure_number = 0
    for module, module_figures in grouped.items():
        cards: list[str] = []
        for figure in module_figures:
            figure_number += 1
            caption = html.escape(figure.note or figure.figure_type, quote=True)
            filename = html.escape(figure.filename, quote=True)
            search_text = html.escape(f"{figure.note} {figure.figure_type} {figure.filename}".lower(), quote=True)
            cards.append(
                f'''<article class="card" data-search="{search_text}">
  <button class="thumb-button" type="button" aria-label="查看完整图片：{caption}" data-caption="{caption}">
    <img src="{figure.data_uri}" alt="{caption}" loading="lazy" decoding="async">
  </button>
  <div class="card-body"><span>图 {figure_number:02d}</span><h3>{caption}</h3><p>{filename}</p></div>
</article>'''
            )
        module_label = html.escape(display_module(module))
        sections.append(
            f'''<section class="module-section">
  <div class="section-heading"><h2>{module_label}</h2><span>{len(module_figures)} 张图</span></div>
  <div class="gallery">{"".join(cards)}</div>
</section>'''
        )

    empty_state = '<p class="empty">figure_manifest.tsv 中没有可展示图片。</p>' if not figures else ""
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}｜缩略图报告</title>
<style>
:root{{--ink:#162235;--muted:#607086;--line:#dce4ec;--paper:#fff;--wash:#f4f7fa;--navy:#193c63;--red:#bb3e3e;--shadow:0 12px 30px rgba(28,48,72,.09)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif;line-height:1.55}}
header{{background:linear-gradient(135deg,#173552,#245b83);color:#fff;padding:44px max(24px,calc((100vw - 1380px)/2)) 38px}}header h1{{max-width:1080px;margin:0 0 12px;font-size:clamp(26px,3vw,42px);line-height:1.2}}header p{{max-width:980px;margin:0;color:#dceaf5}}
.summary{{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}}.pill{{padding:6px 12px;border:1px solid rgba(255,255,255,.28);border-radius:999px;background:rgba(255,255,255,.08);font-size:13px}}
main{{max-width:1380px;margin:0 auto;padding:26px 24px 64px}}.toolbar{{position:sticky;top:0;z-index:5;padding:14px 0;background:rgba(244,247,250,.94);backdrop-filter:blur(8px)}}.toolbar input{{width:min(520px,100%);padding:11px 14px;border:1px solid #cbd6e1;border-radius:9px;background:#fff;font-size:15px}}
.module-section{{margin:22px 0 38px}}.section-heading{{display:flex;align-items:baseline;justify-content:space-between;gap:20px;border-bottom:2px solid var(--navy);margin-bottom:16px}}.section-heading h2{{margin:0;padding:0 0 9px;font-size:22px}}.section-heading span{{color:var(--muted);font-size:13px}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}.card{{min-width:0;background:var(--paper);border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:var(--shadow)}}.thumb-button{{display:block;width:100%;height:230px;padding:12px;border:0;border-bottom:1px solid var(--line);background:#fff;cursor:zoom-in}}.thumb-button img{{width:100%;height:100%;object-fit:contain}}.card-body{{padding:13px 15px 16px}}.card-body>span{{display:inline-block;color:var(--red);font-size:12px;font-weight:700;letter-spacing:.04em}}.card h3{{margin:5px 0 6px;font-size:15px;line-height:1.35}}.card p{{margin:0;color:var(--muted);font-size:12px;word-break:break-all}}.card[hidden]{{display:none}}.empty{{padding:28px;background:#fff;border:1px solid var(--line);border-radius:12px;color:var(--muted)}}
dialog{{width:min(96vw,1500px);max-height:96vh;padding:0;border:0;border-radius:12px;box-shadow:0 24px 80px rgba(0,0,0,.35)}}dialog::backdrop{{background:rgba(8,18,30,.82)}}.modal-head{{display:flex;justify-content:space-between;align-items:center;gap:15px;padding:11px 15px;border-bottom:1px solid var(--line)}}.modal-head strong{{font-size:14px}}.modal-head button{{border:1px solid var(--line);border-radius:7px;background:#fff;padding:7px 11px;cursor:pointer}}.modal-image{{display:block;width:100%;max-height:calc(96vh - 58px);object-fit:contain;background:#fff}}
footer{{padding:20px 24px;text-align:center;color:var(--muted);font-size:12px}}@media(max-width:620px){{header{{padding-top:30px}}main{{padding-inline:14px}}.thumb-button{{height:200px}}}}
</style>
</head>
<body>
<header><h1>{safe_title}｜缩略图报告</h1><p>{safe_subtitle}</p><div class="summary"><span class="pill">{len(figures)} 张结果图</span><span class="pill">{len(grouped)} 个图形模块</span><span class="pill">单文件自包含</span><span class="pill">无资源路径依赖</span></div></header>
<main><div class="toolbar"><input id="search" type="search" placeholder="搜索图名或文件名" aria-label="搜索缩略图"></div>{empty_state}{"".join(sections)}</main>
<footer>Self-contained thumbnail report</footer>
<dialog id="viewer"><div class="modal-head"><strong id="viewer-caption"></strong><button id="viewer-close" type="button">关闭</button></div><img class="modal-image" id="viewer-image" alt="完整图片预览"></dialog>
<script>
const search=document.getElementById('search');search.addEventListener('input',()=>{{const q=search.value.trim().toLowerCase();document.querySelectorAll('.card').forEach(card=>{{card.hidden=q&&!card.dataset.search.includes(q)}})}});
const viewer=document.getElementById('viewer'),viewerImage=document.getElementById('viewer-image'),viewerCaption=document.getElementById('viewer-caption');document.querySelectorAll('.thumb-button').forEach(button=>button.addEventListener('click',()=>{{viewerImage.src=button.querySelector('img').src;viewerCaption.textContent=button.dataset.caption;viewer.showModal()}}));document.getElementById('viewer-close').addEventListener('click',()=>viewer.close());viewer.addEventListener('click',event=>{{if(event.target===viewer)viewer.close()}});
</script>
</body>
</html>'''


def validate_document(document: str, asset_base: Path, manifest: Path, expected_images: int) -> None:
    sources = re.findall(r"\bsrc\s*=\s*[\"']([^\"']+)", document, flags=re.IGNORECASE)
    if len(sources) != expected_images or any(not source.startswith("data:image/") for source in sources):
        raise RuntimeError("Thumbnail HTML contains a missing or non-embedded image source")
    if re.search(r"<link\b|<script\b[^>]*\bsrc\s*=|\burl\s*\(", document, flags=re.IGNORECASE):
        raise RuntimeError("Thumbnail HTML contains an external or local resource dependency")
    without_payloads = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[DATA_URI]", document)
    if str(asset_base.resolve()) in without_payloads or str(manifest.resolve()) in without_payloads:
        raise RuntimeError("Thumbnail HTML leaks an input filesystem path")
    if ABSOLUTE_PATH_RE.search(without_payloads):
        raise RuntimeError("Thumbnail HTML contains an absolute filesystem path")


def main() -> None:
    args = parse_args()
    asset_base = args.asset_base.resolve()
    manifest = args.manifest.resolve()
    title = args.title or title_from_markdown(args.report_md.resolve() if args.report_md else None)
    title = title or "生物信息分析"
    figures = load_figures(manifest, asset_base)
    document = render(title, args.subtitle, figures)
    validate_document(document, asset_base, manifest, len(figures))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"Wrote {output.name}: figures={len(figures)} sha256={digest}")


if __name__ == "__main__":
    main()
