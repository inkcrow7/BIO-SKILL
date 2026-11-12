# Bioinformatics logic-risk checklist

Use every applicable section. The checklist is a search guide; report only evidence-backed findings, including confirmed mitigation.

## 1. Dataset fit and study design

- Verify accession, species, tissue, anatomical region, disease definition, severity, treatment, and assay type against source metadata.
- Distinguish healthy, non-diseased, adjacent, relatively preserved, contralateral, vehicle, and technical controls.
- Record unique donors separately from specimens, regions, libraries, lanes, and cells.
- Detect repeated donors, paired regions, longitudinal samples, technical replicates, or overlapping public cohorts.
- Verify discovery and validation cohorts are genuinely independent.
- Check age, sex, ancestry, disease grade, surgery indication, medication, and collection site imbalance when metadata exist.
- Check whether tissue dissection, cell isolation, storage, sequencing chemistry, reference genome, or platform differs by group.
- Test disease–batch/platform/site confounding and design-matrix rank. Complete confounding is a potential `BLOCKER`.
- Confirm the dataset can answer the claimed question. OA damaged versus relatively preserved tissue cannot establish OA versus healthy disease specificity.
- Keep distinct tissues and biological compartments separate during modeling. Cross-tissue agreement is evidence convergence, not a license to merge matrices.
- Identify reuse of the same dataset across discovery, tuning, filtering, and validation; label non-independent validation.
- Mark missing raw data, incomplete sample metadata, inferred pairing, or ambiguous labels `UNKNOWN`.

## 2. Acquisition, identifiers, and provenance

- Verify checksums, file completeness, matrix orientation, feature IDs, barcode uniqueness, and sample-to-file mapping.
- Confirm gene identifiers and reference builds are compatible before merging or comparing.
- Quantify gene loss during ID conversion, probe aggregation, or feature intersection.
- Verify donor/sample prefixes prevent cross-sample barcode collisions.
- Check that public processed matrices did not already apply unknown filtering, normalization, or batch correction.
- Check whether datasets share samples under different accessions or publications.

## 3. Bulk RNA-seq and microarray

- Use raw integer counts for edgeR/DESeq2; use voom or suitable normalized intensities for limma.
- Match background correction, normalization, and probe aggregation to platform type.
- Verify reference levels, contrast direction, design rank, covariates, blocking, pairing, repeated measures, and surrogate variables.
- Keep batch correction for visualization distinct from model-based adjustment used for inference.
- Inspect library sizes, sample correlation, PCA, clustering, group/platform shapes, and influential outliers.
- Quantify which covariates drive leading PCs; displaying disease alone can hide platform separation.
- Confirm low-count filtering precedes dispersion/model fitting and uses the intended design.
- Report full and filtered differential tables; “not significant” is not evidence of equality.
- Check whether a few samples drive differential expression, enrichment, or network modules.
- For microarrays, verify annotation version, control-probe removal, duplicate probes, and gene mapping.
- Treat bulk changes as a mixture of cell composition and cell-intrinsic regulation unless deconvolution or orthogonal evidence separates them.

## 4. Single-cell and spatial analysis

- Evaluate QC by sample/library; record robust and hard caps for genes, counts, mitochondrial fraction, and doublets.
- Check ambient RNA, dissociation stress, low-complexity cells, doublets, and sample-specific attrition.
- Confirm `var_names` uniqueness and outer-join merging when gene universes differ.
- Verify counts remain available for pseudobulk and that normalized/log layers are not mistaken for counts.
- Inspect batch integration before and after correction; quantify cohort mixing and preservation of disease/region signal.
- Check whether integration uses disease, region, or phenotype as a batch key and may erase the target signal.
- Annotate with positive, negative, and lineage-exclusion markers; distinguish cell type, lineage, transient state, and program score.
- Require donor support for clusters/subclusters; flag states confined to one donor, library, or batch.
- Treat tiny clusters, re-clustering choices, and marker-driven selection as potential selection bias.
- Use donor/sample-level composition models; cell counts are not biological replicates.
- Use pseudobulk or donor-aware mixed models for expression inference; cell-level p-values are exploratory when donors are the unit.
- Separate capture/digestion/survival effects from true tissue abundance changes.
- In spatial data, check spot mixtures, resolution, segmentation, neighborhood dependence, and section-level replication.

### Osteogenic and lineage naming warning

- Cartilage `RUNX2`, `SP7`, `ALPL`, `IBSP`, `BGLAP`, `COL10A1`, `MMP13`, or `SPP1` expression can indicate hypertrophic, mineralizing, injury, or osteogenic-like programs.
- These markers alone do not establish lineage conversion into bona fide osteoblasts.
- Preserve compartment-aware names such as “hypertrophic/mineralizing/osteogenic-like chondrocyte” unless broader lineage evidence supports osteoblast identity.

## 5. Differential abundance and pseudobulk

- State the biological replicate and aggregation key explicitly.
- Require adequate cells per pseudobulk and adequate donors per contrast; show excluded tests.
- Preserve paired designs and repeated measures with donor blocking.
- Fit each cohort separately when cohort effects remain strong; integrate effect evidence rather than pooling cells indiscriminately.
- Check compositional constraints and whether one expanding state forces apparent contraction of others.
- Apply multiple-testing correction within a clearly defined family and report the family.
- Check effect-direction stability across donors and cohorts, not only pooled significance.

## 6. Trajectory and pseudotime

- Justify the root using biology and marker evidence; test alternative roots when plausible.
- Treat pseudotime as transcriptomic ordering, not elapsed time or proven differentiation.
- Check partitions, disconnected components, branch support, and cells with infinite/unassigned pseudotime.
- Test sensitivity to forced connectivity, root, neighbor parameters, cluster resolution, and donor removal.
- Confirm trajectories are not batch, donor, depth, cell cycle, or stress gradients.
- Require multiple donors across branches and endpoints before generalizing a developmental path.
- Separate graph-associated genes from donor-aware differential evidence.
- Describe unstable intermediate ordering explicitly rather than selecting the preferred trajectory.

## 7. Regulatory networks and pySCENIC

- Verify organism, TF list, motif-ranking database, genome build, window sizes, and database versions.
- Record input cells/genes, TF overlap, GRN edges, retained regulons, and AUCell cells.
- Confirm cell IDs align between expression objects and loom outputs without loss or reordering.
- Check regulon size, TF detection, donor stability, region/group direction, and sensitivity to cell composition.
- Distinguish TF expression, regulon activity, motif enrichment, target expression, and phenotype association.
- Motif pruning predicts plausible binding; it is not direct TF occupancy.
- Co-expression and regulon activity do not establish causal activation or repression.
- Cell-level regulon tests are exploratory when donor count is the inferential unit.
- Require ChIP/CUT&Tag, reporter assays, perturbation, rescue, or equivalent evidence for direct regulation claims.

## 8. Enrichment and gene-set analysis

- Use the actually tested gene universe for ORA, not the whole genome by default.
- Record gene-set source, collection, version/date, species, and ID-conversion losses.
- Use a complete, deterministic ranked list for GSEA and document the statistic and direction.
- Separate positive and negative enrichment; avoid interpreting absolute significance without direction.
- Collapse redundant GO terms into themes without counting correlated terms as independent evidence.
- Check whether large regulons/modules or housekeeping genes dominate ORA.
- Treat pathway enrichment as shared annotation, not proof that the candidate directly controls the pathway.
- Test cross-cohort direction and avoid choosing only pathways that support the preferred model.

## 9. WGCNA and co-expression networks

- State independent sample count, gene filtering, network type, correlation, soft threshold, minimum module size, and merge threshold.
- Assess sample outliers and trait/batch balance before network construction.
- Report scale-free-fit limitations and predefined fallback rules.
- Model module–trait association with relevant batch, region, or clinical covariates.
- Correct across tested modules and distinguish gene significance from module membership.
- Test module stability or preservation when sample size and independent data permit.
- High kME or hub status indicates network centrality, not causal regulation.
- Bulk modules may reflect cell composition; integrate cell-resolved evidence before assigning a cell-intrinsic mechanism.

## 10. Multi-dataset, multi-tissue, and candidate integration

- Define the unit of integration: effect direction, significance, rank, module membership, regulon edge, or pathway theme.
- Never numerically merge incompatible tissues/platforms merely because genes overlap.
- Track evidence dependence: pseudobulk, markers, trajectory, and pySCENIC may originate from the same cells.
- Prevent double-counting multiple analyses of one dataset as independent replication.
- Predefine candidate filters or disclose post hoc selection and circularity.
- Include discordant datasets and missing evidence in the candidate matrix.
- Distinguish regulators, predicted direct targets, effectors, markers, and downstream phenotype readouts.
- Check tissue/cell-type direction consistency and plausible compartment-specific differences.
- Treat a weighted score as prioritization, not effect size, probability, or causal confidence.

## 11. Interpretation and logic

- Map each headline claim to the exact dataset, contrast, statistical unit, and evidence type that support it.
- Separate observation, statistical association, computational inference, biological hypothesis, and direct causality.
- State what the current design cannot answer.
- Provide at least one competing biological explanation for every central mechanism.
- Report negative or inconsistent evidence that would change confidence.
- Use “supports”, “is consistent with”, or “predicts” for observational/computational results.
- Reserve “drives”, “directly regulates”, and “causes” for perturbation or direct binding evidence.
- End with a decisive validation experiment tied to the weakest causal edge.

## Severity guide

- `BLOCKER`: the design cannot identify the central claimed effect, such as complete condition–platform confounding or absent comparator for the stated contrast.
- `MAJOR`: a likely bias or inference error can materially change the central result, such as pseudoreplication, wrong pairing, or non-independent validation.
- `MODERATE`: affects magnitude, ranking, stability, or generalizability but does not invalidate the whole analysis.
- `MINOR`: reporting, provenance, or presentation gap with limited biological impact.
- `INFO`: important boundary or context, not an error.
