# Matrix and correlation heatmaps

Use this branch for annotation-dense sample heatmaps, correlation matrices, and correlation-plus-distance-association composites. Select the route from the matrix meaning; visual resemblance is not a sufficient reason to change the statistic.

## Route by question

| Route | Required input | Cell or edge meaning | Use when |
|---|---|---|---|
| COMPASS heatmap | Numeric matrix plus aligned row/column annotations, or a true `COMPASSResult` | Matrix value such as expression, score, or posterior response probability | A COMPASS layout is explicitly requested, annotations and sample ordering are central, or the input is genuine COMPASS output |
| compact corrplot matrix | Square correlation matrix with matching row/column variables | Pearson `r`, Spearman `rho`, or another explicitly named correlation coefficient | The question concerns pairwise association among biological variables; sample-sample correlation is reserved for necessary QC |
| linkET/Mantel composite | An environmental/clinical matrix and one or more community or omics matrices measured on the same independent samples | Heatmap cells are variable-variable correlations; links are distance-matrix associations | The question asks whether whole-community or omics composition covaries with environmental/clinical factors |

Do not describe an annotation heatmap as a correlation heatmap. Do not add Mantel links merely to make a corrplot more elaborate.

Follow the parent SKILL.md naming and export rules: figure names describe the analysis, never the plotting library. Sample correlation is a QC diagnostic only when needed; it is not a sample-versus-sample biological research objective.

## Establish the matrices

- Align sample identifiers before calculating any statistic; report unmatched and excluded samples.
- Name the statistical unit. Aggregate single-cell data by donor/sample before patient- or condition-level correlation or Mantel inference.
- Declare the input scale, transform, missing-value policy, correlation method, and any distance metric. Record the effective paired `n` for every correlation when missingness varies.
- Choose Pearson for a justified linear relationship on an appropriate transformed scale. Use Spearman by default for monotonic, ordinal, skewed, or outlier-prone biological variables.
- Apply BH correction across the stated correlation or Mantel family. Keep the full coefficient, raw `P`, adjusted `q`, and sample-count tables even when the figure omits significance marks.
- Treat every result as association. A heatmap or Mantel edge does not establish direction, regulation, mechanism, or causality.

## COMPASS heatmap route

The formal name is a COMPASS heatmap, not a `campassheat` package. The Bioconductor `COMPASS` package exports a modified `pheatmap()` with column annotations, row annotations, cytokine annotations, and header plots.

- For a true `COMPASSResult`, use its `plot()` method so matrix values retain their posterior-response meaning.
- For an explicitly requested annotation-style matrix, use `COMPASS::pheatmap()` with a documented numeric matrix and aligned annotation data frames.
- Keep `scale = "none"` unless scaling is scientifically intended and label the displayed scale. Use named categorical colors and fail on uncovered levels.
- Use one shared sample order for the matrix and every annotation track. When contiguous color blocks are requested, define a biologically meaningful lexicographic sort key and export the final order table. Different annotation rows cannot each have an independent sample order.
- Use `cytokine_annotation`, `headerplot`, and functionality ordering only when their COMPASS meanings apply; use ordinary annotations for clinical metadata.
- Prefer the installed exported function. If compatibility requires vendored upstream code or a local patch, record the COMPASS version or commit, source URL, checksum, and exact patch; never present a patched helper as an unmodified package call.
- Keep `ComplexHeatmap` as the general expression/marker heatmap default. COMPASS is an explicit semantic or layout branch, not a universal replacement.

Minimal annotation-layout skeleton:

```r
COMPASS::pheatmap(
  mat,
  scale = "none",
  cluster_rows = FALSE,
  cluster_cols = FALSE,
  annotation = column_annotation,
  annotation_colors = annotation_colors,
  border_color = NA,
  show_colnames = FALSE,
  main = NA
)
```

## Compact corrplot route

Use a symmetric matrix with identical row and column variables. The strict publication layout is:

- the diagonal is removed from the coordinate system rather than drawn as blank cells; no diagonal strip, gap, `1.00`, glyph, name, or significance mark remains;
- upper-square and lower-number regions meet directly along their staircase boundary;
- all variable labels are outside the data region: row labels at left, upper-square column labels above, and lower-number column labels below, with a visible gap between text and the data region;
- cells are borderless: omit cell grid lines, square outlines, and the outer frame;
- lower-left triangle as correlation coefficients;
- upper-right triangle as squares whose area and color encode correlation magnitude and sign;
- negative correlation blue, zero white, positive correlation red;
- a fixed `[-1, 1]` color scale across comparable figures.

Use restrained colors such as `#2166AC` (negative), `#F7F7F7` (zero), and `#B2182B` (positive). Reorder only by a declared original, manual, AOE, or hierarchical order and apply the identical permutation to coefficient, `P`, `q`, and `n` matrices. Use `corrplot::corrMatOrder()` when a corrplot ordering is requested.

Square fills and coefficient text use exactly the same blue-white-red palette and fixed `[-1, 1]` mapping: negative coefficients are blue, positive coefficients red, and larger absolute values have deeper colors. Near-zero text follows the pale center of this scale. Preserve the full coefficient table for exact reading; keep variable labels in a readable neutral color.

`corrplot.mixed(diag = "n")` is not sufficient: corrplot still reserves the diagonal cell band, so the two regions remain separated. Source [the reusable compact renderer](../scripts/plot_compact_corrplot.R) instead. It keeps only off-diagonal pairs and compacts them into an `n × (n - 1)` layout:

- upper cells use `x = original_column - 1`;
- lower cells use `x = original_column`;
- rows keep their original variable identity;
- top labels are variables 2 through `n` for the shifted upper region;
- bottom labels are variables 1 through `n - 1` for the lower region.

This mapping tiles every data position exactly once, so there is no coordinate allocated to self-correlation. The helper returns both the ggplot and its compact coordinate/result table.

In the local personal `sc` environment, the same renderer is available through `yt.pl.correlation_heatmap(...)`; see [the persistent personal extension](personal-extension.md) for the Python interface, parameters and update logs. The R source below remains available for direct R use.

```r
source("scripts/plot_compact_corrplot.R")

compact <- plot_compact_corrplot(
  r_mat = correlation_matrix,
  p_mat = p_matrix,
  q_mat = q_matrix,
  n_mat = paired_n_matrix,
  method_label = "Spearman rho",
  order = "original",
  label_margin_pt = 8
)

ggplot2::ggsave("correlation_compact.pdf", compact$plot,
                width = 8, height = 7, bg = "white")
ggplot2::ggsave("correlation_compact.png", compact$plot,
                width = 8, height = 7, dpi = 300, bg = "white")
write.table(compact$source, "correlation_matrix.full.tsv",
            sep = "\t", quote = FALSE, row.names = FALSE)
```

Resolve the script path relative to this skill directory when calling it from a project. The compact renderer uses corrplot ordering semantics but custom geometry because `corrplot.mixed()` cannot remove the diagonal coordinate band.

Before export, verify that the plot contains exactly `n × (n - 1)` occupied compact positions and zero self-correlations. Confirm that the two regions touch with no reserved diagonal staircase, cell grid lines and outer borders are absent, all three label sets remain outside the data region, and square fills and coefficient text give the same color for the same value. Check that signs map to blue and red respectively and labels are not clipped. When the matrix is too dense for readable numbers, use a squares-only corrplot with the same ordering and palette and retain exact coefficients in the complete result table.

Significance marks are optional. If used, state whether they represent raw `P` or BH-adjusted `q`; prefer `q`, keep nonsignificant handling explicit, and avoid marks that obscure the required lower-triangle coefficients.

## linkET and Mantel route

Add this route only when all of the following are true:

1. the matrices share independent biological samples in the same order;
2. at least one response is naturally represented by a between-sample distance or dissimilarity matrix;
3. the research question concerns association between whole-matrix structures rather than ordinary variable-variable correlation;
4. the chosen transform, distance, permutation scheme, and any strata or covariate adjustment are scientifically defensible.

For microbiome or compositional abundance, choose and record an appropriate preprocessing and distance definition rather than applying Euclidean distance to raw proportions by default. Use at least 9,999 permutations for formal output when sample size and exchangeability permit, set a seed, and respect blocks, pairing, or strata in the permutation design.

Use `linkET::qcorrplot(..., type = "lower", diag = FALSE) + geom_square()` for the correlation triangle and `geom_couple()` for Mantel links. Map negative Mantel effects with an explicit sign channel and use magnitude for width; negative values cannot be line widths. Keep correlation-variable labels outside the heatmap boundary and place community/omics node labels beyond the triangle, no variable label belongs on the removed diagonal. Map edge width to Mantel effect size and edge color to raw `P` or preferably BH-adjusted `q`; label the legend with the quantity actually mapped. Preserve the same blue-white-red correlation scale used by corrplot.

```r
linkET::qcorrplot(
  linkET::correlate(environment, method = "spearman"),
  type = "lower",
  diag = FALSE
) +
  linkET::geom_square() +
  linkET::geom_couple(
    ggplot2::aes(colour = q_bin, size = r_bin),
    data = mantel_results,
    curvature = linkET::nice_curvature()
  ) +
  ggplot2::scale_fill_gradientn(
    colours = c("#2166AC", "#F7F7F7", "#B2182B"),
    limits = c(-1, 1)
  )
```

The linkET composite uses one correlation triangle to leave room for links; it does not need to preserve the full lower-number/upper-square corrplot layout. Partial Mantel is not a general substitute for covariate-adjusted modeling. When confounding or explanatory partitioning is central, add an appropriate model such as PERMANOVA or dbRDA and treat the Mantel graphic as a visualization of the stated distance association.

## Deliver and verify

For each generated heatmap, deliver PDF, 300-dpi PNG, and reconstruction tables containing:

- the displayed matrix and its row/column order;
- annotations and complete named color mappings for COMPASS heatmaps;
- `r` or `rho`, raw `P`, BH `q`, effective paired `n`, method, and missingness rule for corrplot;
- Mantel effect, raw `P`, BH `q`, distance metrics, transforms, permutations, seed, strata, and aligned sample list for linkET;
- package versions and any vendored-code provenance or compatibility patch.

Inspect PNG and PDF for clipped labels, unreadable coefficients, non-square cells, mismatched legends, reversed sign colors, and annotation-order drift.

## Reference implementations and appearance

- [COMPASS package manual](https://bioconductor.org/packages/release/bioc/manuals/COMPASS/man/COMPASS.pdf)
- [corrplot mixed-matrix documentation](https://search.r-project.org/CRAN/refmans/corrplot/html/corrplot.mixed.html)
- [corrplot vignette](https://github.com/taiyun/corrplot/blob/master/vignettes/corrplot-intro.Rmd)
- [linkET source and Mantel example](https://github.com/Hy4m/linkET)
- [Requested corrplot appearance](https://zhuanlan.zhihu.com/p/1902654256953161702)
