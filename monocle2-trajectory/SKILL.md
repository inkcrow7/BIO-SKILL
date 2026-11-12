---
name: monocle2-trajectory
description: 基于 IPF 项目已验证流程开展 Monocle2/DDRTree 共同拟时序建模、定向、轨迹重绘、连续基因表达及热图、供体层面组间比较和动态基因核验。用于 Monocle2 拟时序、共同轨迹、拟时序基因趋势图或复用已有 CellDataSet；不自动替换为 Monocle3。
---

# Monocle2 共同拟时序

来源为 `/share/data/Projects/20260727-IPF` 的当前流程：第60步建模、第62步共同展示、第67步在共同时间轴上重算候选。读取 [来源及版本演进](references/ipf-provenance.md)，区分历史单组模型与当前共同模型。IPF 的细胞数、细胞类型、候选数和阈值是实例，不是所有项目的要求。

## 先确认任务类型

- **重新建轨**：细胞集合、表达输入、排序基因或生物学范围改变且任务要求重新推断时，按 [建模与定向](references/modeling.md) 运行；提供 [参数化建轨脚本](scripts/fit_shared_trajectory.R) 和 [IPF 参数示例](assets/ipf-example.yaml)。
- **复用模型出图**：仅修改标签展示、配色、图形或目标基因时，沿用已确认 CDS 的图、根、Pseudotime、State、counts、size factors。按 [共同轨迹与基因模式绘图](references/plotting.md) 实施。
- **动态基因或组间检验**：按 [供体统计与候选筛选](references/statistics.md) 实施，声明正在检验的模型、条件、候选集合和统计单位。旧模型的统计不得用于新模型的新结论。

## 核心要求

1. 使用当前 QC 后的原始非负整数 UMI counts、定稿细胞 ID 和最新细胞类型/亚型标签；保留 donor/sample 与 condition。先完成聚类/注释后的 FindMarkers 复核，遵循 [marker 重跑规则](/home/taojj/bioinfo-plotting/references/post-annotation-markers.md)。本 skill 的建轨输入不是整合表达、scVI 潜空间或 UMAP。
2. 正式比较围绕两组或多组组织，默认联合建一条共同轨迹，不按组独立建轨或按样本单独出轨迹图。各图共用同一坐标、时间轴与根。单组或均衡重拟合仅在任务明确需要时作为独立敏感性分析，独立轨迹的时间值和 State 编号不可直接对比。
3. 排序基因采用供体感知的变异特征等预先规定方案，避免用希望观察到的疾病 DEG 定义时间轴。起点依据先验细胞身份及 marker 程序评分，供体等权汇总支持根状态；记录并核查实际最早细胞，而非仅把某 State 叫作起点。证据不足时停止定向并报告原因。
4. 细胞级样条及合并曲线用于动态关联描述；正式条件比较先按供体汇总。保留配对/重复设计，任何一组缺少生物学重复时只描述。拟时序不是实际时间、谱系追踪或因果证据。
5. 轨迹用 `monocle::plot_cell_trajectory`，沿拟时序的表达用 `plot_genes_in_pseudotime`，模式热图用 `plot_pseudotime_heatmap`。这些是本分支的专用入口；常规表达量/评分 UMAP 仍遵循 bioinfo-plotting 的 ytbiokit 规则，沿用定稿坐标。
6. 脚本、缓存、日志、临时文件、模型及完整运行记录在用户项目内；本 skill 目录只保存可复用规范与代码。数据、参数、代码、版本和模型哈希全部匹配才复用缓存。通路富集不是本分支的自动后续步骤，GSEA 冻结状态保持不变。

## 导出与完成条件

- 使用 bioinfo-delivery 的项目目录与图表规范：内部 `Data/Processed/NN.shared_trajectory` 和 `Scripts/NN.shared_trajectory`，交付 `Tables/`、`Figures/`、中文 README 和 `figure_index.tsv`；名字写明分析内容，不包含软件包名。
- PDF + 300 dpi PNG、无 title/subtitle；每个独立轨迹视角/基因单独出图，不默认 facet 或拼图。项目配色来自 `Scripts/config/colors.yaml`。
- 保留模型 RDS、细胞/基因清单、counts来源、排序基因、根证据、逐细胞 Pseudotime/State/坐标、主图边和顶点、供体统计、完整/筛选基因表、实际作图矩阵及软件版本。不额外生成重复的 source.tsv。
- 验证细胞与基因对齐、原计数不变、真实起点、有限拟时序、图的连通性、模型与缓存哈希；重绘核对 size factor/时间轴未变；热图核对预测、变换及实际渲染矩阵。检查图例、时间轴、标签裁切、P/FDR 数值及报告链接。仅生成模板或做模拟测试时明确说明，不声称已跑真实项目。
