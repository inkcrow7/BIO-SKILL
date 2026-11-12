# [研究对象] [实验组] vs [对照组] 转录组差异表达分析报告

<!--
Template: Bulk RNA-seq DEG + 富集 (DESeq2 / limma + clusterProfiler)
方法对应 methods-snippets.md "Bulk RNA-seq" + "功能富集" 章节。
图对应 figure-catalog.md "Bulk RNA-seq (+ GEO + TCGA DE)" + "功能富集" 区。
-->

## 1. 背景

[3–6 句话；末句给出总体目标：展示 [实验组] vs [对照组] 的差异表达、富集、GSEA 输出结果，并说明每类图表和结果表如何查看与使用。不要写超出数据展示范围的研究方向解释。]

## 2. 方法

### 2.1 数据获取

[从 methods-snippets.md "2.1 数据获取" 选择 Variant A (公共数据库) 或 Variant D (委托测序)]

### 2.2 原始数据预处理与基因定量

[Variant A — nf-core/rnaseq] 原始测序数据使用 nf-core/rnaseq v3.22.2 自动化流程进行处理。流程依次执行：(1) fastp 接头剪切与低质量碱基过滤；(2) STAR 比对至 [Ensembl Homo_sapiens.GRCh38 / Mus_musculus.GRCm39]；(3) Salmon 在 quasi-mapping 模式下进行转录本与基因水平 TPM 定量；(4) MultiQC 汇总各步骤的质量报告。最终得到样本 × 基因的原始 count 矩阵与 TPM 矩阵用于下游分析。

[或 Variant B — 自研 fastp + STAR] 原始测序数据使用 fastp 进行接头剪切与低质量碱基过滤 (默认参数)，过滤后的 clean reads 使用 STAR 比对至 [参考基因组及版本]。比对得到的 BAM 文件使用 featureCounts 基于 [GTF 注释文件] 进行基因水平 reads 计数，并计算 TPM / FPKM 表达量。

### 2.3 表达谱质控与样本概览

为评估样本测序质量与组间分离度，对 log2(CPM+1) 归一化后的表达矩阵进行整体可视化：(1) 各样本表达分布箱式图，用于检测异常样本与系统偏差；(2) 样本间 Pearson 相关性热图，反映样本一致性；(3) 主成分分析 (PCA) 散点图，基于前两个主成分检查样本在组别上的分离度。[若组间分离明显受批次或文库制备时间影响，使用 limma::removeBatchEffect 或 sva::ComBat 在差异分析模型中进行批次校正]。

### 2.4 差异表达分析

[选用 DESeq2 (count-based) 或 limma (voom/微阵列)]

差异表达分析使用 R 包 DESeq2 进行。以原始 count 矩阵为输入，构建包含分组 (及必要协变量) 的设计矩阵，使用 DESeq() 函数完成大小因子估计、基因离散度估计与基于负二项分布的 Wald 检验，得到 [实验组] vs [对照组] 的差异表达结果。差异基因 (DEGs) 筛选阈值定义为 |log2FoldChange| > [1] (即 fold change > 2) 且 padj < [0.05]。

### 2.5 GO / KEGG 富集分析

针对显著差异基因 (DEGs) 列表，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征 (over-representation) 分析。GO 富集通过 enrichGO() 函数对三大本体 (BP / CC / MF) 分别进行，基因背景设为 [org.Hs.eg.db / org.Mm.eg.db] 的全基因列表；KEGG 富集通过 enrichKEGG() 在线访问 KEGG 数据库 (organism='[hsa / mmu]') 完成。p 值校正使用 Benjamini-Hochberg 方法，富集显著性阈值定义为 pvalueCutoff=0.05 与 qvalueCutoff=0.2。富集结果以 dotplot 与 emapplot (enrichplot::pairwise_termsim 后构建术语-术语网络) 可视化。

### 2.6 基因集富集分析 (GSEA)

为捕捉差异表达分析中"亚显著但协同变化"的功能信号，对差异分析得到的全基因 log2FoldChange 排序列表进行基因集富集分析 (Gene Set Enrichment Analysis, GSEA)。使用 R 包 clusterProfiler 的 gseGO() 与 gseKEGG() 函数（minGSSize=10, maxGSSize=500, pvalueCutoff=0.25, nPermSimple=10000），分别基于 GO 与 KEGG 基因集进行富集。富集结果以归一化富集得分 (Normalized Enrichment Score, NES) 与 padj 进行排序，使用 enrichplot::gseaplot2 绘制 top [5] 激活与 top [5] 抑制通路的 running enrichment 图。

## 3. 结果

### 3.1 样本质控与表达谱概览

我们首先对 [N] 例样本的全基因表达谱进行整体质控与降维。各样本 log2(CPM+1) 表达分布相对一致（图1A），未发现异常样本。PCA 分析显示 [实验组] 与 [对照组] 在 PC1 (解释 [X%] 方差) 上呈现明显的组间分离（图1B），说明两组样本在整体表达矩阵上可被区分。

![](Figures/QC_boxplot.png)
![](Figures/PCA.png)

**图1.** A：各样本 log2(CPM+1) 表达分布箱线图；B：基于全基因表达谱的样本主成分分析 (PCA) 散点图，颜色表示分组。

### 3.2 差异表达分析

在确认样本质量后，我们使用 DESeq2 对 [实验组] vs [对照组] 进行差异表达分析（|log2FC| > 1, padj < 0.05），共鉴定 [N] 个显著差异基因，其中 [N1] 个上调、[N2] 个下调（图2A）。Top 差异基因 [列出 3–5 个] 在两组样本间呈现清晰的表达分层（图2B）。

![](Figures/Volcano.png)
![](Figures/heatmap.png)

**图2.** A：[实验组] vs [对照组] 差异表达分析火山图，横轴为 log2FoldChange，纵轴为 -log10(padj)，红/蓝点分别表示显著上调/下调基因，标注 top [N] 个最显著差异基因；B：top [50] 差异基因在所有样本中的 z-score 标准化表达热图。

### 3.3 GO/KEGG 富集分析

我们进一步对差异基因进行 GO/KEGG 富集分析。GO Biological Process 点图展示 [代表性 BP 条目 1–3] 的 GeneRatio、Count 与校正后显著性（图3A）；KEGG 点图以相同方式展示 [代表性 KEGG 条目 1–3]（图3B）。对应结果表记录富集条目、校正后显著性、富集比例和命中基因集合。

![](Figures/GO_BP.dotplot.png)
![](Figures/KEGG_dot.png)

**图3.** A：差异基因的 GO Biological Process 富集 top 通路点图（颜色表示 -log10(padj)、点大小表示富集基因数）；B：差异基因的 KEGG 通路富集 top 通路点图。

### 3.4 GSEA 富集分析

为展示全基因排序列表上的富集曲线，对差异分析得到的 log2FoldChange 排序结果进行 GSEA。Top [5] NES > 0 条目与 top [5] NES < 0 条目见图4。[关键观察句，例如"[通路 X] 的 NES=[数值], padj=[数值]，在 NES > 0 条目中排序靠前；[通路 Y] 的 NES=[数值]，在 NES < 0 条目中排序靠前"]。

![](Figures/GSEA_activate.top5.png)
![](Figures/GSEA_inhibit.top5.png)

**图4.** A：基于差异表达基因 log2FoldChange 排序列表的 KEGG GSEA top 5 激活通路 (NES > 0) 富集得分曲线；B：top 5 抑制通路 (NES < 0) 富集得分曲线。

---

## 5. 参考文献

- [Love2014DESeq2] Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. Genome Biology. 2014. doi:10.1186/s13059-014-0550-8.
- [Ritchie2015Limma] Ritchie ME et al. limma powers differential expression analyses for RNA-sequencing and microarray studies. Nucleic Acids Research. 2015. doi:10.1093/nar/gkv007.
- [Yu2012ClusterProfiler] Yu G, Wang LG, Han Y, He QY. clusterProfiler: an R package for comparing biological themes among gene clusters. OMICS. 2012. doi:10.1089/omi.2011.0118.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
