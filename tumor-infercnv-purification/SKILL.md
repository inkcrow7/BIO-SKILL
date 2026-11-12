---
name: tumor-infercnv-purification
description: Require inferCNV-based malignant-cell identification and purification for tumor single-cell RNA-seq projects. Use for solid-tumor scRNA-seq QC, annotation, malignant-versus-normal classification, tumor-cell subsetting, reanalysis, or delivery review; also trigger when a tumor project proposes downstream tumor-cell analysis without an inferCNV purity gate.
---

# Tumor inferCNV purification

Apply an inferCNV purity gate before treating any scRNA-seq compartment as malignant. Use the `bioinfo-delivery` skill for directory structure, reproducibility, tables, figures, and acceptance checks.

## Workflow

1. Verify the input contract.
   - Use raw integer counts, a genome-build-matched gene-order file, donor/sample metadata, disease group, and broad cell-type annotations.
   - Keep integrated, scaled, batch-corrected, and log-normalized matrices out of inferCNV input.
   - Record inferCNV version, genome build, gene-order source/checksum, parameters, seed, cell counts, and sample counts in `run_summary.yaml`.

2. Define candidate and reference cells before inferCNV.
   - Test plausible tumor-lineage compartments; do not label cells malignant from lineage markers alone.
   - Build a trusted diploid reference from confidently annotated immune, endothelial, or stromal cells. Exclude doublets, low-quality cells, cycling artifacts, and biologically ambiguous reference clusters.
   - Preserve donor and sample identifiers. Prefer within-sample references; otherwise justify a cohort-level reference and quantify sample composition.
   - Make minimum reference/candidate cell counts configurable. If no defensible reference exists, acquire an appropriate normal reference or mark inferCNV purification as not assessable.

3. Run inferCNV on every eligible tumor project.
   - Run at sample-aware resolution or jointly with sample identity retained; never let one large patient silently dominate the reference.
   - Keep the full inferCNV observation, denoised expression, clustering, and CNV-state outputs in `Data/Processed`.
   - Treat HMM calls as optional corroboration, not a substitute for inspecting broad chromosome-scale patterns.

4. Classify cells with an explicit evidence gate.
   - Derive a per-cell CNV burden relative to the diploid reference and calibrate thresholds from the reference distribution, such as a configurable robust median/MAD rule.
   - Require concordant evidence for `malignant_high_confidence`: elevated CNV burden, coherent chromosome-arm-scale alterations, cluster consistency, and enrichment in tumor samples or tumor-lineage compartments.
   - Assign `normal_like` when the profile remains reference-like and `ambiguous` when evidence conflicts or coverage is insufficient.
   - Use CopyKAT, known genomic alterations, tumor markers, or pathology as orthogonal validation when available. Do not promote immune/stromal cells solely because of a noisy CNV score.
   - Keep thresholds, evidence columns, and reasons in the cell-level table; never overwrite the original annotation.

5. Purify downstream tumor-cell inputs.
   - Use only `malignant_high_confidence` cells as the primary malignant object for tumor subclustering, differential expression, trajectory, regulons, communication, and perturbation analyses.
   - Run a sensitivity analysis that adds `ambiguous` cells when their exclusion could change conclusions.
   - Retain `normal_like` and `ambiguous` cells in the full object and classification table so the decision is reversible.

6. Validate at the biological replicate level.
   - Report malignant fraction and CNV burden per donor/sample, not only pooled cells.
   - Check stability across patients, library batches, sequencing depth, cell cycle, and candidate subclusters.
   - Use donor/sample-level statistics for group inference. Cell-level P values do not establish cohort-level significance.

## Required outputs

- `infercnv_cell_classification.full.tsv`: one row per tested cell with sample, donor, original annotation, CNV metrics, evidence flags, final class, and decision reason.
- `malignant_cells.filtered.tsv`: stable cell IDs for `malignant_high_confidence`; preserve the header when zero cells pass.
- `infercnv_sample_summary.full.tsv`: per-sample counts, malignant fractions, reference composition, and QC metrics.
- `infercnv_statistical_tests.full.tsv`: exact P values, adjusted P values, test method, comparison, and replicate unit used by inferCNV boxplots.
- `malignant_cells.high_confidence.h5ad` or `.rds` in `Data/Processed`, plus the complete annotated object.
- Separate, semantically named PDF/PNG files for the chromosome-scale CNV heatmap, malignancy-class UMAP, sample-level malignant fraction, and CNV-score boxplot. Follow `bioinfo-delivery`: no generic Figure names, multi-panel composites, or facets; split gene-expression plots one gene per file; show significance stars on every valid boxplot and retain exact statistics.
- A `figure_index.tsv`, analysis README, and internal `run_summary.yaml` in their prescribed locations.

## Decision boundaries

- A completed inferCNV run is mandatory; a malignant call is not. If no cells pass, deliver the full table and an empty filtered table without a placeholder plot.
- For hematologic malignancies, near-diploid tumors, pediatric tumors with low CNV burden, or datasets lacking a defensible diploid reference, report inferCNV as limited or not assessable and use disease-appropriate genetic/lineage evidence. Do not force a purified malignant set.
- State that inferCNV supports malignancy inference from transcriptional CNV patterns; it does not prove genomic copy-number alterations or causality.

## Completion criteria

Finish only when every eligible cell has a reversible class and reason, the high-confidence malignant object exactly matches the filtered cell list, donor-level sensitivity is documented, required figures/tables pass `bioinfo-delivery`, and no downstream tumor-cell analysis uses an unpurified compartment.
