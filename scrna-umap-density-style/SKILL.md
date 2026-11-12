---
name: scrna-umap-density-style
description: Standardize single-cell UMAP, FeaturePlot, expression-density, and QC figures made from Seurat v5 objects with scop, Nebulosa, ggplot2, and patchwork. Use when creating, revising, reviewing, or exporting scRNA-seq dimensional-reduction plots, marker-expression maps, split-group density maps, or QC violin plots in R.
---

# scRNA UMAP and density style

Apply the visual contract in [`references/scRNA_umap_density_style.md`](references/scRNA_umap_density_style.md) completely before writing or revising figure code.

## Workflow

1. Inspect the Seurat object's metadata names, grouping levels, feature names, and existing project palette before plotting.
2. Ensure the project has `Scripts/config/colors.yaml`. Merge the required palette sections into an existing file while preserving unrelated project colors.
3. Use named palettes whose keys exactly match grouping or cell-type levels. Report unmatched levels instead of silently recycling colors.
4. Implement the requested plot with the reference's scop, Nebulosa, ggplot2, and patchwork patterns. Preserve equivalent semantics when a package version requires a compatible alternative.
5. For split expression-density maps, calculate density within each group and apply one shared color scale from zero to the global maximum.
6. Export every final figure as vector PDF and 300 dpi PNG with the same basename.
7. Review the outputs for readable labels, sensible aspect ratios, nonduplicated legends, and comparable scales.

## Required defaults

- Remove UMAP titles, subtitles, cell-count statistics, and counts appended to legend labels.
- Keep only the gene name as the FeaturePlot panel title.
- Read all colors from `Scripts/config/colors.yaml`; keep plotting scripts free of hard-coded color literals.
- Apply the `bioinfo-delivery` continuous-numeric palette rules to FeaturePlot expression and expression-density mappings.
- Use compact legend titles such as `Group`, `Cell type`, and `Sample`.
- Combine repeated legends in multi-panel figures.
- Prefer in-panel labels or a single legend and remove unreadable redundant variants.

Explicit user instructions and repository-local figure standards override these defaults. When a requested deviation is necessary for scientific interpretability, state it in the delivery note.

## Completion criteria

Finish only when every requested figure has both output formats, palette keys cover all plotted levels, split panels use comparable scales, and no title, count, legend, or aspect-ratio violations remain.
