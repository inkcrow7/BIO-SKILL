---
name: bioinfo-project-packaging
description: Package final bioinformatics Results figures, tables and Report.html, excluding preview resource directories, caches, index lists, build intermediates, large analysis objects and previous archives throughout Results; place archives in the project directory by default and verify scope with SHA256. Use for 打包、压缩、归档、交付生信项目 or packaging exclusions.
---

# Bioinformatics Project Packaging

Use `scripts/package_bioinfo_project.sh` for deterministic Results-only packaging.

## Final-artifact contract

Include formal Results figures and result tables, plus the final `Results/Report_delivery/Report.html` when present. Exclude preview resource directories, caches, index lists and other generated process files throughout Results, including Report_delivery. There is no exact-preservation exception for Report_delivery.

打包时排除所有层级的 `.md` 文件（扩展名不区分大小写），包括 `README.md`、`Report.md` 及其他 Markdown 说明文件；`Report_delivery/` 内同样适用。只从压缩包中排除，保留项目中的源文件。

Before packaging, prepare a final HTML with required styles, scripts and table-preview data embedded. Synchronize the report image copies from the current formal Results before packaging and preserve them in `Report_delivery/Results/`. The report must reference these synchronized image copies. Retain scientific result-table copies used by the report, with relative links that resolve within the archive root. Verify those links and offline report resources. If the HTML still depends on excluded resources, fix a staged copy before packaging; never deliver a broken report or silently restore user-deleted files.

Package `Report.html` together with synchronized final figures (PDF/PNG/SVG/JPEG) and formal result tables under `Report_delivery/Results/`. These are delivery artifacts and must not be classified as preview resources or process files. Verify that every synchronized figure matches the current formal Results file byte for byte. Keep editable `Report.md`, `figure_manifest.tsv`, `Report.bundle_*`, `report_assets`, `table_previews`, thumbnail HTML, stale result copies, screenshots, drafts and review artifacts outside the archive. Source copies may remain in the project; exclusions change archive membership only. Do not generate additional thumbnail HTML unless explicitly requested. Retain formal scientific result tables; an index or manifest is not an analysis result table.

## Workflow

1. Resolve the exact project path. Package only `SOURCE_PROJECT/Results/`.
2. Audit cache directories and large files under `Results/`. Retain deliberate delivery tables; report unexpectedly large included files.
3. Place the archive and checksum in `SOURCE_PROJECT/` by default:

   ```bash
   scripts/package_bioinfo_project.sh SOURCE_PROJECT SOURCE_PROJECT
   ```

4. Pass a safe archive basename and project-relative exclusions when the user excludes result modules. Exclusions also apply inside `Results/Report_delivery/`:

   ```bash
   scripts/package_bioinfo_project.sh SOURCE_PROJECT SOURCE_PROJECT ARCHIVE_BASENAME \
     'Results/09.module' 'Results/09.module/*'
   ```

5. Preserve an existing archive or checksum; the script must refuse overwrite.
6. Finish only after the archive is readable and all printed validation gates pass.

An explicitly requested destination may override the project-directory default.

## Default exclusions throughout Results

Apply these to every Results path; the final `Results/Report_delivery/Report.html` is the sole HTML exception:

- Large analysis objects: `*.h5ad`, `*.h5ad.gz`, RDS/RData variants, `*.log`, `*loom`, `*bam*`, `*arrow*`, `*.h5`, `Save-Uwot-UMAP*tar`, `Impute-Weights*`, `*.pkl`, `*.pkl.gz`, `*bgz`, `*qs`, `*qs2`.
- Markdown, review, and audit documents: `*.md`, `*.mmd`, `*.docx`, `*.doc`, `*.txt`, and paths containing `manifest`.
- HTML: `*.html` and `*.htm`.
- Preview resources and process artifacts: `Report.bundle_*`, `report_assets`, `table_previews`, `preview_resources`, `previews`, paths containing `gallery`, `Report_thumbnails.html`, `figure_index.tsv`, `figure_manifest.tsv`, `file_index.tsv`, `index.tsv`, `index.csv`, `run_summary*`, source maps, screenshots, review builds and draft reports. Keep validation logs outside the archive.
- Caches: `__pycache__`, `.cache`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.ipynb_checkpoints`, `.snakemake`, `.nextflow`, `dask-worker-space`, `node_modules`.
- Temporary/system files: `*.pyc`, `*.pyo`, `*.tmp`, `*.temp`, `*.swp`, `*.swo`, backup-suffix files, `.DS_Store`, `Thumbs.db`.
- Previous delivery archives: `*.tgz`, `*.tar.gz`.

Every non-Results path remains outside the archive. Retain `Data/Raw/` patterns as defense in depth.

## Validation gates

Require all of these:

- `VALIDATION_OK`
- `OUTSIDE_RESULTS_MATCHES=0`
- `EXCLUDED_MATCHES=0`
- `USER_EXCLUDE_MATCHES=0`
- `HTML_OUTSIDE_REPORT_MATCHES=0`
- `REPORT_MISSING_FILES=0` for the final HTML and synchronized final figures/tables (not process assets)
- `REPORT_PRESERVATION_STATUS=not_present|complete`
- archive path inside the requested destination, with a SHA256 sidecar

Report the archive path, size, checksum path and digest, exclusions, final report status, and whether raw archives remain included.

## Safety

- Write the archive to the project root by default, never inside `Results/`.
- Use temporary archives and atomic rename after validation.
- Do not create a packaging manifest.
- Do not delete or edit source files; exclusions affect archive membership only.
- Do not overwrite an existing archive or checksum.
