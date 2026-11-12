# Methods Snippets — Reusable Boilerplate per Analysis Module

Each snippet is a **drop-in 方法 subsection** for the report. Copy verbatim, then substitute the bracketed placeholders. Style: formal Chinese scientific prose, dense but not overdetailed, methods-only (no results, no interpretation).

Per the `summary-report` skill, methods order MUST mirror results order. Keep `数据获取` as the first subsection whenever a dataset / cohort source exists. For purely *in-silico* modules (e.g. pharmacology network), open with `数据收集与对象选择` instead.

Before copying any snippet, load `workflow-parameter-guide.md` and `references.bib`. Keep package/program names, official-documentation parameters, client-approved project parameters, and result-affecting analysis thresholds in the final report, but do not expose internal workflow names, private helper names, company-internal custom parameter names, private paths, or raw internal flags. Convert all references to China National Standard GB/T 7714-2005 numeric style with clickable superscript body links, for example `<sup class="citation-ref"><a href="#ref-1">[1]</a></sup>`. The citation numbers below are illustrative; renumber them sequentially in the final report according to first citation order and add matching `id="ref-N"` anchors in `## 5. 参考文献`. If the project command or config overrides a reportable parameter shown here, replace the snippet value with the actual project value.

**Method depth contract.** Each copied method paragraph must keep five elements: input/output object, algorithm or statistical principle, one method characteristic, actual reportable parameters or thresholds, and literature citation. Do not shorten a method to "使用某软件分析并作图"; that is a workflow inventory, not a methods section. If a snippet contains multiple alternatives, delete alternatives that were not run.

**Scope notice.** These snippets are reusable method-writing templates, not a license to invent methods. Use a snippet only when the corresponding analysis was actually run, then replace placeholders with the project-specific software, public parameters, thresholds, databases, contrasts, and references. If a project uses a method not covered here, draft it with the same depth contract from real run evidence and traceable literature.

---

## 2.1 数据获取 (universal opener)

### Variant A — Public database cohort

```markdown
### 2.1 数据获取

本研究使用的[组学类型]数据来自[公共数据库名]，数据集编号为 [数据集编号]。该数据集包含 [N] 例[研究对象描述]，涵盖 [分组描述：肿瘤/对照、时间点、处理条件等]，每例样本采集 [样本类型描述]。所有样本均采用 [测序平台/技术平台]，在 [测序仪型号] 上完成文库构建与测序。原始测序数据经 [上游处理流程，见 2.X] 处理后得到表达矩阵用于下游分析。
```

### Variant B — TCGA cohort

```markdown
### 2.1 数据获取

本研究使用的转录组与临床数据来自美国国家癌症研究所基因组数据共享平台 (GDC, https://portal.gdc.cancer.gov/) 的 The Cancer Genome Atlas (TCGA) 项目 [癌型缩写] 队列（[TCGA-XXX]）。通过 GDC API 下载该队列的 [STAR-Counts mRNA 表达 / miRNA isoform 表达] 文件以及对应的样本信息表。配套临床数据（生存时间、状态、分期等）通过 cBioPortal 公共接口 (cBioPortalData R 包) 获取。该队列共纳入 [N] 例样本，其中 [实验组] [N1] 例、[对照组/正常组织] [N2] 例。
```

### Variant C — GEO 系列矩阵

```markdown
### 2.1 数据获取

本研究使用的转录组数据来自基因表达综合数据库 (Gene Expression Omnibus, GEO) 的 [GSExxxxxx] 数据集（平台 [GPLxxxx]）。通过 R 包 GEOquery 下载该数据集的 series matrix 文件并解析样本表型 (pData)，得到 [N] 例样本的探针水平表达矩阵。基于 [GPLxxxx] 平台注释文件将探针 ID 映射为基因 symbol，对一基因对多探针的情况保留最大平均表达探针。
```

### Variant D — 自有数据 / 合作单位委托

```markdown
### 2.1 数据获取

本研究使用的[组学类型]数据由[委托方简述：例如"项目合作单位"]于 [年份] 完成采集与测序。共纳入 [N] 例[研究对象描述]，涵盖 [分组描述]，每例样本采集 [样本类型]。文库构建采用 [建库试剂盒]，在 [测序仪型号] 上完成 [PE150/SE100] 测序。原始测序数据由委托方提供并经 [上游处理流程，见 2.X] 处理后得到表达矩阵用于下游分析。
```

### Variant E — 网络药理学 (无传统"样本")

```markdown
### 2.1 数据收集与对象选择

研究对象为 [中药 / 复方名称]，包含 [N] 味中药：[药材列表 (拉丁学名)]。通过 [BATMAN-TCM v2 数据库 (http://bionet.ncpsb.org.cn/batman-tcm/) ] 检索各味中药的化学成分及其对应的潜在靶点蛋白；目标疾病为 [疾病名]，通过 [GeneCards / OMIM / DisGeNET] 等公开疾病-基因关联数据库收集疾病相关基因集合。
```

**占位符说明**：

- `[组学类型]`：scRNA / 普通 (bulk) 转录组 / 微阵列 等
- `[公共数据库名]` / `[数据集编号]`：GEO / GSE — / SRA / PRJNA— / ENA / TCGA-XXX 等
- `[N]` / `[N1]` / `[N2]`：样本/队列规模
- `[研究对象描述]` / `[分组描述]` / `[样本类型描述]`：实验设计核心
- `[测序平台]`：10X Genomics Chromium / Illumina TruSeq mRNA Library Prep 等
- `[测序仪型号]`：Illumina NovaSeq 6000 / NextSeq 2000 / DNBSEQ-T7 等

---

# scRNA-seq

> 常见方法组合：Scanpy + AnnData，配合 GPU 加速版 rapids_singlecell；细胞类型注释可采用 scType 基于先验标志物得分的方法；转录因子调控网络可采用 pySCENIC。

## 2.X scRNA-seq 上游原始数据处理

```markdown
### 2.X 原始测序数据处理

10X Genomics 测序得到的原始 FASTQ 数据使用 Cell Ranger ([版本号]) 对参考基因组 [refdata-gex-GRCh38-2024-A / refdata-gex-GRCm39-2024-A] 进行 reads 比对、细胞条形码识别、UMI 去重和基因-细胞矩阵生成 [1]。该流程将测序 reads 映射到参考转录组后按有效 barcode 与 UMI 聚合为 feature-barcode 矩阵，特点是与 10X Genomics 单细胞建库结构匹配，能够将每个样本转换为后续 Scanpy/AnnData 可直接读取的 filtered_feature_bc_matrix 表达矩阵。
```

## 2.X 单细胞数据预处理与质控

```markdown
### 2.X 数据预处理与细胞质控

各样本 filtered_feature_bc_matrix 表达矩阵使用 Scanpy [版本号] 与 AnnData 数据结构进行管理，并配合 rapids_singlecell 进行后续高通量矩阵运算 [1-3]。Scanpy/AnnData 以细胞 × 基因稀疏矩阵为核心对象，能够同时保存 counts、细胞元数据、基因元数据和降维结果；rapids_singlecell 在相同分析语义下利用 GPU 加速大规模单细胞矩阵处理。每个细胞通过 Scanpy calculate_qc_metrics 计算检测基因数 (n_genes_by_counts)、总 UMI 数 (total_counts)、线粒体基因表达比例 (pct_counts_mt)、血红蛋白基因比例 (pct_counts_hb)、核糖体基因比例 (pct_counts_ribo)、percent_top=20 对应的 top20 高表达基因占比，以及 log1p 转换后的计数指标。质控采用基于中位数绝对偏差 (Median Absolute Deviation, MAD) 的稳健异常值检测；MAD 以样本内中位数为中心度量偏离程度，特点是对极端细胞不敏感，适合单细胞 QC 指标的长尾分布。log1p(total_counts)、log1p(n_genes_by_counts) 及 top20 基因占比偏离样本中位数达到 5 MAD 的细胞、以及 pct_counts_mt 偏离中位数达到 3 MAD 或 pct_counts_mt > 8 的细胞被过滤。Scrublet 通过模拟人工双细胞并比较每个细胞与模拟双细胞邻域的相似性预测潜在 doublet，按样本/batch 分别运行后去除预测为双细胞的细胞 [4]。原始 counts 保存于 AnnData counts layer，归一化采用总表达量缩放至每细胞 1×10⁴ 后进行 log1p 变换，最终得到用于下游分析的高质量单细胞表达矩阵。
```

## 2.X scVI 批次效应校正与整合

```markdown
### 2.X scVI 批次效应校正与整合

质控后的单细胞表达矩阵使用 scVI/scvi-tools 进行样本批次效应校正，并构建批次校正后的低维细胞嵌入（cell embedding） [5]。scVI 是基于深度生成模型的单细胞整合方法，以变分自编码器在低维状态空间（latent space）中刻画细胞表达结构，并在计数分布建模中纳入 batch 协变量，从而把技术批次差异与主要表达结构分离。该方法适合稀疏、高维且含批次来源的单细胞 count 数据；得到的低维细胞嵌入矩阵可作为邻近图构建、Leiden 聚类、UMAP 投影和细胞类型注释的输入。若项目参数中包含 batch key、嵌入维度、模型结构或训练轮数，在此处补充实际参数。
```

## 2.X 降维聚类与 UMAP 可视化

```markdown
### 2.X 高变基因鉴定、降维与聚类

基于归一化表达矩阵，使用 Scanpy 的 highly_variable_genes 函数（flavor='seurat_v3'）鉴定 top [2000–4000] 个高变基因 (HVG)。HVG 筛选通过均值-方差关系识别跨细胞变异度较高的基因，特点是减少低信息量基因对下游距离计算的影响。以高变基因子集作为输入，进行标准化 (scale) 与主成分分析 (PCA, n_comps=50)，用于表达矩阵降维概览和质控检查。邻近图（nearest-neighbor graph）默认基于 scVI 校正后的低维细胞嵌入构建，例如 `sc.pp.neighbors(..., use_rep='X_scVI')`；只有在项目明确未使用 scVI 时，才改为报告实际使用的 PCA/Harmony/BBKNN/Scanorama 等嵌入或降维结果。基于批次校正后的低维细胞嵌入构建细胞 K 最近邻图 (k=[15])，采用 Leiden 算法（分辨率 resolution=[0.5–1.0]）进行图聚类，并以 UMAP (min_dist=[0.3]) 算法投影至二维空间用于可视化 [1-3]。Leiden 在细胞邻接图上优化社区结构并保证社区连通性，适合从单细胞近邻图中得到可解释 cluster；UMAP 基于流形学习保留局部邻域结构，适合将高维细胞状态投影到二维图中展示。
```

## 2.X 细胞类型注释 (scType)

```markdown
### 2.X 细胞类型注释

细胞类型注释在 Leiden 聚类结果基础上进行。输入 h5ad 文件通过 anndataR 读取 [1-2]，scType 以 ScTypeDB 数据库中 [人 / 小鼠] [组织名] 的细胞类型-标志基因列表为先验（默认 `--tissue='Immune system'`、`--db='short'`，如项目另有设置则填入实际值），对每个细胞计算其在各候选细胞类型上的特异性表达评分；对每个 Leiden cluster 取细胞累加评分最高的细胞类型作为该 cluster 的注释结果。该方法的原理是用正向 marker 与负向 marker 的表达差异形成细胞类型得分，特点是结果可直接追溯到 marker 集合，适合与 cluster marker 表和人工整理注释共同核对。当某 cluster 的最高得分低于 cluster 内细胞数的 1/4 时，标注为 "Unknown"。最终在 UMAP 上以颜色区分细胞类型，并使用 Scanpy 的 rank_genes_groups（method='wilcoxon'）输出各细胞类型的特异性差异表达基因列表用于注释验证 [3]。
```

## 2.X 细胞组成与组织偏好分析

```markdown
### 2.X 细胞组成与组织偏好分析

为定量评估各细胞类型在不同组/样本间的相对丰度差异，对每个细胞类型计算其在各分组中的细胞计数及百分比，使用堆叠柱状图与百分比柱状图进行展示。进一步采用 Ro/e (Ratio of observed to expected) 指标量化细胞类型对样本/组织来源的偏好性：基于细胞类型 × 组织/分组列联表，在行列独立性假设下计算期望细胞数，以 observed/expected 作为 Ro/e [1]。Ro/e 的特点是将不同分组样本量差异纳入期望值计算，适合用热图比较细胞类型在不同组织或分组中的相对富集程度。
```

## 2.X 细胞亚型注释

```markdown
### 2.X [父细胞类型] 子集 Leiden Cluster 与亚型注释

从总体细胞注释结果中提取 [父细胞类型] 子集后，在该子集内基于 scVI/PCA 表示重新构建邻近图并进行 Leiden 分群，得到 [Cluster0-ClusterN / res_*] [1-3]。子集内重新分群的原理是只在同一父细胞类型内部重新估计近邻关系和社区结构，特点是能提高对细胞亚群差异的分辨率，避免总体聚类被其他大类细胞的距离结构主导。随后以每个 Leiden Cluster 为注释单位，结合 Cluster marker 基因、亚型 marker 表和人工整理注释，将各 Cluster 注释为 [亚型1-亚型N]。若细胞元数据同时包含 Cluster 列和亚型标签列，应写明对应关系，例如 `Cluster0 -> [亚型1]`、`Cluster1 -> [亚型2]`；不要把亚型标签写成分群前已存在的类别。
```

## 2.X 标志基因表达谱

```markdown
### 2.X 重点基因表达模式可视化

为可视化感兴趣基因（[基因列表 / 标志基因 / cluster top DEG]）在不同细胞类型间的表达分布，使用 Scanpy 的 dotplot、stacked_violin 与 matrixplot 函数分别绘制点图、堆叠小提琴图与矩阵热图 [1]。这些图以细胞类型或 cluster 为分组单位汇总单细胞表达矩阵，特点是可同时展示表达强度、表达细胞比例和组内分布形态，适合核对 marker 基因与注释标签的一致性。点图中点的大小代表表达该基因细胞的比例 (pct.expressed)，颜色深浅代表该分组内的平均表达水平 (Scanpy `dotplot` 默认对该分组全部细胞求均值；若设置 `mean_only_expressed=True`，则仅对表达细胞求均值)。
```

## 2.X 标志基因热图 + 功能富集

```markdown
### 2.X 各细胞类型标志基因鉴定与功能富集

使用 Seurat::FindAllMarkers (test.use='wilcox') 对各细胞类型鉴定差异表达基因 (DEGs) [1]。FindAllMarkers 将目标细胞类型与其余细胞进行逐基因比较，Wilcoxon 秩和检验不要求表达量服从正态分布，适合单细胞表达矩阵中零值多、分布偏态的 marker 筛选。筛选 |avg_log2FC| > [1] 且 p_val_adj < 0.05 的基因作为该细胞类型的标志基因。提取每个细胞类型的 top [10] 标志基因，使用 ClusterGVis R 包绘制综合热图；ClusterGVis 可将表达模式聚类、热图展示和富集结果组合到同一图形中，适合展示多个细胞类型 marker 的表达结构 [2]。左侧热图按细胞类型展示标志基因表达矩阵，右侧条形图展示 ClusterGVis 内置 enrichGO (org.Hs.eg.db / org.Mm.eg.db / org.Rn.eg.db; ont='BP') 富集得到的代表性 GO Biological Process 通路。
```

## 2.X 单细胞差异表达分析

```markdown
### 2.X 组间差异表达分析

针对感兴趣的细胞类型 / 亚群，比较 [实验组] vs [对照组] 之间的差异表达。若项目使用 pseudobulk，先按样本来源汇总目标 cluster 的 counts，形成样本 × 基因矩阵后使用 DESeq2 建模；DESeq2 基于负二项分布估计计数数据的均值-离散度关系，并通过离散度和 fold change 收缩提高小样本估计稳定性，适合有样本重复的细胞类型内组间比较 [1]。若项目使用单细胞水平检验，则使用 Scanpy rank_genes_groups (method='wilcoxon') 进行 Wilcoxon 秩和检验，适合以细胞为单位输出 cluster/组别 marker 排名 [2]。差异基因筛选阈值为 |log2FC| > [1] 且 [adjusted p-value / padj] < [0.05]，结果以火山图与热图展示。
```

## 2.X 转录因子调控网络 (pySCENIC)

```markdown
### 2.X 转录因子调控网络分析

为解析各细胞类型的转录因子调控单元，采用 pySCENIC 构建 regulon 网络并计算单细胞 regulon 活性 [1-2]。pySCENIC 包含三个标准步骤：(1) GRN — 基于 GRNBoost2 从表达矩阵推断转录因子-靶基因共表达关系；GRNBoost2 使用梯度提升树评估转录因子对靶基因表达的预测贡献，特点是适合大规模单细胞表达矩阵的非线性网络推断 [3]；(2) ctx — 利用 cisTarget ranking database feather 文件 (如 `hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.genes_vs_motifs.rankings.feather` 及配套 `motifs-v9-nr.hgnc-m0.001-o0.0.tbl` 注释表，以实际下载版本为准；小鼠对应 `mm10__refseq-r80__*` 系列) 通过转录因子结合 motif 富集对靶基因进行剪枝，得到高置信度 regulon；(3) AUCell — 在单细胞水平根据 regulon 靶基因在每个细胞表达排序中的富集程度计算 AUC 活性评分。本流程从 counts layer 读取表达矩阵，物种参数为 [hsa/mmu]；如项目使用其他物种或数据库版本，应填入实际值。基于二值化 AUC 矩阵计算各 regulon 在各细胞类型中的特异性评分 (Regulon Specificity Score, RSS)，并以点图展示各细胞类型 top [5] 特异性 regulon；RSS/top regulon 点图中的点颜色用于区分 top regulon 名称，RSS 数值以 `cellRSS.matrix.tsv` 为准。
```

## 2.X inferCNV 拷贝数变异信号可视化

```markdown
### 2.X inferCNV 拷贝数变异信号分析

基于细胞注释结果、单细胞表达矩阵和基因染色体位置信息，使用 inferCNV 对染色体区段层面的相对表达信号进行估计与可视化 [1]。inferCNV 将基因按染色体坐标排序，比较观测细胞与参考细胞集合的表达偏移，并对相邻基因信号进行平滑，以展示大尺度拷贝数增益或缺失相关的表达模式。该方法的特点是利用 scRNA-seq 表达数据提供 CNV 线索，适合与细胞注释和 CNV score 一起进行恶性细胞/细胞群信号展示。分析按项目配置选择 [参考细胞类型 / 对照细胞集合] 作为参考集合，并按 Leiden cluster 或细胞类型对细胞进行分组；输出包括 CNV score 映射至 UMAP 坐标的可视化图，以及按染色体位置排列的细胞 × 基因区段热图。若项目配置中包含 cutoff、denoise、HMM 或参考组名称等 inferCNV 参数，应在此处写明实际值。
```

## 2.X CellChat 细胞通讯分析

```markdown
### 2.X CellChat 细胞通讯分析

细胞通讯分析使用 R 包 CellChat，以细胞类型注释作为分组变量，基于配体-受体及辅因子数据库计算不同细胞类型之间的潜在通讯概率与通路级别汇总结果 [1]。CellChat 根据发送细胞中配体和接收细胞中受体/复合体的表达估计细胞对通讯概率，并通过置换检验获得显著性；其特点是可以把单个配体-受体对汇总到 signaling pathway、incoming/outgoing role 和整体通讯网络层面。单组分析分别对 [Ctrl / Tumor / 其他分组] 子集运行，输出细胞对通讯数量矩阵、通讯权重矩阵、配体-受体对概率与 p 值表、通路概率表、网络图、signaling role 热图及 pathway 级别 circle / hierarchy / contribution / gene expression 图。组间比较使用 CellChat 合并对象比较两组通讯数量、通讯强度、通路 rankNet、差异互作网络和 pathway aggregate/heatmap；incoming/outgoing communication pattern 分析按 CellChat 模式选择结果确定 nPatterns，并输出 dot plot 与 river plot。
```

## 2.X Augur 细胞类型分组可区分度评分

```markdown
### 2.X Augur 细胞类型评分

为比较不同细胞类型对分组标签的可区分度，使用 Augur 对每个细胞类型分别构建监督学习分类任务，并汇总 mean_augur_score、mean_auc、mean_accuracy、mean_precision、mean_f1 与 mean_recall 等指标 [1]。Augur 的原理是评估某一细胞类型内部的表达特征能否区分给定实验分组，通常以交叉验证分类器的 AUC 作为排序指标；其特点是将细胞类型优先级转化为可比较的分类性能评分，适合在多个细胞类型之间筛选分组差异更明显的细胞群。若项目运行中调整了 subsampling、交叉验证折数或分类器参数，应在此处记录实际参数。
```

---

# Bulk RNA-seq

> 常见方法组合：上游可使用 nf-core/rnaseq v3.22.2 (STAR + Salmon) 或 fastp + STAR + featureCounts；差异表达可使用 DESeq2 (count 矩阵) 或 limma/voom (微阵列 / 已归一化矩阵 / RNA-seq)。

## 2.X 原始测序数据预处理与表达定量

### Variant A — nf-core/rnaseq (推荐)

```markdown
### 2.X 原始数据预处理与基因定量

原始测序数据使用 nf-core/rnaseq v[版本号] 进行 RNA-seq 上游处理。FASTQ reads 首先经 fastp 进行接头识别、低质量碱基剪切和长度过滤；fastp 将质量评估与 reads 清洗整合在同一步骤，适合在比对前统一去除低质量序列 [1]。过滤后的 reads 使用 STAR 比对至 [参考基因组 Ensembl Homo_sapiens.GRCh38 / Mus_musculus.GRCm39] 并投影至转录组；STAR 是 splice-aware RNA-seq 比对器，通过最大可映射种子搜索和剪接位点识别处理跨外显子 reads，适合真核转录组比对 [2]。在 star_salmon 模式下，Salmon 对 STAR 输出的 transcriptome BAM 进行 bias-aware 转录本定量，并汇总得到基因层面的 counts 与 TPM；Salmon 通过概率模型估计转录本丰度并校正序列/GC 偏好，特点是定量速度快且适合转录本到基因层面的表达汇总 [3]。最终得到样本 × 基因的原始 count 矩阵与 TPM 矩阵用于下游分析。
```

### Variant B — fastp + STAR + featureCounts

```markdown
### 2.X 原始数据预处理与基因定量

原始测序数据使用 fastp 进行接头剪切、低质量碱基过滤和 reads 质量统计 [1]。过滤后的 clean reads 使用 STAR 比对至 [参考基因组及版本]；STAR 识别剪接位点并将跨外显子 reads 对齐至基因组，适合 RNA-seq reads 的剪接感知比对 [2]。比对得到的 BAM 文件使用 featureCounts 基于 [GTF 注释文件] 进行基因水平 reads 计数；featureCounts 将已比对 reads 按 exon/gene 等注释 feature 汇总为 count 矩阵，特点是支持链特异性、双端片段和多种 reads 分配策略 [3]。最终得到样本 × 基因的原始 count 矩阵用于下游差异分析；如项目计算 TPM / FPKM，应写明所用基因长度来源和归一化公式。
```

## 2.X 表达谱整体质控

```markdown
### 2.X 表达谱质控与样本概览

为评估样本测序质量与组间分离度，对 log2(CPM+1) 归一化后的表达矩阵进行整体可视化：(1) 各样本表达分布箱式图，用于检测样本表达分布偏移；(2) 样本间 Pearson 相关性热图，用于查看样本一致性；(3) 主成分分析 (PCA) 散点图，用于概览主要变异轴与分组或批次的关系。PCA 通过线性组合提取解释表达矩阵方差最高的正交方向，特点是适合样本层面异常值、批次结构和组间分离的探索性检查。若组间分离明显受批次或文库制备时间影响，差异分析时将批次/协变量纳入设计矩阵 (~batch + group)；PCA / 热图等可视化层面的批次贡献校正由 limma::removeBatchEffect 或 sva::ComBat 生成校正后的展示矩阵 [1-2]。ComBat 使用经验贝叶斯框架估计并校正已知批次效应，报告中需写明 batch 变量、保护变量和输入矩阵类型。
```

## 2.X 差异表达分析

### Variant A — DESeq2 (count-based)

```markdown
### 2.X 差异表达分析

差异表达分析使用 R 包 DESeq2 进行 [1]。以原始 count 矩阵为输入，构建包含分组 (及必要协变量) 的设计矩阵 [~ group / ~ batch + group]，使用 DESeq() 函数完成大小因子估计、基因离散度估计与基于负二项分布的 Wald 检验，得到 [实验组] vs [对照组] 的差异表达结果。DESeq2 通过估计均值-离散度关系并对离散度和 fold change 进行收缩，提高 RNA-seq count 数据在有限重复样本下的统计稳定性。结果表列名通常包含 `baseMean`、`log2FoldChange`、`lfcSE`、`stat`、`pvalue` 与 `padj`；差异基因 (DEGs) 筛选阈值定义为 |log2FoldChange| > [1] (即 fold change > 2 或 < 0.5) 且 padj < [0.05]。
```

### Variant B — limma (微阵列 / 已归一化矩阵 / voom 流程)

```markdown
### 2.X 差异表达分析

差异表达分析使用 R 包 limma 进行 [1]。[微阵列 / 已 log2(CPM+1) 归一化] 表达矩阵作为输入，构建包含分组的设计矩阵后调用 lmFit() 拟合线性模型，eBayes() 进行经验贝叶斯调节，topTable(adjust.method='fdr') 输出每个基因的 `logFC`、`t`、`P.Value` 与 `adj.P.Val`。limma 的特点是通过经验贝叶斯方法稳定基因层面方差估计，适合微阵列、已归一化表达矩阵和含协变量的复杂设计。对于 RNA-seq 原始计数，先经 edgeR::filterByExpr 过滤低表达基因并使用 voom() 将 counts 转换为带精度权重的 logCPM，再进入 limma 线性模型框架 [2-3]。差异基因 (DEGs) 筛选阈值定义为 |logFC| > [1] (即 fold change > 2 或 < 0.5) 且 adj.P.Val < [0.05]；若项目使用原始 P.Value 作为筛选依据，应写明实际阈值。
```

## 2.X 差异基因可视化

```markdown
### 2.X 差异表达基因可视化

差异表达结果使用以下图表进行可视化：(1) 火山图（基于 ggplot2 + ggrepel），横轴为 log2FoldChange，纵轴为 -log10(padj) 或 -log10(adj.P.Val)，按照设定阈值将基因分为显著上调、显著下调及非显著三类，并对 top 上下调基因加注基因名 [1-2]；(2) 表达热图（基于 ComplexHeatmap 或 pheatmap），展示 top [50–100] 显著差异基因在所有样本中的 z-score 标准化表达值，行按层次聚类排序 [3-4]。火山图适合同时展示效应量与统计显著性，热图适合查看筛选基因在样本间的表达模式与聚类结构。
```

---

# GEO 公共转录组数据集

## 2.X GEO 数据获取与平台注释

```markdown
### 2.X GEO 数据下载与探针注释

使用 R 包 GEOquery 的 getGEO() 函数（getGPL=FALSE, AnnotGPL=FALSE）下载 [GSExxxxxx] 数据集的 series matrix 文件，通过 `exprs()` 提取探针 × 样本的表达矩阵（行为探针/feature、列为 GEO 样本编号），通过 `pData(phenoData(.))` 提取样本表型信息 [1]。GEOquery 将 GEO 的表达矩阵、平台信息和样本表型整理为 Bioconductor 对象，特点是便于从同一数据源同步获得表达量和样本分组信息。基于该数据集所在测序平台 ([GPLxxxx]) 的注释文件，将探针 ID 映射至基因 symbol；一对多探针保留平均表达最高的探针；对照 phenoData 信息重构样本分组标签 ([gp1] / [gp2])。
```

## 2.X GEO 批次效应处理 (按需添加)

```markdown
### 2.X 批次效应处理

针对样本表型中显式记录批次的情形（不同 batch / 不同测序时间），使用 limma::removeBatchEffect 或 sva::ComBat 在保留分组结构 (design = ~group) 的前提下移除 batch 项的贡献 [1-2]。removeBatchEffect 基于线性模型从表达矩阵中扣除指定批次变量的贡献，适合 PCA、热图等展示矩阵；ComBat 使用经验贝叶斯框架估计批次均值和方差偏移，适合已知批次效应校正。方法段需写明 batch 列、分组保护变量、输入矩阵类型以及校正后矩阵的用途。
```

## 2.X GEO 差异表达分析

```markdown
### 2.X 差异表达分析

差异表达分析使用 R 包 limma [1]。基于探针注释后的表达矩阵与分组信息构建设计矩阵，使用 lmFit() + eBayes() 进行经验贝叶斯线性模型拟合，对每组比较 ([gp1] vs [gp2]) 调用 topTable(adjust.method='fdr') 输出 logFC、P.Value 及 adj.P.Val。limma 通过跨基因借用信息稳定方差估计，特点是适合微阵列和已归一化表达矩阵的小样本差异分析。差异基因 (DEGs) 筛选阈值定义为 |log2FC| > [1] 且 [adj.P.Val / P.Value] < [0.05]。
```

---

# TCGA 队列分析

## 2.X TCGA 数据下载与合并

```markdown
### 2.X TCGA 表达数据获取

通过美国国家癌症研究所基因组数据共享平台 (GDC, https://portal.gdc.cancer.gov/) API 或 TCGAbiolinks 检索并下载 TCGA-[癌型] 队列的 [STAR-Counts mRNA / BCGSC miRNA isoform] 数据 [1-4]。GDC 提供统一的癌症组学数据访问与元数据结构，TCGAbiolinks 可将查询、下载、样本筛选和表达矩阵整理整合到 Bioconductor 流程中。基于 GDC manifest 与样本表 (sample sheet) 整合各样本表达文件，构建样本 × 基因的原始 count 矩阵；通过 TCGA 标准条形码前 16 位 (TCGA-XX-XXXX-01 / TCGA-XX-XXXX-11) 区分肿瘤样本与配对正常对照。报告需写明 project ID、data type、workflow type、sample type 和重复样本处理规则。
```

## 2.X TCGA 临床数据获取

```markdown
### 2.X 临床表型数据获取

通过 cBioPortal 公共接口 (R 包 cBioPortalData) 下载 TCGA-[癌型] (cBioPortal studyId: [studyId]) 队列的临床数据表，包括生存时间 (OS_MONTHS)、生存状态 (OS_STATUS)、肿瘤分期 (AJCC stage)、年龄和性别等信息 [1]。cBioPortalData 将 cBioPortal 的研究编号、样本表型和多组学矩阵整理为 R/Bioconductor 可分析对象，特点是便于将公开癌症队列表型与表达矩阵进行样本级匹配。临床数据与表达矩阵基于 TCGA 患者编号 (前 12 位 barcode) 进行匹配。
```

## 2.X TCGA 差异表达分析

```markdown
### 2.X 差异表达分析

基于 TCGA-[癌型] 原始 count 表达矩阵，以 [肿瘤 (Tumor) / 正常 (Normal)] 为分组变量构建 DESeq2 模型 [1]。DESeq2 对 count 数据使用负二项广义线性模型，先估计 size factor 与基因离散度，再通过 Wald 检验获得组间差异表达统计量；该方法适合 TCGA count 矩阵的基因层面差异分析。差异基因筛选阈值为 |log2FoldChange| > [1] 且 padj < [0.05]，如设计矩阵包含批次或临床协变量，应写明实际公式。
```

---

# 功能富集分析

> 富集分析以 R 包 clusterProfiler 为核心，针对差异基因 (DEGs) 列表的 over-representation 分析 (ORA) 与全基因排序的 GSEA 两种范式分开实现；KEGG 通路细节可使用 pathview 可视化。

## 2.X GO / KEGG 富集分析 (ORA)

```markdown
### 2.X GO / KEGG 富集分析

针对显著差异基因 (DEGs) 列表，使用 R 包 clusterProfiler 进行 GO 与 KEGG 过表征 (over-representation) 分析 [1]。ORA 的原理是在给定背景基因集下检验输入基因列表是否在某个功能条目中出现比例高于随机期望，通常使用超几何检验或等价的富集统计；其特点是适合对阈值筛选后的差异基因列表进行功能主题汇总。GO 富集通过 enrichGO() 函数对三大本体 (BP / CC / MF) 分别进行，基因背景设为 [全部检测基因 / org.Hs.eg.db / org.Mm.eg.db / org.Rn.eg.db 的全基因列表] [2-5]；KEGG 富集通过 enrichKEGG() 在线访问 KEGG 数据库 (organism='hsa' / 'mmu') 完成 [6]。p 值校正使用 Benjamini-Hochberg 方法，富集显著性阈值定义为 `pvalueCutoff=0.05` 与 `qvalueCutoff=0.2`。富集结果以 dotplot 与 emapplot (enrichplot::pairwise_termsim 后构建术语-术语网络) 可视化 [7]；对 GO BP 进一步使用 topGO R 包以 elim 算法消除父子术语冗余，输出层次结构精简后的代表性术语 [8]。
```

## 2.X GSEA 基因集富集分析

```markdown
### 2.X 基因集富集分析 (GSEA)

为捕捉差异表达分析中未必通过单基因阈值但具有协同变化的功能信号，对差异分析得到的全基因排序列表进行基因集富集分析 (Gene Set Enrichment Analysis, GSEA) [1]。GSEA 在排序列表上计算 running enrichment score，检验某一基因集是否集中分布在排序顶部或底部，特点是保留全基因排序信息而不依赖预先截断的 DEGs 列表。使用 R 包 clusterProfiler 的 gseGO() 与 gseKEGG() 函数，分别基于 GO 与 KEGG 基因集进行富集 [2-4]；常见参数包括排序统计量、gene ID 类型、minGSSize、maxGSSize、pvalueCutoff 以及最终按 qvalue/p.adjust 的过滤阈值。富集结果以归一化富集得分 (Normalized Enrichment Score, NES) 与 padj 进行排序，使用 enrichplot::gseaplot2 绘制 top [5] 激活与 top [5] 抑制通路的 running enrichment 图 [5]。
```

## 2.X KEGG 通路可视化 (按需添加)

```markdown
### 2.X KEGG 重点通路可视化

对感兴趣的 KEGG 通路 ([hsaXXXXX / mmuXXXXX])，使用 R 包 pathview 将差异基因的 log2FoldChange 映射至 KEGG 通路图谱中相应的基因节点 [1-2]。pathview 将基因、代谢物或统计量与 KEGG pathway 拓扑图进行 ID 映射，特点是能够把差异分析结果放回标准通路图中展示节点方向和幅度。报告需写明 pathway ID、species KEGG code、gene ID 类型、输入统计量列和颜色截断范围。
```

---

# WGCNA — 加权基因共表达网络分析

## 2.X WGCNA 模块构建

```markdown
### 2.X 加权基因共表达网络构建

对样本 × 基因的归一化表达矩阵（通常筛选保留方差 top [25%–50%] 或表达量 top [N] 的基因）使用 R 包 WGCNA 进行加权基因共表达网络分析 [1]。WGCNA 基于基因表达相关性构建加权网络，通过 soft-threshold power 将相关系数转换为邻接强度，并以拓扑重叠矩阵 (Topological Overlap Matrix, TOM) 衡量基因共享邻居结构；其特点是可把大量基因压缩为共表达模块和模块特征基因 (Module Eigengene, ME)，便于后续与样本性状关联。首先以样本层次聚类树识别可能的离群样本并进行剔除；其次基于无标度网络拓扑准则筛选最优 soft-threshold power β，候选值为 `1:10` 与 `12:50 by 2`，选取使得 scale-free 拓扑拟合优度 R² 首次超过 [0.85] 的最小 β 值；如项目使用经验回退值，应写明实际 β。基于该 β 值构建邻接矩阵，转换为 TOM；`pickSoftThreshold` 使用 `blockSize=50000`，`blockwiseModules` 使用项目配置的 networkType、minModuleSize 与 mergeCutHeight，并设置 `numericLabels=TRUE`、`pamRespectsDendro=FALSE` 与 `saveTOMs=TRUE`。对 1-TOM 距离矩阵进行层次聚类，使用 dynamicTreeCut 动态混合树切割得到初始模块，并对模块特征基因相关性 > [0.75] (即 dissimilarity < 0.25) 的模块进行合并，最终得到共表达模块集合。
```

## 2.X 模块-性状关联与枢纽基因鉴定

```markdown
### 2.X 模块-性状关联与枢纽基因鉴定

将各模块特征基因 (ME) 与样本临床/表型变量 ([生存时间 / 分组 / 评分等]) 进行 Pearson 相关分析，得到模块-性状关联热图，使用相关系数与对应 p 值识别与目标性状相关的模块 [1]。ME 是模块内基因表达模式的第一主成分，特点是用一个连续变量概括模块整体表达变化。在关键模块内基于基因模块内连接度 kME (Module Membership, 基因与模块 ME 的 Pearson 相关系数) 与基因-性状显著性 GS (Gene Significance) 的散点图 (verboseScatterplot) 鉴定枢纽基因 (hub genes)，筛选阈值为 |kME| > [0.8] 且 |GS| > [0.2]，如项目调整需填入实际值。
```

---

# ceRNA 网络分析

## 2.X miRNA 靶基因预测

```markdown
### 2.X miRNA 靶基因预测

差异表达 miRNA 与潜在 lncRNA / circRNA 上下游靶基因关系通过 starBase / ENCORI 数据库 (https://rnasysu.com/encori/) 在线 API 进行预测 [1]。starBase 整合 CLIP-seq 支持的 RNA-RNA 和 RNA-蛋白互作信息，并结合多个 miRNA 靶标预测来源，特点是可为 ceRNA 网络提供带实验或多工具支持的候选互作对。对每个查询 miRNA，提取该数据库整合的 [CLIP-seq 实验支持] 的 miRNA-mRNA 与 miRNA-lncRNA 互作对；筛选至少被 [k≥3] 个独立预测工具支持的高置信靶基因。
```

## 2.X ceRNA 网络构建

```markdown
### 2.X 竞争性内源 RNA (ceRNA) 网络构建

基于"lncRNA / circRNA 通过竞争性结合共同 miRNA 调控 mRNA 表达"的 ceRNA 网络模型，将差异表达的 lncRNA / circRNA、miRNA 与 mRNA 三层节点按以下规则连边：(1) miRNA 与 mRNA 之间的边来自 2.X miRNA 靶基因预测；(2) lncRNA / circRNA 与 miRNA 之间的边同样来自 starBase 整合的预测 [1]；(3) 同时保留 lncRNA-mRNA 表达呈正相关（Pearson r > [0.3], p < 0.05）且与共同 miRNA 表达呈负相关 (r < -[0.3]) 的 ceRNA 三元组。该网络构建方法的特点是把预测互作和表达相关性过滤结合，输出可在 Cytoscape 中查看的 RNA 三层调控关系 [2]。最终网络使用 Cytoscape 进行可视化与拓扑分析，节点属性、边类型和相关性阈值需写入方法段。
```

---

# 网络药理学 (Pharmacology Network)

> 常见方法组合：BATMAN-TCM 数据库的中药成分-靶点关联；AutoDock Vina 蛋白-小分子对接（含 fpocket 结合口袋预测）；PLIP + PyMOL 相互作用可视化；Cytoscape 网络构建。

## 2.X 中药成分-靶点关联

```markdown
### 2.X 中药化学成分与潜在靶点筛选

对研究纳入的 [N] 味中药通过 BATMAN-TCM v2 数据库 (http://bionet.ncpsb.org.cn/batman-tcm/) 检索其化学成分及潜在靶点蛋白 [1]。BATMAN-TCM 整合已知和预测的中药成分-蛋白相互作用，基于相似性、功能关联和统计评分提供成分-靶点候选关系，特点是可将中药成分、靶点蛋白和疾病基因整理为网络分析输入。成分层面以 BATMAN-TCM 结果列中给出的 [类药性/成药性相关信息，例如 OB / DL / 数据库默认 score；以实际下载结果列名为准] ≥ [评分阈值] 筛选；成分-靶点关联以数据库提供的预测得分及对应 p-value < [0.05] 筛选高置信关联对。所使用的列名与阈值以实际 BATMAN-TCM 检索结果的列定义为准，在结果表中明确标注。
```

## 2.X 成分-靶点-疾病网络构建

```markdown
### 2.X 网络构建与拓扑分析

将筛选后的中药、成分、潜在靶点蛋白及目标疾病相关基因导入 Cytoscape 进行多层网络可视化 [1]。Cytoscape 以节点和边表示生物分子及其关系，特点是可把节点属性、边属性、表达量、富集结果和拓扑指标整合在同一网络中。节点按类型 (中药 / 成分 / 蛋白靶点 / 疾病基因) 着色，边代表"中药-成分""成分-靶点"以及"靶点-疾病"关联。基于 CytoHubba 插件的度中心性 (degree)、介数中心性 (betweenness) 等拓扑指标筛选网络中的关键节点 (hub nodes) [2]；报告需写明节点/边来源、置信度阈值、去重规则和使用的拓扑指标。
```

## 2.X 靶点功能富集 (复用上方 GO/KEGG 段落)

参考上方 [GO / KEGG 富集分析 (ORA)](#2x-go--kegg-富集分析-ora) 段落，将基因输入替换为"中药-疾病交集基因集合"。

## 2.X 蛋白-小分子分子对接

```markdown
### 2.X 蛋白-小分子分子对接

针对网络中关键的"成分-靶点"对开展分子对接。受体蛋白三维结构由 RCSB Protein Data Bank 下载（PDB 编号见结果表）[1]，使用 PyMOL 移除结晶水分子、共结晶配体及非催化辅基并进行结构可视化 [2]；小分子配体由其 PubChem / ChEMBL SMILES 经 RDKit 与 Open Babel 生成三维构象并进行 MMFF94 能量最小化，构象生成使用固定随机种子以保证结果可复现 [3-6]。受体口袋使用 fpocket 自动识别；fpocket 基于蛋白表面的几何空腔和 alpha sphere 识别潜在结合口袋，特点是不依赖已知配体即可为 docking 网格中心选择提供依据 [7]。对接采用 AutoDock Vina (v[1.2.x])；Vina 通过构象搜索和经验评分函数预测配体结合姿势及亲和力，特点是能输出多个 docking pose 和对应 predicted binding affinity [8-9]。口袋优先选择 `P_0`，否则选择 simpleScore / drugScore 最高的口袋；对接盒中心来自几何口袋中心，X/Y/Z 尺寸均按最大口袋半径计算。每对受体-配体使用 Vina `exhaustiveness=8`、`energy_range=3`、`num_modes=9` 进行搜索；选取 Vina 预测亲和力数值最低（绝对值最大，kcal/mol）的构象作为代表性对接构象。
```

## 2.X 蛋白-配体相互作用可视化

```markdown
### 2.X 蛋白-配体相互作用解析与可视化

对各对接最佳构象，使用 PLIP (Protein-Ligand Interaction Profiler) 解析蛋白-配体之间的氢键、疏水接触、π-π 堆积、盐桥及水桥等相互作用 [1]。PLIP 根据距离和角度规则自动识别非共价相互作用，特点是可将 docking pose 转换为残基-配体作用列表和可解释的相互作用图。使用 PyMOL 绘制相互作用细节图 (含残基侧链、氢键虚线、距离标注) 并输出 PNG 图像 [2]；报告需写明展示的 pose、配体 ID、关键残基和相互作用类型。
```

## 2.X 量子化学优化 (可选)

```markdown
### 2.X 量子化学结构优化 (可选)

对关键小分子配体使用 Psi4 程序在 [B3LYP/6-31G(d) / HF/3-21G] 水平下进行密度泛函结构优化与单点能计算 [1]。Psi4 是开源量子化学程序，可通过 Hartree-Fock、DFT、MP2 等电子结构方法计算小分子能量和电子性质；其特点是能在明确方法、基组、电荷和自旋多重度的条件下输出可复现的量子化学描述符。若未另行指定，电荷为 0、多重度为 1，方法为 B3LYP，基组为 6-31G*，并设置 `scf_type df`。输出包括优化构象与前线轨道能量 (HOMO / LUMO) 等量子化学描述符。
```

---

# Immune Infiltration / Pathway Scores

## 2.X GSVA / ssGSEA 通路评分

```markdown
### 2.X 通路活性评分分析

基于样本 × 基因表达矩阵，使用 GSVA / ssGSEA 计算每个样本的基因集活性评分 [1-2]。GSVA/ssGSEA 将表达矩阵转换为样本 × 基因集的评分矩阵，原理是在样本内或样本间比较基因集成员相对于其他基因的排序分布；其特点是不需要先设定差异基因阈值，适合对通路、免疫功能或代谢模块进行样本级量化。基因集来自 [MSigDB Hallmark / KEGG / GO / 自定义 GMT]，表达矩阵单位为 [log2(TPM+1) / log2(CPM+1) / normalized expression]，常见参数包括 minGSSize=[10]、maxGSSize=[500]、kcdf=[Gaussian/Poisson] 和后续分组比较方法 [limma / Wilcoxon / t-test]。
```

## 2.X CIBERSORT / xCell / ESTIMATE / MCP-counter 免疫浸润评分

```markdown
### 2.X 免疫浸润与微环境评分

基于 bulk 表达矩阵，使用 [CIBERSORT / xCell / ESTIMATE / MCP-counter] 进行样本级免疫浸润或微环境评分 [1-4]。CIBERSORT 基于支持向量回归和参考 signature matrix 估计细胞组成比例；xCell 使用细胞类型 signature 与 ssGSEA 风格评分并进行 spillover compensation；ESTIMATE 基于 immune 与 stromal signature 计算 ImmuneScore、StromalScore 和 ESTIMATEScore；MCP-counter 使用标志基因集合计算免疫和基质细胞群的丰度评分。这类方法的共同特点是可从 bulk 表达谱中获得样本层面的细胞组成或富集评分，但输出指标含义取决于具体方法：CIBERSORT 常为相对比例，xCell/MCP-counter/ESTIMATE 多为队列内可比较的评分。报告需写明输入表达单位、基因 ID 类型、signature 版本、是否做 quantile normalization、permutation 次数或 score 转换方式。
```

---

# Metabolomics

## 2.X 非靶向代谢组数据处理与差异代谢物筛选

```markdown
### 2.X 非靶向代谢组数据处理

[LC-MS / GC-MS] 原始数据使用 [XCMS / MS-DIAL / tidymass / MetaboAnalystR] 进行峰检测、保留时间校正、峰匹配、缺失值处理和特征定量 [1-4]。XCMS 从 m/z 与保留时间二维信号中提取代谢特征并进行非线性保留时间对齐；MS-DIAL 将 MS1 定量特征与 MS/MS 谱图解卷积和谱库匹配结合；tidymass 以统一 R 对象组织峰表、样本信息、注释和统计结果；MetaboAnalystR 提供归一化、统计分析和通路解释模块。这些方法的特点是将原始质谱信号转换为样本 × 代谢特征矩阵，便于后续 QC、差异分析和代谢物注释。报告需写明离子模式、峰检测算法、ppm、peakwidth、MS1/MS2 tolerance、保留时间校正方法、缺失值过滤比例、QC RSD 阈值、归一化/标准化方法和代谢物注释等级。

差异代谢物筛选基于归一化后的样本 × 代谢物矩阵进行，常用统计量包括 fold change、t-test/Wilcoxon/limma p 值、FDR、PCA/PLS-DA/OPLS-DA 得分和 VIP 值。若使用 PLS-DA 或 OPLS-DA，应写明交叉验证方式、置换检验、VIP 阈值和模型评价指标；最终差异代谢物阈值按项目实际设置填写，例如 |log2FC| > [1]、FDR < [0.05] 和 VIP > [1]。
```

## 2.X 代谢通路富集分析

```markdown
### 2.X 代谢通路富集分析

差异代谢物基于 [KEGG / HMDB / MetaboAnalyst pathway library] 注释结果进行通路富集或 pathway impact 分析 [1]。该分析以已注释代谢物列表为输入，检验特定代谢通路中差异代谢物数量是否高于背景期望，并可结合通路拓扑计算 impact score；特点是将单个代谢物变化汇总到代谢通路层面。报告需写明物种、代谢物 ID 类型、背景集合、富集检验方法、多重检验校正、p/q 阈值和 pathway impact 阈值。
```

---

# Microbiome

## 2.X 扩增子测序去噪与物种注释

```markdown
### 2.X 扩增子数据处理与物种注释

16S/ITS 扩增子测序数据使用 QIIME 2 与 DADA2 进行数据导入、质量控制、去噪、嵌合体去除和 ASV 表构建 [1-2]。QIIME 2 以 artifact 保存数据对象和 provenance，特点是提高微生物组分析的可追溯性；DADA2 通过学习 Illumina 测序错误模型从 reads 中推断精确的 amplicon sequence variants (ASVs)，相比传统 OTU 聚类具有更高序列分辨率。分类注释使用 [SILVA / Greengenes / UNITE] 数据库和 [Naive Bayes / consensus BLAST] 分类器完成。报告需写明测序区域、引物剪切长度、trim/trunc length、maxEE、chimera 去除策略、分类数据库版本、分类器版本和 ASV 过滤阈值。
```

## 2.X 微生物群落多样性与排序分析

```markdown
### 2.X 群落多样性与排序分析

ASV/OTU 丰度表、分类注释表和样本分组信息使用 phyloseq 与 vegan 进行群落数据整理、多样性计算和排序分析 [1-2]。phyloseq 将丰度矩阵、taxonomy、sample metadata 和系统发育树整合为统一对象，便于在 R 中进行过滤、聚合和可视化；vegan 提供 Shannon、Simpson、Bray-Curtis、Jaccard、UniFrac、PCoA/NMDS 和 PERMANOVA 等群落生态统计方法。报告需写明输入丰度类型、分类聚合层级、稀释深度或转换方法、alpha diversity 指标、beta diversity 距离、ordination 方法、PERMANOVA 公式和置换次数。
```

## 2.X 差异菌群分析

```markdown
### 2.X 差异菌群分析

差异菌群分析使用 [LEfSe / ANCOM-BC / ANCOM-BC2] 进行 [1-3]。LEfSe 结合 Kruskal-Wallis 检验、成对 Wilcoxon 检验和线性判别分析 (LDA) effect size，适合输出组间差异分类单元及 cladogram；ANCOM-BC 通过估计并校正微生物组组成型数据中的抽样分数偏差，在回归框架下计算差异丰度；ANCOM-BC2 进一步支持多组比较、协变量校正和重复测量设计。这类方法的特点是针对稀疏、组成型微生物组丰度数据进行统计建模，报告需写明分类水平、丰度过滤阈值、设计公式、协变量、p 值校正方法、LDA score 或 log fold change 阈值。
```

---

# ATAC-seq / ChIP-seq

## 2.X Peak calling 与区间注释

```markdown
### 2.X Peak calling 与区间注释

比对后的 ATAC-seq / ChIP-seq BAM 文件使用 MACS2 进行 peak calling [1]。MACS 通过建模正负链 reads 位移提高结合位点分辨率，并使用局部背景模型评估 peak 显著性；其特点是适合从 ChIP-seq 或 ATAC-seq reads 中识别开放染色质区域或蛋白结合富集区域。peak 注释使用 ChIPseeker 基于 [TxDb / EnsDb / GTF] 将 BED/narrowPeak 区间映射至 promoter、exon、intron、distal intergenic 等基因组功能区域，并计算到最近 TSS 的距离 [2]。报告需写明参考基因组、genome size、control/input 使用情况、narrow/broad 模式、q value/p value 阈值、blacklist 过滤、TSS 窗口和 promoter 定义。
```

## 2.X Motif 富集分析

```markdown
### 2.X Motif 富集分析

Peak 序列使用 HOMER 进行已知 motif 富集和 de novo motif 发现 [1]。HOMER 将目标 peak 序列与背景序列比较，检验特定转录因子结合 motif 在目标区间中的富集程度；其特点是可将 ATAC/ChIP peak 集合转换为转录因子结合序列模式和富集排名。报告需写明输入 peak 集合、背景序列选择、基因组版本、peak 中心窗口大小、motif 长度、motif 数据库版本、p/FDR 阈值和富集倍数。
```

## 2.X 差异 peak 分析

```markdown
### 2.X 差异 peak 分析

差异 peak 分析以 consensus peak 区域上的 reads count 矩阵为输入，使用 DESeq2 或 DiffBind 进行组间差异可及性/差异富集检验 [1-2]。DESeq2 对每个 peak 的 count 使用负二项广义线性模型，估计 size factor、离散度和组间 fold change；DiffBind 封装 peak 集合读取、consensus peak 构建、reads 计数、归一化和差异分析步骤，适合 ChIP/ATAC 多样本差异结合分析。报告需写明 consensus peak 构建规则、count 方法、设计公式、批次/协变量、contrast、Wald/LRT 或 edgeR/DESeq2 后端、padj 和 log2FC 阈值。
```

---

<a name="methods-requiring-confirmation"></a>

# Methods Requiring Confirmation

以下方法只有在项目结果或实施记录明确显示已运行时才能写入报告。若报告确实需要这些模块，必须按本文件的深度合同重新撰写：输入/输出对象、算法或统计原理、方法特点、实际可报告参数、真实引用。若这些模块已经产生真实结果图，仍需按 `figure_manifest.tsv` 覆盖每一种图类型；只是方法段落不能从本文件虚构。

| 类别 | 不覆盖的具体方法 |
|---|---|
| 空间组学 | Visium, Stereo-seq, Xenium, MERFISH 等 |
| 多组学整合 | WNN, CITE-seq, MOFA+, MEFISTO, Seurat anchor-based integration |
| scRNA 批次整合 | Harmony, scANVI, BBKNN, Scanorama, fastMNN |
| scRNA 双细胞检测 | DoubletFinder, scDblFinder (本流程仅使用 Scrublet) |
| scRNA 参考映射注释 | Azimuth, CellTypist, SingleR, scmap |
| 细胞-细胞通讯 | NicheNet, CellPhoneDB, ICELLNET |
| 恶性细胞推断 | CopyKAT, SCEVAN |
| 扰动敏感性 | DA-seq, Milo, scCODA |
| 拟时序 / 轨迹 | Monocle (v2/v3), Slingshot, PAGA, scVelo, dynVerse |

> **写报告时务必交叉核对**：方法段落里出现的每一个软件名、参数与算法步骤，都应当能在项目结果、参数清单、代码、日志或实施人员说明中找到对应证据；找不到的，要么改写为已确认方法，要么补充确认后再交付。
