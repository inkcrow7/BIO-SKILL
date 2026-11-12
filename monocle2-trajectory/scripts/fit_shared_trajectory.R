#!/usr/bin/env Rscript
# Generalized from IPF module60/infer.R; follows module62's shared-model policy.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 1L && args[[1L]] %in% c('-h', '--help')) {
  cat('Usage: Rscript fit_shared_trajectory.R CONFIG_YAML PROJECT_ROOT OUTPUT_DIR\n')
  quit(status = 0)
}
if (length(args) != 3L) stop('Expected CONFIG_YAML PROJECT_ROOT OUTPUT_DIR; use --help.')
packages <- c('monocle', 'Matrix', 'Biobase', 'BiocGenerics', 'VGAM', 'DDRTree', 'igraph', 'yaml', 'digest', 'jsonlite')
missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop('Missing R packages: ', paste(missing, collapse = ', '))
if (utils::packageVersion('monocle') >= '3.0.0') stop('This workflow requires Monocle2.')
suppressPackageStartupMessages(library(monocle))
config_file <- normalizePath(args[[1L]], mustWork = TRUE)
project <- normalizePath(args[[2L]], mustWork = TRUE)
resolve <- function(path) {
  normalizePath(if (startsWith(path, '/')) path else file.path(project, path), mustWork = TRUE)
}
cfg <- yaml::read_yaml(config_file)
required <- c('organism', 'counts_mtx', 'cells_tsv', 'genes_tsv', 'ordering_tsv',
              'donor_col', 'group_col', 'identity_col', 'root_identity_col',
              'root_score_col', 'root_identity', 'root', 'seed', 'DDRTree')
if (!all(required %in% names(cfg))) stop('Missing required configuration keys.')
files <- vapply(cfg[c('counts_mtx', 'cells_tsv', 'genes_tsv', 'ordering_tsv')], resolve, character(1))
hash_file <- function(path) digest::digest(file = path, algo = 'sha256')
script_arg <- grep('^--file=', commandArgs(), value = TRUE)
script <- normalizePath(sub('^--file=', '', script_arg[[1L]]), mustWork = TRUE)
versions <- setNames(lapply(packages, function(p) as.character(utils::packageVersion(p))), packages)
signature <- digest::digest(list(config = cfg, inputs = lapply(files, hash_file),
                                code = hash_file(script), versions = versions), algo = 'sha256')
meta <- read.delim(files[['cells_tsv']], row.names = 1, check.names = FALSE)
genes <- read.delim(files[['genes_tsv']], row.names = 1, check.names = FALSE)
ordering <- read.delim(files[['ordering_tsv']], check.names = FALSE)
fields <- unlist(cfg[c('donor_col', 'group_col', 'identity_col', 'root_identity_col', 'root_score_col')])
if (!all(fields %in% names(meta)) || anyNA(meta[, fields, drop = FALSE])) stop('Incomplete cell metadata.')
if (!is.numeric(meta[[cfg$root_score_col]]) || any(!is.finite(meta[[cfg$root_score_col]]))) stop('Invalid root scores.')
for (field in setdiff(fields, cfg$root_score_col)) {
  if (any(!nzchar(as.character(meta[[field]])))) stop('Empty metadata labels: ', field)
}
if (anyDuplicated(rownames(meta)) || anyDuplicated(rownames(genes)) ||
    !nrow(meta) || !nrow(genes)) stop('Cell and gene IDs must be unique and nonempty.')
if (length(unique(meta[[cfg$group_col]])) < 2L) stop('The shared model requires at least two biological groups.')
donor_groups <- tapply(as.character(meta[[cfg$group_col]]), meta[[cfg$donor_col]], function(x) length(unique(x)))
if (any(donor_groups != 1L)) stop('This template assumes one group per donor; adapt the design for paired/repeated-condition subjects.')
counts <- as(Matrix::readMM(files[['counts_mtx']]), 'CsparseMatrix')
if (!identical(dim(counts), c(nrow(genes), nrow(meta)))) stop('Matrix dimensions must match ordered gene/cell tables.')
if (any(!is.finite(counts@x) | counts@x < 0 | counts@x != floor(counts@x)) ||
    any(Matrix::colSums(counts) <= 0)) stop('Expected finite nonnegative integer UMI counts with nonempty libraries.')
dimnames(counts) <- list(rownames(genes), rownames(meta))
if (!'gene_short_name' %in% names(genes)) genes$gene_short_name <- rownames(genes)
if (!'gene' %in% names(ordering) || anyNA(ordering$gene) || anyDuplicated(ordering$gene) ||
    length(ordering$gene) < 2L || !all(ordering$gene %in% rownames(genes))) stop('Invalid ordering-gene list.')
if (!cfg$root_identity %in% as.character(meta[[cfg$root_identity_col]])) stop('Root identity is absent.')
if (!is.numeric(cfg$root$minimum_cells) || length(cfg$root$minimum_cells) != 1L ||
    !is.finite(cfg$root$minimum_cells) || cfg$root$minimum_cells < 1 ||
    !is.numeric(cfg$root$minimum_fraction) || length(cfg$root$minimum_fraction) != 1L ||
    !is.finite(cfg$root$minimum_fraction) || cfg$root$minimum_fraction < 0 || cfg$root$minimum_fraction > 1) {
  stop('Invalid root-state eligibility thresholds.')
}
if (!is.numeric(cfg$seed) || length(cfg$seed) != 1L || !is.finite(cfg$seed)) stop('Invalid seed.')
output <- if (startsWith(args[[3L]], '/')) args[[3L]] else file.path(project, args[[3L]])
output <- file.path(normalizePath(dirname(output), mustWork = TRUE), basename(output))
if (dir.exists(output)) output <- normalizePath(output, mustWork = TRUE)
if (!startsWith(paste0(output, '/'), paste0(project, '/')) || identical(output, project)) {
  stop('OUTPUT_DIR must be inside the project root.')
}
if (!dir.exists(output) && !dir.create(output)) stop('Cannot create OUTPUT_DIR.')
target <- file.path(output, 'Joint.rds')
cache_file <- file.path(output, 'Joint.cache.json')
if (length(list.files(output, all.files = TRUE, no.. = TRUE))) {
  if (!file.exists(target) || !file.exists(cache_file)) stop('Output is nonempty without a complete model cache; use a new module or archive it.')
  cache <- jsonlite::read_json(cache_file, simplifyVector = TRUE)
  if (!identical(cache$key, signature) || !identical(cache$sha256, hash_file(target))) stop('Model cache mismatch; archive before refitting.')
  artifacts <- unlist(cache$artifacts)
  if (!length(artifacts) || !all(file.exists(file.path(output, names(artifacts)))) ||
      !identical(unname(vapply(file.path(output, names(artifacts)), hash_file, character(1))), unname(artifacts))) {
    stop('Cached output files changed or are incomplete; archive before rerunning.')
  }
  cached <- readRDS(target)
  if (!identical(colnames(cached), rownames(meta)) || any(!is.finite(Biobase::pData(cached)$Pseudotime))) stop('Cached model validation failed.')
  cat('Verified current shared model cache:', target, '\n')
  quit(status = 0)
}
for (field in unique(unlist(cfg[c('donor_col', 'group_col', 'identity_col', 'root_identity_col')]))) {
  meta[[field]] <- factor(meta[[field]])
}
set.seed(cfg$seed)
cds <- monocle::newCellDataSet(counts,
  phenoData = methods::new('AnnotatedDataFrame', data = meta),
  featureData = methods::new('AnnotatedDataFrame', data = genes),
  lowerDetectionLimit = 0.5, expressionFamily = VGAM::negbinomial.size())
cds <- BiocGenerics::estimateSizeFactors(cds)
cds <- BiocGenerics::estimateDispersions(cds, cores = 1)
cds <- monocle::setOrderingFilter(cds, ordering$gene)
cds <- monocle::reduceDimension(cds, max_components = 2, reduction_method = 'DDRTree',
  norm_method = cfg$DDRTree$norm_method,
  residualModelFormulaStr = cfg$DDRTree$residual_model,
  maxIter = cfg$DDRTree$maxIter, verbose = TRUE)
cds <- monocle::orderCells(cds)
cell <- Biobase::pData(cds)
evidence <- do.call(rbind, lapply(split(seq_len(nrow(cell)), cell$State), function(rows) {
  donor_scores <- tapply(cell[[cfg$root_score_col]][rows], as.character(cell[[cfg$donor_col]][rows]), mean)
  data.frame(State = as.character(cell$State[rows[1L]]), n_cells = length(rows),
    n_donors = length(donor_scores),
    root_identity_fraction = mean(as.character(cell[[cfg$root_identity_col]][rows]) == cfg$root_identity),
    root_score_donor_mean = mean(donor_scores))
}))
evidence$eligible <- evidence$n_cells >= cfg$root$minimum_cells &
  evidence$root_identity_fraction >= cfg$root$minimum_fraction
write.table(evidence, file.path(output, 'Joint.root_state_evidence.full.tsv'),
            sep = '\t', quote = FALSE, row.names = FALSE)
candidates <- evidence[evidence$eligible, , drop = FALSE]
if (!nrow(candidates)) stop('No eligible root state; retain evidence and review the root rationale rather than force a direction.')
candidates <- candidates[order(-candidates$root_score_donor_mean, as.numeric(candidates$State)), ]
selected <- candidates$State[[1L]]
evidence$selected_root <- evidence$State == selected
cds <- monocle::orderCells(cds, root_state = as.numeric(selected))
cell <- Biobase::pData(cds)
origin <- which.min(cell$Pseudotime)
evidence$actual_origin_cell <- rownames(cell)[origin]
evidence$actual_origin_identity <- as.character(cell[[cfg$root_identity_col]][origin])
write_tsv <- function(data, name) write.table(data, file.path(output, name), sep = '\t', quote = FALSE, row.names = FALSE, na = 'NA')
write_tsv(evidence, 'Joint.root_state_evidence.full.tsv')
if (any(!is.finite(cell$Pseudotime)) || min(cell$Pseudotime) != 0 ||
    evidence$actual_origin_identity[[1L]] != cfg$root_identity) stop('Pseudotime or actual origin failed validation; inspect root evidence.')
if (!identical(colnames(cds), rownames(meta)) || !isTRUE(all.equal(Biobase::exprs(cds), counts))) stop('Counts or cell order changed.')
coordinates <- as.data.frame(t(monocle::reducedDimS(cds)))
colnames(coordinates) <- c('DDRTree1', 'DDRTree2')
cell$cell_id <- rownames(cell)
write_tsv(cbind(cell, coordinates), 'Joint.cell_pseudotime.full.tsv')
graph <- monocle::minSpanningTree(cds)
if (!igraph::is_connected(graph) || igraph::ecount(graph) != igraph::vcount(graph) - 1L) stop('Principal graph is not a connected tree.')
write_tsv(igraph::as_data_frame(graph, what = 'edges'), 'Joint.principal_graph_edges.full.tsv')
vertices <- data.frame(vertex = colnames(monocle::reducedDimK(cds)), t(monocle::reducedDimK(cds)))
colnames(vertices) <- c('vertex', 'DDRTree1', 'DDRTree2')
write_tsv(vertices, 'Joint.principal_graph_vertices.full.tsv')
saveRDS(cds, paste0(target, '.tmp'))
if (!file.rename(paste0(target, '.tmp'), target)) stop('Atomic model publication failed.')
writeLines(capture.output(sessionInfo()), file.path(output, 'R_sessionInfo.txt'))
artifacts <- list.files(output, full.names = FALSE)
artifact_hashes <- as.list(setNames(vapply(file.path(output, artifacts), hash_file, character(1)), artifacts))
group_counts <- table(cell[[cfg$group_col]])
jsonlite::write_json(list(key = signature, sha256 = hash_file(target),
  input_sha256 = lapply(files, hash_file), organism = cfg$organism, config = cfg,
  cells = ncol(cds), genes = nrow(cds),
  groups = setNames(as.list(as.integer(group_counts)), names(group_counts)),
  versions = versions, script_sha256 = hash_file(script), artifacts = artifact_hashes),
  paste0(cache_file, '.tmp'), pretty = TRUE, auto_unbox = TRUE)
if (!file.rename(paste0(cache_file, '.tmp'), cache_file)) stop('Atomic cache publication failed.')
cat('Completed shared trajectory:', target, '\n')
