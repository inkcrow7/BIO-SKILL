# 已有 regulon 结果的绘图

适用于完成 pySCENIC 后的 adj.csv、含 RegulonsAUC 的 output.loom 及最终 h5ad 的重绘；本分支不运行 grn/ctx/aucell。按请求生成 importance 分布、AUCell 评分 UMAP、regulon AUC 热图、TF 表达热图。

- 严格以 cell ID 对齐 AUC、h5ad 元数据和最终细胞集合，记录交集与排除。保留 regulon→TF 映射、正负 regulon 区别以及 top N 选择依据；不要凭截断字符串错误合并 regulon。
- Importance 直方图展示网络边权分布并说明单位；它不检验生物学组间差异。
- AUCell 作为评分通过 `yt.pl.sc.save_gene_list_exprs` 绘制；必要时使用临时评分对象并复制最终 UMAP，见 [单细胞口径](scrna-data.md)。不基于 AUC 重新计算 UMAP，也不增加点样式美化。
- Regulon AUC 热图用 Marsilea ClusterBoard，TF 表达热图用 Marsilea Heatmap。按 donor/sample × cell_type × group 汇总后组织组间比较，保持样本等权；只按细胞类型池化的均值用于描述，不支持独立重复推断。
- TF 表达使用核实的表达层，记录归一化和 log1p；所需层缺失时不能静默使用 X。已经 log 的数据不再次 log1p。热图缩放方向、距离和聚类方法见 [热图规范](heatmap-style.md)。
- 将可调热图参数保存在项目 YAML/配置中，使用目标环境实际 API。旧 pyscenic-plot 的 plot_pyscenic.py 会重算 AUC UMAP且可静默回退表达层，不能直接作为当前规范的出图入口；如复用其中热图代码，先修正上述行为。
- 输出名描述 `regulon_auc_heatmap`、`tf_expression_heatmap`、`regulatory_edge_importance_histogram` 等分析内容，遵循主 skill 的命名与交付规则；软件包名写入运行记录。
