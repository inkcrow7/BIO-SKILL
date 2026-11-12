#!/usr/bin/env python3
"""
Build an obfuscated delivery HTML report from an editable Markdown source.

The build has two stages:
1. Render Markdown with md_to_html.py into a temporary normal report.
2. Rewrite the generated report into a delivery package:
   - vendor/luckysheet is copied to a hash-named directory.
   - table-preview sidecars are copied to a hash-named directory.
   - third-party CSS/JS is minified conservatively, not aggressively obfuscated.
   - report business JavaScript is minified lightly, XOR-encoded, and loaded by a
     small runtime decoder.

This is packaging obfuscation for client delivery, not a security boundary: a
browser must still be able to decode and execute the report code.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

import md_to_html


RAW_VENDOR_PREFIX = "report_assets/vendor/luckysheet"
RAW_TABLE_PREFIX = "report_assets/table_previews"
GENERATED_MARKER = ".omics-delivery-bundle"
FINAL_DELIVERY_DIR_NAME = "Report_delivery"
URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def posix_relpath(path: Path, start: Path) -> str:
    return os.path.relpath(path, start).replace(os.sep, "/")


def short_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def write_generated_marker(path: Path, build_id: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / GENERATED_MARKER).write_text(
        json.dumps(
            {
                "tool": "omics-analysis-report.compile_delivery",
                "buildId": build_id,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def reset_generated_dir(path: Path, build_id: str) -> None:
    if path.exists():
        marker = path / GENERATED_MARKER
        if not marker.exists():
            raise RuntimeError(f"Refusing to overwrite non-generated directory: {path}")
        shutil.rmtree(path)
    write_generated_marker(path, build_id)


def reset_final_delivery_dir(path: Path) -> None:
    """Clear a generated final delivery directory before rebuilding it."""
    if not path.exists():
        return
    if not path.is_dir():
        raise RuntimeError(f"Refusing to overwrite non-directory output parent: {path}")
    if not any((path / name).exists() for name in (GENERATED_MARKER, "Report.html")):
        raise RuntimeError(f"Refusing to clear non-delivery directory: {path}")
    shutil.rmtree(path)


def is_copyable_delivery_ref(ref: str) -> bool:
    if not ref:
        return False
    if ref.startswith(("#", "data:", "mailto:", "tel:")) or URL_SCHEME_RE.match(ref):
        return False
    if md_to_html.ABS_PATH_RE.search(ref):
        return False
    return True


def collect_source_asset_refs(delivery_html: str, bundle_root: Path) -> list[str]:
    soup = BeautifulSoup(delivery_html, "html.parser")
    refs: set[str] = set()
    bundle_prefix = bundle_root.name + "/"

    def add(ref: str | None) -> None:
        if not ref or not is_copyable_delivery_ref(ref):
            return
        normalized = ref.split("#", 1)[0].split("?", 1)[0]
        if not normalized or normalized.startswith((bundle_prefix, RAW_VENDOR_PREFIX + "/", RAW_TABLE_PREFIX + "/")):
            return
        refs.add(normalized)

    for img in soup.find_all("img"):
        add(img.get("src"))
    for a in soup.find_all("a"):
        if "file-link" in (a.get("class") or []) or "img-link" in (a.get("class") or []):
            add(a.get("href"))
    for button in soup.find_all("button", class_="table-preview-trigger"):
        add(button.get("data-source-href") or button.get("data-table-path"))
    return sorted(refs)


def copy_source_assets(
    delivery_html: str,
    asset_base: Path,
    output_dir: Path,
    bundle_root: Path,
) -> list[str]:
    """Copy linked source figures/tables into the final delivery directory."""
    copied: list[str] = []
    output_root = output_dir.resolve()
    for ref in collect_source_asset_refs(delivery_html, bundle_root):
        source = (asset_base / ref).resolve()
        if not source.exists() or not source.is_file():
            continue
        target = (output_dir / ref).resolve()
        if not target.is_relative_to(output_root):
            raise RuntimeError(f"Refusing to copy source outside delivery directory: {ref}")
        if source == target:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(ref)
    return copied


def minify_css(text: str) -> str:
    text = re.sub(r"/\*(?!\!)[\s\S]*?\*/", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([{}:;,>])\s*", r"\1", text)
    text = text.replace(";}", "}")
    return text.strip()


def minify_js_conservative(text: str) -> str:
    """Keep JS semantics safe: remove sourcemap markers without reflowing code."""
    text = re.sub(r"(?m)^[ \t]*//[#@]\s*sourceMappingURL=.*(?:\n|$)", "", text)
    return text.strip()


def minify_html_shell(text: str) -> str:
    text = re.sub(r">\s+<", "><", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip() + "\n"


def copy_minified_tree(source: Path, target: Path) -> None:
    for src in source.rglob("*"):
        if src.name in {".DS_Store"} or src.suffix == ".map":
            continue
        rel = src.relative_to(source)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == ".css":
            dst.write_text(minify_css(src.read_text(encoding="utf-8")), encoding="utf-8")
        elif src.suffix.lower() == ".js":
            dst.write_text(minify_js_conservative(src.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(src, dst)


def rename_vendor_entries(vendor_target: Path, build_id: str) -> dict[str, str]:
    entry_map = {
        "jquery.min.js": f"j_{build_id[:10]}.js",
        "luckysheet.umd.js": f"l_{build_id[2:12]}.js",
        "css/luckysheet.css": f"css/s_{build_id[4:12]}.css",
        "plugins/plugins.css": f"plugins/p_{build_id[6:12]}.css",
        "plugins/css/pluginsCss.css": f"plugins/css/c_{build_id[8:12]}.css",
    }
    applied: dict[str, str] = {}
    for old_rel, new_rel in entry_map.items():
        old_path = vendor_target / old_rel
        if not old_path.exists():
            continue
        new_path = vendor_target / new_rel
        new_path.parent.mkdir(parents=True, exist_ok=True)
        if new_path.exists():
            new_path.unlink()
        old_path.rename(new_path)
        applied[old_rel] = new_rel
    return applied


def rewrite_prefixed_path(value: str, old_prefix: str, new_prefix: str) -> str:
    if value == old_prefix:
        return new_prefix
    if value.startswith(old_prefix + "/"):
        return new_prefix + value[len(old_prefix):]
    return value


def rewrite_vendor_path(value: str, vendor_rel: str, entry_map: dict[str, str]) -> str:
    if value == RAW_VENDOR_PREFIX:
        return vendor_rel
    if not value.startswith(RAW_VENDOR_PREFIX + "/"):
        return value
    suffix = value[len(RAW_VENDOR_PREFIX) + 1:]
    return f"{vendor_rel}/{entry_map.get(suffix, suffix)}"


def js_assignment(name: str, value: object) -> str:
    return f"window.{name}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))};"


def parse_assignment_json(script_text: str, name: str) -> object:
    pattern = re.compile(rf"window\.{re.escape(name)}\s*=\s*(.+?)\s*;?\s*$", re.S)
    match = pattern.search(script_text.strip())
    if not match:
        raise RuntimeError(f"Cannot parse JS assignment for {name}")
    return json.loads(match.group(1))



def update_manifest(
    manifest_path: Path,
    vendor_rel: str,
    table_rel: str,
    vendor_entry_map: dict[str, str],
) -> None:
    manifest = parse_assignment_json(manifest_path.read_text(encoding="utf-8"), "__OMICS_TABLE_MANIFEST__")
    vendor = manifest.get("vendor", {})
    for key, value in list(vendor.items()):
        if isinstance(value, str):
            vendor[key] = rewrite_vendor_path(value, vendor_rel, vendor_entry_map)
    for entry in manifest.get("tables", {}).values():
        sidecar = entry.get("sidecar", "")
        if isinstance(sidecar, str):
            entry["sidecar"] = rewrite_prefixed_path(sidecar, RAW_TABLE_PREFIX, table_rel)
    manifest_path.write_text(js_assignment("__OMICS_TABLE_MANIFEST__", manifest) + "\n", encoding="utf-8")


def obfuscate_business_js(script_text: str, build_id: str) -> str:
    source = minify_js_conservative(script_text)
    key = hashlib.sha256(f"{build_id}:business-js".encode("utf-8")).digest()[:24]
    payload = bytearray(source.encode("utf-8"))
    for index, byte in enumerate(payload):
        payload[index] = byte ^ key[index % len(key)]
    key_b64 = base64.b64encode(key).decode("ascii")
    payload_b64 = base64.b64encode(bytes(payload)).decode("ascii")
    return (
        '(()=>{const k=Uint8Array.from(atob("'
        + key_b64
        + '"),c=>c.charCodeAt(0));const b=Uint8Array.from(atob("'
        + payload_b64
        + '"),c=>c.charCodeAt(0));for(let i=0;i<b.length;i++)b[i]^=k[i%k.length];'
        + "new Function(new TextDecoder().decode(b))();})();"
    )


def rewrite_html(
    raw_html: str,
    output_path: Path,
    vendor_rel: str,
    table_rel: str,
    build_id: str,
    vendor_entry_map: dict[str, str],
) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")

    for style in soup.find_all("style"):
        style.string = minify_css(style.get_text())

    for link in soup.find_all("link", href=True):
        href = link["href"]
        link["href"] = html.escape(
            rewrite_vendor_path(href, vendor_rel, vendor_entry_map),
            quote=True,
        )

    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            script["src"] = html.escape(
                rewrite_prefixed_path(src, RAW_TABLE_PREFIX, table_rel),
                quote=True,
            )
            continue

        script_text = script.string if script.string is not None else script.get_text()
        if re.search(r"window\.__OMICS_TABLE_RUNTIME__\s*=", script_text):
            runtime = parse_assignment_json(script_text, "__OMICS_TABLE_RUNTIME__")
            for key in ("luckysheetCss", "jqueryJs", "luckysheetJs"):
                value = runtime.get(key, "")
                if isinstance(value, str):
                    runtime[key] = rewrite_vendor_path(value, vendor_rel, vendor_entry_map)
            script.string = js_assignment("__OMICS_TABLE_RUNTIME__", runtime)
        elif "function currentPreviewWidth" in script_text or "const manifest = window.__OMICS_TABLE_MANIFEST__" in script_text:
            script.string = obfuscate_business_js(script_text, build_id)
        elif "window.__OMICS_TABLE_PREVIEWS__" in script_text:
            script.string = minify_js_conservative(script_text)
        else:
            script.string = minify_js_conservative(script_text)

    return minify_html_shell(str(soup))


def default_output_for(input_path: Path) -> Path:
    return input_path.parent / FINAL_DELIVERY_DIR_NAME / "Report.html"


def build_delivery(args: argparse.Namespace) -> tuple[Path, Path]:
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output_path = Path(args.output).resolve() if args.output else default_output_for(input_path).resolve()
    asset_base = Path(args.asset_base).resolve() if args.asset_base else input_path.parent
    md_content = input_path.read_text(encoding="utf-8")
    title = args.title
    if not title:
        match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
        title = match.group(1).strip() if match else "Analysis Report"

    if not args.output and output_path.parent.name == FINAL_DELIVERY_DIR_NAME:
        reset_final_delivery_dir(output_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".omics-delivery-stage-", dir=output_path.parent) as stage_name:
        stage_dir = Path(stage_name)
        raw_output = stage_dir / "raw.html"
        rendered, broken = md_to_html.convert(
            md_content,
            title=title,
            asset_base=asset_base,
            allow_raw_html=args.allow_raw_html,
            output_path=raw_output,
        )
        raw_output.write_text(rendered, encoding="utf-8")

        if broken:
            print(f"⚠ {len(broken)} unresolved reference(s) under {asset_base}:", file=sys.stderr)
            for item in broken:
                print(f"  {item}", file=sys.stderr)
            if args.strict_links:
                raise RuntimeError("Strict link validation failed")

        build_id = short_hash(rendered + md_content + str(input_path))
        bundle_root = output_path.parent / f"{output_path.stem}.bundle_{build_id}"
        vendor_dir_name = f"v_{build_id[:8]}"
        table_dir_name = f"d_{build_id[4:12]}"
        vendor_target = bundle_root / vendor_dir_name
        table_target = bundle_root / table_dir_name

        reset_generated_dir(bundle_root, build_id)

        raw_vendor = stage_dir / RAW_VENDOR_PREFIX
        raw_table = stage_dir / RAW_TABLE_PREFIX
        if raw_vendor.exists():
            copy_minified_tree(raw_vendor, vendor_target)
        if raw_table.exists():
            copy_minified_tree(raw_table, table_target)
        vendor_entry_map = rename_vendor_entries(vendor_target, build_id) if vendor_target.exists() else {}

        vendor_rel = posix_relpath(vendor_target, output_path.parent)
        table_rel = posix_relpath(table_target, output_path.parent)

        manifest_path = table_target / "manifest.js"
        if manifest_path.exists():
            update_manifest(manifest_path, vendor_rel, table_rel, vendor_entry_map)

        delivery_html = rewrite_html(
            rendered,
            output_path=output_path,
            vendor_rel=vendor_rel,
            table_rel=table_rel,
            build_id=build_id,
            vendor_entry_map=vendor_entry_map,
        )
        copied_source_assets = [] if args.no_copy_source_assets else copy_source_assets(
            delivery_html,
            asset_base=asset_base,
            output_dir=output_path.parent,
            bundle_root=bundle_root,
        )
        output_path.write_text(delivery_html, encoding="utf-8")
        if input_path.parent != output_path.parent:
            shutil.copy2(input_path, output_path.parent / "Report.md")
            for manifest_name in ("figure_manifest.tsv", "figure_manifest.xls", "figure_manifest.csv", "figure_manifest.xlsx"):
                manifest_path = input_path.parent / manifest_name
                if manifest_path.exists():
                    shutil.copy2(manifest_path, output_path.parent / manifest_name)

        (bundle_root / "build-manifest.json").write_text(
            json.dumps(
                {
                    "buildId": build_id,
                    "outputHtml": output_path.name,
                    "vendorPolicy": "renamed and conservatively minified; no aggressive third-party obfuscation",
                    "businessCodePolicy": "light minify plus runtime XOR/base64 obfuscation",
                    "sourceMapPolicy": "source maps and .map files are omitted from delivery builds",
                    "vendorDir": vendor_dir_name,
                    "tablePreviewDir": table_dir_name,
                    "copiedSourceFileCount": len(copied_source_assets),
                    "sourceAssetPolicy": "linked source figures and tables are copied into the final delivery directory",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return output_path, bundle_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile an omics Markdown report into a delivery HTML package.")
    parser.add_argument("input", help="Editable Markdown report source")
    parser.add_argument("-o", "--output", help="Delivery HTML output path. Defaults to Report.html in the Markdown directory")
    parser.add_argument("--title", help="HTML title. Defaults to first H1 in the Markdown")
    parser.add_argument("--asset-base", help="Directory used to resolve figures/tables. Defaults to the Markdown parent directory")
    parser.add_argument("--strict-links", action="store_true", help="Fail if images or linked source tables cannot be resolved")
    parser.add_argument("--allow-raw-html", action="store_true", help="Pass through md_to_html.py raw HTML override")
    parser.add_argument("--no-copy-source-assets", action="store_true", help="Do not copy linked source figures/tables into the delivery directory")
    args = parser.parse_args()

    try:
        output_path, bundle_root = build_delivery(args)
    except Exception as exc:
        print(f"✗ Delivery build failed: {exc}", file=sys.stderr)
        return 1

    print(f"✓ Delivery report generated: {output_path}")
    print(f"✓ Delivery assets: {bundle_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
