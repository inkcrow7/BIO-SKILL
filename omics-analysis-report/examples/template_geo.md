# [GSE 编号] [组织/疾病] 转录组差异分析报告

<!--
Template: GEO 公共数据集 DE + 富集 (limma + clusterProfiler)
方法对应 methods-snippets.md "GEO 公共转录组数据集" + "功能富集" 章节。
图对应 figure-catalog.md "Bulk RNA-seq (+ GEO + TCGA DE)" + "GEO 流程特有图" + "功能富集" 区。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：GEO 数据集 [GSExxxxxx] 的来源、平台、样本量和分组
- 第二句：本报告覆盖的分析模块（探针注释、批次处理、差异表达、富集、GSEA）
- 第三句：本报告将说明每类图表怎么看以及结果表如何筛选使用
- 末尾：不对研究方向做数据展示范围之外的解释]

## 2. 方法

### 2.1 数据获取

本研究使用的转录组数据来自基因表达综合数据库 (Gene Expression Omnibus, GEO) 的 [GSExxxxxx] 数据集 (平台 [GPLxxxx])。通过 R 包 GEOquery 下载该数据集的 series matrix 文件并解析样本表型 (pData)，得到 [N] 例样本的探针水平表达矩阵。该数据集共包含 [N1] 例 [实验组] 与 [N2] 例 [对照组]，样本类型为 [组织/血液/细胞系]。

### 2.2 GEO 数据下载与探针注释

使用 R 包 GEOquery 的 getGEO() 函数（getGPL=FALSE, AnnotGPL=FALSE）下载 [GSExxxxxx] 数据集的 series matrix 文件，得到样本 × 探针的表达矩阵及 phenoData (样本表型信息)。基于该数据集所在测序平台 ([GPLxxxx]) 的注释文件，将探针 ID 映射至基因 symbol；一对多探针保留平均表达最高的探针；对照 phenoData 信息重构样本分组标签 ([gp1] / [gp2])。

### 2.3 批次效应处理 (按需保留)

[如该数据集 phenoData 显式记录批次：] 针对样本表型中显式记录批次的情形（不同 batch / 不同测序时间），使用 limma::removeBatchEffect 在保留分组结构 (design = ~group) 的前提下移除 batch 项的贡献，并以批次校正前 / 后的样本箱式图与 PCA 评估去批次效果。[若无批次，删除整段]

### 2.4 差异表达分析

差异表达分析使用 R 包 limma。基于探针注释后的表达矩阵与分组信息构建设计矩阵，使用 lmFit() + eBayes() 进行经验贝叶斯线性模型拟合，对每组比较 ([gp1] vs [gp2]) 调用 topTable(adjust.method='fdr') 输出 logFC、P.Value 及 adj.P.Val。差异基因 (DEGs) 筛选阈值定义为 |log2FC| > [1] 且 [adj.P.Val / P.Value] < [0.05]。

### 2.5 GO / KEGG 富集分析

针对显著差异基因 (DEGs) 列表，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征分析。GO 富集通过 enrichGO() 函数对三大本体 (BP / CC / MF) 分别进行，基因背景设为 [org.Hs.eg.db / org.Mm.eg.db] 的全基因列表；KEGG 富集通过 enrichKEGG() 在线访问 KEGG 数据库 (organism='[hsa / mmu]') 完成。p 值校正使用 Benjamini-Hochberg 方法，富集显著性阈值定义为 pvalueCutoff=0.05 与 qvalueCutoff=0.2。

### 2.6 基因集富集分析 (GSEA)

为捕捉差异表达分析中"亚显著但协同变化"的功能信号，对全基因 log2FC 排序列表进行基因集富集分析 (GSEA)。使用 R 包 clusterProfiler 的 gseGO() 与 gseKEGG() 函数（minGSSize=10, maxGSSize=500, pvalueCutoff=0.25, nPermSimple=10000），分别基于 GO 与 KEGG 基因集进行富集。

## 3. 结果

### 3.1 样本质控与表达谱概览

我们首先对 [GSExxxxxx] 数据集 [N] 例样本的探针水平表达分布进行整体检查（图1A）。[去批次前后图，若有：] [如不一致：] 经 limma::removeBatchEffect 处理后，各样本表达分布趋于一致（图1B），适合后续差异分析。

![](Figures/QC_boxplot.png)
![](Figures/rmB.QC_boxplot.png)

**图1.** A：[GSExxxxxx] 全部样本探针表达分布箱线图（去批次前）；B：limma::removeBatchEffect 处理后各样本表达分布。[如无批次校正，仅保留 A]

### 3.2 差异表达分析

使用 limma 对 [gp1] vs [gp2] 进行差异表达分析（|log2FC| > 1, adj.P.Val < 0.05），共鉴定 [N] 个显著差异基因，其中 [N up] 个上调、[N down] 个下调（图2A）。Top 差异基因 [列出 3–5 个] 在两组样本间呈现清晰的表达分层（图2B）。

![](Figures/Volcano.png)
![](Figures/heatmap.png)

**图2.** A：[GSExxxxxx] [gp1] vs [gp2] 差异表达分析火山图，横轴为 log2FC，纵轴为 -log10(adj.P.Val)，红/蓝点表示显著上/下调基因；B：top [N] 差异基因在所有样本中的 z-score 标准化表达热图。

### 3.3 GO/KEGG 富集分析

我们进一步对差异基因进行 GO/KEGG 富集（图3）。GO BP 点图展示 [代表性 BP 条目 1–3] 的 GeneRatio、Count 与校正后显著性；KEGG 点图以相同方式展示 [代表性 KEGG 条目 1–3]。对应结果表记录富集条目、校正后显著性、富集比例和命中基因集合。

![](Figures/GO_BP.dotplot.png)
![](Figures/KEGG_dot.png)

**图3.** A：差异基因 GO Biological Process 富集 top 通路点图；B：差异基因 KEGG 通路富集 top 通路点图。

### 3.4 GSEA 富集分析

最后，对全基因 log2FC 排序列表进行 GSEA。Top [5] NES > 0 条目与 top [5] NES < 0 条目见图4。[关键观察句，例如"[通路 X] 的 NES=[数值], padj=[数值]，在 NES > 0 条目中排序靠前"]。

![](Figures/GSEA_GO.png)
![](Figures/GSEA_KEGG.png)

**图4.** A：基于差异表达基因 log2FC 排序列表的 GO GSEA top 通路富集得分曲线；B：KEGG GSEA top 通路富集得分曲线。

---

## 5. 参考文献

- [Davis2007GEOquery] Davis S, Meltzer PS. GEOquery: a bridge between the Gene Expression Omnibus and BioConductor. Bioinformatics. 2007. doi:10.1093/bioinformatics/btm254.
- [Ritchie2015Limma] Ritchie ME et al. limma powers differential expression analyses for RNA-sequencing and microarray studies. Nucleic Acids Research. 2015. doi:10.1093/nar/gkv007.
- [Yu2012ClusterProfiler] Yu G, Wang LG, Han Y, He QY. clusterProfiler: an R package for comparing biological themes among gene clusters. OMICS. 2012. doi:10.1089/omi.2011.0118.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
