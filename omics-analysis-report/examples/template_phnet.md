# [中药 / 复方名称] - [疾病名] 网络药理学与分子对接结果报告

<!--
Template: 网络药理学 (BATMAN-TCM + Cytoscape + AutoDock Vina + PLIP + PyMOL)
方法对应 methods-snippets.md "网络药理学" + "功能富集" 章节。
图对应 figure-catalog.md "网络药理学" + "功能富集" 区。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：输入对象、数据库来源和疾病基因集合来源
- 第二句：本报告覆盖的输出图型（多层网络、Venn、富集、Vina 评分、构象图、PLIP/PyMOL 图；不单独展示 legend-only 图）
- 第三句：本报告将说明每类图表怎么看以及网络/评分表/结构图如何使用
- 末尾：只说明数据库、网络、评分表和结构图结果，不扩展为数据展示范围之外的结论]

## 2. 方法

### 2.1 数据收集与对象选择

研究对象为 [中药 / 复方名称]，包含 [N] 味中药：[药材列表 (拉丁学名)]。通过 BATMAN-TCM v2 数据库 (http://bionet.ncpsb.org.cn/batman-tcm/) 检索各味中药的化学成分及其对应的潜在靶点蛋白；目标疾病为 [疾病名]，通过 [GeneCards / OMIM / DisGeNET] 等公开疾病-基因关联数据库收集疾病相关基因集合。

### 2.2 中药化学成分与潜在靶点筛选

对研究纳入的 [N] 味中药通过 BATMAN-TCM v2 数据库检索其化学成分及潜在靶点蛋白。以药物相似度评分 (drug-likeness score) ≥ [评分阈值] 筛选具有成药性的成分；以 BATMAN-TCM 的 cluster relevance score ≥ [评分阈值] 与 p-value < [0.05] 筛选高置信成分-靶点关联对。

### 2.3 中药-成分-靶点-疾病多层网络构建

将筛选后的中药、成分、潜在靶点蛋白及目标疾病相关基因导入 Cytoscape 进行多层网络可视化。节点按类型 (中药 / 成分 / 蛋白靶点 / 疾病基因) 着色，边代表"中药-成分""成分-靶点"以及"靶点-疾病"关联。基于 CytoHubba 插件的度中心性 (degree)、介数中心性 (betweenness) 等拓扑指标筛选网络中的关键节点 (hub nodes) 作为重点候选成分-靶点对。

### 2.4 中药-疾病交集基因功能富集

[复用 methods-snippets.md "GO / KEGG 富集分析 (ORA)"，输入基因列表为中药潜在靶点与疾病基因的交集。]

将中药潜在靶点与疾病基因的交集（即中药-疾病交集基因）作为输入，使用 R 包 clusterProfiler 的 enrichGO() 与 enrichKEGG() 分别进行 GO 与 KEGG 过表征分析。

### 2.5 蛋白-小分子分子对接

针对网络中关键的"成分-靶点"对开展分子对接。受体蛋白三维结构由 RCSB Protein Data Bank 下载（PDB 编号见结果表），使用 PyMOL 移除结晶水分子、共结晶配体及非催化辅基；小分子配体由其 PubChem / ChEMBL SMILES 经 RDKit 与 OpenBabel 生成三维构象并进行 MMFF94 能量最小化。对接采用 AutoDock Vina (v[1.2.x])：受体口袋使用 fpocket 自动识别打分前 [3] 的潜在结合口袋作为对接盒中心，并以一致的盒尺寸 ([25×25×25 Å]) 覆盖关键残基。每对受体-配体进行 [exhaustiveness=8 / 32] 次独立对接，选取 Vina 评分最低（绝对值最大，单位 kcal/mol）的构象作为代表性对接构象。

### 2.6 蛋白-配体相互作用解析与可视化

对各对接最佳构象，使用 PLIP (Protein-Ligand Interaction Profiler) 解析蛋白-配体之间的氢键、疏水接触、π-π 堆积、盐桥及水桥等相互作用；使用 PyMOL 绘制相互作用细节图 (含残基侧链、氢键虚线、距离标注) 并输出 PNG 图像。

## 3. 结果

### 3.1 成分-蛋白节点网络分析

我们首先通过 BATMAN-TCM v2 数据库获取 [中药 / 复方] [N 味] 中药的高置信化学成分共 [N comp] 个、关联蛋白节点 [N tgt] 个；同时从 [疾病基因数据库] 获取 [疾病] 相关基因 [N dis] 个。两类列表交集得到交集基因 [N share] 个（图1B），并在多层网络中作为蛋白层节点展示 (图1A)。

![](Figures/phnet.network.png)
![](Figures/drug_disease.venn.png)

**图1.** A：[中药 / 复方] 中药-成分-蛋白节点-[疾病] 疾病基因多层网络，节点按类型着色（紫：中药；蓝：成分；橙：蛋白节点；红：疾病基因）；B：中药相关蛋白节点与 [疾病] 疾病基因 Venn 图，交集表示两类数据库列表的重叠部分。

### 3.2 GO/KEGG 富集分析

为展示重叠蛋白节点对应基因列表的富集结果，我们对 [N share] 个基因进行 GO BP 与 KEGG 富集（图2）。GO BP 点图展示 [代表性 BP 条目 1–3] 的 GeneRatio、Count 与校正后显著性；KEGG 点图以相同方式展示 [代表性 KEGG 条目 1–3]。对应结果表记录富集条目、校正后显著性、富集比例和命中基因集合。

![](Figures/GO_BP.dotplot.png)
![](Figures/KEGG_dot.png)

**图2.** A：重叠蛋白节点对应基因列表的 GO Biological Process 富集 top 条目点图；B：同一基因列表的 KEGG 富集 top 条目点图。

### 3.3 AutoDock Vina 分子对接分析

在网络节点筛选后，我们对 [N pair] 对"成分-蛋白"组合 ([列出 2–4 对] ) 进行 AutoDock Vina 分子对接。对接评分热图展示各组合的 Vina 预测亲和力 (kcal/mol)（图3A），其中 [成分]-[蛋白] (PDB ID: [PDB]) 的评分为 [数值] kcal/mol，并作为代表性构象展示（图3B）。

![](Figures/vina_scores.heatmap.png)
![](Figures/dock.pose.png)

**图3.** A：[中药成分] 与 [蛋白] (PDB ID: [PDB]) 的 AutoDock Vina 分子对接评分热图，值越负代表 Vina 评分模型给出的相对评分越低；B：代表性对接构象的 PyMOL 渲染图，展示配体在受体口袋内的空间位置。

### 3.4 PLIP 和 PyMOL 相互作用标注

最后，对代表性对接构象使用 PLIP 解析蛋白-配体相互作用细节（图4）。PLIP 共识别 [N hb] 个氢键、[N hyd] 个疏水接触、[N pi] 个 π-π 堆积，涉及残基包括 [列出 2–3 个残基]。该图用于查看残基位置、相互作用类型和距离标注，不扩展为作用结论。

![](Figures/PLIP.png)
![](Figures/pymol.png)

**图4.** [中药成分] 与 [蛋白] 代表性对接构象的相互作用解析图：A：PLIP 自动识别的相互作用残基与连接类型 (氢键 / 疏水接触 / π-π 堆积 / 盐桥)；B：PyMOL 渲染的残基-配体距离细节。

---

## 5. 参考文献

- [Kong2024BATMANTCM2] Kong Y et al. BATMAN-TCM 2.0: an enhanced integrative database for known and predicted interactions between traditional Chinese medicine ingredients and target proteins. Nucleic Acids Research. 2024. doi:10.1093/nar/gkad926.
- [Trott2010AutoDockVina] Trott O, Olson AJ. AutoDock Vina: improving the speed and accuracy of docking. Journal of Computational Chemistry. 2010. doi:10.1002/jcc.21334.
- [LeGuilloux2009Fpocket] Le Guilloux V, Schmidtke P, Tuffery P. Fpocket: an open source platform for ligand pocket detection. BMC Bioinformatics. 2009. doi:10.1186/1471-2105-10-168.

<!--
Lint + 渲染：
  python ~/.claude/skills/omics-analysis-report/report_lint.py <this>.md --strict-references
  python ~/.claude/skills/omics-analysis-report/md_to_html.py <this>.md -o <this>.html
-->
