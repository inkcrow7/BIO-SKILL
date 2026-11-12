#!/usr/bin/env python3
"""Collect a deterministic, path-safe inventory for bioinformatics logic audits."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


MODULE_PATTERN = re.compile(r"^\d{2}\.[A-Za-z0-9_.-]+$")
ACCESSION_PATTERNS = (
    re.compile(r"\bGSE\d{3,}\b", re.IGNORECASE),
    re.compile(r"\bE-MTAB-\d{3,}\b", re.IGNORECASE),
    re.compile(r"\bSRP\d{5,}\b", re.IGNORECASE),
    re.compile(r"\bPRJ[EDN][A-Z]?\d+\b", re.IGNORECASE),
    re.compile(r"\bTCGA-[A-Z0-9-]+\b", re.IGNORECASE),
)
TEXT_SUFFIXES = {".md", ".txt", ".tsv", ".csv", ".yaml", ".yml", ".py", ".r", ".sh"}
FIGURE_SUFFIXES = {".png", ".pdf", ".svg", ".jpg", ".jpeg"}
MAX_SCAN_BYTES = 2_000_000


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_small_text_files(project_root: Path) -> Iterable[Path]:
    for top_name in ("Results", "Scripts", "Data/Processed"):
        top = project_root / top_name
        if not top.exists():
            continue
        for path in top.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size <= MAX_SCAN_BYTES:
                    yield path
            except OSError:
                continue


def detect_accessions(project_root: Path) -> list[dict[str, Any]]:
    evidence: dict[str, set[str]] = defaultdict(set)
    for path in iter_small_text_files(project_root):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in ACCESSION_PATTERNS:
            for match in pattern.findall(content):
                evidence[match.upper()].add(relative(path, project_root))
    return [
        {"accession": accession, "evidence_files": sorted(paths)[:20]}
        for accession, paths in sorted(evidence.items())
    ]


def infer_figure_types(figures: list[str]) -> list[str]:
    rules = {
        "QC": ("qc", "violin", "retention"),
        "PCA": ("pca",),
        "UMAP": ("umap",),
        "volcano": ("volcano",),
        "heatmap": ("heatmap", "clustermap", "matrixplot"),
        "DotPlot": ("dotplot", "dot_plot"),
        "proportion": ("proportion", "composition", "abundance"),
        "trajectory/pseudotime": ("trajectory", "pseudotime"),
        "enrichment/GSEA": ("enrichment", "gsea", "ora", "pathway"),
        "WGCNA/network": ("wgcna", "module", "dendrogram", "soft_threshold", "network"),
        "regulon/AUCell": ("regulon", "aucell", "importance"),
        "evidence matrix/score": ("evidence", "score", "axis", "axes"),
    }
    joined = "\n".join(figures).lower()
    return sorted(label for label, tokens in rules.items() if any(token in joined for token in tokens))


def module_files(directory: Path, suffixes: set[str] | None = None) -> list[str]:
    if not directory.exists():
        return []
    paths = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if suffixes is None or path.suffix.lower() in suffixes:
            paths.append(path.relative_to(directory).as_posix())
    return sorted(paths)


def collect_modules(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    roots = {
        "results": project_root / "Results",
        "scripts": project_root / "Scripts",
        "processed": project_root / "Data/Processed",
    }
    names: set[str] = set()
    for root in roots.values():
        if root.exists():
            names.update(path.name for path in root.iterdir() if path.is_dir() and MODULE_PATTERN.match(path.name))

    modules: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    for name in sorted(names):
        result_dir = roots["results"] / name
        script_dir = roots["scripts"] / name
        processed_dir = roots["processed"] / name
        figures = module_files(result_dir / "Figures", FIGURE_SUFFIXES)
        tables = module_files(result_dir / "Tables")
        scripts = module_files(script_dir, {".py", ".r", ".sh", ".nf", ".yaml", ".yml"})
        figure_index = next(
            (
                path
                for path in (
                    result_dir / "Tables" / "figure_index.tsv",
                    result_dir / "figure_index.tsv",
                )
                if path.exists()
            ),
            None,
        )
        stems: dict[str, set[str]] = defaultdict(set)
        for figure in figures:
            path = Path(figure)
            stems[path.with_suffix("").as_posix()].add(path.suffix.lower())

        if result_dir.exists() and not (result_dir / "README.md").exists():
            findings.append({"module": name, "code": "MISSING_RESULTS_README", "detail": "Results module has no README.md"})
        if figures and figure_index is None:
            findings.append({"module": name, "code": "MISSING_FIGURE_INDEX", "detail": "Figures exist but Tables/figure_index.tsv is absent"})
        if processed_dir.exists() and not any(processed_dir.glob("*run_summary*")):
            findings.append({"module": name, "code": "MISSING_RUN_SUMMARY", "detail": "Processed module has no run_summary file"})
        if any(result_dir.glob("*run_summary*")):
            findings.append({"module": name, "code": "RUN_SUMMARY_IN_RESULTS", "detail": "Run summary is stored in Results"})
        for stem, extensions in sorted(stems.items()):
            if extensions.intersection({".png", ".pdf"}) and not {".png", ".pdf"}.issubset(extensions):
                findings.append({
                    "module": name,
                    "code": "UNPAIRED_PNG_PDF",
                    "detail": f"{stem} has {','.join(sorted(extensions))}",
                })
        modules.append({
            "module": name,
            "locations": {key: root.joinpath(name).exists() for key, root in roots.items()},
            "readme": relative(result_dir / "README.md", project_root) if (result_dir / "README.md").exists() else None,
            "run_summaries": [relative(path, project_root) for path in sorted(processed_dir.glob("*run_summary*"))],
            "figure_index": relative(figure_index, project_root) if figure_index is not None else None,
            "figures": figures,
            "figure_types": infer_figure_types(figures),
            "tables": tables,
            "scripts_and_configs": scripts,
        })
    return modules, findings


def candidate_design_files(project_root: Path) -> list[str]:
    tokens = ("dataset", "accession", "manifest", "sample_sheet", "metadata", "inventory", "catalog")
    candidates = []
    for path in iter_small_text_files(project_root):
        if any(token in path.name.lower() for token in tokens):
            candidates.append(relative(path, project_root))
    return sorted(set(candidates))


def collect(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    modules, findings = collect_modules(project_root)
    missing_roots = [name for name in ("Data", "Results", "Scripts") if not (project_root / name).exists()]
    for name in missing_roots:
        findings.append({"module": "project", "code": "MISSING_PROJECT_ROOT", "detail": f"{name}/ is absent"})
    return {
        "project_name": project_root.name,
        "dataset_accessions": detect_accessions(project_root),
        "candidate_design_files": candidate_design_files(project_root),
        "modules": modules,
        "structural_audit_findings": sorted(findings, key=lambda item: (item["module"], item["code"], item["detail"])),
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "demo"
        (root / "Results/01.demo/Figures").mkdir(parents=True)
        (root / "Scripts/01.demo").mkdir(parents=True)
        (root / "Data/Processed/01.demo").mkdir(parents=True)
        (root / "Results/01.demo/README.md").write_text("GSE12345 demo\n", encoding="utf-8")
        (root / "Results/01.demo/Figures/01_umap.png").write_bytes(b"synthetic")
        (root / "Scripts/01.demo/run.py").write_text("# GSE12345\n", encoding="utf-8")
        (root / "Data/Processed/01.demo/run_summary.yaml").write_text("dataset: GSE12345\n", encoding="utf-8")
        payload = collect(root)
        assert payload["dataset_accessions"][0]["accession"] == "GSE12345"
        assert payload["modules"][0]["figure_types"] == ["UMAP"]
        codes = {item["code"] for item in payload["structural_audit_findings"]}
        assert "MISSING_FIGURE_INDEX" in codes
        assert "UNPAIRED_PNG_PDF" in codes
    print("self-test: ok")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON output; defaults to stdout")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.project_root is None:
        parser.error("--project-root is required unless --self-test is used")
    payload = collect(args.project_root)
    if args.output:
        atomic_write_json(args.output, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
