# TCGA-[癌型] 队列 [研究主题] 转录组分析报告

<!--
Template: TCGA cohort DE + 富集 (+ 可选生存)
方法对应 methods-snippets.md "TCGA 队列分析" + "功能富集" 章节。
图对应 figure-catalog.md "Bulk RNA-seq (+ GEO + TCGA DE)" + "功能富集" + "TCGA 流程特有图" 区。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：TCGA-[癌型] 队列的数据来源、样本类型与分组
- 第二句：本报告覆盖的分析模块（差异表达 / 富集 / GSEA / 可选生存曲线）
- 第三句：本报告将说明每类图和表如何查看与使用
- 末尾：不对数据展示范围之外的研究问题做结论]

## 2. 方法

### 2.1 数据获取

本研究使用的转录组与临床数据来自美国国家癌症研究所基因组数据共享平台 (GDC, https://portal.gdc.cancer.gov/) 的 The Cancer Genome Atlas (TCGA) 项目 [癌型缩写] 队列 ([TCGA-XXX])。通过 GDC API 下载该队列的 STAR-Counts mRNA 表达文件以及对应的样本信息表。配套临床数据（生存时间、状态、分期等）通过 cBioPortal 公共接口 (R 包 cBioPortalData) 获取。该队列共纳入 [N] 例样本，其中肿瘤组织 [N1] 例、配对/未配对正常组织 [N2] 例。

### 2.2 TCGA 表达数据预处理

基于 GDC manifest 与样本表 (sample sheet) 整合各样本表达文件，构建样本 × 基因的原始 count 矩阵；通过 TCGA 标准条形码前 16 位 (TCGA-XX-XXXX-01 / TCGA-XX-XXXX-11) 区分肿瘤样本与配对正常对照。

### 2.3 临床表型数据获取

通过 cBioPortal 公共接口 (R 包 cBioPortalData) 下载 TCGA-[癌型] (cBioPortal studyId: [studyId]) 队列的临床数据表，包括生存时间 (OS_MONTHS)、生存状态 (OS_STATUS)、肿瘤分期 (AJCC stage)、年龄和性别等信息。临床数据与表达矩阵基于 TCGA 患者编号 (前 12 位 barcode) 进行匹配。

### 2.4 差异表达分析

基于 TCGA-[癌型] 表达矩阵，以肿瘤 (Tumor) / 正常 (Normal) 为分组变量构建 DESeq2 模型，使用 DESeq() 完成离散度估计与 Wald 检验，得到肿瘤 vs 正常的差异基因。差异基因筛选阈值为 |log2FoldChange| > [1] 且 padj < [0.05]。

### 2.5 功能富集分析

[复用 methods-snippets.md "GO / KEGG 富集分析 (ORA)" 与 "GSEA 基因集富集分析" 段落。]

针对显著差异基因列表，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征分析；并对全基因 log2FoldChange 排序列表进行 GSEA (gseGO / gseKEGG, minGSSize=10, maxGSSize=500, pvalueCutoff=0.25, nPermSimple=10000)。

### 2.6 生存关联分析 (可选)

[若包含生存分析] 基于关键基因表达量按中位值划分高/低表达组，使用 R 包 survival 的 survfit() 函数拟合 Kaplan-Meier 生存曲线，使用 survdiff() 进行对数秩检验 (log-rank test) 评估两组生存差异；使用 survminer::ggsurvplot 绘制 KM 曲线及风险表。多变量 Cox 回归 (coxph) 用于在临床协变量调整后评估关键基因的独立生存预测价值。

## 3. 结果

### 3.1 差异表达分析

我们首先对 TCGA-[癌型] 队列 [N1] 例肿瘤组织与 [N2] 例正常组织进行差异表达分析。共鉴定 [N] 个显著差异基因 (|log2FC| > 1, padj < 0.05)，其中肿瘤组织中上调 [N up] 个、下调 [N down] 个（图1A）。Top 差异基因 ([列出 3–5 个]) 在肿瘤与正常组织间呈现清晰的表达分层（图1B）。

![](Figures/Volcano.png)
![](Figures/heatmap.png)

**图1.** A：TCGA-[癌型] 肿瘤 vs 正常组织差异表达分析火山图，横轴为 log2FoldChange，纵轴为 -log10(padj)，红/蓝点表示显著上/下调基因；B：top [N] 差异基因在所有样本中的 z-score 标准化表达热图。

### 3.2 GO/KEGG 富集分析

在明确肿瘤 vs 正常组织的差异基因后，我们进一步对差异基因进行 GO/KEGG 富集（图2）。GO BP 点图展示 [代表性 BP 条目 1–3] 的 GeneRatio、Count 与校正后显著性；KEGG 点图以相同方式展示 [代表性 KEGG 条目 1–3]。对应结果表记录富集条目、校正后显著性、富集比例和命中基因集合。

![](Figures/GO_BP.dotplot.png)
![](Figures/KEGG_dot.png)

**图2.** A：差异基因 GO Biological Process 富集 top 通路点图；B：差异基因 KEGG 通路富集 top 通路点图。

### 3.3 GSEA 富集分析

为补充 ORA 分析，我们对全基因 log2FoldChange 排序列表进行 GSEA。Top [5] NES > 0 条目与 top [5] NES < 0 条目见图3。[关键观察句，例如"[通路 X] 的 NES=[数值], padj=[数值]，在 NES > 0 条目中排序靠前"]。

![](Figures/GSEA_activate.top5.png)
![](Figures/GSEA_inhibit.top5.png)

**图3.** A：基于差异表达基因 log2FoldChange 排序列表的 KEGG GSEA top 5 激活通路 (NES > 0) 富集得分曲线；B：top 5 抑制通路 (NES < 0) 富集得分曲线。

### 3.4 Kaplan-Meier 生存分析 (可选 - 仅在生存分析存在时保留)

若项目包含生存曲线，本节仅说明图表读法和统计输出。TCGA-[癌型] 队列基于 [关键基因] 表达中位值划分为高/低表达两组，Kaplan-Meier 曲线展示两组 OS 时间分布（图4）。图中 p 值来自对数秩检验，风险表显示各时间点仍处于风险集中的样本数；不要据此扩展为数据展示范围之外的应用结论。

![](Figures/KM.gene.png)

**图4.** [关键基因] 高/低表达组在 TCGA-[癌型] 队列中的 Kaplan-Meier 总生存曲线，对数秩检验 p=[数值]。下方风险表显示各时间点处仍处于风险中的样本数。

---

## 5. 参考文献

- [Jensen2017GDC] Jensen MA et al. The NCI Genomic Data Commons as an engine for precision medicine. Blood. 2017. doi:10.1182/blood-2017-03-735654.
- [Ramos2020cBioPortalData] Ramos M et al. Multiomic Integration of Public Oncology Databases in Bioconductor. JCO Clinical Cancer Informatics. 2020. doi:10.1200/CCI.19.00119.
- [Love2014DESeq2] Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. Genome Biology. 2014. doi:10.1186/s13059-014-0550-8.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
