# [研究对象] 单细胞转录组分析报告

<!--
Template: scRNA-seq (Scanpy + scType + pySCENIC)
方法对应 methods-snippets.md 的 scRNA-seq 章节。
图对应 figure-catalog.md 的 scRNA-seq A–F 区。
不要在交付前保留 HTML 注释；report_lint.py 会以 warning 提示。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：单细胞数据来源、样本数量、分组与组织来源
- 第二句：本报告覆盖的分析模块（质控、聚类注释、组成、marker、可选调控评分等）
- 第三句：本报告将说明每类图表怎么看以及 AnnData/表格/图片如何使用
- 末尾：不对研究方向做机制、疾病意义或应用价值解读]

## 2. 方法

### 2.1 数据获取

[从 methods-snippets.md "2.1 数据获取" 选择合适变体；公共数据/委托测序/混合多来源]

### 2.2 原始测序数据处理

10X Genomics 测序得到的原始 fastq 数据使用 Cell Ranger ([版本号]) 对参考基因组 [refdata-gex-GRCh38-2024-A / refdata-gex-GRCm39-2024-A] 进行 reads 比对、UMI 去重及细胞条形码识别，得到每个样本的 filtered_feature_bc_matrix 表达矩阵。

### 2.3 数据预处理与细胞质控

各样本 filtered_feature_bc_matrix 表达矩阵使用 Scanpy [版本号] 与 GPU 加速实现 rapids_singlecell 进行后续处理。每个细胞通过 Scanpy calculate_qc_metrics 计算检测基因数 (n_genes_by_counts)、总 UMI 数 (total_counts)、线粒体基因表达比例 (pct_counts_mt)、血红蛋白基因比例 (pct_counts_hb)、核糖体基因比例 (pct_counts_ribo)、percent_top=20 对应的 top20 高表达基因占比，以及 log1p 转换后的计数指标。采用基于中位数绝对偏差 (Median Absolute Deviation, MAD) 的稳健异常值检测策略，对 log1p(total_counts)、log1p(n_genes_by_counts) 及 top20 基因占比偏离样本中位数达到 5 MAD 的细胞、以及 pct_counts_mt 偏离中位数达到 3 MAD 或 pct_counts_mt > 8 的细胞进行过滤。在此基础上，使用 Scrublet 算法按样本分别进行潜在双细胞预测，并去除 predicted_doublet 为真的细胞。归一化采用总表达量缩放至每细胞 1×10⁴ 后进行 log1p 变换，最终得到用于下游分析的高质量单细胞表达矩阵。

### 2.4 scVI 批次效应校正与整合

质控后的单细胞表达矩阵使用 scVI/scvi-tools 进行样本批次效应校正，并构建批次校正后的低维细胞嵌入（cell embedding）。该低维细胞嵌入矩阵用于后续邻近图构建、Leiden 聚类、UMAP 投影和细胞类型注释。若项目参数中包含 batch key、嵌入维度、模型结构或训练轮数，可在此句后补充实际参数；未能确认的参数不写入正文。

### 2.5 高变基因鉴定、降维与聚类

基于归一化表达矩阵，使用 Scanpy 的 highly_variable_genes 函数（flavor='seurat_v3'）鉴定 top [3000] 个高变基因 (HVG)。以高变基因子集作为输入，进行标准化 (scale)、主成分分析 (PCA, n_comps=50) 降维，用于表达矩阵降维概览和质控检查。邻近图（nearest-neighbor graph）默认基于 scVI 校正后的低维细胞嵌入构建，例如 `sc.pp.neighbors(..., use_rep='X_scVI')`；只有在项目明确未使用 scVI 时，才改为报告实际使用的 PCA/Harmony/BBKNN/Scanorama 等嵌入或降维结果。基于批次校正后的低维细胞嵌入构建细胞 K 最近邻图 (k=[15])，采用 Leiden 算法（分辨率 resolution=[0.8]）进行图聚类，并以 UMAP (min_dist=[0.3]) 算法投影至二维空间用于可视化。

### 2.6 细胞类型注释

细胞类型注释在 Leiden 聚类结果基础上进行。scType 以 ScTypeDB 数据库中 [人 / 小鼠] [组织名] 的细胞类型-标志基因列表为先验，对每个细胞计算其在各候选细胞类型上的特异性表达评分；对每个 Leiden cluster 取细胞累加评分最高的细胞类型作为该 cluster 的注释结果。当某 cluster 的最高得分低于 cluster 内细胞数的 1/4 时，标注为 "Unknown" 以反映置信度不足。最终在 UMAP 上以颜色区分细胞类型，并使用 Scanpy 的 rank_genes_groups（method='wilcoxon'）输出各细胞类型的特异性差异表达基因列表用于注释验证。

### 2.7 细胞组成与组织偏好分析

为定量评估各细胞类型在不同组/样本间的相对丰度差异，对每个细胞类型计算其在各分组中的细胞计数及百分比，使用堆叠柱状图与百分比柱状图进行展示。进一步采用 Ro/e (Ratio of observed to expected) 指标量化细胞类型对样本/组织来源的偏好性：以卡方检验四格表得到的"实际细胞数 / 期望细胞数"作为偏好度，使用热图可视化各细胞类型 × 各组织来源的 Ro/e 值。

### 2.8 细胞亚型注释

从总体细胞注释结果中提取 [父细胞类型] 子集后，在该子集内重新构建邻近图并进行 Leiden 分群，得到 [Cluster0-ClusterN / res_*]。随后以每个 Leiden Cluster 为注释单位，结合 Cluster marker 基因、亚型 marker 表和人工整理注释，将各 Cluster 注释为 [亚型1-亚型N]。若细胞元数据同时包含 Cluster 列和亚型标签列，应写明对应关系，例如 `Cluster0 -> [亚型1]`、`Cluster1 -> [亚型2]`；不要把亚型标签写成分群前已存在的类别。

### 2.9 各细胞类型标志基因鉴定与功能富集

使用 Seurat::FindAllMarkers (test.use='wilcox') 对各细胞类型鉴定差异表达基因 (DEGs)，筛选 |avg_log2FC| > [1] 且 p_val_adj < 0.05 的基因作为该细胞类型的标志基因。提取每个细胞类型的 top [10] 标志基因，使用 ClusterGVis R 包绘制综合热图：左侧热图按细胞类型展示标志基因表达矩阵，右侧条形图展示 ClusterGVis 内置 enrichGO ([org.Hs.eg.db / org.Mm.eg.db]; ont='BP') 富集得到的代表性 GO Biological Process 通路。

### 2.10 转录因子调控网络分析

为从转录因子调控层面解析各细胞类型的特异性调控程序，采用 pySCENIC 流程构建调控单元 (regulon) 网络。pySCENIC 包含三个标准步骤：(1) GRN — 基于 GRNBoost2 算法从表达矩阵推断转录因子-靶基因共表达关系；(2) ctx — 利用 cisTarget 数据库 ([hg38__refseq-r80__500bp_up_and_100bp_down_tss / mm10 对应版本]) 通过转录因子结合 motif 富集对靶基因进行剪枝，得到高置信度 regulon；(3) AUCell — 在单细胞水平计算各 regulon 在每个细胞中的活性评分 (AUC)。基于二值化 AUC 矩阵计算各 regulon 在各细胞类型中的特异性评分 (Regulon Specificity Score, RSS)，并以点图展示各细胞类型 top [5] 特异性 regulon。

## 3. 结果

### 3.1 降维聚类与细胞类型注释

我们首先对 [N] 例 [研究对象] 的单细胞转录组数据进行整合预处理，最终获得 [N 万] 个高质量单细胞。基于 Scanpy 标准流程 (PCA + Leiden) 进行降维聚类，共得到 [N] 个 Leiden cluster。结合 scType 算法基于先验标志基因的得分注释，将这些 cluster 归类为 [N] 种主要细胞类型 ([列出主要细胞类型])（图1A）。各样本均贡献全部主要细胞类型 (图1B)，表明数据整合效果良好、无明显的样本驱动聚类偏差。

经典标志基因 (例如 [基因列表]) 在对应细胞类型中呈现高度特异性的表达模式（图1C），进一步支持注释的可靠性。

![](Figures/Cell_Types.ALL.UMAP.png)
![](Figures/Cell_Types.SAMPLES.UMAP.png)
![](Figures/Dotplot.gene_cells.png)

**图1.** A：基于 Scanpy 标准流程 (PCA + Leiden) 与 UMAP 投影的全队列细胞图谱，颜色表示 scType 注释的 [N] 种主要细胞类型；B：UMAP 按样本来源着色，展示各样本细胞分布的均衡性；C：经典标志基因在各细胞类型中的表达点图，点大小表示表达细胞比例，颜色表示平均表达水平。

### 3.2 细胞组成分析

在明确细胞图谱的基础上，我们进一步比较 [实验组] 与 [对照组] 之间各细胞类型的相对组成（图2A、B）。[对照组] 中以 [类别 X] 占比最高（[N%]），其次为 [类别 Y]（[N%]）；[实验组] 中 [类别 Z] 比例升高至 [N%]，[类别 X] 则下降至 [N%]。

进一步采用 Ro/e 指标量化各细胞类型的组别偏好（图2C）：[列出 Ro/e>1 的细胞类型] 在 [实验组] 中显著富集 (Ro/e [数值])，[列出 Ro/e<1 的细胞类型] 则在 [对照组] 中相对富集。

![](Figures/cell_types.barplot_PCT.png)
![](Figures/cell_types.barplot.png)
![](Figures/roe_heatmap.png)

**图2.** A：[实验组] vs [对照组] 各细胞类型相对百分比堆叠柱状图；B：各细胞类型在两组中的细胞计数堆叠柱状图；C：基于 Ro/e 指标的细胞类型-组别偏好热图，颜色越深表示该细胞类型在该组中越富集。

### 3.3 标志基因与功能条目展示

为展示各细胞类型的表达标记，我们对每种细胞类型鉴定其标志基因 ([avg_log2FC] > 1, [p_val_adj] < 0.05)，并对 top [10] 标志基因进行 GO Biological Process 条目汇总（图3）。热图左侧展示 marker 基因在细胞类型间的表达分布，右侧条形图展示每类细胞对应的 GO BP 条目及显著性。

[一句观察性总结，例如"两组在 [细胞类型 C] 的功能模块上呈现差异"。停在观察，不展开机制]。

![](Figures/CellMarkerGenesHeatmap_GOBP.png)

**图3.** 各细胞类型 top [10] 标志基因表达热图（左）与 ClusterGVis 集成的 GO Biological Process 富集结果（右），右侧条形图长度表示 -log10(padj)。

### 3.4 pySCENIC 转录因子调控网络分析

为展示 pySCENIC 的 regulon 评分结果，我们采用 pySCENIC 重建 [实验组] 与 [对照组] 全部细胞的转录因子-基因关联网络，基于 AUCell 评分计算各 regulon 的细胞类型特异性 (RSS)（图4）。

图4 展示各细胞类型 RSS 排名前 [5] 的 regulon。例如 [细胞类型 A] 中 [TF 名] regulon 的 RSS 为 [数值]；[细胞类型 B] 中 [TF 名] regulon 的 RSS 为 [数值]。对应结果表记录细胞类型、regulon 名称和 RSS/AUC 相关结果。

![](Figures/RSS_top5.png)

**图4.** 各细胞类型 pySCENIC 调控单元 (regulon) 特异性评分 (RSS) 排名前 5 的转录因子点图，点的大小或颜色表示 RSS 值。

---

## 5. 参考文献

- [Wolf2018Scanpy] Wolf FA, Angerer P, Theis FJ. SCANPY: large-scale single-cell gene expression data analysis. Genome Biology. 2018. doi:10.1186/s13059-017-1382-0.
- [Ianevski2022ScType] Ianevski A, Giri AK, Aittokallio T. Fully-automated and ultra-fast cell-type identification using specific marker combinations from single-cell transcriptomic data. Nature Communications. 2022. doi:10.1038/s41467-022-28803-w.
- [VanDeSande2020pySCENIC] Van de Sande B et al. A scalable SCENIC workflow for single-cell gene regulatory network analysis. Nature Protocols. 2020. doi:10.1038/s41596-020-0336-2.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
