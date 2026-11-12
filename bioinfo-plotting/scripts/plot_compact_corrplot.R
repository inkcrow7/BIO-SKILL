# Draw a mixed correlation matrix with no diagonal coordinate band.
#
# The upper triangle is shifted left by one column and the lower triangle keeps
# its original column index. This packs every off-diagonal pair into an
# n-row by (n - 1)-column rectangle: upper squares and lower coefficients meet
# directly, while all variable labels remain outside the data region.
# Default cells are borderless; numbers and squares share the same color scale.

plot_compact_corrplot <- function(
    r_mat,
    p_mat = NULL,
    q_mat = NULL,
    n_mat = NULL,
    method_label = "Spearman rho",
    order = c("original", "AOE", "FPC", "hclust", "alphabet"),
    hclust_method = "complete",
    digits = 2L,
    number_size = 3.2,
    palette = c("#2166AC", "#F7F7F7", "#B2182B"),
    cell_border_colour = NA_character_,
    cell_border_linewidth = 0.35,
    label_margin_pt = 8) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package 'ggplot2' is required.", call. = FALSE)
  }
  if (!requireNamespace("scales", quietly = TRUE)) {
    stop("Package 'scales' is required.", call. = FALSE)
  }

  order <- match.arg(order)
  digits <- as.integer(digits)
  if (length(digits) != 1L || is.na(digits) || digits < 0L) {
    stop("'digits' must be one non-negative integer.", call. = FALSE)
  }
  if (length(cell_border_colour) != 1L ||
      (!is.na(cell_border_colour) &&
       (!is.character(cell_border_colour) || cell_border_colour == ""))) {
    stop("'cell_border_colour' must be NA or one non-empty colour value.",
         call. = FALSE)
  }
  if (length(cell_border_linewidth) != 1L ||
      !is.finite(cell_border_linewidth) || cell_border_linewidth < 0) {
    stop("'cell_border_linewidth' must be one non-negative finite number.",
         call. = FALSE)
  }
  if (length(label_margin_pt) != 1L || !is.finite(label_margin_pt) ||
      label_margin_pt < 0) {
    stop("'label_margin_pt' must be one non-negative finite number.",
         call. = FALSE)
  }
  if (!is.numeric(r_mat) || !is.matrix(r_mat) || nrow(r_mat) != ncol(r_mat) ||
      nrow(r_mat) < 2L) {
    stop("'r_mat' must be a numeric square matrix with at least two variables.",
         call. = FALSE)
  }

  variable_names <- rownames(r_mat)
  if (is.null(variable_names) || is.null(colnames(r_mat)) ||
      anyNA(variable_names) || any(variable_names == "") ||
      anyDuplicated(variable_names) ||
      !identical(variable_names, colnames(r_mat))) {
    stop("'r_mat' must have unique, non-empty, identical row and column names.",
         call. = FALSE)
  }

  off_diagonal <- row(r_mat) != col(r_mat)
  if (any(!is.finite(r_mat[off_diagonal]))) {
    stop("All off-diagonal correlations must be finite.", call. = FALSE)
  }
  if (any(abs(r_mat[off_diagonal]) > 1 + sqrt(.Machine$double.eps))) {
    stop("All correlations must lie in [-1, 1].", call. = FALSE)
  }
  symmetry_difference <- abs(r_mat - t(r_mat))
  if (any(symmetry_difference[off_diagonal] > 1e-8)) {
    stop("'r_mat' must be symmetric.", call. = FALSE)
  }

  validate_companion <- function(x, argument) {
    if (is.null(x)) {
      return(NULL)
    }
    if (!is.numeric(x) || !is.matrix(x) || !identical(dim(x), dim(r_mat)) ||
        !identical(rownames(x), variable_names) ||
        !identical(colnames(x), variable_names)) {
      stop(sprintf(
        "'%s' must be a numeric matrix with dimensions and dimnames identical to 'r_mat'.",
        argument
      ), call. = FALSE)
    }
    x
  }

  p_mat <- validate_companion(p_mat, "p_mat")
  q_mat <- validate_companion(q_mat, "q_mat")
  n_mat <- validate_companion(n_mat, "n_mat")

  if (order != "original") {
    if (!requireNamespace("corrplot", quietly = TRUE)) {
      stop("Package 'corrplot' is required for non-original ordering.",
           call. = FALSE)
    }
    permutation <- corrplot::corrMatOrder(
      r_mat,
      order = order,
      hclust.method = hclust_method
    )
    r_mat <- r_mat[permutation, permutation, drop = FALSE]
    if (!is.null(p_mat)) p_mat <- p_mat[permutation, permutation, drop = FALSE]
    if (!is.null(q_mat)) q_mat <- q_mat[permutation, permutation, drop = FALSE]
    if (!is.null(n_mat)) n_mat <- n_mat[permutation, permutation, drop = FALSE]
    variable_names <- rownames(r_mat)
  }

  variable_count <- nrow(r_mat)
  source_data <- expand.grid(
    row_index = seq_len(variable_count),
    column_index = seq_len(variable_count),
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )
  source_data <- source_data[
    source_data$row_index != source_data$column_index,
    ,
    drop = FALSE
  ]
  matrix_index <- cbind(source_data$row_index, source_data$column_index)
  source_data$row_variable <- variable_names[source_data$row_index]
  source_data$column_variable <- variable_names[source_data$column_index]
  source_data$region <- ifelse(
    source_data$row_index < source_data$column_index,
    "upper_square",
    "lower_number"
  )
  source_data$x_compact <- ifelse(
    source_data$region == "upper_square",
    source_data$column_index - 1L,
    source_data$column_index
  )
  source_data$y_compact <- variable_count - source_data$row_index + 1L
  source_data$correlation <- r_mat[matrix_index]
  source_data$abs_correlation <- abs(source_data$correlation)
  source_data$square_side <- sqrt(source_data$abs_correlation)
  source_data$p_value <- if (is.null(p_mat)) NA_real_ else p_mat[matrix_index]
  source_data$q_value <- if (is.null(q_mat)) NA_real_ else q_mat[matrix_index]
  source_data$paired_n <- if (is.null(n_mat)) NA_real_ else n_mat[matrix_index]
  source_data$number_label <- formatC(
    source_data$correlation,
    format = "f",
    digits = digits
  )

  compact_key <- paste(source_data$x_compact, source_data$y_compact, sep = ":")
  expected_positions <- variable_count * (variable_count - 1L)
  if (nrow(source_data) != expected_positions ||
      anyDuplicated(compact_key) ||
      length(unique(compact_key)) != expected_positions) {
    stop("Internal compact-coordinate validation failed.", call. = FALSE)
  }

  upper_data <- source_data[source_data$region == "upper_square", , drop = FALSE]
  lower_data <- source_data[source_data$region == "lower_number", , drop = FALSE]
  top_labels <- data.frame(
    x_compact = seq_len(variable_count - 1L),
    variable = variable_names[-1L],
    stringsAsFactors = FALSE
  )
  bottom_labels <- data.frame(
    x_compact = seq_len(variable_count - 1L),
    variable = variable_names[-variable_count],
    stringsAsFactors = FALSE
  )

  plot_object <- ggplot2::ggplot() +
    ggplot2::geom_tile(
      data = upper_data,
      ggplot2::aes(
        x = x_compact,
        y = y_compact,
        width = square_side,
        height = square_side,
        fill = correlation
      ),
      colour = NA
    )
  # Retain an explicit border option for existing callers; default renders none.
  if (!is.na(cell_border_colour) && cell_border_linewidth > 0) {
    plot_object <- plot_object + ggplot2::geom_tile(
      data = source_data,
      ggplot2::aes(x = x_compact, y = y_compact),
      width = 1,
      height = 1,
      fill = NA,
      colour = cell_border_colour,
      linewidth = cell_border_linewidth
    )
  }
  plot_object <- plot_object +
    ggplot2::geom_text(
      data = lower_data,
      ggplot2::aes(
        x = x_compact,
        y = y_compact,
        label = number_label,
        colour = correlation
      ),
      size = number_size,
      family = "sans"
    ) +
    ggplot2::scale_fill_gradientn(
      colours = palette,
      limits = c(-1, 1),
      oob = scales::squish,
      name = method_label
    ) +
    ggplot2::scale_colour_gradientn(
      colours = palette,
      limits = c(-1, 1),
      oob = scales::squish,
      guide = "none"
    ) +
    ggplot2::scale_x_continuous(
      breaks = bottom_labels$x_compact,
      labels = bottom_labels$variable,
      limits = c(0.5, variable_count - 0.5),
      expand = ggplot2::expansion(mult = 0),
      sec.axis = ggplot2::dup_axis(
        breaks = top_labels$x_compact,
        labels = top_labels$variable,
        name = NULL
      )
    ) +
    ggplot2::scale_y_continuous(
      breaks = seq_len(variable_count),
      labels = rev(variable_names),
      limits = c(0.5, variable_count + 0.5),
      expand = ggplot2::expansion(mult = 0)
    ) +
    ggplot2::coord_fixed(clip = "off") +
    ggplot2::labs(x = NULL, y = NULL) +
    ggplot2::theme_void(base_family = "sans") +
    ggplot2::theme(
      axis.text.x.bottom = ggplot2::element_text(
        colour = "black", angle = 45, hjust = 1, vjust = 1, size = 9,
        margin = ggplot2::margin(t = label_margin_pt)
      ),
      axis.text.x.top = ggplot2::element_text(
        colour = "black", angle = 45, hjust = 0, vjust = 0, size = 9,
        margin = ggplot2::margin(b = label_margin_pt)
      ),
      axis.text.y.left = ggplot2::element_text(
        colour = "black", hjust = 1, size = 9,
        margin = ggplot2::margin(r = label_margin_pt)
      ),
      axis.ticks = ggplot2::element_blank(),
      legend.position = "right",
      legend.key.height = grid::unit(18, "mm"),
      plot.margin = ggplot2::margin(18, 18, 18, 18)
    )

  list(
    plot = plot_object,
    source = source_data,
    order = variable_names,
    top_labels = top_labels,
    bottom_labels = bottom_labels
  )
}
