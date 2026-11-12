# Workflow Parameter Guide

This guide records method evidence from internal workflow code, notebooks, command logs, and result metadata. Use it to identify what was run, then disclose official-documentation parameters, client-approved project parameters, and result-affecting analysis thresholds in delivery reports. Workflow-only helper names, private paths, and company-internal custom parameter names are evidence for the writer, not report prose.

## Reporting Rule

- Name the package or external program that performed each analysis.
- Report official-documentation parameters, client-approved project parameters, and analysis thresholds that affect biological/statistical output.
- Do not report internal workflow names such as `Auto 工作流`, private helper names, private paths, raw internal flags, or company-internal custom parameter names in client reports.
- Do not report compute-resource or implementation-only settings in client reports: CPU counts, thread counts, worker counts, parallel backends, shell commands, private script paths, private repository paths, or code-internal helper names.
- Express public method parameters in report prose rather than exposing raw command lines.
- Do not report purely cosmetic plot dimensions unless the figure interpretation depends on them.
- If a result-affecting parameter cannot be recovered from result files or command logs, ask for the run command/config before final delivery. Do not write missing-parameter or missing-metadata narration in the report body.

## scRNA-seq Core Workflow

Internal evidence anchors:

- scRNA preprocessing source
- scType annotation source
- pySCENIC source
- Cell marker heatmap / GO BP source

Parameters to disclose:

- QC metrics: `n_genes_by_counts`, `total_counts`, `pct_counts_mt`; for regular scRNA also include mitochondrial scatter plots; for snRNA, only `n_genes_by_counts` and `total_counts` are used in the primary QC violin.
- QC gene groups: mitochondrial genes match `^Mt-` case-insensitively; hemoglobin genes match `^Hb[^pP]`; ribosomal genes match `^Rp[sl]`.
- `sc.pp.calculate_qc_metrics(..., qc_vars=['mt','hb','ribo'], percent_top=[20], log1p=True)`.
- Automatic outlier filtering: `log1p_total_counts`, `log1p_n_genes_by_counts`, and `pct_counts_in_top_20_genes` filtered at `5 MAD`; mitochondrial outliers filtered at `3 MAD` or `pct_counts_mt > 8`.
- If no `report.params.json`, command log, or config explicitly shows a different QC branch, report the MAD filtering rule above. Do not mention manual fallback thresholds, missing-parameter/missing-metadata statements, or `Auto 工作流` in client reports.
- Doublet detection: `rapids_singlecell.pp.scrublet(..., batch_key='samples')`; report the actual `sample_key` if changed.
- Counts preservation: raw counts are saved to `adata.layers['counts']`.
- Batch-effect correction/integration: default single-cell workflow uses scVI/scvi-tools for batch correction and construction of a batch-corrected low-dimensional cell embedding before neighbor graph construction, clustering, UMAP, and annotation. Report scVI/scvi-tools by default unless run metadata explicitly says a non-scVI branch was used. Describe neighbor graph construction as using the scVI batch-corrected cell embedding, for example `use_rep='X_scVI'`, when the exact embedding key is recoverable. Report actual `batch_key`, embedding dimension, model settings, and training parameters only when recoverable from project metadata/logs; omit unrecoverable parameters from the report body without writing missing-parameter or missing-metadata statements.
- Clustering/UMAP parameters are often set in notebooks or run scripts rather than `src/`; report the actual `n_top_genes`, `n_comps`, `n_neighbors`, `n_pcs`, `resolution`, `min_dist`, and `random_state` if present in project logs. If only output column `res_0_6` exists, disclose `resolution=0.6`.
- scType annotation: annotation is cluster-based after Leiden clustering; `--cluster-key` is required; default `--tissue='Immune system'`; default `--db='short'`; low-memory mode is enabled; clusters with best score `< ncells/4` are set to `Unknown`.
- Subtype annotation: subset the parent cell type first, run Leiden clustering/subclustering within that subset to generate explicit clusters such as `Cluster0`, `Cluster1`, or a `res_*` column, then annotate each Cluster as a named subtype using subtype marker genes and annotation tables. If metadata contains both the cluster column and subtype label column, report the mapping, for example `Cluster0 -> Mac1`.
- Marker heatmap/GO BP summary: `--n_genes=50`, `--top_n=5`, `--organ='hsa'` by default unless overridden.

## pySCENIC

Internal evidence anchor: pySCENIC source.

Parameters to disclose:

- Input expression source: filtered/annotated `.h5ad`; counts layer defaults to `counts`.
- Organism: `--ORGANISM hsa` or `mmu`.
- Databases/resources: `--RESOURCES_FOLDER`, `--DATABASE_FOLDER`, and `--MOTIF_FOLDER`.
- GRN step uses GRNBoost2 to infer TF-target co-expression links.
- ctx step uses motif annotation and cisTarget ranking databases; report dropout masking only as a method choice when scientifically relevant, not as a raw CLI flag.
- AUCell step computes cell-level regulon AUC scores.

## DEG Workflows

Internal evidence anchors:

- DESeq2 heatmap/volcano source
- limma volcano/heatmap source
- t-test differential source

Parameters to disclose:

- DESeq2 input count matrix (`--ex`), optional normalized matrix for heatmap (`--norm_ex`), group file (`--groups_path`), contrast order (`--groups_order`), and optional ID translation table (`--trans_df`).
- DESeq2 threshold: `--fc` is fold change, not log2 fold change; default `FC_cutoff=2`, equivalent to `|log2FoldChange| > 1`.
- DESeq2 significance selector: `--p_filter_by` defaults to `padj`; can be `pval` or `pval:<value>` / `padj:<value>`.
- DESeq2 batch model: `--batch` uses column `batch`; `--batch_colname` overrides the batch column and should always be reported.
- limma input type: `--dt` defaults to `array`; report `array` vs `NGS` if changed.
- limma threshold: `--fc=2` and `--pval=0.05` by default; report whether `adj.P.Val` or raw `P.Value` was used when zero adjusted-significant genes cause fallback.
- t-test workflow threshold: `--fc=2`, `--pval=0.05`; use only when the actual project ran this script.

## GEO / TCGA Data Workflows

Internal evidence anchors:

- GEO extraction source
- GEO series-matrix download source
- TCGA/GDC download-merge source
- cBioPortal clinical download source

Parameters to disclose:

- GEO: input raw directory, output directory, GSE name, platform annotation source, probe-to-symbol collapse rule if applied.
- TCGA/GDC: `--input_dir`, `--file_name_prefix`, `--data_type` (`mRNA` or `miRNA`), `--db` (`TCGA` or `TARGET`), and whether `--download_only`, `--merge_only`, or `--deg_only` was used.
- cBioPortalData: study ID and clinical fields used for downstream matching.

## GO / KEGG / Reactome / GSEA

Internal evidence anchors:

- GO/KEGG enrichment source
- GSEA source
- pathview source

Parameters to disclose:

- ORA gene input file, gene column (`--gene_col`, default first column), organism (`--organ`, default `hsa`, choices include `hsa`, `mmu`; rat support appears in GSEA).
- ORA thresholds: `enrichGO(..., ont='ALL', pAdjustMethod='BH', pvalueCutoff=0.05, qvalueCutoff=0.2)`; `enrichKEGG(..., keyType='ncbi-geneid', pvalueCutoff=0.05, pAdjustMethod='BH', qvalueCutoff=0.2)`.
- KEGG cache flag: `--kegg_cache` / internal-data setting affects whether KEGG data are fetched or reused.
- GSEA input: full DEG table, fold-change column (`--fc`, default `auto`), gene column (`--gene`, default first column), gene ID type (`--gene_type`, default `ALIAS`), optional `--gmt` file.
- GSEA significance filter: `--p_filter_by` defaults to `qval`; if no explicit value, threshold is `0.05`.
- GSEA enrichment call uses `pvalueCutoff=1` before downstream filtering in this workflow; disclose this if reporting final filtered GSEA tables.
- pathview: report KEGG ID input, DEG input, fold-change column (`--fc`, default `log2FoldChange`), and organism (`--organ`, default `hsa`).

## WGCNA

Internal evidence anchors:

- WGCNA module construction source
- WGCNA fine-tune source

Parameters to disclose:

- Input expression matrix, trait/group file, group order, optional config file, and whether cached server files are used.
- Soft-threshold candidates: `1:10` and `12:50` by `2`.
- Selection rule: first power with scale-free topology fit `R2 > 0.85`.
- Experience fallback if no power is estimated: for `nSamples < 20`, `unsigned=9`, `signed=18`; for `nSamples < 30`, `unsigned=8`, `signed=16`; for `nSamples < 40`, `unsigned=7`, `signed=14`; otherwise `unsigned=6`, `signed=12`.
- `pickSoftThreshold(..., blockSize=50000, networkType=type)`.
- `blockwiseModules(..., maxBlockSize=nGenes, TOMType=type, minModuleSize, mergeCutHeight, numericLabels=TRUE, pamRespectsDendro=FALSE, saveTOMs=TRUE, corType, maxPOutliers, loadTOMs=TRUE)`.
- Hub gene rule visible in fine-tune script: `|MM| > 0.8` and `|gene_sig| > 0.2`.

## Network Pharmacology / Docking

Internal evidence anchors:

- docking config source
- Vina execution source
- 3D ligand generation source
- Psi4 input source
- fpocket execution source

Parameters to disclose:

- BATMAN-TCM version/database and score/p-value threshold actually used in the exported tables.
- fpocket: receptor PDB input and selected pocket (`P_0` when available; otherwise highest `simpleScore` / `drugScore` row).
- Docking box: center from `Geometric pocket center`; size is `ceil(max_radius * 2)` for all X/Y/Z dimensions.
- AutoDock Vina config: `exhaustiveness=8`, `energy_range=3`, `num_modes=9`; do not disclose CPU/thread settings or raw command lines.
- RDKit: `AllChem.EmbedMolecule(..., randomSeed=1)` where the simple 3D generation helper is used.
- Psi4 input: default charge `0`, multiplicity `1`, method `B3LYP`, basis `6-31G*`, and `scf_type df`.
