# ClusterGVis：左侧箱线图、模块热图与富集注释

## 布局要求

沿用用户提供的 `visCluster(object = st.data, plot.type = "both", ...)` 布局：列名旋转 45 度、不显示行树状图、目标基因标签位于左侧、模块附带富集条目及条形注释。将左侧趋势图替换为箱线图，不保留作为默认图层的趋势线。

模块顺序以真实 `st.data` 为准。用户示例 `cluster.order = c(1:9)` 仅适用于确实有这些模块的结果；不强制聚为九类。用户示例的 `jjAnno::useMyCol("stallion", n = 9)` 可用于生成项目模块配色，再保存到项目颜色配置。富集条目按各自模块匹配颜色，不固定假设每个模块恰有五条条目。

## 参数兼容

先检查 `packageVersion("ClusterGVis")` 和 `formals(ClusterGVis::visCluster)`。作者源码提供新版驼峰参数，并保留旧版点号参数的兼容映射；按实际版本选择一套命名，不混用。

| 意图 | 用户示例/旧参数 | 新参数 |
|---|---|---|
| 组合图 | `plot.type` | `plotType` |
| 左侧箱线图 | `add.box = TRUE` | `addBox = TRUE` |
| 关闭趋势线 | `add.line = FALSE` | `addLine = FALSE` |
| 关闭单独中位数趋势线 | `add.mline = FALSE` | `addMline = FALSE` |
| 图形位于左侧 | `line.side` | `lineSide` |
| 基因标签位于左侧 | `markGenes.side` | `markGenesSide` |
| 模块顺序 | `cluster.order` | `clusterOrder` |
| 富集注释 | `annoTerm.data` | `annoTermData` |
| 富集条目颜色 | `go.col` | `goCol` |
| 富集条形注释 | `add.bar` | `addBar` |

## 旧参数调用模板

运行前准备真实 `st.data`、`markGenes`、`enrich`、已核对的 `cluster_order` 及按 `enrich` 各行所属模块匹配的 `go_colors`。相对用户原示例增加了箱线图开关、关闭趋势线，并用实际模块顺序和颜色替代固定长度。

```r
ClusterGVis::visCluster(
  object = st.data,
  plot.type = "both",
  column_names_rot = 45,
  show_row_dend = FALSE,
  markGenes = markGenes,
  markGenes.side = "left",
  annoTerm.data = enrich,
  line.side = "left",
  cluster.order = cluster_order,
  go.col = go_colors,
  add.bar = TRUE,
  add.box = TRUE,
  add.line = FALSE,
  add.mline = FALSE
)
```

## 箱线图的数据语义

- 查明当前版本内置箱线图的分布单位。模块内基因表达的分布可以作为描述性注释，不能把模块基因数当作生物学重复计算组间 P 值。
- 若箱线图需要支持生物学组间比较，先按样本计算该模块的表达汇总或评分，以每个生物学重复的值构建箱线图；分组而非样本 ID 作为比较轴，保留配对关系。
- 内置注释无法表达所需统计单位时，使用对应版本支持的自定义图形/ComplexHeatmap 注释接口，将真实组间箱线图放到左侧并对齐模块。不假设 `gglist` 的默认位置就是左侧；检查最终导出的位置。
- `st.data` 的表达值、模块归属、基因标签、富集结果、箱线图及颜色必须一一对应。不要为了画图重新聚类或更改已定稿模块。

## 依据

- [作者仓库](https://github.com/junjunlab/ClusterGVis)
- [作者接口源码](https://github.com/junjunlab/ClusterGVis/blob/main/R/4.visCluster.R)
- [作者手册](https://junjunlab.github.io/ClusterGvis-manual/)
- [用户提供的参考文章](https://mp.weixin.qq.com/s?__biz=MzkyMTI1MTYxNA==&mid=2247508319&idx=1&sn=6fe9cc5ea16468de8f8b15f00cdf8d22)

创建本规范时微信原文无法访问；用户给出的代码和布局要求已保留，箱线图参数依据作者源码核对。
