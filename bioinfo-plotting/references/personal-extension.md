# 个人绘图扩展

本机 `/opt/miniconda3/envs/sc` 为当前账户优先加载 `~/miniconda3` 下的 ytbiokit；独立扩展位于 `/home/taojj/miniconda3/plugins/ytbiokit-user`。新进程用 `python -m ytbiokit_user status` 核查来源。

| 输入与目的 | 入口 | 默认输出 |
|---|---|---|
| 已计算的相关系数及 P/q/n 矩阵 | `yt.pl.correlation_heatmap` | 无对角线占位的紧凑相关性图及完整表 |
| 样本级 DataFrame，两个数值变量 | `yt.pl.scatter_regression` | 散点、OLS 回归线、95% 拟合均值置信带；按组分别出图及完整统计表 |
| 标准化的基因×样本矩阵、样本分组、已定稿模块及可选富集结果 | `yt.pl.expression_module_heatmap` | 左侧描述性箱线图＋模块表达热图＋可用的富集注释，默认 PDF/PNG300 |
| 已标准化的基因×donor/分组矩阵及列注释 | `yt.pl.expression_comparison_heatmaps` | 组别分块和 donor 内配对两张表达热图 |
| 同一模型的 WT/扰动预测矩阵 | `yt.pl.virtual_knockout_heatmaps` | 联合行 Z-score 预测表达图、原尺度 KO-WT 差值图 |
| 定稿 AnnData，执行单步条件预测 | `yt.tl.virtual_knockout` | `plot=True`，默认生成上述两张预测图，保存模型与 donor 统计 |

接口参数和调用例见 [扩展说明](/home/taojj/miniconda3/plugins/ytbiokit-user/README.txt)。按输入真实字段传 `donor_key`、`group_key`、`control_group`、`treatment_group`，按对象传 donor/基因清单和顺序；函数检查配对及矩阵对齐。相关性统计仍按原 [相关性矩阵规范](matrix-correlation-heatmaps.md) 预先计算。观测表达输入由既定 pseudobulk/TMM 等流程生成，绘图入口不自动重算标准化或显著基因。条件预测不等于实际敲除或因果效应，肿瘤细胞训练必须使用已通过既定纯度门槛的子集。

参数权威来源为 [defaults.json](/home/taojj/miniconda3/plugins/ytbiokit-user/defaults.json)；主包默认值、插件版本摘要、参数 old/new 和维护事件统一写入 [CHANGELOG.md](/home/taojj/miniconda3/CHANGELOG.md)。用 `python -m ytbiokit_user set <section.parameter> <value>` 修改持久化绘图参数，保留校验、备份和统一日志。分析参数按调用传入并写入 workdir 的运行记录。

散点图传 `x/y` 变量列、`sample_key` 样本列及可选 `groupby`。默认 `method="pearson"`、`ci=0.95`，可显式选择 Spearman；相关性方法和原尺度 OLS 回归是两个明确的统计内容。每组内重复样本默认拒绝，须先汇总或显式传 `aggregate="mean"/"median"`；bootstrap 按样本重采样，置信带为拟合均值逐点区间。组内 P、BH q 的校正范围是本次调用，不能当成跨所有基因对的校正结果。缺失值成对剔除，样本不足和常数输入标记不可检验。指定 `outdir` 自动写 PDF、PNG300、统计/拟合/绘图点/剔除/参数表，未指定则返回图和表。具体统计单位与方法仍遵循 [表达与相关性绘图规范](expression-plots.md)。

扩展与参数保存在主包之外；使用 `python -m ytbiokit_user upgrade /path/to/ytbiokit-NEW-py3-none-any.whl` 升级本地 wheel，执行前备份、执行后验证接口。独立保存不保证任意未来版本的 API 兼容，兼容性失败须核查适配器。插件更新需提升插件版本、追加版本摘要，并保留原脚本来源指纹及验证记录。

表达模块组合图为独立接口，按 [ClusterGVis 布局规范](clustergvis.md) 绘制。差异分析后可传 `genes` 选择已筛选基因，必须提供对应 `modules`；不自动替用户重做差异、聚类或富集。`group_key`、`donor_key`、对照/实验组名及排序可配置。左侧箱线图的分布单位是模块内基因，属于描述性注释，不能用于基于基因数的组间显著性检验。全量富集 P/q 保留，具体统计列和含义由 `pvalue_key/pvalue_label` 声明。

CellPhoneDB 已于 2026-10-27 冻结，细胞通讯默认使用原生 CellChat：`ytbiokit cellchat run/compare` 或工作流 `.cellchat()`。个人扩展会阻止 `yt.pl.sc.cellphonedb_viz` 的函数和类构造；该命名空间中的 `CellChatViz/CellChatVizPlus` 实际属于 CellPhoneDB，也在冻结范围内。原始文件保留，不自动解冻、不以它代替 CellChat。配置位于 `cell_communication.cellphonedb_frozen`。

原生富集总览 `enrich_combined_plot.pdf/png` 是 `ytbiokit enrich go-kegg` 的默认输出；每类最多10条且至少有5个合格条目才显示该类，全部不足时不生成空图。它是 ORA，总览横轴按实际标签显示 pvalue 或 qvalue；GSEA 冻结规则不受影响。
