# Figure Catalog — Available Figures per Analysis Module

A menu of figures actually produced by the `/share/CodeBase/work_flow/Auto` pipelines. Each entry lists: typical filename pattern (as emitted by the upstream R/Python script), what the figure shows, when to include in a client report, and a recommended Chinese caption template.

**Selection principle:** every produced figure type must be represented at least once in the customer report. When one type has many files (many contrasts, pathways, clusters or ligand-receptor pairs), include one representative example and add a file-navigation note for the remaining instances. Drop only internal-process plots that were not delivered as client-facing result figures.

**Filename conventions** (across modules):

| Token | Meaning |
|-------|---------|
| `{prefix}` / `{file_name_prefix}` | Caller-supplied prefix (script CLI argument); typical values: `Cell_Types.ALL`, `Cell_Types.SAMPLES`, sample/group/contrast labels |
| `{gse}` | GSE accession (e.g. `GSE12345`) |
| `{gp}` | Group / comparison label (e.g. `TumorVsNormal`) |
| `{module}` | WGCNA module color (`turquoise`, `blue`, ...) |
| `{gene}` | Gene symbol |
| `{pathway_name}` / `{gsea_id}` | KEGG pathway code (`hsa04110`) or GSEA term ID |

大多数图表脚本默认同时保存 `.pdf` 与 `.png`；个别脚本只输出其中一种（如 Cytoscape 导出仅 PNG / SVG，pathview 仅 PNG）。在 HTML 报告中统一使用 `.png`，必要时附上 `.pdf` 链接以便使用者下载矢量图。

---

## Universal panels (any module)

| Panel | Typical filename | Shows | Include when |
|-------|------------------|-------|-------------|
| Sample overview | `sample_metadata_table.tsv` (table, not figure) | Cohort design | Always — as first table after 背景 |
| Pipeline schematic | `workflow.{drawio,png}` | Workflow diagram | Optional — only if multi-stage workflow needs explanation |

---

# scRNA-seq

> Scripts under `/share/CodeBase/work_flow/Auto/scRNA/{src,Plot}/`. Filename patterns are caller-driven (`file_name_prefix`); the labels in this catalog reflect the canonical prefixes used in the team's downstream notebooks.

## A. QC

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Per-sample QC violin (before) | `QC.violin.plot.png` | n_genes / total_counts / pct_mt / pct_hb / pct_ribo distribution per sample | Skip unless QC was delivered as a result figure |
| QC scatter — counts × MT% | `QC.total_counts.MT_pct.plot.png` | Joint distribution; outlier 区域 | Skip — internal QC |
| QC scatter — counts × genes | `QC.total_counts.n_genes_by_counts.plot.png` | Joint distribution | Skip — internal QC |
| QC distribution plot | `QC.total_counts.displot.png` | Marginal density | Skip — internal QC |
| Per-sample QC violin (after) | `QC_after.violin.plot.png` | Distributions after filtering | Methods-side support only |

**Caption template (if used):** `**图N.** 各样本细胞水平质控指标分布：n_genes_by_counts、total_counts、pct_counts_mt、pct_counts_hb、pct_counts_ribo（自上而下）。`

## B. Clustering & 注释

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Cell-type UMAP (整体) | `Cell_Types.ALL.UMAP.png` | All cells colored by scType cell type | Always — landscape figure |
| Cell-type UMAP (按样本) | `Cell_Types.SAMPLES.UMAP.png` | UMAP split / colored by sample | Always for multi-sample projects |
| Cell-type UMAP (按分组) | `Cell_Types.GROUPS.UMAP.png` | UMAP split / colored by group | Always for case/control comparison |
| Cluster UMAP | `Leiden.{res}.UMAP.png` | Leiden cluster labels (before annotation) | Optional support |
| Marker dotplot (per cell type) | `Dotplot.gene_cells.png` | Marker expression × cell type | Always — annotation evidence |
| Marker dotplot (per group) | `Dotplot.gene_cells.groups.png` | Marker × cell type × group | When group-level marker comparison is included |
| Marker stacked violin | `Violin.gene_cells.png` / `Violin.gene_cells.groups.png` | Marker expression distributions | Alternative format |
| Marker matrixplot | `Matrixplot.gene_cells.png` / `Matrixplot.gene_cells.groups.png` | Cell-type × marker mean heatmap | Compact alternative |
| Marker heatmap + GO BP | `{file_name_prefix}.png` (driven by `CellMarkerGenesHeatmap_GOBP.cli.R`) | Top-N markers heatmap + ClusterGVis GO BP terms | Always — supports annotation + function |
| Circular UMAP | `{FILE_NAME_PREFIX}.png` (driven by `plot_circlizeUMAP_adata_cli.R`) | Circular cluster layout | Optional design alternative to flat UMAP |
| 单基因表达小提琴 | `violin.{gene}.exprs.png` | Single-gene expression distribution as violin per cell-type/group | Highlight specific markers |

**Caption template:** `**图N.** A：基于 Scanpy 标准流程 (PCA + Leiden) 与 UMAP 投影的细胞图谱，颜色表示 scType 注释的 N 种主要细胞类型；B：各细胞类型在 [实验组] 与 [对照组] 中的分布对比；C：经典标志基因在各细胞类型中的表达点图，点大小表示表达比例、颜色表示平均表达量。`

## C. 细胞组成 / Ro/e

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Cell-type stacked barplot | `{prefix}cell_types.barplot.png` | Per-sample / per-group cell counts | Always — composition comparison |
| Cell-type % stacked barplot | `{prefix}cell_types.barplot_PCT.png` | Per-sample / per-group cell percentages | Always — composition comparison |
| Ro/e heatmap | `{prefix}roe_heatmap.png` | Tissue/group preference of each cell type | When tissue or group is the comparison variable |
| Composition pie | (via `plot_pie_for_group` helper) | Single-group pie | Decorative — use only if pie genuinely helps |
| Stat-tested boxplot | (via `feature_stat_plot` helper) | Per-group cell-type % with p-value | When statistical comparison matters |

**Caption template:** `**图N.** A：[实验组] 与 [对照组] 各细胞类型相对比例堆叠柱状图；B：基于 Ro/e 指标的细胞类型-组织来源偏好热图（颜色越深表示该细胞类型在该组织中越富集）。`

## D. 标志 / 重点基因表达

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Gene panel violin | `Violin.gene_cells.png` | Multi-gene violin grid | Always for marker panel |
| Gene panel dotplot | `Dotplot.gene_cells.png` | Marker × cell-type expression dot grid | Always |
| Gene panel matrixplot | `Matrixplot.gene_cells.png` | Mean-expression heatmap | Compact alternative |
| Gene panel (group split) | `Violin.gene_cells.groups.png`, `Dotplot.gene_cells.groups.png`, `Matrixplot.gene_cells.groups.png` | Same as above split by group | When group comparison is included |

## E. 单细胞 DEG

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| DEG volcano (per cell type) | caller-named (driven by `sc_DEGs_volcano_plot_func.R`) | Wilcoxon / pseudobulk DEGs on log2FC × -log10(adj. p-value)；Scanpy `rank_genes_groups` 输出列为 `pvals_adj`，pseudobulk + DESeq2 输出列为 `padj`，二者择一标注 | When per-cluster DE drives the conclusion |

## F. 转录因子调控网络 (pySCENIC)

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| AUCell binarization histogram | `binarization.{regulon}.png` (via `AUCell_histplot.py`) | AUC distribution + chosen threshold | Methods-side support; skip in customer report |
| Regulon specificity top-5 per cell type | `RSS_top5.{cell_type}.png` | Top regulons ranked by RSS | Always for TF focus |
| Regulon AUC heatmap | `regulon_AUC.heatmap.png` | TF activity × cell type | Alternative summary |

**Caption template:** `**图N.** 各细胞类型 pySCENIC 调控单元 (regulon) 特异性评分 (RSS) 排名前 5 的转录因子点图，点大小或颜色表示 RSS 值。`

---

# Bulk RNA-seq (+ GEO + TCGA DE)

> Scripts under `/share/CodeBase/work_flow/Auto/DEG_auto/`. Bulk / GEO / TCGA share the same DE plotting back-end; only the `{prefix}` token convention differs.

## A. 样本质控与概览

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Sample boxplot | `{prefix}.QC_boxplot.png` (bulk) / `{tissu}{prefix}.QC_boxplot.png` (GEO) | log2(CPM+1) sample-wise distribution | Always — confirms normalization parity |
| Batch-removed boxplot | `{tissu}{prefix}.rmB.QC_boxplot.png` | Distribution after `limma::removeBatchEffect` | Only when batch effect was applied |
| Sample correlation heatmap | `{prefix}.sample_correlation.heatmap.png` | Pearson r between samples | Always for cohort overview |
| PCA scatter | `{prefix}.PCA.png` | Sample positions on PC1×PC2 | Always — group separation evidence |

**Caption template:** `**图N.** A：各样本 log2(CPM+1) 表达分布箱线图；B：基于全基因表达谱的样本主成分分析 (PCA) 散点图，颜色表示分组。`

## B. 差异表达

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Volcano plot (bulk) | `{prefix}.png` (DESeq2 driver) / `{prefix}.Volcano.png` (limma) | log2FC × -log10(padj/adj.P.Val), top genes labeled | Always per contrast |
| Volcano plot (GEO) | `{gse}.{gp}_Volcano.png` | Same, per GEO-comparison | Always per GEO contrast |
| DEG heatmap (bulk) | `{prefix}.heatmap.png` | Top DEGs z-score heatmap | Always — pairs with volcano |
| DEG heatmap (GEO) | `{gse}.{gp}_heatmap.png` | Same, per GEO-comparison | Always |
| DEG heatmap (TCGA) | `{cancer_code}.{prefix}.heatmap.png` (e.g. `LUSC.mRNA.heatmap.png`) | Same, per TCGA-comparison | Always |

**Caption template:** `**图N.** A：[实验组] vs [对照组] 差异表达分析火山图，横轴为 log2 fold change（DESeq2 列名 `log2FoldChange` / limma 列名 `logFC`），纵轴为 -log10(adjusted p-value)（DESeq2 列名 `padj` / limma 列名 `adj.P.Val`），红/蓝点分别表示显著上调/下调基因，标注前 N 个最显著差异基因；B：top [N] 差异基因在所有样本中的 z-score 标准化表达热图。`

---

# 功能富集 (Enrichment)

> Scripts under `/share/CodeBase/work_flow/Auto/Enrichment/`. Identical plotting back-end whether the input DEG list comes from bulk, scRNA, GEO or TCGA.

## A. ORA — GO / KEGG

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| GO BP dotplot | `GO_BP.dotplot.png` | Top BP terms (gene ratio × padj × count) | Always for functional readout |
| GO CC dotplot | `GO_CC.dotplot.png` | Cellular component terms | Optional — only if CC is biologically informative |
| GO MF dotplot | `GO_MF.dotplot.png` | Molecular function terms | Optional |
| GO combined plot | `GO.png` | BP + CC + MF facet | Compact alternative |
| KEGG dotplot | `KEGG_dot.png` | Top KEGG pathways | Always for functional readout |
| GO term-term network | `GO_emapplot.png` | Pairwise term similarity network | Use when GO list is long and clustering helps |
| KEGG term-term network | `KEGG_emapplot.png` | Same for KEGG | Same |
| topGO 精简 BP | `topGO_BP.png` (and `_CC`, `_MF`) | topGO `elim` 算法在 GO DAG 上自下而上从祖先节点中剔除已被显著子节点占用的基因，从而保留更具体的、冗余度较低的子术语 | Use when GO term list is very redundant |
| Single-pathway dot | `{pathway_name}_dot.png` | Single pathway summary | Highlight specific pathway |
| Single-pathway emap | `{pathway_name}_emapplot.png` | Single pathway network | Highlight specific pathway |
| KEGG pathview | `{pathway_name}.pathview.png` (e.g. `hsa04110.pathview.png`) | Genes mapped to KEGG schematic with log2FC color | When pathway-specific figures are produced |

**Caption template:** `**图N.** A：差异基因的 GO Biological Process 富集 top 通路点图（enrichplot::dotplot 默认配色：颜色越浅/越红表示 `p.adjust` 越小、即富集越显著；点大小表示该通路中富集到的差异基因数 Count，横轴为 GeneRatio）；B：差异基因的 KEGG 通路富集 top 通路点图（同上）。`

## B. GSEA

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| GSEA running plot (single) | `GSEA.{gsea_id}.png` | Running enrichment + ranked list | Highlight key pathway |
| GSEA top-5 activated | `{prefix}GSEA{file_name_mid}activate.top5.png` | Top 5 NES > 0 pathways enrichment plot | Always when GSEA is included |
| GSEA top-5 inhibited | `{prefix}GSEA{file_name_mid}inhibit.top5.png` | Top 5 NES < 0 pathways enrichment plot | Always when GSEA is included |
| GSEA GO panel | `{gse}_GSEA_GO_{i}.png`, `{gse}_GSEA_GO_1_5.png` | GO-based GSEA result panel | GEO-flavor projects |
| GSEA KEGG panel | `{gsea_id}_GSEA_KEGG.png` (and topic-specific like `ECM_related_GSEA_KEGG.png`) | KEGG-based GSEA result panel | Always when KEGG GSEA included |

**Caption template:** `**图N.** A：基于差异表达基因 log2FoldChange 排序列表的 KEGG GSEA top 5 激活通路 (NES > 0) 富集得分曲线；B：top 5 抑制通路 (NES < 0) 富集得分曲线。`

---

# WGCNA

> Scripts under `/share/CodeBase/work_flow/Auto/WGCNA/`. All figure names share the caller's `{prefix}`; `{exprMat}` is an optional matrix-id prefix when multiple matrices are processed together.

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Sample tree | `{exprMat}{prefix}_sampleTree.png` | Hierarchical clustering of samples; outlier detection | Methods-side - only include if delivered as a result figure |
| Sample tree with cut | `{prefix}_sampleTree_cut.png` | Same with cutoff line | Methods-side |
| Soft-threshold power | `{prefix}_Soft_Threshold_plot.png` | Scale-free R² and mean connectivity vs β | Methods-side support |
| Scale-free check | `{prefix}_check_scale_free_plot.png` | log(k) vs log(p(k)) for selected β | Methods-side |
| Module dendrogram | `{prefix}_cluster_plot.png` | Gene clustering + module color band | Always — landscape figure |
| Module eigengene plot | `{prefix}.eigen_plot.png` | Module-eigengene-vs-sample/trait | Optional support |
| TOM matrix plot | `{prefix}_TOM_plot.png` | Topological overlap matrix heatmap | Methods-side |
| Module-trait heatmap | `{prefix}_trait_cor_heatmap.png` | Pearson correlation × p-value across modules × traits | Always — main module-trait result |
| Module membership scatter | `{prefix}.Module_membership_{module}.verboseScatterplot.png` | |kME| vs |GS| within a module | Hub-gene identification figure |
| Module summary scatter | `{prefix}_verboseScatterplot.png` | Overall MM-GS landscape | Alternative |

**Caption template:** `**图N.** A：基因层次聚类树及对应的 WGCNA 共表达模块色带；B：各共表达模块特征基因 (ME) 与样本临床/分组性状的 Pearson 相关性热图，单元格内为相关系数 (上) 与 p 值 (下)；C：关键模块内基因模块隶属度 (kME) 与基因显著性 (GS) 散点图，右上角为枢纽基因区。`

---

# GEO 流程特有图

> Scripts under `/share/CodeBase/work_flow/Auto/GEO_data_auto/`. All GEO figures use `{tissu}{prefix}` token convention; downstream DE shares the bulk DE figure types above.

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| GEO 平台分布 | `{gse}.platform_summary.png` | Probe count / platform distribution | Methods-side only |
| GEO 探针表达分布 | `{tissu}{prefix}.QC_boxplot.png` | Per-sample boxplot of probe expression | Always — sanity check |
| GEO 探针表达去批次 | `{tissu}{prefix}.rmB.QC_boxplot.png` | Same after `removeBatchEffect` | When batch removal is applied |
| GEO DE 火山图 | `{gse}.{gp}_Volcano.png` | DE volcano per comparison | Always |
| GEO DE 热图 | `{gse}.{gp}_heatmap.png` | Top DEGs z-score heatmap | Always |

---

# TCGA 流程特有图

> Scripts under `/share/CodeBase/work_flow/Auto/TCGA_data_auto/`. DE figures share the bulk DE plotting back-end with cancer-code prefix; survival/WGCNA share the existing generic modules.

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| TCGA DEG 火山 / 热图 | `{cancer_code}.{prefix}.png`, `{cancer_code}.{prefix}.heatmap.png` | T vs N DEGs | Always for TCGA cohort |
| TCGA WGCNA | `{cancer_code}.{prefix}_cluster_plot.png`, `_trait_cor_heatmap.png` | Module discovery in TCGA cohort | When TCGA WGCNA is included |
| Survival KM curve | `KM.{gene}.png` | Kaplan-Meier survival stratified by gene expression | When survival analysis was performed |
| Survival forest plot | `forest.png` | Cox regression hazard ratio | Multi-variable risk model |

**Caption template (survival):** `**图N.** [基因名] 高/低表达组在 TCGA-[癌型] 队列中的 Kaplan-Meier 总生存曲线，对数秩检验 p = [p-value]。`

---

# ceRNA 网络

> Scripts under `/share/CodeBase/work_flow/Auto/ceRNA/`. Figure outputs are emitted by downstream Cytoscape session and helper scripts (`VennNetworkPlot.py`).

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| miRNA 靶基因 Venn 图 | `miRNA_target.venn.png` | Overlap across multiple databases / miRNAs | When intersection logic is the rationale |
| ceRNA 网络 | `ceRNA_network.png` (Cytoscape export) | lncRNA/circRNA – miRNA – mRNA tri-layer network | Always for ceRNA focus |
| 三元组表达相关性散点 | `ceRNA_triplet.{lnc}_{mir}_{mrna}.scatter.png` | Per-triplet expression correlation | Optional support |

**Caption template:** `**图N.** ceRNA 网络示意图：以 [miRNA] 为连接节点，展示 lncRNA/circRNA、miRNA 与 mRNA 三类 RNA 节点及其数据库预测/表达相关性支持的连接关系；节点颜色按 RNA 类型区分。`

---

# 网络药理学 (Pharmacology Network)

> Scripts under `/share/CodeBase/work_flow/Auto/Ph_net/`. Outputs combine Cytoscape XML-styled networks, docking PDB structures rendered to PNG, PLIP labelled interaction maps, and PyMOL ray-traced figures.

## A. 成分-靶点网络

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| BATMAN 检索摘要 | `batman_query_summary.png` | Components × herbs heatmap | Methods-side support |
| 中药-成分-蛋白节点-疾病多层网络 | `phnet.network.png` (Cytoscape export, `Drug_net.styles.xml`) | Multi-layer network (中药 / 成分 / 蛋白节点 / 疾病) | Always - main network figure |
| PPI 子网络 | `ppi.{module}.png` (Cytoscape `PPI_styles.xml`) | Protein-protein interaction sub-network within a target module | Optional |
| Venn - 中药相关蛋白 vs 疾病基因 | `drug_disease.venn.png` (via `VennNetworkPlot.py`) | Intersection of compound-related proteins and disease genes | Always - database-list overlap |
| 重叠蛋白节点 GO/KEGG | (reuse Enrichment patterns above with target-list prefix) | Functional enrichment of overlapping protein-node genes | Always |

**Caption template:** `**图N.** A：[中药/复方] 中药-成分-蛋白节点-[疾病] 疾病基因多层网络，节点按类型着色（紫：中药；蓝：成分；橙：蛋白节点；红：疾病基因）；B：中药相关蛋白节点与 [疾病] 疾病基因 Venn 图，交集表示两类数据库列表的重叠部分。`

## B. 分子对接 (Vina)

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| 受体口袋识别 (fpocket) | `fpocket.{receptor}.png` | Top-3 predicted binding pockets | Methods-side or appendix |
| Vina 评分表 | `vina_scores.tsv` (table) | Receptor × ligand 预测亲和力 (predicted binding affinity, kcal/mol) 表 | Always — main quantitative result |
| Vina 评分热图 | `vina_scores.heatmap.png` | Same as table, visualized | Compact alternative to table |
| 最佳对接构象图 | `{receptor}_{ligand}.dock.pose.png` | PyMOL-rendered ligand inside binding pocket | Highlight key pairs |

**Caption template:** `**图N.** A：[中药成分] 与 [蛋白] (PDB ID: [PDB]) 的 AutoDock Vina 分子对接预测亲和力 (predicted binding affinity, kcal/mol) 热图，数值越负代表 Vina 评分模型给出的相对评分越低；B：对接评分最低（绝对值最大）的构象的 PyMOL 渲染图，展示配体在受体口袋内的空间位置。`

## C. 蛋白-配体相互作用 (PLIP)

| Panel | Filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| PLIP 标注图 | `{receptor}_{ligand}.PLIP.png` (含 PLIP_add_labels.py 注释) | 氢键、疏水接触、π-π 堆积、盐桥等相互作用残基 | Always for key docking pairs |
| PLIP legend | `PLIP_legend.png` | 图例 (PLIP_legend_creator.py) | 辅助资产，不作为独立报告图或 manifest figure type |
| PyMOL 细节图 | `{receptor}_{ligand}.pymol.png` | Close-up of interactions with bond annotations | Always — pair with PLIP |

**Caption template:** `**图N.** [中药成分] 与 [蛋白] 对接评分最低（绝对值最大）的构象相互作用解析图：A：PLIP 自动识别的相互作用残基与连接类型 (氢键 / 疏水接触 / π-π 堆积 / 盐桥)；B：PyMOL 渲染的残基-配体距离细节。`

For overall-pocket outputs, prefer `Viz/png/raw/overall_pocket/...overall_pocket.png` when both raw and legend-rendered files exist. Do not use `Viz/png/legend/overall_pocket/...overall_pocket.png` as the displayed overall-pocket report panel.

---

# Ad-hoc / Extra Figure Types

These modules may be produced outside `/share/CodeBase/work_flow/Auto`. Do not invent filenames or methods. If real files exist in the project results directory, still cover every figure type in the report and state the method factually from the project artifacts or implementing bioinformatician.

## scRNA cell-cell communication

Use one representative pathway/comparison per type when many pathways exist.

| Figure type | Common filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Communication circle | `CellChat_*circle*.png`, `*_circle_*.png` | Sending/receiving cell groups and edge weights in a pathway or aggregate network | Include if produced |
| Communication heatmap | `CellChat_*heatmap*.png`, `*_heatmap_*.png` | Sender-target pair intensity matrix | Include if produced |
| Bubble / dot plot | `CellChat_*bubble*.png`, `CellPhoneDB_*dot*.png` | Ligand-receptor pairs across cell pairs; color/size encode strength/significance | Include if produced |
| Chord / network | `*chord*.png`, `*network*.png`, `*netVisual*.png` | Cell-pair or pathway network view | Include if produced |
| River / alluvial | `*river*.png`, `*alluvial*.png` | Source-target or signal contribution flow | Include if produced |
| Ligand-receptor table figure | `*LR*.png`, `*ligand*receptor*.png` | Ranked or filtered ligand-receptor interactions | Include if produced |
| Pathway-specific panel | `*pathway*.png`, `{pathway}*.png` | One pathway-level communication summary | Include one representative pathway if pathway-specific panels are produced |

**Caption template:** `**图N.** 以 [通路/比较] 为例展示细胞通讯分析图型：A：circle 图展示发送与接收细胞类型之间的通讯边；B：heatmap 展示细胞对强度矩阵；C：bubble/dot 图展示配体-受体对的强度与显著性；D：river/alluvial 图展示来源到目标的贡献流向；E：network/chord 图展示该通路下的通讯连接。其他通路或比较可在 [目录] 中按同名规则查看。`

## scRNA trajectory / pseudotime

| Figure type | Common filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Pseudotime embedding | `*pseudotime*.png`, `*monocle*umap*.png` | Cells colored by pseudotime score on UMAP/tSNE | Include if produced |
| Branch/state embedding | `*state*.png`, `*partition*.png` | Trajectory branches or states | Include if produced |
| Gene trend heatmap | `*trend*.png`, `*pseudotime*heatmap*.png` | Gene expression changes along pseudotime ordering | Include if produced |
| RNA velocity arrows | `*velocity*.png`, `*scvelo*.png` | Directional arrows or stream plot | Include if produced |

## Immune infiltration / deconvolution

| Figure type | Common filename pattern | Shows | Include when |
|-------|------------------|-------|-------------|
| Infiltration stacked bar | `*CIBERSORT*bar*.png`, `*immune*bar*.png` | Estimated cell fractions per sample/group | Include if produced |
| Infiltration heatmap | `*CIBERSORT*heatmap*.png`, `*immune*heatmap*.png` | Sample-by-cell-type score matrix | Include if produced |
| Group comparison boxplot | `*immune*boxplot*.png`, `*infiltration*box*.png` | Per-cell-type scores across groups | Include if produced |
| Correlation plot | `*immune*cor*.png` | Correlation among cell types or with genes/scores | Include if produced |

---

# Selection Checklist (per report)

Before settling on a figure list, verify:

1. **Cover every figure type** in the project-level `figure_manifest.tsv`; many files of one type may be represented by one pathway/contrast/example.
2. **No result subsection without a figure; no figure without a read-the-figure explanation.**
3. **Panel order matches caption letters** - A first, B second; reorder image markdown if needed.
4. **Use file-navigation notes** when only one representative is shown from a large family, e.g. "其他通路见 `CellChat/pathways/`".
5. **Drop only internal-process plots** that were not delivered as result figures, such as batch logs, parameter scans and temporary debugging plots.
6. **Stay data/bioinformatics-facing** - no mechanism, clinical, diagnostic, prognostic or therapeutic claims.
7. **Filename sanity-check** - the `![]()` paths in the report MUST resolve under the report's `--asset-base` directory after copy; run `report_lint.py` with `--figure-manifest`.

# Out-of-scope (no figures shipped by current pipeline)

The following figure categories are NOT produced by `/share/CodeBase/work_flow/Auto`; do **not** invent fictional filenames for them. If a project genuinely needs them, the implementing bioinformatician must produce the figures using an ad-hoc workflow and the writer must list real filenames in the report.

- ATAC-seq / scATAC-seq (fragment size, TSS enrichment, peak annotation, ChromVAR, peak-to-gene, footprint)
- ChIP-seq / CUT&RUN / CUT&Tag (profile, heatmap, DiffBind, motif)
- Spatial transcriptomics (H&E overlays, Cell2location, SpatialDE, niche)
- Multi-omics (WNN, MOFA, joint UMAP)
- scRNA malignancy (inferCNV / CopyKAT / SCEVAN)
- scRNA perturbation (Augur lollipop, Milo beeswarm, DA-seq)
