# [研究对象] 竞争性内源 RNA (ceRNA) 网络分析报告

<!--
Template: lncRNA / circRNA – miRNA – mRNA ceRNA 网络
方法对应 methods-snippets.md "ceRNA 网络分析" + "Bulk RNA-seq" + "GEO" + "功能富集" 章节。
图对应 figure-catalog.md "ceRNA 网络" + "Bulk RNA-seq (+ GEO + TCGA DE)" + "功能富集" 区。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：数据来源、样本量、分组和 RNA 类型
- 第二句：本报告覆盖的 ceRNA 输出图型（差异表达、数据库交集、网络、表达相关性、富集图）
- 第三句：本报告将说明每类图表怎么看以及网络/表格如何使用
- 末尾：不对研究方向做数据展示范围之外的解释]

## 2. 方法

### 2.1 数据获取

[根据数据来源选择 methods-snippets.md "2.1 数据获取" 的 GEO/TCGA/委托数据变体。]

### 2.2 差异表达分析

[选用 DESeq2 (count-based) 或 limma (GEO probe-based)，分别得到差异 mRNA、差异 lncRNA、差异 miRNA 三类列表。每类筛选阈值见对应章节。]

差异 lncRNA / circRNA / mRNA：|log2FC| > [1] 且 padj < [0.05]；差异 miRNA：|log2FC| > [1] 且 padj < [0.05]（miRNA 检测灵敏度较低时可适当放宽至 P.Value < 0.05）。

### 2.3 miRNA 靶基因预测

差异表达 miRNA 与潜在 lncRNA / circRNA / mRNA 靶基因关系通过 starBase / ENCORI 数据库 (https://rnasysu.com/encori/) 在线 API 进行预测。对每个查询 miRNA，提取该数据库整合的 CLIP-seq 实验支持的 miRNA-mRNA 与 miRNA-lncRNA 互作对；筛选至少被 [k≥3] 个独立预测工具支持的高置信靶基因。

### 2.4 ceRNA 网络构建

基于"lncRNA / circRNA 通过竞争性结合共同 miRNA 调控 mRNA 表达"的 ceRNA 假说，将差异表达的 lncRNA / circRNA、miRNA 与 mRNA 三层节点按以下规则连边：(1) miRNA 与 mRNA 之间的边来自 2.3 miRNA 靶基因预测；(2) lncRNA / circRNA 与 miRNA 之间的边同样来自 starBase 整合的预测；(3) 同时保留 lncRNA-mRNA 表达呈正相关（Pearson r > [0.3], p < 0.05）且与共同 miRNA 表达呈负相关 (r < -[0.3]) 的 ceRNA 三元组。最终网络使用 Cytoscape 进行可视化与拓扑分析。

### 2.5 靶基因功能富集

[复用 methods-snippets.md "GO / KEGG 富集分析 (ORA)"，输入基因列表为最终 ceRNA 网络中的 mRNA 集合。]

针对最终 ceRNA 网络中的 mRNA 集合，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征分析。

## 3. 结果

### 3.1 差异表达分析

我们首先对 [实验组] vs [对照组] 在 mRNA、lncRNA 与 miRNA 三个层面进行差异表达分析。最终鉴定 [N mRNA] 个差异 mRNA、[N lnc] 个差异 lncRNA 与 [N mi] 个差异 miRNA（图1）。

![](Figures/Volcano.png)
![](Figures/heatmap.png)

**图1.** A：[实验组] vs [对照组] mRNA / lncRNA / miRNA 差异表达火山图；B：top 差异 ncRNA + mRNA 表达热图。

### 3.2 miRNA 靶基因预测

在差异表达基因鉴定的基础上，我们对差异 miRNA 进行靶基因预测。基于 starBase / ENCORI 数据库中至少 [k≥3] 个工具支持的高置信关系，共得到 miRNA-mRNA 互作对 [N1] 个、miRNA-lncRNA 互作对 [N2] 个（图2）。

![](Figures/miRNA_target.venn.png)

**图2.** 差异 miRNA 在 starBase / ENCORI 不同预测工具间共有的高置信靶基因 Venn 图，阴影部分为本研究后续纳入网络的高置信靶基因集合。

### 3.3 ceRNA 网络分析

在 miRNA-基因互作预测的基础上，叠加 lncRNA-mRNA 表达正相关 (r > 0.3) 与 lncRNA-miRNA / miRNA-mRNA 表达负相关 (r < -0.3) 约束，最终构建得到 ceRNA 网络（图3）。网络共包含 [N lnc] 个 lncRNA、[N mi] 个 miRNA 与 [N m] 个 mRNA，连接构成 [N triplet] 个 ceRNA 三元组。

![](Figures/ceRNA_network.png)

**图3.** ceRNA 网络示意图：以差异 miRNA 为连接节点，展示 lncRNA / circRNA、miRNA 与 mRNA 三类节点之间的数据库预测和表达相关性连接；节点颜色按 RNA 类型区分（紫：lncRNA / circRNA；蓝：miRNA；橙：mRNA）。

### 3.4 ceRNA 三元组表达相关性分析

在网络层面之外，我们进一步对核心三元组 [lnc 名]–[mir 名]–[mrna 名] 进行表达相关性展示（图4A）。lnc 与 mrna 表达呈正相关 (r=[数值], p=[数值])，二者与共同 miRNA 表达呈负相关 (lnc-mir r=[数值]; mir-mrna r=[数值])。mRNA 集合的 KEGG 富集点图展示 [代表性 KEGG 条目] 的 GeneRatio、Count 与校正后显著性（图4B）。

![](Figures/ceRNA_triplet.scatter.png)
![](Figures/KEGG_dot.png)

**图4.** A：核心 ceRNA 三元组 [lnc]–[mir]–[mrna] 表达散点图，展示三者之间的协同表达趋势；B：ceRNA 网络 mRNA 集合 KEGG 通路富集 top 通路点图。

---

## 5. 参考文献

- [Li2014StarBase] Li JH et al. starBase v2.0: decoding miRNA-ceRNA, miRNA-ncRNA and protein-RNA interaction networks. Nucleic Acids Research. 2014. doi:10.1093/nar/gkt1248.
- [Shannon2003Cytoscape] Shannon P et al. Cytoscape: a software environment for integrated models of biomolecular interaction networks. Genome Research. 2003. doi:10.1101/gr.1239303.
- [Yu2012ClusterProfiler] Yu G, Wang LG, Han Y, He QY. clusterProfiler: an R package for comparing biological themes among gene clusters. OMICS. 2012. doi:10.1089/omi.2011.0118.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
