# 单细胞 UMAP / FeaturePlot / 密度图作图规范（可分享版）

本文件自包含，可直接复制到其他 skill 的 `reference/` 目录下，并在对应 SKILL.md 中加一句：

> 单细胞图形风格遵循 `reference/scRNA_umap_density_style.md`。

也可只摘取其中的 colors.yaml 片段与代码段使用。

适用范围：Seurat v5 对象 + scop + Nebulosa（R）。所有图形同时导出矢量 PDF 与 300 dpi PNG；配色一律读取 `Scripts/config/colors.yaml`，不在脚本中硬编码颜色。

---

## 1. colors.yaml 模板片段

```yaml
primary:
  deep_sea_blue: "#1F4E79"
  academic_blue: "#2E75B6"
  indigo: "#3B5B6E"
  matte_gold: "#C9A227"
  neutral_gray: "#8C8C8C"
  light_gray: "#D9D9D9"

# 分组（示例：对照/处理两时间点；按项目实际组名改 key）
group:
  Sham_D2: "#2E75B6"
  Stroke_D2: "#C9A227"
  Stroke_D14: "#8C8C8C"

# 细胞类型（低饱和、色盲友好；按项目实际类型改 key）
celltype:
  Microglia: "#1F4E79"
  Monocyte-derived: "#C9A227"
  Dendritic cell: "#5B8E7D"
  Granulocyte: "#8C6D9C"
  Border-assoc. Mac: "#C08552"
  T/NK cell: "#4E8D8D"
  B cell: "#7A9E7E"
  Mast cell: "#B07D8C"
  Endothelial: "#2E75B6"
  Other: "#BFBFBF"

# 表达渐变（FeaturePlot；Reds）
gradient:
  low: "#FFF5F0"
  mid: "#FB6A4A"
  high: "#67000D"

# 表达密度图（magma）
density:
  low: "#000004"
  mid: "#B5367A"
  high: "#FCFDBF"
```

R 读取：

```r
library(yaml)
COLORS <- yaml::read_yaml("Scripts/config/colors.yaml")
uc <- function(x) unlist(x, use.names = TRUE)
group_cols    <- uc(COLORS$group)
celltype_cols <- uc(COLORS$celltype)
grad          <- unlist(COLORS$gradient, use.names = FALSE)
dens_cols     <- unlist(COLORS$density,  use.names = FALSE)
```

双格式保存：

```r
save_fig <- function(p, path_base, width, height) {
  ggplot2::ggsave(paste0(path_base, ".pdf"), p, width = width, height = height)
  ggplot2::ggsave(paste0(path_base, ".png"), p, width = width, height = height, dpi = 300)
}
```

---

## 2. UMAP（scop::CellDimPlot）

铁律：`title = NULL, subtitle = NULL, show_stat = FALSE`（无标题、无 nCells 副标题、图例不带细胞计数）。

```r
library(scop)

# 标准版
p1 <- CellDimPlot(obj, group.by = "celltype", palcolor = celltype_cols,
                  title = NULL, subtitle = NULL, show_stat = FALSE,
                  legend.title = "Cell type")

# 标签直接标注版（无图例）
p2 <- CellDimPlot(obj, group.by = "celltype", palcolor = celltype_cols,
                  label = TRUE, label_insitu = TRUE, label_repel = TRUE,
                  label_repulsion = 2, legend.position = "none",
                  title = NULL, subtitle = NULL, show_stat = FALSE)

# 轮廓版（密度等高线）
p3 <- CellDimPlot(obj, group.by = "celltype", palcolor = celltype_cols,
                  add_density = TRUE,
                  title = NULL, subtitle = NULL, show_stat = FALSE)

# 分组拆分版
p4 <- CellDimPlot(obj, group.by = "celltype", split.by = "group", ncol = 3,
                  palcolor = celltype_cols,
                  title = NULL, subtitle = NULL, show_stat = FALSE)

# 只画部分细胞（如去掉 Other）
p5 <- CellDimPlot(obj, group.by = "celltype",
                  cells = colnames(obj)[obj$celltype != "Other"],
                  palcolor = celltype_cols,
                  title = NULL, subtitle = NULL, show_stat = FALSE)
```

注意：
- scop 命名向量色板按名字匹配；多分类变量（如 16 个 cluster）建议显式命名（C01–C16）并配同名色板，避免错位。
- 高亮细胞：`cells.highlight = <细胞名向量>, cols.highlight = <高亮色>`。

## 3. FeaturePlot（scop::FeatureDimPlot）

```r
p <- FeatureDimPlot(obj, features = "Txn2", palcolor = grad,
                    subtitle = NULL, show_stat = FALSE, pt.size = 1.2)
# 分组
p2 <- FeatureDimPlot(obj, features = "Txn2", split.by = "group", ncol = 3,
                     palcolor = grad, subtitle = NULL, show_stat = FALSE,
                     pt.size = 1.2)
```

- 只保留基因名作为面板题；稀疏基因适当加大 `pt.size`。
- 多基因 featureplots：`features = unname(gene_vector)`，否则面板题会带上向量名前缀。

## 4. 表达密度图（Nebulosa::plot_density）

表达加权核密度 UMAP（`magma` 色系）。**勿用 scop::CellDensityPlot**——它是表达分布曲线，不是 UMAP 密度图。

```r
library(Nebulosa)
library(patchwork)

# 全部细胞
p_dens <- plot_density(obj, "Txn2") +
  scale_color_gradientn(colors = dens_cols, name = "Density")
save_fig(p_dens, "TXN2.density.UMAP", 7, 6)

# 分组拆分：逐组计算 + 全局共享色标 + 合并图例
dens_list <- lapply(levels(obj$group), function(g) {
  plot_density(subset(obj, group == g), "Txn2") + ggplot2::ggtitle(g)
})
dens_max <- max(vapply(dens_list, function(p) max(p$data[[3]], na.rm = TRUE), numeric(1)))
p_dens_split <- wrap_plots(dens_list, nrow = 1, guides = "collect") &
  scale_color_gradientn(colors = dens_cols, name = "Density",
                        limits = c(0, dens_max)) &
  ggplot2::theme(legend.position = "right")
save_fig(p_dens_split, "TXN2.density.UMAP_by_group", 15, 5)
```

要点：分组版必须 `limits = c(0, 全局最大密度)`，否则各组色标各自归一，无法横向比较。

## 5. QC 小提琴（scop::FeatureStatPlot）

```r
# 多样本合并版：三指标一排，图例合一
p <- FeatureStatPlot(obj, stat.by = c("nFeature_RNA", "nCount_RNA", "percent.mt.calc"),
                     group.by = "sample", plot_type = "violin",
                     palcolor = sample_cols, combine = TRUE, nrow = 1) +
  patchwork::plot_layout(guides = "collect")

# 每样本版：去图例、去 x 轴刻度文本
p_s <- p & ggplot2::theme(legend.position = "none",
                          axis.text.x  = ggplot2::element_blank(),
                          axis.title.x = ggplot2::element_blank(),
                          axis.ticks.x = ggplot2::element_blank())
```

## 6. 长宽比与图例规则

- 单基因点图（1 个 x 列）：窄版（宽 ~6in，y 轴标签小字号），勿用 9in 宽留白。
- 单行/单列热图：矮宽构图使格子近正方形；图例多时用 `legend.position = "bottom", legend.direction = "horizontal"` 水平排列，过宽再微调高度。
- 多面板组合图：`plot_layout(guides = "collect")` 或 `wrap_plots(guides = "collect")` 合并重复图例。
- 分面图基因/细胞类型标签重叠时：x 轴标签 45° 旋转（`element_text(angle = 45, hjust = 1)`）并适当加宽；仍不可读的横纵变体直接删除，不留废图。

## 7. Do / Don't 清单

**Do**
- UMAP 类无标题无副标题，信息靠图例/图内标签/分组条表达
- 图例题简洁：Group / Cell type / Sample（不带冒号、不带计数）
- 配色全部来自 colors.yaml
- PDF + 300 dpi PNG 双格式

**Don't**
- 不要 nCells/nPos 统计副标题（scop：`subtitle=NULL, show_stat=FALSE`）
- 不要图例带细胞计数（如 Microglia(5621)）
- 不要重复图例、重复标题（多面板合一）
- 不要极端长宽比（单基因宽图、单行高图）
- 不要为凑数保留标签不可读的横纵变体图
