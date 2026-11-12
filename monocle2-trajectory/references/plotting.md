# 共同轨迹与连续表达图

采用 IPF 第62步及第67步的当前口径，读取同一个 Joint CDS，在同一空间中展示所有条件；不默认恢复第60步的 Control/IPF/DonorBalanced 独立模型及分开高亮图。项目条件和细胞类型顺序从当前 metadata/config 读取。

## 轨迹图与固定 UMAP

- 使用 `monocle::plot_cell_trajectory(cds, color_by=...)`，按 Pseudotime、最终细胞类型、粗身份、condition、State 分别导出独立图。所有视角共享原图、根及时间范围，State 和分支编号只属于该模型。
- 细胞数及分支覆盖检查每供体贡献，不以某组细胞更多支持组间富集。需要组间统计时用供体汇总，见 [统计](statistics.md)。
- 已有上游 UMAP 仅作标签/时间投影，保持定稿坐标，用 ytbiokit 对应入口及默认样式；不能将 DDRTree 图称作 UMAP，也不能把固定 UMAP 当作新拟时序推断。

## 逐基因趋势图

```r
sub <- cds[genes, ]
stopifnot(identical(sizeFactors(sub), sizeFactors(cds)),
          identical(pData(sub)$Pseudotime, pData(cds)$Pseudotime))
for (gene in genes) {
  p <- monocle::plot_genes_in_pseudotime(
    sub[gene, ], color_by = cell_type_column,
    trend_formula = "~sm.ns(Pseudotime, df=3)", relative_expr = TRUE,
    min_expr = 0.1, horizontal_jitter = 0, vertical_jitter = 0
  )
  p$facet <- ggplot2::facet_null()
  # 读取项目分类配色，设置明确的拟时序/表达坐标、移除 title/subtitle，再输出 PDF/300dpi PNG。
}
```

这是沿时间轴的专用绘图入口；通用基因表达/评分 UMAP 仍用 ytbiokit。每基因一图，默认两组共同显示，按当前细胞身份着色并保留原生合并平滑曲线。自然样条不要求单调；不能为上升形态篡改拟合值。这里的合并描述性拟合不等于含 donor 的推断模型，也不自动增加组间箱线图或检验。

IPF 验证版本的原生点值是 `pmax(round(raw_count / Size_Factor), min_expr)`，纵轴采用 log10，需明确区分原 counts、未取整相对表达、实际显示点与拟合期望。提取 `p$data` 并按 Cell/cell ID 回核到 CDS，保留实际显示表；其他版本先读真实实现，不能假定沿用此变换。

## 拟时序热图

- 使用 `genSmoothCurves` / `plot_pseudotime_heatmap` 的真实原生拟合。IPF 示例为100个等间隔时间点、`~sm.ns(Pseudotime,df=3)`、相对表达，之后 `log10(predicted+1)`、逐基因 Z-score、显示截断 [-3,3]。预测、时间网格、未截断 Z-score 和最终显示矩阵分别可追溯。
- 保留实际选择基因及预定顺序；IPF 的当前20候选为固定排序、不再聚类。新任务需要聚类时明确声明，不强制所有任务20基因或固定行序。常数/无法拟合的基因显式列出原因，不能悄悄丢弃或补零。
- 用项目 RdBu_r 配色，红高、零白、蓝低。标签包含真实基因名、拟时序刻度及早→晚方向；列是预测时间网格，不是细胞或供体。单基因 Z-score 不代表跨基因绝对表达。
- 需要字体/坐标适配时，在函数副本的局部环境中包装 pheatmap，捕获真正渲染矩阵；不改系统 namespace。保留 Monocle2 的拟合/变换，不以其他热图算法替代。参考来源 `62.shared_trajectory/plot.R` 的做法：

```r
native <- monocle::plot_pseudotime_heatmap
capture <- new.env(parent=emptyenv())
original_pheatmap <- get("pheatmap", envir=asNamespace("monocle"))
local_pheatmap <- function(mat, ...) {
  capture$matrix <- mat
  original_pheatmap(mat, ...)
}
local_environment <- new.env(parent=environment(native))
local_environment$pheatmap <- local_pheatmap
environment(native) <- local_environment
# 使用 native(..., return_heatmap=TRUE)，按实际 API 从结果取得 gtable。
```

独立重算变换并与 capture$matrix 比较；新增时间轴在画布内预留高度，检查 PDF/PNG 裁切。使用 Cairo PDF/ragg 等目标环境可用设备，记录任何兼容适配。

## 必须区分的来源

只把旧 IPF 模型筛出的候选搬到 Joint 图上时，候选清单可以保留，但旧统计加 historical 标识，不可当作 Joint 显著性。若任务要求 Joint 模型上的动态关联，按第67步方法在 Joint 的目标条件细胞子集上重算，保留原 Joint Pseudotime 和 size factors，再全候选校正。图表说明清楚区分候选选择模型、当前展示模型及是否重算检验。
