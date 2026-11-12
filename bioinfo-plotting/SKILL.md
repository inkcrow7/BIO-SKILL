---
name: bioinfo-plotting
description: 生信绘图与重绘规范。用于单细胞注释、bulk/单细胞表达量、评分、marker、临床注释或相关性热图、COMPASS、Mantel/linkET、基因相关性、模块热图、regulon 和 Monocle2 拟时序可视化；统一组间比较、统计单位、工具选择和交付命名。GSEA 相关绘图分支暂时冻结。
---

# 生信绘图

## 现有流程优先（所有生信分析适用）

- 开始分析或绘图前，先检查现有项目流程及个人环境中的工具，尤其是 `ytbiokit`（`import ytbiokit as yt`）及其个人扩展，核对实际版本、接口、参数和依赖。已有流程能完成任务时直接调用，不另写分析函数或重复实现其分析逻辑；项目脚本仅承担必要的输入整理、参数配置、流程调用及输出组织。
- 需要对现有流程、函数或图形进行修饰、调整、后处理，或现有能力不足而需新增分析实现时，动手前先告知用户：现有入口、具体不足、拟改内容及其对分析结果或展示的影响；不静默修改、替换或绕过现有流程。此前已明确授权的同一项调整可按原授权执行。
- 正常使用已提供且符合用户既定规范的参数不视为重写流程；依赖缺失、接口不兼容或执行失败时，先说明具体问题，不自行改写一套分析作为替代。已有冻结分支继续保持冻结。

## 暂时冻结的分支

- **GSEA 相关绘图已于 2026-10-21 按用户要求暂时冻结。** 暂停本 skill 中该分支的包选择、经典/多通路曲线、样式、图层与渐变修正、P/FDR 标签处理、调用模板及辅助脚本；不再默认应用、调用或维护，也不自动换包继续该分支。
- 本压缩包已排除 GSEA 冻结分支的历史规范及辅助脚本。普通绘图或富集任务不自动解冻；只有用户明确要求恢复/解冻后才重新启用。其他绘图分支照常使用。

## 细胞通讯接口

- **CellPhoneDB 接口已于 2026-10-27 按用户要求冻结；细胞通讯默认使用原生 CellChat。** 使用 `ytbiokit cellchat run/compare` 或工作流 `.cellchat()`，不新运行 CellPhoneDB 分析/绘图，不自动解冻。
- `yt.pl.sc.cellphonedb_viz.CellChatViz/CellChatVizPlus` 虽然名称含 CellChat，实际处理 CellPhoneDB 结果，同样冻结。保留已有结果文件；个人环境的接口保护及配置见 [个人扩展](references/personal-extension.md)。

## 比较目标与数据口径

- 正式比较围绕两组或多组之间的变化组织。样本或 donor 是生物学重复；细胞、模块内基因和技术重复不能充当独立生物学重复。保留分组、样本及配对关系，按设计计算统计量。
- 只有各组都只有一个样本、无生物学重复时，才以单样本代表比较组；此时展示描述性变化，不以细胞数或基因数支持总体推断。
- 为控制异质性而逐样本执行 QC、NMF 时，只按需输出各样本内部图，不默认将所有样本合并为比较图。
- 使用分析证据链中当前定稿的数据、注释和嵌入。明确表达矩阵、评分、标准化和变换的含义；不为图形效果重跑上游分析、改变统计结果或回退到旧数据。
- 开展谱系二次聚类时，先按全局`bioinfo-delivery`的“单细胞注释与二次聚类”规则完成子集分析，再使用该分支定稿的坐标和标签绘图；本技能的固定坐标要求针对绘图，不替代二次聚类分析流程。
- 每次聚类及细胞类型/亚型注释完成或修订后，必须在最新对象与分组上重新运行 `FindMarkers`（全簇可用 `FindAllMarkers`）并核验标签，再进行注释可视化；读取 [注释后 marker 重跑规则](references/post-annotation-markers.md)。

## 按图形类型选择入口

| 图形任务 | 指定入口 | 要求 |
|---|---|---|
| 完成细胞类型或亚群注释后的可视化 | `yt.wf.sc.do_cell_type_viz_recipe` | 每次注释完成或修订完成后运行。 |
| 基因表达量和评分图 | `yt.pl.sc.save_gene_list_exprs` | 使用 `import ytbiokit as yt`；评分按真实接口传入，必要时用临时绘图对象适配，不改原矩阵。 |
| UMAP | ytbiokit 对应入口 | 使用包内默认样式和定稿坐标，不额外美化、调点大小/透明度/描边或重算嵌入。 |
| GSEA 富集可视化 | 暂时冻结 | 不启用该分支的绘图或后处理；冻结分支的历史规范不包含在本压缩包中。 |
| 表达模块热图与富集注释 | `ClusterGVis::visCluster` | 左侧用箱线图替换趋势图；实施时读取 [ClusterGVis 规范](references/clustergvis.md)。 |
| bulk 表达量、marker、患者层面验证、基因相关性 | 按数据口径选择 | 读取 [表达量与相关性](references/expression-plots.md)；表达量与评分仍优先使用上述指定入口。 |
| 相关性矩阵、COMPASS、Mantel/linkET | 无方格线的紧凑相关矩阵渲染器、COMPASS、linkET | 相关性矩阵数值文字随系数红蓝深浅着色；读取 [相关性与注释热图](references/matrix-correlation-heatmaps.md)。 |
| 一般表达/临床注释热图 | ComplexHeatmap | 读取 [热图样式](references/heatmap-style.md)。 |
| 已有 pySCENIC 结果的 regulon/TF 热图 | Marsilea | 读取 [regulon 绘图](references/regulon-plots.md)；AUCell 评分图使用指定评分入口和定稿 UMAP。 |
| Monocle2 共同拟时序、连续基因趋势及模式热图 | Monocle2 原生轨迹/基因趋势/热图入口 | 使用 [Monocle2 拟时序 skill](/home/taojj/monocle2-trajectory/SKILL.md)，沿用定稿共同模型；本分支专用绘图入口与常规表达/评分 UMAP 区分。 |

表达量和评分的矩阵适配、单细胞汇总读取 [单细胞数据口径](references/scrna-data.md)。表中专用工具用于各自图形类型；表达量、评分及注释图使用用户指定的 ytbiokit 入口。接口参数以目标环境实际版本为准。依赖缺失或接口不兼容时说明具体问题，不静默更换绘图库。

本机 `sc` 的个人扩展提供紧凑相关性矩阵、donor 配对表达对比和虚拟敲除预测热图；UMAP 默认白红且零值白，`yt.pl.heatmap` 默认蓝白红。调用这些扩展、修改默认参数或升级主包时读取 [个人扩展与更新日志](references/personal-extension.md)。这些默认值仅适用于此个人环境。

## 统计、导出与核对

- 分组比较图按生物学分组组织，可保留各生物学重复的点；不把逐样本两两比较作为研究目标。单细胞推断使用样本汇总、pseudobulk 或控制重复结构的模型。
- 可检验的表达量或评分组间比较，按设计显示显著性符号与精确 P 值，保留完整统计表；多重比较明确校正方式。样本量不足时记录 `insufficient_n`，不伪造显著性。
- 项目配色、分组顺序和尺度在同类图之间保持一致。UMAP 仍使用 ytbiokit 默认样式，不套用其他技能的额外美化流程。
- 图形同时导出 PDF 和 300 dpi PNG；图片名称按分析内容命名，写明对象、分组比较、基因或通路及图形类型，不包含绘图包或库的名字（如 `ytbiokit`、`ClusterGVis`、`corrplot`、`Marsilea`）。例如 `THEM6_Tumor_vs_Control_expression_boxplot.pdf`、`marker_gene_correlation_heatmap.png`。PDF/PNG 共用文件名主体。包版本记入运行记录，代码保存到项目 `Scripts/`。
- 按上述规则显式设置输出名；绘图函数只支持自动文件名时，在导出后重命名并同步 `figure_index.tsv`、报告链接及其他引用，检查重名冲突。此规则约束图片文件名，不改真实基因、通路、算法名称或函数调用。
- 遵循项目现有 `Tables/`、`Figures/`、统计表及 `figure_index.tsv` 交付规范，不新增重复的 `source.tsv`。统计适用性、模型和表字段读取 [统计与交付](references/statistics-and-delivery.md)。
- 项目文件夹及各级输出子目录按分析内容命名，不以软件包名命名（包括 `ytbiokit`）；遵循 `bioinfo-delivery` 的目录命名规则，路径变动时同步图形索引及报告引用。
- 图形不加 title/subtitle；独立图按对象分别输出。用户指定的 ClusterGVis 热图/箱线图/注释组合保持为完整图形，不拆散其对应关系。
- 检查最终图中的坐标含义、统计单位、分组、P 值字段、模块顺序及注释是否一致，并检查导出文件的字体、裁切和可读性。未提供真实数据时仅交付规范或调用模板，不声称已生成或验证实际分析图。
