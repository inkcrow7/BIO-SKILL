---
name: omics-analysis-report
description: Draft, lint, render, and review Chinese omics/bioinformatics analysis delivery reports. Use when the user asks to write/generate/render an analysis report, bioinformatics report, omics report, summary report, or provides an analysis-results directory. The report must show what analyses were performed, what result files/figures exist, how to read each figure type, and how result tables/files correspond to the analysis outputs; it must not add biology-direction, mechanism, clinical, therapeutic, diagnostic, research-hypothesis interpretation, reader-address wording, or third-party action guidance. Every produced figure type must be represented in the report, using one representative contrast/pathway/example when a type has many files.
---

# Omics Analysis Report Skill

Create polished delivery reports for omics and bioinformatics projects. The report is a result-explanation deliverable, not a biological discovery manuscript.

## Output Contract

Final delivery files must use the base name `Report`. Do not name final outputs `omics_analysis_report`, `omics-analysis-report`, or similar internal skill/workflow names. The standard full report `Report.html` is the sole default HTML entry point. Generate an additional thumbnail HTML only when explicitly requested. If a Markdown source is created for editing, prefer `Report.md`.

Generate the standard report regardless of figure count; figure-type coverage and result-module admission rules determine report content.

Drafts, raw renders, screenshots, and validation-only builds must stay in a temporary working folder such as `.report_tmp/` inside the result directory or an OS temp directory. Do not write multiple draft `Report.html`, `Report.raw.html`, or `Report.bundle_*` versions into the result root while iterating.

The final report belongs in `Report_delivery/`. Package the final `Report.html` and formal result figures/tables according to `bioinfo-project-packaging`. Keep editable Markdown, manifests, preview sidecars, hashed resource bundles, screenshots and staging files outside the delivery archive. Before packaging, embed required report styles, scripts and preview data in the final HTML and synchronize image copies from the current formal Results into `Report_delivery/Results/` and retain these figures in the archive; they are final report content, not preview resources. Keep formal result-table copies referenced by the report and resolve figure/table links against the packaged files. Keep report compilation intermediates in a temporary working directory.

Absolute filesystem paths are privacy leaks and are always forbidden in report Markdown, rendered HTML, table manifests, file chips, figure links, captions, references to source files, and delivery-package metadata. `Report.html` uses only paths relative to the report asset base or `Report_delivery/`, such as `4.GO_KEGG/Enrich/GO_enrichment.xls`. Any POSIX path such as `/Users/...`, `/private/...`, `/tmp/...`, `/share/...`, `/data/...`, any `~/...` path, Windows drive path such as `C:\...`, or UNC path such as `\\server\share\...` is `BLOCKED` and must be removed before lint, render, review, or delivery can pass.

In `Report.html`, the displayed browser image may be a PNG/JPEG/SVG, but clicking the figure must open the original source figure file. If a same-path same-stem PDF exists for the displayed image, the figure link must target that PDF; otherwise it must target the displayed source image. Do not link figure clicks to PNG files generated only as report-rendering derivatives when an original PDF exists.

The finished report must answer four reader questions:

1. 做了哪些生信分析。
2. 产生了哪些主要结果和输出文件。
3. 每一种图应该怎么看，包括坐标轴、颜色、点大小、分组、显著性和文件关系。
4. 结果表格、图片和结果文件夹分别对应哪些分析输出。

Do not answer: 这个结果说明研究方向里的什么生物学机制、病理机制、治疗价值、诊断价值、预后价值或候选假说。 Stay at the data and bioinformatics layer.

Generated Chinese report text must not address or instruct a third party. Do not use `客户`, `用户`, `使用者`, `读者`, or similar address terms. Do not write action-guidance sentences such as `使用者可...`, `用户可...`, `后续可...`, `建议...`, `如需...`, `可按...筛选`, `可导入...`, `可载入...`, `可在 R/Python/Excel/Cytoscape 中...`, or similar instructions telling someone what to do. Write neutral result language such as `该表记录...`, `相关文件位于...`, `完整结果位于...`, `PNG 为位图结果，PDF 为矢量版本`, or `该矩阵对应...`.

## Assets

```
omics-analysis-report/
├── SKILL.md
├── compile_delivery.py
├── md_to_html.py
├── report_lint.py
├── template.html
├── figure-catalog.md
├── methods-snippets.md
├── workflow-parameter-guide.md
├── references.bib
├── vendor/
│   └── luckysheet/
└── examples/
    ├── figure_manifest_example.tsv
    ├── template_blank.md
    ├── template_scrna.md
    ├── template_bulk_deg.md
    ├── template_wgcna.md
    ├── template_tcga.md
    ├── template_geo.md
    ├── template_cerna.md
    └── template_phnet.md
```

Load `figure-catalog.md` when selecting figures. Load any `report.params.json` files found in the result directories before writing methods, then load `methods-snippets.md`, `workflow-parameter-guide.md`, and `references.bib` as fallbacks and citation sources. Use the matching example template as a starting point, then remove template comments before delivery.

## Report Structure

Use this structure unless the user provides a stricter one:

1. `## 1. 项目概述`
   - Describe sample/source, analysis modules, and deliverables.
   - Keep background data-oriented. Do not write clinical need, treatment gap, mechanism rationale, or disease biology unless the user explicitly asks for a biology discussion.
   - Present sample-group information as a Markdown table. Do not enumerate sample IDs in prose.
2. `## 2. 方法`
   - Start with `### 2.1 数据获取` or `### 2.1 数据收集与对象选择`.
   - `数据获取` must describe the actual dataset/cohort/source in natural bioinformatics report language. Do not write meta text such as "本报告使用当前交付目录中的已完成分析结果" or "不重新推断原始实验设计".
   - If the dataset/source is not clear from local files, ask the user for the dataset/accession/source before drafting methods. If a public accession such as GSE/GSM/SRP/PRJNA/TCGA is available, retrieve or search the sample/platform/group information and write the source/sample method from that evidence.
   - Add one method subsection per analysis module, in the same order as results.
   - Use `methods-snippets.md` only for methods actually run. If the module is ad-hoc or outside the snippets, write a factual method summary from the project files or ask the implementing bioinformatician.
   - Methods must describe data source, design, software, algorithm/statistical principle, method characteristics, thresholds, databases, organism codes, and reportable parameters for analyses actually performed in the current project only. For public processed data, do not write upstream sequencing/base-calling/read-alignment/quantification methods merely because they appear in GEO/SRA/ArrayExpress/TCGA records or the original article. Do not write result observations, result counts, top entries, selected modules, "highest qvalue" statements, or concrete result file paths in method prose. Result file paths belong in `## 3` or `## 4`, except sample/source information tables.
3. `## 3. 结果与图表解读`
   - One subsection can cover one analysis module or one related set of figure types.
   - Each subsection must include figures, explain how to read them, state only data-level observations, and name the related output tables/files.
4. `## 4. 结果文件说明`
   - Describe how result tables, image files, and folders correspond to the analysis outputs. Do not write third-party operation guidance such as opening files in Excel/R, loading networks into Cytoscape, using AnnData/Seurat objects, downloading files, or selecting follow-up targets.
5. `## 5. 参考文献`
   - Include only references for software, databases, methods, or resources actually named in the report.
   - Use China National Standard GB/T 7714-2005 numeric style in Chinese reports. Body citations must be numeric superscript links, for example `<sup class="citation-ref"><a href="#ref-1">[1]</a></sup>`, `<sup class="citation-ref"><a href="#ref-1">[1-3]</a></sup>`, or `<sup class="citation-ref"><a href="#ref-1">[1,4]</a></sup>`; do not expose BibTeX citation keys such as `[Wolf2018Scanpy]`.
6. Optional appendix
   - Use when figure-type coverage is large. Appendices may contain representative figure panels and file navigation tables, but they still count as part of the delivery report.

## Contrast And Sample-Information Rules

For every section that directly performs or interprets differential, comparison, marker, differential abundance, differential metabolite, differential peak, module-trait/group-trait, or feature-ranking analysis, explicitly state the control group and experimental group when such groups exist. Use direct wording such as `对照组为 Healthy，实验组为 NAFLD` or `Healthy 作为对照组，NAFLD 作为实验组`.

Do not force comparison wording into enrichment sections. GO/KEGG/Reactome over-representation analysis and GSEA are enrichment analyses; they may state their input object, such as `DEGs_filter 表中的显著差异基因` or `按 log2FoldChange 排序的全基因列表`, but they should not say `沿用差异表达对比设置`, should not introduce `对照组/实验组`, and should not describe the enrichment step itself as a group comparison unless the project actually ran a comparison test inside that enrichment module.

Sample information must be shown in a table, not as long prose. Do not enumerate sample IDs one by one in sentences. If sample IDs, sample groups, retained/removed samples, or cohort splits need to appear, present them as a Markdown table with columns such as `样本集合 / 对照组 / 实验组 / 样本数 / 相关表格` or `分组 / 样本数 / 样本表`. The report may link the source TSV/CSV/XLS/XLSX table instead of listing every sample ID.

Methods must not contain results. In `## 2. 方法`, do not write concrete result counts, top-ranked entries, selected result modules, graph/plot observations, output-file inventories, upstream processing copied from public database records, or statements such as `该表最高 qvalue 为...`, `对应 ... 个显著差异基因`, `当前结果包含...`, or concrete result paths like `...DGEs_filter.tsv`. Keep methods to how the current project analysis was run; move result quantities, output paths, and visible data observations to `## 3. 结果与图表解读` or `## 4. 结果文件说明`.

## Method Software, Principles, Parameters, and References

Method text must disclose the analysis software, package names, method principles, method characteristics, important parameters, and references. This is a required part of the deliverable, not an optional manuscript-style add-on.

Rules:

- Name the package/program/database that performed each analysis step: for example Scanpy, AnnData, rapids_singlecell, Scrublet, scType, inferCNV, CellChat, Augur, pySCENIC, DESeq2, limma, clusterProfiler, WGCNA, Cytoscape, AutoDock Vina, fpocket, PLIP, RDKit, Open Babel, PyMOL, or Psi4.
- Each `## 2. 方法` subsection after data/source collection must contain enough method depth for a client-facing bioinformatics report:
  - the input object and output object, such as count matrix to DEG table, gene list to enrichment table, or peak table to annotated regions;
  - the core algorithm, statistical model, or scoring principle, such as negative binomial modeling, empirical Bayes moderation, graph-based community detection, variational autoencoder-based low-dimensional embedding construction, over-representation analysis, running-sum GSEA, regulon motif pruning, ligand-receptor probability modeling, or docking search/scoring;
  - one concise method characteristic explaining why the method is suitable for this output, such as robustness to dispersion, suitability for sparse single-cell matrices, preservation of graph neighborhood structure, handling of batch covariates, support for compositional microbiome counts, reproducible LC-MS object workflows, or interpretable network topology;
  - actual result-affecting parameters, thresholds, databases, organism codes, design formulas, grouping/contrast definitions, or filtering rules that are recoverable and reportable;
  - numeric GB/T citations for the software, database, or method papers named in the paragraph.
- Do not write method subsections as a bare list of software and files. A sentence such as `使用 DESeq2 进行差异分析并绘制火山图` is insufficient unless it also explains the count model/test principle, the feature of the method, and the actual threshold/design used.
- When several packages jointly implement one module, cite and explain the role of each result-affecting method. For example, bulk RNA-seq quantification should distinguish FASTQ QC/trimming, genome alignment or transcript quantification, read summarization, and downstream differential modeling; single-cell integration should distinguish QC/doublet detection, scVI batch-corrected low-dimensional cell embedding construction, graph clustering, UMAP projection, and marker-based annotation.
- Use current package/method literature for every named method. Prefer entries already in `references.bib`; if a report needs a method not represented there, add a real traceable citation to `references.bib` before using the method in a report.
- Use module-local `report.params.json`, workflow guides, code, logs, and result metadata as internal evidence, but write only package/program/database names plus official-documentation parameters, client-approved project parameters, and result-affecting analysis thresholds in the delivery report.
- Treat `report.params.json` as delivery-report-safe metadata: use its `software`, `parameters`, `references`, and `outputs` fields, but still do not paste JSON verbatim into the report.
- For any report section containing single-cell QC, write the MAD filtering thresholds when they were used: `log1p_total_counts`, `log1p_n_genes_by_counts`, and `pct_counts_in_top_20_genes` outliers at `5 MAD`, plus mitochondrial filtering at `3 MAD` or `pct_counts_mt > 8`. These are reportable QC thresholds. Do not mention `Auto 工作流`, company-internal workflow names, private helper names, or code-internal parameter names in final report prose.
- Do not disclose private implementation details in delivery reports: CPU counts, thread counts, worker counts, parallel backends, raw shell commands, script paths, private repository paths, code-internal helper names, or "from the codebase/log/script" phrasing.
- Keep public method parameters in prose. For example, write `物种参数为 hsa` or `Leiden resolution=0.6`; do not write internal command fragments such as `--N_WORKERS=32`, `vina --cpu 60`, or `pyscenic ... --num_workers`.
- If project logs/configs override a parameter, report the actual value rather than the guide value.
- If a parameter cannot be recovered from results, logs, or code, do not invent it; add a concise caveat in the draft and ask for the run command/config before final delivery.
- Add numeric citations immediately after the method sentence or paragraph that names the software/resource, using GB/T 7714-2005 sequential numbering rendered as clickable superscript links such as `<sup class="citation-ref"><a href="#ref-1">[1]</a></sup>` or `<sup class="citation-ref"><a href="#ref-1">[1-3]</a></sup>`.
- The final `## 5. 参考文献` section must contain every numeric citation used in the body and must not contain unused references. Each body citation must jump to a matching `id="ref-N"` anchor in the reference section. Reference entries must use GB/T 7714-2005 numeric format, for example `[1] <span id="ref-1" class="reference-anchor"></span>作者. 题名[J]. 刊名, 年, 卷(期): 页码.`.
- Third-party package citations must be real and traceable. Prefer entries already in `references.bib` as the source library, but convert them to GB/T 7714-2005 numeric entries in the final report instead of printing BibTeX keys.

### Related-Figure Panels

One figure number identifies one gallery: `图1` is one gallery containing panels A, B, C, D, ...; `图2` is the next gallery and starts again at A. Group images by analytical object or topic, such as clustering and annotation, marker expression, cell composition, or one communication pathway. Choose the panel count from the content; four panels are not required. A standalone image keeps its own figure number.

Write the group's image references consecutively, then one `**图N.**` caption that explains each panel in the same order. Keep headings and individual captions outside the image sequence. A caption can combine consecutive panels with identical semantics using a range such as `B–C：...`.

```markdown
![](Figures/cluster_umap.png)
![](Figures/sample_umap.png)
![](Figures/cell_type_umap.png)
![](Figures/marker_dotplot.png)

**图1.** 降维聚类与细胞注释。A：Leiden 簇分布；B：样本来源分布；C：细胞类型分布；D：marker 点图，颜色表示平均表达量，点大小表示表达细胞比例。
```

The HTML structure is one `<figure>` containing one `.figure-scroll` gallery of independently linked images and one shared `<figcaption>`. Put A/B/C/... immediately above each image, visible at rest and in print, with space for the letters so they do not cover axes or data. Reserve space for the floating contents panel so it does not hide panel labels. Preserve the template's bounded horizontal layout. Each panel links to its same-stem original PDF when available. Keep formal PNG/PDF files separate and retain figure-type coverage. Keep one manifest entry per source image; record the common `figure_number` and the individual `panel` when revising an existing report.

When converting an existing report, rewrite `Report.md` and its manifest so related images are consecutive and have one shared caption. Update cross-references to the new figure numbers. Remove individual image headings/captions inside each gallery. A scrolling wrapper around separately numbered `<figure>` elements does not satisfy this layout. Remove legacy gallery postprocessors that recreate that structure, regenerate the project's actual `Report.html`, and refresh an existing delivery archive when requested; updating the skill alone does not update a report.

Before delivery, run `report_lint.py` for panel explanations and `md_to_html.validate_figure_galleries()` on the final HTML after all postprocessing. Require one sequential figure number and shared caption per gallery, A/B/C/... in image order with numbering restarting in each gallery, no nested separately numbered figures, and working original figure links.

## Mandatory Figure-Type Coverage

Every produced figure type must appear in the report. The goal is coverage of figure categories, not every individual file.

### Result Module Admission Gate

Treat the report's result modules as a subset of the internal workflow. A standalone result subsection must contain at least one real, interpretable figure type that presents a biological analysis result or QC/integration/validation evidence required to interpret downstream biology.

Steps limited to download, file acquisition, checksum, decompression, format conversion, provenance, sample-field audit, archive inventory, or workflow `go/no-go` gating must not become standalone result modules when they produce no qualifying figure. Keep their necessary dataset/source facts in `2.1 数据获取` or the relevant method paragraph, and omit their internal tables, empty figure folders, empty manifests, status-only sections, and placeholder figures from the report and delivery package.

A biological analysis that completes with no significant entries is not an empty technical module: retain its full/empty-filtered tables and show a real effect, distribution, diagnostic, or negative-result figure when available. Never manufacture a placeholder figure to satisfy this gate.

Definition of a figure type:

- Same analysis module + same visualization grammar + same displayed metric = one type.
- Different contrasts, samples, clusters, pathways, or ligand-receptor pairs are usually instances of the same type.
- Different visual encodings are different types: volcano, heatmap, PCA, dotplot, bubble plot, circle network, chord plot, river/alluvial, stacked bar, UMAP, pathview, enrichment running plot, Cytoscape network, docking pose, PLIP interaction diagram.

For figure-rich modules, choose one representative instance per type:

- If CellChat/CellPhoneDB/NicheNet has many pathways, include one pathway or one comparison per figure type, then add a short file-navigation table for the remaining instances.
- For enrichment/pathview/GSEA, include the dotplot type, network/map type if produced, and one representative pathway-specific figure if such files exist.
- For single-cell marker plots, dotplot, violin, matrixplot, heatmap, UMAP, composition bar, and Ro/e heatmap are separate types if produced.
- Do not hide a type because it is redundant. If it was delivered as a result figure, represent it at least once.
- When a section shows one representative example from a result folder that contains many same-type figures, explicitly state the complete result folder path immediately after the example and explain how to find the remaining files.

Create a figure manifest before drafting:

```tsv
figure_type	representative_path	note
communication_circle	Figures/CellChat_circle_TNF.png	CellChat pathway-level circle plot
communication_heatmap	Figures/CellChat_heatmap_TNF.png	Interaction strength heatmap
communication_bubble	Figures/CellChat_bubble_TNF.png	Ligand-receptor bubble plot
communication_river	Figures/CellChat_river_TNF.png	Source-target contribution river plot
communication_network	Figures/CellChat_network_TNF.png	Pathway network view
```

The `figure_type` values are stable labels chosen by the report writer. `representative_path` must be a path that appears in the Markdown report. Multiple representative paths may be separated with `;`; at least one must be included.

## Narrative Rules

### Global Scope Of Constraints

All user-defined delivery constraints in this skill are global by default and apply to every bioinformatics report generated through this skill. Do not narrow a rule to single-cell reports, bulk reports, metabolomics reports, or another report type unless the rule depends on an analysis object that exists only in that module.

Module-specific rules are still global triggers: whenever a report contains that module or output family, the rule applies. For example, table-preview field descriptions apply to every linked TSV/CSV/XLS/XLSX in any omics report; complete result-folder wording applies to every representative figure family; complete marker/differential table exposure applies to any marker, DEG, differential abundance, differential metabolite, peak, or feature-ranking output with per-unit or per-contrast tables; single-cell annotation ordering applies to any report section that performs cell-type/subtype annotation; scVI wording applies to any report using the default single-cell integration workflow.

Each result subsection should contain:

1. What analysis produced this result.
2. What the figure type shows.
3. How to read the axes/colors/point sizes/panel letters.
4. What data-level observation is visible.
5. Which output file/table corresponds to the result module.
6. For major result table families, describe the table's analysis role at the file level only. Do not enumerate table fields in the report body; field explanations belong only to the rendered table-preview field-description panel.

Allowed wording:

- `图中颜色表示平均表达量，点大小表示表达细胞比例。`
- `横轴为 log2FoldChange，纵轴为 -log10(padj)。`
- `该表记录各 cluster 的 DEGs 表与 DEGs_filter 表路径。`
- `该网络文件记录节点、边与拓扑指标。`
- `该结果说明两组在该评分/比例/表达量上存在数据层面的差异。`

Forbidden wording unless the user explicitly requests biological interpretation:

- 机制、病理机制、通路驱动、TME 重塑、表型驱动
- 治疗、药物疗效、诊断、预后、临床意义
- 靶点筛选、候选靶点、治疗靶点、下游靶点
- 与既往研究一致、为某机制提供依据、提示某疾病机制
- 任何把数据结果推进到研究方向生物学意义的句子

When a term such as `靶点` is part of an analysis object name in network pharmacology or ceRNA, keep it factual: describe it as a database/network node or table column, not as a biological claim or application recommendation.

### Intersection Gene Terminology

When a gene set is produced by intersecting two or more input gene lists, call the resulting object `交集基因` or `交集基因集合` in report body text, headings, captions, table labels, and file descriptions.

Do not call intersection-derived genes `共享基因`, `共享基因集合`, `共享靶点`, or `重叠基因`. This applies especially to network pharmacology, ceRNA database-overlap, Venn, PPI, enrichment-input, and docking-input sections. Use direct wording such as `两类列表交集得到 89 个交集基因`, `PPI 网络以交集基因对应蛋白为节点`, and `富集分析以交集基因集合为输入`.

### No Meta-Report Or Renderer Narration

The delivered report body must contain only bioinformatics content: dataset/source, methods, result modules, figure reading, result tables, and result file/table organization. Do not write sentences about the report as a report, the writer's intent, the interpretation boundary, the renderer, HTML behavior, validation workflow, result-generation logs, missing metadata, absent parameters, or third-party operations.

Forbidden report-body wording includes but is not limited to:

- `本报告重点说明...`
- `报告重点说明已完成哪些生信分析...`
- `结果解读限定在...`
- `不对研究方向、应用价值或假说作延伸判断`
- `渲染后该长表可折叠`
- `点击任一 TSV 可在右侧表格区查看`
- `HTML 报告中点击...`
- `TSV 按钮`
- `右侧表格预览`
- `可折叠` when describing report UI behavior instead of bioinformatics content
- `结果文件未记录...`
- `未记录软件版本号`
- `方法部分保留...`
- `运行记录未保存...`
- `结果元数据未保存...`
- `无法确认...`
- `不补写无法确认...`
- `完整 marker/DEG 表`
- `完整 marker/差异基因表`

Correct the content by removing the meta/log sentence, not by rephrasing it into another report/process statement. For example, instead of saying `报告重点说明...`, start directly with the dataset, sample counts, and analysis modules. Instead of saying `结果文件未记录软件版本号...`, omit the missing-version statement and keep the actual methods and thresholds. Instead of saying `渲染后该长表可折叠，点击任一 TSV...`, write `完整结果文件夹位于 ...；每个 cluster 均保留 DEGs 表与 DEGs_filter 表。`

### No Comment-Style Caveats

This rule applies to every bioinformatics report generated by this skill, including single-cell, bulk transcriptome, enrichment, WGCNA, network pharmacology, docking, metabolomics, microbiome, ATAC/ChIP, and other omics reports.

Do not add comment-like caveats, disclaimer sentences, or narration about what a result should not be interpreted as. These sentences read like review comments rather than a bioinformatics report. If such wording appears, rewrite it as a direct method/result sentence or remove it.

Forbidden report-body wording includes but is not limited to:

- `该描述仅反映...`
- `该分析仅作为...`
- `该结果仅用于...`
- `该图仅用于说明...`
- `仅作为...指标使用`
- `仅供参考`
- `不将...解释为...`
- `不直接解释为...`
- `不代表...`

Correct by keeping the bioinformatics observation itself. For example, replace `该描述仅反映当前细胞组成矩阵中的组间比例差异` with the actual composition result sentence, such as `Tumor 组中 EC、Tumor cell、Fibroblast 和 Macrophage 的比例高于 Ctrl 组。`

### Single-Cell Annotation Workflow

Single-cell annotation sections must describe the actual annotation order:

- Global cell-type annotation: first perform dimensional reduction/neighborhood graph construction and clustering, then use cluster-level marker genes plus annotation tools or curated annotation tables to assign cell-type labels to clusters.
- Subtype annotation: first subset the parent cell type, then run Leiden clustering/subclustering within that subset to produce explicit subtype clusters such as `Cluster0`, `Cluster1`, or a `res_*` column. Next, assign subtype labels to each Leiden Cluster using subtype marker genes, annotation tools, and/or curated annotation tables. The report should state the recoverable mapping, for example `Cluster0 -> Mac1`, when the metadata or tables contain both cluster identifiers and subtype labels.
- 二次聚类的报告正文、方法和图注只说明分析的细胞群、实际采用的方法、关键分析参数、聚类与marker注释结果及相关图表，不展开该步骤的输入数据集、父对象或文件版本，也不写原始counts、标准化矩阵、全图嵌入、assay/layer或`active.assay`等输入实现细节。这些来源与配置完整保留在内部脚本和运行记录中；本条覆盖该步骤的一般输入对象及精确嵌入键披露要求。项目整体数据来源仍在数据获取章节说明，报告的方法和完成状态必须与实际运行一致。
- Do not write subtype sections as if subtype labels were assigned directly before clustering, as if subtyping and clustering were the same step, or as if labels such as `Mac1-Mac6` are themselves the initial Leiden clustering output.
- The same order applies to all single-cell annotation-related modules: clustering/subclustering first, marker/annotation evidence second, final cell-type/subtype naming third. For subtype modules, the final naming step is a cluster-to-subtype annotation step.
- Final review should block reports that omit the clustering-before-annotation order in single-cell cell-type or subtype annotation sections, or omit an available Leiden Cluster -> subtype label mapping in subtype sections.

### Batch-Effect Correction Language

For any report section using the default single-cell integration workflow, scVI/scvi-tools batch-effect correction/integration is the default workflow assumption. Methods must state that scVI was used for batch-effect correction/integration and construction of a batch-corrected low-dimensional cell embedding before downstream neighbor graph, clustering, UMAP, and annotation, unless the user or run metadata explicitly says a different integration method or no batch correction was used. Describe the neighbor graph as based on the scVI batch-corrected cell embedding, for example `use_rep='X_scVI'`, when the exact embedding key is recoverable. Name scVI or scvi-tools and cite the corresponding method/software reference. Include recovered parameters such as batch key, embedding dimension, model settings, or training settings only when they are present in result metadata or workflow logs. If a parameter is absent, omit it from the report body; do not write missing-parameter or missing-metadata narration.

For any report section using the default single-cell integration workflow, omission of scVI/scvi-tools batch correction is `BLOCKED` by default unless the report provides explicit run evidence for a non-scVI integration branch.

### Single-Cell Academic Wording

Single-cell method and result prose must use natural academic terminology. Prefer expressions such as `批次校正后的低维细胞嵌入（cell embedding）`, `低维细胞嵌入矩阵`, `scVI 校正后的低维嵌入空间（batch-corrected embedding space）`, `邻近图（nearest-neighbor graph）`, and `低维状态空间（latent space）` when those English terms clarify specialized concepts.

Do not use direct or awkward translations such as `潜在表示`, `整合表示`, `低维潜在表示`, `scVI 整合后的潜在表示`, or `基于整合表示构建...`. If similar unnatural, non-academic single-cell wording appears in a report, the final review must return `BLOCKED` and require replacement with the academic wording above.

### Dataset Source Language

The `### 2.1 数据获取` paragraph must read like a formal report method, not like an agent note.

Use natural wording:

- `本研究使用 GEO 数据库 GSE281266 数据集的单细胞转录组数据。该数据集包含 ...`
- `本研究纳入 TCGA-XXX 队列的 RNA-seq 表达矩阵及配套临床信息，样本信息通过 GDC/cBioPortal 获取。`
- `本研究使用委托方提供的 10X Genomics 单细胞转录组数据，共包含 ...`

Do not use internal-process wording:

- `本报告使用当前交付目录中的已完成分析结果`
- `不重新推断原始实验设计`
- `由于只提供了结果目录`
- `根据文件名推测`

If only a results directory is available and no public accession or sample-source metadata can be found, stop before writing `2.1 数据获取` and ask one concise question for the dataset/source information. After the user answers, continue drafting.

### Result Heading Language

`### 3.X` result headings should be analysis module names or standard project items, not inventory-style descriptions of how many plots were output.

Good headings:

- `### 3.1 单细胞数据质控`
- `### 3.2 降维聚类与细胞类型注释`
- `### 3.3 细胞组成分析`
- `### 3.4 细胞通讯分析`
- `### 3.5 转录因子调控网络分析`

Avoid headings such as:

- `单细胞质控输出五类样本级图表`
- `CellChat 单组结果输出网络、通路和配体-受体图`
- `富集结果包含 dotplot、网络图和组合图`

The body can explain which figure types and files were produced; the heading should stay clean and report-like.

### Representative Figure Wording

For figure families with many samples, contrasts, pathways, cell types, or regulons, use natural report wording:

- `以 GSM8649020_015T 样本为例进行展示。`
- `图中选取 TGFb 通路展示该类图表的结构。`
- `完整结果位于 CellChat/pathways/，其他通路以通路名保存对应文件。`
- `完整差异表达结果位于 4.DEGs_groups/，每个细胞类型对应一个子目录。`

Avoid mechanical wording:

- `以下以 ... 为代表说明读法`
- `以 ... 为代表说明每类图的读法`
- `代表图用于说明读法`
- `完整同类型结果位于 ...`
- `同类型结果位于 ...`

When pointing to sibling files for a representative figure family, write `完整结果位于 ...` instead of redundant phrases such as `完整同类型结果位于 ...`.

### Molecular Docking Score Wording

For molecular docking modules, describe the selected pose as `对接评分最低（绝对值最大）的构象` or `Vina 评分最低（绝对值最大）的构象`. When referring to the numerical Vina value, keep the data-level wording: `数值越负表示评分模型给出的相对评分越低`.

Do not use awkward Chinese such as `评分最负`, `最负构象`, `结合能最负`, or `亲和力最负`. These phrases are `BLOCKED` in report methods, results, captions, table descriptions, figure catalogs, and review prompts. Rewrite them as `对接评分最低（绝对值最大）` before lint, render, review, or delivery.

### Molecular Docking Figure Selection

For molecular docking modules, standalone legend files are auxiliary assets, not report figures. Do not add `PLIP.legend.*`, `PLIP_legend.*`, or other legend-only images as standalone panels in the report or `figure_manifest.tsv`. Explain visual encodings in the caption or body only when needed.

When both raw and legend-rendered overall pocket images exist, use the raw overall-pocket image in the report and manifest, such as `Viz/png/raw/overall_pocket/...overall_pocket.png`. Do not use `Viz/png/legend/overall_pocket/...overall_pocket.png` for the displayed overall-pocket panel.

### pySCENIC Figure Semantics

For pySCENIC RSS/top regulon figures such as `RSS/Viz/ALLcellTypes_RSS_top5.png`, `RSS/Viz/*_RSS_top5.png`, and similarly named top-regulon dot plots, dot color distinguishes top regulon identities/names. Do not describe dot color as RSS value, activity strength, expression level, or statistical significance unless the figure legend explicitly encodes a numeric color scale. In ordinary reports, state that RSS values are available in `cellRSS.matrix.tsv` and that the top-regulon figure shows regulons selected by RSS ranking for each cell type/subtype.

## Workflow

### 1. Inventory Inputs

If the user provides only a directory, list figures and result tables first. Infer modules from filenames and folder names. Create or update `figure_manifest.tsv` with every figure type and representative path.

For projects generated by an internal workflow, inspect the relevant code, notebooks, command logs, and result metadata before drafting methods. Use that material as internal evidence for package/program names, official package parameters, database choices, organism codes, cluster resolutions, and client-visible filtering choices. Do not copy `Auto 工作流`, private helper names, code paths, or company-internal custom parameter names into the client-facing report. QC thresholds such as `5 MAD`, `3 MAD`, and `pct_counts_mt > 8` are reportable when they are the actual analysis thresholds.

First look for generated parameter manifests:

```bash
rg --files <results-dir> | rg '(^|/)report\.params\.json$'
```

When manifests exist, use them as the primary source for method software, reportable parameters, references, and output-file names. If a module has no manifest, fall back to `workflow-parameter-guide.md` and targeted code/log inspection.

Recommended shell lookup:

```bash
rg --files <results-dir> | rg '\.(png|jpg|jpeg|svg|pdf|tsv|csv|xls|xlsx|rds|h5ad)$'
```

### 2. Choose Template

| Project type | Start from |
|---|---|
| single-cell RNA-seq | `examples/template_scrna.md` |
| bulk RNA-seq DE + enrichment | `examples/template_bulk_deg.md` |
| public GEO cohort | `examples/template_geo.md` |
| TCGA cohort | `examples/template_tcga.md` |
| WGCNA | `examples/template_wgcna.md` |
| ceRNA | `examples/template_cerna.md` |
| pharmacology network + docking | `examples/template_phnet.md` |
| mixed/ad-hoc modules | `examples/template_blank.md` |

### 3. Write Methods

Copy only applicable snippets from `methods-snippets.md`. Cross-check `workflow-parameter-guide.md` and the project's code/logs/metadata for actual reportable parameters before finalizing. Replace every placeholder. Method order must mirror result order. Do not invent software, thresholds, file names, sample counts, or versions. Do not promote internal workflow names, company-internal custom parameter names, private helper names, or private paths into final report prose.

Every method subsection must name the software/package, explain the method principle, state a concise method characteristic, and include numeric GB/T citations derived from `references.bib`. When a package or database is named in methods, a clickable superscript numeric citation must appear in the same paragraph or the immediately following sentence. After methods are drafted, add `## 5. 参考文献` and include the matching references only.

Use this method paragraph shape when no more specific snippet exists:

```markdown
[输入对象] 使用 [软件/方法] 进行 [分析任务]。该方法基于 [算法/统计模型/评分原理]，将 [输入] 转换为 [输出]；其特点是 [适合该类数据或结果的原因]。[实际分组、阈值、数据库、物种、关键参数] 按项目结果记录填写。<sup class="citation-ref"><a href="#ref-N">[N]</a></sup>
```

Do not leave package-only method text in final reports. If the method actually run is not covered by existing snippets or literature entries, add a real reference entry first or ask the implementing bioinformatician for the method details before final delivery.

### 4. Write Results

For each subsection:

- Use a concise analysis-module heading, such as `单细胞数据质控`, `差异表达分析`, `GO/KEGG 富集分析`, or `细胞通讯分析`.
- Include one or more representative figures for the covered figure types.
- Explain how to read every panel.
- Stop at observed data patterns.
- Add the relevant output table paths in backticks when available.

For large figure families, group them:

```markdown
### 3.X 细胞通讯分析

CellChat 结果包含 circle、heatmap、bubble、river 和 pathway network 五类图。图中选取 TNF 通路进行展示；完整结果位于 `CellChat/pathways/`，其他通路以通路名保存同名文件。

![](Figures/CellChat_circle_TNF.png)
![](Figures/CellChat_heatmap_TNF.png)
![](Figures/CellChat_bubble_TNF.png)
![](Figures/CellChat_river_TNF.png)
![](Figures/CellChat_network_TNF.png)

**图N.** A：circle 图展示发送与接收细胞类型之间的通讯强度；B：heatmap 展示细胞对之间的汇总强度；C：bubble 图展示配体-受体对的显著性与强度；D：river 图展示来源细胞到目标细胞的贡献流向；E：network 图展示该通路下的通讯边。
```

### 5. Add Result File Description

The final report must describe result file organization and table-output relationships without instructing a third party to take actions. Use neutral file/content descriptions:

- `差异基因结果包括 all.DEGs.tsv 和 all.DEGs_filter.tsv；DEGs_filter 表为对应 DEGs 表的过滤结果。`
- `UMAP 和 marker dotplot 展示细胞注释、marker 表达比例与平均表达水平。`
- `网络文件记录节点、边、权重和拓扑指标。`
- `通路图以 pathway ID 或 pathway 名称保存于同一分析目录下的 PNG/PDF 文件。`

### 6. Add References

Create a `## 5. 参考文献` section before optional appendices. Use China National Standard GB/T 7714-2005 numeric style. Body citations must be superscript links, and every reference entry must carry the matching anchor:

```markdown
正文示例：Scanpy 用于单细胞数据处理 <sup class="citation-ref"><a href="#ref-1">[1]</a></sup>。

## 5. 参考文献

[1] <span id="ref-1" class="reference-anchor"></span>Wolf F A, Angerer P, Theis F J. SCANPY: large-scale single-cell gene expression data analysis[J]. Genome Biology, 2018, 19: 15. DOI: 10.1186/s13059-017-1382-0.
[2] <span id="ref-2" class="reference-anchor"></span>Wolock S L, Lopez R, Klein A M. Scrublet: Computational Identification of Cell Doublets in Single-Cell Transcriptomic Data[J]. Cell Systems, 2019, 8(4): 281-291.e9. DOI: 10.1016/j.cels.2018.11.005.
```

Do not include bibliography entries that are not cited in the report body. Use `references.bib` only as the verified source library; if a new package is introduced, add a real citation to `references.bib` first, then render it as a GB/T numeric entry in the final report.

### Table Preview Interaction

When mentioning result tables, continue to write relative table paths in backticks, such as `5.CellChat/Ctrl/cellchat_LR_prob_pval.tsv`.
During HTML rendering, `.tsv`, `.csv`, `.xls`, and `.xlsx` paths are converted into table-preview chips instead of direct download links. In this workflow, files ending in `.xls` may be tab-delimited text tables rather than binary Excel workbooks; parse `.xls` as tab-delimited text for preview unless the project explicitly supplies real Excel workbook files.

Every TSV/CSV/XLS/XLSX table that appears in the report and can be opened in the table preview must have field descriptions displayed under the opened table. The table-preview panel itself must be responsive: use a right-side split panel on wide screens and a stacked bottom panel on narrow screens, with wrapping header controls and visible table space. The table-preview header should stay compact and responsive: file name plus helper marker on the first line, metadata plus actions on the remaining header space, with truncation/large-table notes exposed through a short-delay custom helper popover rather than as a persistent long header sentence, native `title` tooltip, or CSS pseudo-element tooltip. The popover must use viewport-aware positioning, such as fixed positioning with boundary clamping, so it is not hidden by the table drawer/header or clipped by screen edges. The field-description area must be collapsible and its expanded height must be user-adjustable through a dedicated horizontal drag handle, analogous to the side-panel width splitter; do not rely only on browser-native CSS `resize`. Shared schemas may reuse one field-description mapping, but the rendered preview for each linked table must show the relevant field names and meanings. This applies to metadata tables, marker/DEG tables, enrichment tables, CellChat matrices/long tables, Augur metrics, pySCENIC adjacency/regulon/RSS tables, and any other TSV/CSV/XLS/XLSX path in the report.

For marker, differential, or feature-ranking outputs in any omics report, do not stop at a single combined table link. This includes single-cell marker/DEG tables, bulk DEG tables, differential abundance tables, differential metabolite tables, differential peak tables, enrichment input/result tables, regulon target tables, network node/edge tables, and any similar per-unit/per-contrast outputs. If per-cluster, per-cell-type, per-subtype, per-group, per-contrast, per-pathway, per-regulon, per-module, per-taxon, per-metabolite-class, per-peak-set, or other split result tables exist, the report must expose the complete table-entry surface:

- Link the combined all/long table when available.
- Link each per-unit table and each relevant comparison/contrast table that exists in the result directories.
- State where the complete result folder lives, such as `2.Cluster/leiden_0_6_rank.res/`, `3.CellAnnot/Cell_Marker_Genes/`, or `7.Subtypes/<cell-type>/Annot/Cell_Marker_Genes/`.
- In the report body and table headers, name table types directly from the output, such as `Marker Genes 表`, `DEGs 表`, `DEGs_filter 表`, `differential_abundance.tsv`, `differential_metabolites.tsv`, `peaks.tsv`, `all.DEGs.tsv`, or `GO_enrichment.tsv`. Do not use generic column labels or prose such as `完整 marker/DEG 表`, `完整 marker/差异基因表`, `完整差异表`, or `过滤表` when a concrete table name is available.
- Explain the relationship between unfiltered tables and filtered tables. It is acceptable to describe a filename suffix in plain text, but every linked table path must be a real relative file path that passes `--strict-links`.
- Ensure these linked table paths render as table-preview chips in `Report.html`, so the right-side table preview can show the full table for the selected cluster, cell type, subtype, group, contrast, pathway, regulon, module, taxon, metabolite class, peak set, or other analysis unit. This is an implementation/verification requirement; do not describe the right-side preview, buttons, clicking, HTML, or collapsibility in the report body.
- Ensure each table preview has field descriptions under the opened table. The field-description block must render as a collapsible region and support vertical height adjustment through a visible drag separator when expanded. The table-preview panel must keep a responsive side-by-side layout on wide screens and a stacked layout on narrow screens. Large-table or truncated-preview messages such as `该表较大，当前预览加载 5000 行、32 列；完整内容请下载源文件。` must be attached to a file-name helper marker using a short-delay custom helper popover, not printed as a long visible header status line, not exposed through native `title`, and not rendered by CSS pseudo-element tooltip content. The popover must avoid occlusion/clipping by the drawer, header, and viewport edges. The field descriptions must be specific to the table schema; do not leave generic placeholders such as `字段说明待补充` or fallback text that says the fields are unknown/unrecognized.
- Present any multi-table result-entry surface as a Markdown table or another renderer-supported collapsible structure, grouped by the relevant analysis unit, contrast, result type, group, pathway, regulon, or module. If a paragraph would name two or more TSV/CSV/XLS/XLSX paths, rewrite it as a table with clear columns such as `结果类型 / 表格 / 内容`, `分组 / 表格 / 内容`, or `Leiden Cluster / DEGs 表 / DEGs_filter 表`. Do not place multiple table paths in one long prose sentence or paragraph. The rendered HTML must let the reader collapse these table-entry lists while still opening each TSV/CSV/XLS/XLSX in the right-side preview. This behavior is for verification, not report prose.

Rendered reports must follow these interaction rules:

- Every Markdown table in the rendered report must be collapsible. Long tables must be closed by default; short context tables may be open by default but must still be collapsible.
- Clicking a table chip opens an embedded split-view sidebar inside the report page, with a draggable divider for adjusting preview width.
- The sidebar uses Luckysheet's native toolbar, formula bar, sheet bar, table preview area, and status bar instead of adding a separate `table-preview-controls` layer. Keep the toolbar focused on preview operations such as freeze, sort/filter, and find/replace; remove Luckysheet print UI such as `luckysheet-print-viewList`. Table files remain read-only and are downloaded only through the `下载源文件` button.
- The rendered HTML uses a viewport-contained shell: the report pane scrolls inside the report area, the table sidebar scrolls inside the sidebar, and `body` must not become the report scrolling layer on desktop.
- The table of contents remains a left-side floating window on desktop, including when the table preview sidebar is open; the report pane must reserve enough left-side space so the floating TOC does not cover report content.
- The `下载源文件` button is the only download affordance for table files in the rendered report.
- Preview data is read-only. Intermediate sidecars may be created in the temporary build directory; source table files must retain their bytes and order.
- Final `Report.html` embeds required preview data and loads individual tables into the preview panel on demand. Separate preview-resource directories and sidecars stay outside the archive.
- Verify that final `Report.html` opens offline from the packaged layout, with no missing bundle, font, style, script or table-preview resources.
- Delivery-visible resource paths in Markdown, HTML, table manifests, and table trigger attributes must be normalized relative paths: no absolute path, no `./` prefix, parent-relative paths may refer to formal Results files only when their resolved target remains inside the delivery root; no escaping that root, and no spaces in paths that appear in `src`, `href`, `data-source-href`, `data-table-path`, manifest `sourceHref`, or manifest `sidecar`. If an original source file has spaces or other fragile characters in its filename, create a module-local no-space copy and use that path consistently in `Report.md`, the figure manifest, and `Report.html`.
- Avoid introducing extra cross-directory figure aliases only for renderer convenience. If a required source figure has spaces or other fragile characters in its filename, prefer fixing the generated HTML/package relative resource references first; create a module-local, no-space relative copy only when Markdown parsing or browser resource resolution demonstrably requires it, and then use that path consistently in `Report.md`, the figure manifest, and `Report.html`.
- For large tables, the preview may be capped for responsiveness, but the sidebar header must clearly state the loaded range and keep the source-file download button available.

### Table Preview Field Descriptions

When a report links or previews result tables, concise field descriptions must be generated for every linked TSV/CSV/XLS/XLSX table and displayed only inside the rendered table-preview field-description panel. Do not write table-field lists, `主要字段包括...`, `字段 Metrics 表示...`, or any sentence containing `字段` in the report body. Field descriptions must be written according to the actual table schema in that report and stored in the embedded preview payload so the opened table can show them under the table.

Common schema-description coverage includes:

- Cell metadata: sample, group, cluster, cell type, UMAP/tSNE coordinates, and QC metric columns.
- Cluster marker and cell-type marker tables: `group`, `names`, `scores`, `logfoldchanges`, `pvals`, `pvals_adj`, `pct_nz_group`, and `pct_nz_reference`.
- Differential expression tables: `names`, `scores`, `logfoldchanges`, `pvals`, `pvals_adj`, `pct_nz_group`, `pct_nz_reference`, `Reg`, plus the relationship between `.all`, `.filter`, `.filter.up`, and `.filter.down` files.
- Enrichment tables: `ID`, `Description`, `GeneRatio`, `BgRatio`, `pvalue`, `p.adjust`, `qvalue`, `geneID`, `Count`, and GO `ONTOLOGY` when present.
- Bulk transcriptome DEG tables: gene identifier/symbol columns, base expression, log2 fold change, test statistic, p-value, adjusted p-value, direction/regulation, and annotation columns.
- Differential abundance or microbiome tables: taxon/feature identifier, rank/taxonomy, group summaries, effect size, statistic, p-value, adjusted p-value, and direction columns.
- Metabolomics tables: metabolite identifier/name, annotation level, m/z, retention time, group summaries, fold change, VIP/statistic, p-value, adjusted p-value, and pathway/class annotations.
- Peak/region tables: chromosome, start, end, peak/region identifier, score, annotation, nearest gene, fold change, p-value, adjusted p-value, and contrast columns.
- Network tables: source, target, interaction/edge type, weight/score, node attribute, module/community, and topology metric columns.

For every analysis section that links tables, the Markdown body should name the table path and describe only the table's analysis role, such as `该表记录细胞级元数据` or `该表记录配体-受体对层面的通讯概率和显著性`. The rendered preview for each linked table must show the relevant field descriptions below the opened table; the report body must not duplicate those field descriptions.

### 7. Lint

Run lint before rendering:

```bash
python omics-analysis-report/report_lint.py <report>.md \
  --asset-base <report-folder-or-results-root> \
  --figure-manifest <figure_manifest.tsv> \
  --strict-client-scope \
  --strict-references \
  --bad-pattern 客户 \
  --warnings-as-errors
```

This checks privacy, placeholders, raw HTML, missing images, figure captions, figure numbering, result sections without figures, scope-forbidden interpretation, manifest figure-type coverage, and method references.

Absolute-path privacy violations are hard errors. Do not bypass them; rewrite the report to relative paths.

### 8. Render

```bash
python omics-analysis-report/md_to_html.py <report>.md \
  -o Report.html \
  --asset-base <report-folder-or-results-root> \
  --strict-links
```

### 9. Compile Delivery Build

After the Markdown source has been reviewed, use the delivery compiler for HTML packages:

```bash
python omics-analysis-report/compile_delivery.py <report>.md \
  -o Report.html \
  --asset-base <report-folder-or-results-root> \
  --strict-links
```

Delivery builds keep the Markdown as the editable source and write `Report.html` plus a hashed asset bundle next to the delivery HTML. Compile in a temporary working directory; the hashed bundle is an intermediate, not an archive requirement. Prepare the final HTML under the Output Contract before packaging. The compiler renames the Luckysheet vendor path and entry files, conservatively minifies third-party CSS/JS, omits `.map` and sourcemap references by default, and obfuscates only the report template's own business JavaScript. Do not apply aggressive obfuscation to third-party libraries, and do not emit a decrypt/source-recovery artifact for delivery builds.

### 10. Independent Review

After drafting and linting, assign an independent subagent when subagents are available. Give it only the skill path, report path, figure manifest, and raw artifacts needed for review. Ask it to judge whether the report satisfies:

- delivery purpose: what was done, what exists, how to read figures, and how result files/tables correspond to analysis outputs;
- absolute filesystem paths are absent from Markdown, HTML, table preview manifests, figure/file links, captions, and delivery metadata; any `/Users/...`, `/private/...`, `/tmp/...`, `/share/...`, `/data/...`, `~/...`, Windows drive path, or UNC path is `BLOCKED`;
- molecular docking wording uses `对接评分最低（绝对值最大）` or `Vina 评分最低（绝对值最大）`; awkward expressions such as `评分最负`, `最负构象`, `结合能最负`, or `亲和力最负` are `BLOCKED`;
- molecular docking figures do not include standalone legend-only panels such as `PLIP.legend.*`; overall-pocket panels use `Viz/png/raw/overall_pocket/` rather than `Viz/png/legend/overall_pocket/`;
- no biology-direction interpretation;
- every figure type in the manifest is represented;
- every method subsection contains package/software names, method principle, concise method characteristic, actual reportable parameters/thresholds, and numeric literature citations; package-only method text, file inventory masquerading as methods, or output-only method prose is `BLOCKED`;
- every section directly involving differential/comparison/marker/differential-feature/module-trait/group-trait analysis explicitly states both `对照组` and `实验组` when such groups exist; missing control/experimental group labels in those sections is `BLOCKED`;
- enrichment sections do not misuse comparison wording; GO/KEGG/Reactome enrichment and GSEA sections may identify their input gene list/ranking, but wording such as `沿用差异表达对比设置`, `沿用差异表达分组`, or enrichment-section `对照组/实验组` labels is `BLOCKED`;
- sample information is presented through tables, not prose lists; enumerating sample IDs one by one in sentences is `BLOCKED`;
- method sections contain no result observations, result counts, top entries, selected modules, highest-qvalue statements, concrete result file paths, or output-file inventories; any result content in `## 2. 方法` is `BLOCKED`;
- for public processed data, method sections describe only the current project's source/sample handling and performed analyses; upstream base-calling/read-alignment/quantification copied from GEO/SRA/ArrayExpress/TCGA records, original articles, or sample processing notes is `BLOCKED` unless the report provides explicit evidence that the current project reprocessed raw reads;
- report body contains no meta-report, renderer, UI-instruction, self-limitation narration, missing-metadata narration, or result-log narration such as `报告重点说明`, `结果解读限定`, `渲染后`, `点击任一 TSV`, `右侧表格`, `HTML 报告`, `TSV 按钮`, `结果文件未记录`, `未保存`, `无法确认`, or `方法部分保留`;
- report body contains no reader/customer address terms or third-party operation guidance such as `客户`, `用户`, `使用者`, `读者`, `使用者可`, `用户可`, `后续可`, `建议`, `如需`, `可按...筛选`, `可导入`, `可载入`, `可在 R/Python/Excel/Cytoscape 中`, or similar instructions telling someone what to do;
- report body contains no table-field enumeration wording such as `字段`, `主要字段包括`, `字段说明`, `包含 ... 字段`, or `字段 Metrics 表示`; table field descriptions must exist only in the rendered table-preview field-description panel;
- all omics report bodies use direct bioinformatics method/result wording and do not include comment-like caveats or disclaimer phrasing such as `该描述仅反映`, `该分析仅作为`, `该结果仅用于`, `该图仅用于说明`, `仅供参考`, `不将...解释为`, `不直接解释为`, or `不代表...`; if present, the reviewer must return `BLOCKED` and require the sentence to be rewritten or removed;
- methods use official-documentation parameters, client-approved project parameters, and result-affecting analysis thresholds only; reportable QC thresholds such as `5 MAD`, `3 MAD`, and `pct_counts_mt > 8` must be present when used, while `Auto 工作流`, company-internal workflow names, private helper names, code paths, and company-internal custom parameter names must not be exposed in report prose;
- any report section containing single-cell cell-type or subtype annotation describes the correct order: clustering or subclustering first, marker/annotation evidence second, final cell-type or subtype naming third; subtype sections must identify the Leiden Cluster identifiers before the subtype labels and include an available Cluster -> subtype label mapping;
- any report section using the default single-cell integration workflow names and cites scVI/scvi-tools as the default batch-effect correction/integration method unless explicit run evidence shows a non-scVI branch;
- single-cell integration, clustering, UMAP, and annotation prose uses natural academic terminology; awkward direct translations such as `潜在表示`, `整合表示`, `低维潜在表示`, `scVI 整合后的潜在表示`, or `基于整合表示构建...` are `BLOCKED`; specialized concepts may be written as Chinese terms followed by English in parentheses, such as `低维细胞嵌入（cell embedding）`, `低维状态空间（latent space）`, or `邻近图（nearest-neighbor graph）`;
- when a section shows representative figures from a figure-rich folder, the report states the complete result folder path and how to find sibling files;
- representative figure-folder wording uses concise phrases such as `完整结果位于 ...`; redundant wording such as `完整同类型结果位于` or `同类型结果位于` is blocked;
- pySCENIC RSS/top regulon figures describe dot color as distinguishing top regulon identities/names and do not state that dot color, or dot color/size together, represents RSS value unless an explicit figure legend supports that encoding;
- for marker, differential, or feature-ranking outputs in any omics report, every existing split table is linked as a real relative TSV/CSV/XLS/XLSX path and can render as a right-side table preview chip, not merely summarized through one combined table example; this includes per-cluster, per-cell-type, per-subtype, per-group, per-contrast, per-pathway, per-regulon, per-module, per-taxon, per-metabolite-class, per-peak-set, and other analysis-unit tables; report prose and table headers use concrete output names such as `DEGs 表`, `DEGs_filter 表`, `Marker Genes 表`, `differential_abundance.tsv`, `differential_metabolites.tsv`, `peaks.tsv`, or exact filenames, not generic phrases such as `完整 marker/DEG 表`, `完整 marker/差异基因表`, `完整差异表`, or bare `过滤表`;
- every TSV/CSV/XLS/XLSX table linked from the report has field descriptions under the opened table preview; the table-preview panel is responsive across wide and narrow screens; the table-preview header keeps large-table/truncation messages behind a file-name helper marker using a short-delay custom popover instead of visible long status prose, native `title`, or CSS pseudo-element tooltip content; the popover avoids drawer/header clipping and viewport-edge occlusion; the field-description block is collapsible and vertically resizable through a dedicated horizontal drag handle; identical schemas may share descriptions, but the reviewer should block if any preview lacks field descriptions, lacks responsive panel behavior, lacks compact helper-based large-table messaging, lacks non-occluded custom helper behavior, lacks collapsible/drag-resizable behavior, or only shows an uninformative placeholder;
- multi-table result-entry lists are rendered as collapsible tables/groups instead of long prose lists; any report-body sentence or paragraph that introduces two or more TSV/CSV/XLS/XLSX paths in prose is `BLOCKED`;
- captions and result file descriptions are understandable;
- missing/unclear sections that require remediation.

Use this prompt shape:

```text
Use the omics-analysis-report skill at <skill-dir> to review <report.md/html> and <figure_manifest.tsv>. Judge whether this is acceptable as a bioinformatics result delivery report. Do not add biological interpretation. Treat any absolute filesystem path in Markdown, HTML, table manifests, figure/file links, captions, references, or delivery metadata, including `/Users/...`, `/private/...`, `/tmp/...`, `/share/...`, `/data/...`, `~/...`, Windows drive paths, or UNC paths, as a privacy-leaking BLOCKED issue that must be replaced with a relative path. Treat molecular docking wording such as `评分最负`, `最负构象`, `结合能最负`, or `亲和力最负` as BLOCKED; require `对接评分最低（绝对值最大）` or `Vina 评分最低（绝对值最大）`. Treat molecular docking figures that include standalone legend-only panels such as `PLIP.legend.*` or use `Viz/png/legend/overall_pocket/` instead of `Viz/png/raw/overall_pocket/` for the overall-pocket panel as BLOCKED. Treat method subsections that lack method principle, concise method characteristic, actual reportable parameters/thresholds, or numeric literature citations; method sections that contain result observations, result counts, top entries, selected modules, highest-qvalue statements, concrete result file paths, output-file inventories, or upstream public-database processing copied into methods; package-only method prose; file inventory masquerading as methods; any section directly involving differential/comparison/marker/differential-feature/module-trait/group-trait analysis that does not explicitly state both `对照组` and `实验组` when such groups exist; GO/KEGG/Reactome enrichment or GSEA sections that misuse comparison wording such as `沿用差异表达对比设置`, `沿用差异表达分组`, or enrichment-section `对照组/实验组` labels instead of only identifying the input gene list/ranking; public processed data methods that describe upstream base-calling/read-alignment/quantification from GEO/SRA/ArrayExpress/TCGA records or original articles without explicit evidence that the current project reprocessed raw reads; sample information written as prose sample-ID lists instead of Markdown tables; meta-report/renderer/UI/self-limitation narration in the report body, missing-metadata/result-log narration such as `结果文件未记录`, `未保存`, `无法确认`, or `方法部分保留`, reader/customer address terms or third-party action guidance such as `客户`, `用户`, `使用者`, `读者`, `使用者可`, `用户可`, `后续可`, `建议`, `如需`, `可按...筛选`, `可导入`, `可载入`, or `可在 R/Python/Excel/Cytoscape 中`, report-body table-field wording such as `字段`, `主要字段包括`, `字段说明`, `包含 ... 字段`, or `字段 Metrics 表示`, comment-like caveats or disclaimer phrasing in any omics module such as `该描述仅反映`, `该分析仅作为`, `该结果仅用于`, `该图仅用于说明`, `仅作为...指标使用`, `仅供参考`, `不将...解释为`, `不直接解释为`, or `不代表...`, company-internal workflow names or custom parameters such as `Auto 工作流`, private helper names, private code paths, raw internal flags, or code-internal parameter names, missing used QC thresholds such as `5 MAD`, `3 MAD`, or `pct_counts_mt > 8` in single-cell QC methods, redundant representative-folder wording such as `完整同类型结果位于`, `完整同类型图片位于`, or `同类型结果位于`, generic table descriptions such as `完整 marker/DEG 表`, `完整 marker/差异基因表`, `完整差异表`, or bare `过滤表` where concrete table names should be used, unacademic or unnatural single-cell integration/clustering wording such as `潜在表示`, `整合表示`, `低维潜在表示`, `scVI 整合后的潜在表示`, or `基于整合表示构建...` instead of academic phrasing such as `低维细胞嵌入（cell embedding）`, `低维状态空间（latent space）`, or `邻近图（nearest-neighbor graph）`, pySCENIC RSS/top regulon plot text that says dot color or dot color/size represents RSS value without an explicit numeric color-scale legend, missing field descriptions under any TSV/CSV/XLS/XLSX table preview, table-preview panels without responsive wide/narrow layouts, large-table/truncated-preview messages shown as long visible header status text, native `title` tooltip, CSS pseudo-element tooltip, or occluded/clipped popover instead of a file-name helper marker with a viewport-aware short-delay custom popover, field-description blocks that are not collapsible and vertically resizable through a dedicated drag handle, missing clustering-before-annotation order for any report section containing single-cell cell-type/subtype annotation, missing available Leiden Cluster -> subtype label mapping in such subtype sections, omitted scVI/scvi-tools batch-correction language in any report section using the default single-cell integration workflow without explicit evidence for a non-scVI branch, missing complete result-folder paths for representative figure families, missing per-unit/per-contrast marker, differential, or feature-ranking table preview links in any omics section where split result tables exist, multi-table result-entry lists that are not collapsible, or any prose sentence/paragraph that introduces two or more TSV/CSV/XLS/XLSX paths instead of using a Markdown table with columns such as `结果类型 / 表格 / 内容`, `分组 / 表格 / 内容`, or `Leiden Cluster / DEGs 表 / DEGs_filter 表`, as BLOCKED. Return PASS or BLOCKED, with concrete remediation items and file/section references. If comment-like caveat wording is found, require correction by rewriting it as a direct bioinformatics method/result statement or removing it; if table-field wording appears in the report body, require moving the field explanations to the table-preview field-description panel.
```

If the subagent returns `BLOCKED`, revise the report and repeat lint/review until the blocking items are resolved or a genuine missing-input blocker remains.

## Quality Gate

Do not claim completion until all are true:

- Report explains analyses performed, results produced, figure reading, and result file/table organization.
- Every standalone result module passes the admission gate: it contains at least one real interpretable biological-result or necessary QC/integration/validation figure type; figureless acquisition, checksum, conversion, provenance, field-audit, archive, and `go/no-go` steps appear only as concise method provenance and are absent from result-module/file inventories.
- Every method subsection after data/source collection names the software/package/database, explains the algorithm/statistical/scoring principle, gives a concise method characteristic, includes actual reportable parameters or thresholds, and cites the relevant package/method literature. Package-only method text and output-file inventory written as methods are blocked.
- Every required figure type in `figure_manifest.tsv` appears at least once in the Markdown.
- Every method/result section directly involving differential, comparison, marker, differential-feature, module-trait/group-trait, or other feature-ranking analysis explicitly states both `对照组` and `实验组` when such groups exist.
- Enrichment and GSEA sections identify their input gene list/ranking without describing the enrichment step as a group comparison or adding `对照组/实验组` labels.
- Sample information is displayed as Markdown tables. Sample IDs, retained/removed samples, sample groups, and cohort splits are not enumerated one by one in prose.
- Method sections contain no result observations, result counts, top result entries, selected modules, highest-qvalue statements, concrete result file paths, output-file inventories, or upstream public-database processing copied into methods. Methods describe how the current project analysis was run; results and file paths stay in `## 3`/`## 4` or sample-information tables.
- Report body contains no meta-report, renderer, UI-instruction, self-limitation narration, missing-metadata narration, or result-log narration; it should not discuss what the report is trying to do, what it refuses to interpret, HTML behavior, click behavior, buttons, sidebars, collapsibility, missing software versions, missing run parameters, unavailable metadata, or result-file/log provenance.
- Report body contains no reader/customer address terms or third-party operation guidance. It must not use wording such as `客户`, `用户`, `使用者`, `读者`, `使用者可`, `用户可`, `后续可`, `建议`, `如需`, `可按...筛选`, `可导入`, `可载入`, or `可在 R/Python/Excel/Cytoscape 中`.
- Report body contains no table-field wording. It must not include `字段`, `主要字段包括`, `字段说明`, `包含 ... 字段`, or similar field-enumeration sentences; table field descriptions belong only to the rendered table-preview field-description panel.
- Every omics report body contains no comment-like caveats or disclaimer phrasing. It should not use sentences such as `该描述仅反映...`, `该分析仅作为...`, `该结果仅用于...`, `该图仅用于说明...`, `仅作为...指标使用`, `仅供参考`, `不将...解释为...`, `不直接解释为...`, or `不代表...`; rewrite these as direct bioinformatics method/result statements or remove them.
- Method prose exposes only official-documentation parameters, client-approved project parameters, and result-affecting analysis thresholds. It must not mention internal workflow names such as `Auto 工作流`, company-internal custom parameter names, private helper names, private code paths, or raw internal flags. Used single-cell QC thresholds such as `5 MAD`, `3 MAD`, and `pct_counts_mt > 8` must be written in the QC method.
- Any report section containing single-cell cell-type or subtype annotation states clustering/subclustering before marker-based annotation and final label assignment. Subtype sections must name the Leiden Cluster identifiers first and include the available Cluster -> subtype label mapping.
- scVI/scvi-tools batch-effect correction/integration is named and cited by default in any report section using the default single-cell integration workflow unless explicit run evidence shows a non-scVI branch.
- Single-cell integration, clustering, UMAP, and annotation prose uses academic terminology. It must not use awkward direct translations such as `潜在表示`, `整合表示`, `低维潜在表示`, `scVI 整合后的潜在表示`, or `基于整合表示构建...`; use terms such as `批次校正后的低维细胞嵌入（cell embedding）`, `低维状态空间（latent space）`, and `邻近图（nearest-neighbor graph）` when English clarification is useful.
- Representative figure families state the complete result folder path for sibling files.
- Representative figure-folder wording is concise: write `完整结果位于 ...`, not `完整同类型结果位于 ...` or `同类型结果位于 ...`.
- pySCENIC RSS/top regulon figures describe dot color as distinguishing top regulon identities/names; do not state that point color or point color/size represents RSS value unless an explicit legend encodes that numeric variable.
- Marker, differential, and feature-ranking sections in any omics report link complete per-unit and per-contrast table paths when those files exist, and the strict HTML build exposes them as right-side table-preview chips. Report prose and table headers use concrete output names such as `Marker Genes 表`, `DEGs 表`, `DEGs_filter 表`, `differential_abundance.tsv`, `differential_metabolites.tsv`, `peaks.tsv`, or exact filenames; generic labels such as `完整 marker/DEG 表`, `完整 marker/差异基因表`, `完整差异表`, or bare `过滤表` are blocked when concrete table names exist.
- Every rendered table preview uses a responsive table-preview panel; large-table/truncation notes are exposed through a helper marker beside the file name with a viewport-aware short-delay custom popover, not long visible header status prose, native `title`, CSS pseudo-element tooltip content, or an occluded/clipped popover; each preview shows a collapsible, drag-resizable field-description block under the opened table; repeated schemas may share descriptions, but no linked TSV/CSV/XLS/XLSX table may be left without field explanations.
- Multi-table result-entry lists are collapsible in the rendered HTML, not long prose path lists. Any section that introduces two or more TSV/CSV/XLS/XLSX paths must use a Markdown table with explicit columns such as `结果类型 / 表格 / 内容`, `分组 / 表格 / 内容`, or `Leiden Cluster / DEGs 表 / DEGs_filter 表`.
- No result text makes mechanism, clinical, diagnostic, therapeutic, prognostic, or biology-direction claims.
- Molecular docking sections use `对接评分最低（绝对值最大）` or `Vina 评分最低（绝对值最大）`; wording such as `评分最负`, `最负构象`, `结合能最负`, or `亲和力最负` is blocked.
- Molecular docking figure panels exclude standalone legend-only images such as `PLIP.legend.*`, and overall-pocket panels use `Viz/png/raw/overall_pocket/` rather than `Viz/png/legend/overall_pocket/`.
- No absolute filesystem paths remain anywhere in the report source, rendered HTML, table preview manifests, figure/file links, captions, references, or delivery metadata; only relative paths are allowed.
- No internal paths, internal project IDs, unfilled placeholders, or raw HTML remain.
- Every figure path resolves and every image group has a `**图N.**` caption.
- Method order, result order, figure numbers, and figure manifest are mutually consistent.
- Every method software/package/database has relevant parameters, clickable superscript numeric body citations, and matching anchored GB/T 7714-2005 entries in `## 5. 参考文献`.
- Lint passes.
- Independent subagent review is `PASS`, or any remaining blocker is explicitly documented as missing input.
