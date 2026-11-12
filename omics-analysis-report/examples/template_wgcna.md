# [研究对象] 加权基因共表达网络分析报告

<!--
Template: WGCNA module + trait association
方法对应 methods-snippets.md "WGCNA" + "功能富集" 章节。
图对应 figure-catalog.md "WGCNA" + "功能富集" 区。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：表达矩阵来源、样本量、分组或性状信息
- 第二句：本报告覆盖的 WGCNA 输出图型（模块树、模块-性状热图、MM-GS 散点、富集图）
- 第三句：本报告将说明模块颜色、相关系数、p 值、kME 和 GS 如何读取
- 末尾：不对研究方向做数据展示范围之外的解释]

## 2. 方法

### 2.1 数据获取

[从 methods-snippets.md "2.1 数据获取" 选择对应变体]

### 2.2 表达数据预处理与基因筛选

[对应上游来源补充必要的预处理段落：TCGA → GDC + DESeq2 normalize；GEO → GEOquery + 探针注释；自有 RNA-seq → fastp+STAR+featureCounts]。为减少噪音并加快网络构建，对所有基因按方差排序保留 top [25%–50%] 或表达稳定的 top [N] 个基因作为 WGCNA 输入。

### 2.3 加权基因共表达网络构建

对样本 × 基因的归一化表达矩阵进行加权基因共表达网络分析 (WGCNA)。首先以样本层次聚类树识别可能的离群样本并进行剔除；其次基于无标度网络拓扑准则筛选最优 soft-threshold power β —— 选取使得 scale-free 拓扑拟合优度 R² 首次超过 [0.85] 的最小 β 值（对于样本数 n < 20 的小队列，回退至经验值 signed=18 / unsigned=9）。基于该 β 值构建邻接矩阵，转换为拓扑重叠矩阵 (Topological Overlap Matrix, TOM)；对 1-TOM 距离矩阵进行层次聚类，使用 dynamicTreeCut 动态混合树切割得到初始模块，并对模块特征基因 (Module Eigengene, ME) 相关性 > [0.75] (即 dissimilarity < 0.25) 的模块进行合并，最终得到稳定的共表达模块集合。

### 2.4 模块-性状关联与枢纽基因鉴定

将各模块特征基因 (ME) 与样本临床/表型变量 ([生存时间 / 分组 / 评分 / 影像学指标等]) 进行 Pearson 相关分析，得到模块-性状关联热图，使用相关系数与对应 p 值识别与目标性状显著相关的关键模块。在关键模块内基于基因模块内连接度 kME (Module Membership, 基因与模块 ME 的 Pearson 相关系数) 与基因-性状显著性 GS (Gene Significance) 的散点图 (verboseScatterplot) 鉴定枢纽基因 (hub genes)，筛选阈值为 |kME| > [0.8] 且 |GS| > [0.2]。

### 2.5 关键模块功能富集

[复用 methods-snippets.md "功能富集" 节，输入基因列表替换为关键模块基因。]

针对关键模块基因，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征分析。GO 富集通过 enrichGO() 函数对三大本体 (BP / CC / MF) 分别进行，基因背景设为 [org.Hs.eg.db / org.Mm.eg.db] 的全基因列表；KEGG 富集通过 enrichKEGG() 在线访问 KEGG 数据库 (organism='[hsa / mmu]') 完成。p 值校正使用 Benjamini-Hochberg 方法，富集显著性阈值定义为 pvalueCutoff=0.05 与 qvalueCutoff=0.2。

## 3. 结果

### 3.1 共表达模块识别

我们首先对 [N] 例样本的 top [N] 高方差基因进行加权基因共表达网络构建。基于无标度拓扑标准，选取 β=[数值] 作为 soft-threshold (scale-free R² = [数值])。基于 TOM 距离与 dynamicTreeCut，合并 ME 相关性 > 0.75 的模块后，最终得到 [N] 个稳定的共表达模块（图1）。模块大小从 [N min] 到 [N max] 不等，其中 grey 模块包含未能归入任何模块的剩余基因。

![](Figures/cluster_plot.png)

**图1.** 基因层次聚类树及对应的 WGCNA 共表达模块色带，下方色带表示初始模块切割结果与合并后的最终模块归属。

### 3.2 模块-性状相关性分析

在明确模块结构后，我们将各模块 ME 与样本临床/表型变量进行 Pearson 相关分析（图2）。其中 [模块颜色 1] 与 [性状 A] 呈显著正相关 (r=[数值], p=[数值])，[模块颜色 2] 与 [性状 B] 呈显著负相关 (r=[数值], p=[数值])。这些模块可在结果表中按相关系数绝对值和 p 值排序后继续查看。

![](Figures/trait_cor_heatmap.png)

**图2.** 各共表达模块特征基因 (ME) 与样本临床/分组性状的 Pearson 相关性热图，单元格内为相关系数 (上) 与对应 p 值 (下)，颜色表示相关系数的正负与强度。

### 3.3 模块成员关系与基因显著性分析

为定位关键模块内的核心调控基因，我们在 [关键模块颜色] 模块内绘制基因模块隶属度 (|kME|) 与基因-性状显著性 (|GS|) 的散点图（图3）。位于散点图右上区域 (|kME| > 0.8 且 |GS| > 0.2) 的基因被定义为枢纽基因 (hub genes)，本模块共鉴定 [N] 个枢纽基因，包括 [3–5 个代表性基因]。

![](Figures/Module_membership.verboseScatterplot.png)

**图3.** [关键模块颜色] 模块内基因的模块隶属度 (|kME|) 与基因显著性 (|GS|) 散点图，右上角为枢纽基因区，标注若干代表性基因。

### 3.4 模块基因功能富集分析

最后，我们对 [关键模块颜色] 模块全部基因进行 GO BP 与 KEGG 富集（图4）。GO BP 点图展示 [代表性 BP 条目 1–3] 的 GeneRatio、Count 与校正后显著性；KEGG 点图以相同方式展示 [代表性 KEGG 条目 1–3]。对应结果表记录富集条目、校正后显著性、富集比例和命中基因集合。

![](Figures/GO_BP.dotplot.png)
![](Figures/KEGG_dot.png)

**图4.** A：[关键模块颜色] 模块基因的 GO Biological Process 富集 top 通路点图；B：[关键模块颜色] 模块基因的 KEGG 通路富集 top 通路点图。

---

## 5. 参考文献

- [Langfelder2008WGCNA] Langfelder P, Horvath S. WGCNA: an R package for weighted correlation network analysis. BMC Bioinformatics. 2008. doi:10.1186/1471-2105-9-559.
- [Yu2012ClusterProfiler] Yu G, Wang LG, Han Y, He QY. clusterProfiler: an R package for comparing biological themes among gene clusters. OMICS. 2012. doi:10.1089/omi.2011.0118.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
