---
name: bioinfo-mermaid-audit
description: Generate or update a project-wide Mermaid logic-audit report after completing, revising, delivering, or reviewing any bioinformatics analysis, including bulk RNA-seq, microarray, scRNA-seq, spatial or multi-omics integration, differential expression, trajectory, regulatory networks, enrichment, WGCNA, and candidate prioritization. Use whenever new bioinformatics Results are produced or the user asks for a workflow diagram, dataset-fit review, logic/risk audit, gene-function summary, or mechanism-axis interpretation.
---

# Bioinformatics Mermaid Logic Audit

Generate one evidence-backed audit document whose workflow is concise and whose risks, logic warnings, and biological interpretation are detailed. Describe the analysis that actually ran, not the proposed plan.

Use `bioinfo-delivery` alongside this skill when it is available. Preserve its directory, provenance, figure, and Results hygiene rules.

## Workflow

### 1. Fix the scope

Locate the project root containing `Data/`, `Results/`, and `Scripts/`. Default to a project-wide cumulative audit after any completed module. Use a module-local audit only when the user explicitly limits the scope.

Set the stable output path:

- Project-wide: `Results/analysis_logic_audit.md`
- Explicit module scope: `Results/NN.module/analysis_logic_audit.md`

Update the stable file in place. Do not create `final_v2`, dated copies, or a new numbered analysis module merely for documentation.

### 2. Build an evidence inventory

Run the bundled collector before interpreting the project:

```bash
python <skill-root>/scripts/collect_project_evidence.py --project-root <project-root>
```

Then read the relevant evidence directly:

1. Dataset catalogs, accession manifests, sample sheets, and acquisition summaries.
2. Actual scripts and parameter/config files.
3. `Data/Processed/*/run_summary.yaml` and key output object summaries.
4. Results READMEs, `figure_index.tsv`, figure names, and result-table headers.
5. The top rows or targeted records needed to support reported genes, effects, pathways, modules, and regulons.

Treat dataset names, sample counts, donor counts, tissue, region, disease labels, pairing, platform, covariates, reference genome, and completed analyses as evidence claims. Mark unsupported values `Unknown / 待确认`; never infer them from filenames alone.

Completion criterion: every dataset and major analysis node in the report has at least one inspected local evidence source.

### 3. Register datasets and evidence roles

Create a compact dataset table before the diagram:

| Dataset | Modality | Species | Tissue/region | Groups and n | Pairing/platform | Actual role | Main limitation |
|---|---|---|---|---|---|---|---|

Distinguish samples, libraries, and unique donors. Distinguish discovery, internal comparison, external validation, orthogonal support, and evidence reuse. State whether controls are healthy, non-diseased, adjacent, relatively preserved, or another surrogate.

### 4. Audit risks before drawing conclusions

Read [references/risk-checklist.md](references/risk-checklist.md) completely. Audit every applicable branch and label each item:

- Severity: `BLOCKER`, `MAJOR`, `MODERATE`, `MINOR`, or `INFO`.
- Evidence status: `VERIFIED`, `MITIGATED`, `OPEN`, `UNKNOWN`, or `NOT_APPLICABLE`.
- Claim class: dataset/design, preprocessing/QC, statistics, integration, or interpretation.

Use `BLOCKER` only when the intended comparison cannot identify the claimed biological effect. Use `UNKNOWN` when metadata or provenance are insufficient; do not silently downgrade uncertainty.

Rank risks by their impact on the central claim, not by how easy they are to fix. Include both mitigated and unresolved risks so reviewers can see why a result is or is not trusted.

Completion criterion: every central conclusion is checked against dataset suitability, biological replication, confounding, statistical unit, validation independence, and causal overreach.

### 5. Draw the Mermaid workflow

Start from [assets/report-template.md](assets/report-template.md). Keep the main workflow deliberately compact:

- Use separate subgraphs for distinct tissues, modalities, cohorts, or analysis branches.
- Name every actual dataset accession and include compact design facts: tissue/region, groups, donor/sample count when known, and platform when it matters.
- Give each major processing node one short description of what was done and its method.
- List figure types produced at that step, such as QC violin/retention, PCA, UMAP, DotPlot, volcano, trajectory, AUCell UMAP, heatmap, enrichment plot, module-trait heatmap, or evidence matrix.
- Draw arrows only for real data flow. Show evidence-level convergence separately from matrix-level integration.
- Attach three to eight highest-impact risk nodes with dashed arrows. Put the full risk detail in the table after the diagram.
- Prefer 8–25 process nodes. Group repetitive per-dataset operations instead of expanding every script call.
- Quote Mermaid labels and use stable ASCII node IDs. Avoid parentheses-heavy node IDs and unsupported HTML.

Validate Mermaid with a locally available renderer when possible. Do not install a renderer from the network only for validation. Otherwise check balanced subgraphs, unique IDs, defined edges, and closed code fences manually.

### 6. Write the detailed risk and logic table

Place the detailed table immediately after the diagram:

| ID | Severity | Status | Dataset/stage | Verified evidence | Risk or logic warning | Effect on conclusion | Current mitigation | Residual risk | Recommended action |
|---|---|---|---|---|---|---|---|---|---|

Write concrete statements. Example: “GSE196678 contains OA damaged and relatively preserved regions but no healthy donor” is auditable; “controls may be imperfect” is not.

For unresolved `BLOCKER` or `MAJOR` items, make the affected downstream claims explicit. For mitigated items, state exactly what analysis reduced the risk and what remains unresolved.

### 7. Write the biological meaning

Base the summary on actual output tables and effect directions. Search primary sources only when gene function or mechanism facts are not supported locally; cite those sources near the claim.

Separate these layers:

1. **Observed findings:** dataset, cell population or tissue, contrast, direction, effect size/significance, and replication.
2. **Gene functions:** molecular role, relevant cell/tissue context, and whether the statement comes from project data, annotation, or literature.
3. **Mechanism axis:** upstream regulator → predicted/direct target → pathway or phenotype. Label each edge by evidence type.
4. **Alternative explanations:** composition, injury response, stress, hypertrophy, batch, platform, or correlated state.
5. **Validation plan:** perturbation, rescue, ChIP/CUT&Tag, reporter assay, qPCR/protein localization, functional phenotype, and independent human cohort as applicable.

Use these evidence codes:

- `E1` single-cell expression/state association
- `E2` donor-level pseudobulk or mixed-model evidence
- `E3` trajectory dynamics
- `E4` TF/regulon or motif inference
- `E5` independent bulk or external-cohort validation
- `E6` GO/KEGG/GSEA support
- `E7` WGCNA/module membership
- `E8` direct literature or experimental evidence

Classify each mechanism as high, moderate, low, or hypothesis-level confidence. Reserve causal language for direct perturbation or binding evidence. State `independent validation`, `causal evidence`, `main limitation`, and `next validation` explicitly.

### 8. Deliver and verify

Write the Markdown report with `apply_patch`. Keep internal absolute paths, commands, logs, and run status outside `Results`. Link the audit from the project Results README only when that README is already used as project navigation.

Before completion, verify all of the following:

- Every dataset accession, tissue, group, sample/donor count, and role matches inspected evidence.
- Every diagram step ran and every listed figure type exists; missing planned analyses are labeled “not run”.
- The workflow separates tissues and statistical units correctly.
- The risk table is more detailed than the front workflow and contains evidence, impact, mitigation, residual risk, and action.
- The biological summary distinguishes observation, association, computational inference, hypothesis, and causality.
- Candidate genes include functions, direction, evidence codes, inconsistencies, and confidence.
- At least one alternative mechanism and one decisive validation experiment are stated for each central axis.
- The Mermaid block is syntactically coherent and the stable output file opens as Markdown.

Do not declare the audit complete until every check passes or the unresolved item is explicitly marked `UNKNOWN` with the information required to resolve it.
