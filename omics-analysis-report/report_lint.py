#!/usr/bin/env python3
"""
report_lint.py — Pre-flight lint for client-facing omics-analysis reports.

Catches the common defects that destroy a deliverable:

  1. Privacy:        absolute filesystem paths in body, captions or backticks
  2. Privacy:        leftover internal codenames (--bad-pattern flag)
  3. Completeness:   unfilled [占位符] tokens
  4. Cleanliness:    leftover HTML comments (<!-- ... -->) used as drafting notes
  5. Cleanliness:    raw HTML / JS / event handlers / javascript: URLs
  6. Figures:        ![]() image references whose file is missing on disk
  7. Figures:        figures without a **图N.** caption immediately following
  8. Figures:        figure number gaps or duplicates (图1 → 图3 with no 图2)
  9. Structure:      a `### 3.X` results subsection without any figure
  10. Structure:     methods (`### 2.X`) and results (`### 3.X`) counts diverge
  11. Scope:         client-facing results make biology/clinical/mechanism claims
  12. Coverage:      required figure types in a manifest are absent from report
  13. References:    method software has numeric GB/T 7714-2005 citations and a matching References section
  14. Privacy:       CPU/thread/worker counts, raw commands, or private code paths

Usage:
    python report_lint.py report.md
    python report_lint.py report.md --asset-base ./Figures
    python report_lint.py report.md --bad-pattern P20260429 --bad-pattern HBV
    python report_lint.py report.md --figure-manifest figure_manifest.tsv --strict-client-scope
    python report_lint.py report.md --strict-references

Exit code:
    0  no issues
    1  issues found (lint failed)
    2  bad invocation
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ----- patterns -----------------------------------------------------------

ABS_PATH_RE = re.compile(r"""
    (?:
        (?<![<\w.-])/(?!/)[^\s`),;，。<>]+
      | ~[/\\][^\s`),;，。]+
      | [A-Za-z]:[/\\][^\s`),;，。]+
      | \\\\[^\s`),;，。]+
    )
""", re.VERBOSE | re.IGNORECASE)

PLACEHOLDER_RE = re.compile(r"\[[^\[\]]{1,80}?\]")     # naive [..] match
PLACEHOLDER_OK = re.compile(
    r"^\[(?:(?:\d+(?:\s*(?:[-,，;；]\s*)\d+)*)|[A-Z]{1,3}(?:/[A-Z]{1,3})?|图|表|链接|TOC|目录|.\d*[-:].*?)\]$"
)  # whitelist
PLACEHOLDER_HINT_TOKENS = ("占位", "TODO", "FIXME", "XXX", "替换", "示例", "例如",
                           "如「", "如：", "略", "/", "...", "……")

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

DANGEROUS_HTML = [
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
    re.compile(r"<\s*object\b", re.IGNORECASE),
    re.compile(r"<\s*embed\b", re.IGNORECASE),
    re.compile(r"<\s*style\b", re.IGNORECASE),
    # inline event handler — require a real tag-open (`<tagname ... on\w+=`)
    # so prose like `p_val_adj < 0.05 ... ont='BP'` does not trigger.
    re.compile(r"<\s*[a-zA-Z][\w-]*\b[^>]*?\son\w+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
]

IMAGE_REF_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
FIGURE_CAPTION_RE = re.compile(r"^\s*\*\*\s*(图|表)\s*(\d+)[-\d]*\.?\s*\*\*", re.MULTILINE)
H3_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
URL_LIKE_RE = re.compile(r"^(?:https?:|data:|mailto:|#)", re.IGNORECASE)
TABLE_PATH_IN_BACKTICKS_RE = re.compile(r"`[^`\n]+\.(?:tsv|csv|xls|xlsx)`", re.IGNORECASE)
DELIVERABLE_PATH_IN_BACKTICKS_RE = re.compile(
    r"`[^`\n]+\.(?:tsv|csv|xls|xlsx|png|jpg|jpeg|svg|pdf|rds|h5ad|loom|h5|hdf5|qs2)`",
    re.IGNORECASE,
)
SAMPLE_ID_RE = re.compile(
    r"\b(?:GSM|SRR|ERR|DRR|SAMN|SAMEA|SAMDR|PRJNA|PRJEB|PRJDB)\d+\b|"
    r"\bTCGA-[A-Z0-9]{2}-[A-Z0-9]{4}(?:-[A-Z0-9]{2}[A-Z]?)?\b"
)
DIFFERENTIAL_ANALYSIS_RE = re.compile(
    r"(?:差异表达|差异分析|显著差异|DESeq2|limma|edgeR|DEGs?\b|DEGs_|"
    r"log2FoldChange|differential|差异基因|marker\s+gene|markers?\b|特征排序|feature[- ]ranking|"
    r"模块-分组|分组性状|groups\s*性状|module[- ]trait|trait_cor|模块[^。；\n]{0,20}性状)",
    re.IGNORECASE,
)
ENRICHMENT_SECTION_RE = re.compile(
    r"(?:富集|GSEA|GO[、/]|KEGG|Reactome|pathway|enrichment)",
    re.IGNORECASE,
)
ENRICHMENT_COMPARISON_WORDING_RE = re.compile(
    r"(?:沿用[^。；\n]{0,30}(?:差异表达)?(?:对比|比较|分组)|"
    r"富集[^。；\n]{0,30}(?:对照组|实验组)|"
    r"GSEA[^。；\n]{0,30}(?:对照组|实验组)|"
    r"(?:对照组|实验组))",
    re.IGNORECASE,
)
CONTROL_GROUP_RE = re.compile(r"对照组")
EXPERIMENT_GROUP_RE = re.compile(r"实验组")
METHOD_RESULT_WORDING_RE = re.compile(
    r"(?:当前结果|本交付目录|交付目录|结果目录|结果文件|结果包含|当前[^。；\n]{0,40}包含|"
    r"该表|最高\s*qvalue|排序靠前|输出\s*按|输出\s*中|位于\s*`|对应\s*`|"
    r"检查图对应|结果中|显著差异基因|hub genes\s*表|"
    r"包含\s*\d+\s*个|记录\s*\d+\s*例)",
    re.IGNORECASE,
)
PUBLIC_DATA_SOURCE_RE = re.compile(
    r"(?:公共数据|公开数据|GEO|SRA|ArrayExpress|TCGA|\bGSE\d+\b|\bGSM\d+\b|"
    r"\bSRP\d+\b|\bERP\d+\b|\bDRP\d+\b|\bPRJNA\d+\b|\bPRJEB\d+\b|"
    r"\bE-MTAB-\d+\b)",
    re.IGNORECASE,
)
UPSTREAM_ALIGNMENT_METHOD_RE = re.compile(
    r"(?:bcl2fastq|base calling|STAR(?:\s+v?[\d.]|\b)|HISAT2|Bowtie2|BWA|"
    r"featureCounts|HTSeq|Salmon|Kallisto|Cell Ranger|FastQC|fastp|Trim Galore|"
    r"cutadapt|Trimmomatic|上游比对|比对到|比对至|映射到参考基因组|参考基因组比对|"
    r"测序\s*reads|原始\s*reads|\breads?\b)",
    re.IGNORECASE,
)
RAW_REPROCESSING_EVIDENCE_RE = re.compile(
    r"(?:(?:本项目|当前项目|本次分析|current project)[^。；\n]{0,80}"
    r"(?:重新|reprocess|raw|FASTQ|fastq|原始\s*reads|\breads?\b|比对|定量)|"
    r"(?:使用|从)[^。；\n]{0,30}(?:FASTQ|fastq|原始\s*reads)[^。；\n]{0,80}"
    r"(?:比对|定量|reprocess))",
    re.IGNORECASE,
)

CLIENT_SCOPE_FORBIDDEN = [
    (
        "biology-mechanism",
        re.compile(
            r"(?:病理机制|作用机制|分子机制|疾病机制|通路驱动|TME\s*重塑|"
            r"肿瘤微环境重塑|表型驱动|机制假说|机制方面|揭示[^。；，]*机制|"
            r"提供[^。；，]*机制)",
            re.IGNORECASE,
        ),
    ),
    (
        "clinical-claim",
        re.compile(
            r"(?:临床意义|治疗(?:价值|策略|作用|效果|潜力|靶点|应用)|"
            r"诊断(?:价值|标志物|模型)|预后(?:价值|相关|不良|良好|模型)|"
            r"患者获益|疗效)",
            re.IGNORECASE,
        ),
    ),
    (
        "target-claim",
        re.compile(
            r"(?:靶点筛选|候选靶点|治疗靶点|下游靶点|关键靶点|"
            r"重点关注的对象|提供[^。；，]*靶点|drug target)",
            re.IGNORECASE,
        ),
    ),
    (
        "overclaim",
        re.compile(
            r"(?:与既往研究一致|为[^。；，]*提供依据|提供了[^。；，]*假说|"
            r"提示[^。；，]*(?:机制|治疗|诊断|预后|病理|生物学|靶点)|"
            r"暗示[^。；，]*(?:机制|治疗|诊断|预后|病理|生物学|靶点)|"
            r"已知[^。；，]*(?:机制|恶性表型))",
            re.IGNORECASE,
        ),
    ),
    (
        "biology-direction",
        re.compile(r"(?:生物学意义|生物学功能|核心生物学发现|功能特征[^。；，]*高度一致)"),
    ),
]

REPORT_STYLE_FORBIDDEN = [
    (
        "dataset-source-meta",
        re.compile(
            r"(?:本报告使用当前交付目录中的已完成分析结果|不重新推断原始实验设计|"
            r"由于只提供了结果目录|根据文件名推测|仅根据结果目录)",
        ),
    ),
    (
        "awkward-representative-wording",
        re.compile(
            r"(?:以下以[^。；\n]{1,80}为代表说明读法|"
            r"以[^。；\n]{1,80}为代表说明每类图的读法|代表图用于说明读法)",
        ),
    ),
    (
        "redundant-result-folder-wording",
        re.compile(r"(?:完整同类型结果位于|完整同类型图片位于|同类型结果位于|同类型图片位于)"),
    ),
    (
        "generic-table-label",
        re.compile(r"(?:完整\s*marker/DEG\s*表|完整\s*marker/差异基因表|完整差异表|完整差异基因表|完整差异表达表|(?<!DEGs_)过滤表)"),
    ),
    (
        "intersection-gene-wording",
        re.compile(r"(?:共享基因|共享基因集合|共享靶点|重叠基因)"),
    ),
    (
        "awkward-docking-score-wording",
        re.compile(r"(?:评分最负|最负构象|结合能最负|亲和力[^。；\n]{0,20}最负)"),
    ),
    (
        "docking-legend-only-panel",
        re.compile(r"(?:PLIP[._-]?legend|PLIP\s*图例|相互作用类型图例|图例面板|图例说明氢键)", re.IGNORECASE),
    ),
    (
        "docking-overall-pocket-legend-path",
        re.compile(r"Viz/png/legend/overall_pocket", re.IGNORECASE),
    ),
    (
        "single-cell-unacademic-integration-wording",
        re.compile(
            r"(?:低维潜在表示|潜在表示|整合表示|整合后的潜在表示|"
            r"scVI\s*整合后的[^。；\n]{0,20}表示|"
            r"latent representation|integrated latent representation)",
            re.IGNORECASE,
        ),
    ),
    (
        "reader-address-term",
        re.compile(r"(?:客户|用户|使用者|读者)"),
    ),
    (
        "report-body-field-wording",
        re.compile(r"(?:字段|主要字段包括|字段说明|包含[^。；\n]{0,60}字段|字段\s*Metrics\s*表示)"),
    ),
    (
        "third-party-action-guidance",
        re.compile(
            r"(?:"
            r"使用者可|用户可|后续可|如需|"
            r"建议(?:按|将|使用|继续|打开|导入|载入|下载|筛选|查看)?|"
            r"可按[^。；\n]{0,80}(?:筛选|查看|查找|检索|排序|定位|复核|关联|载入|导入|打开|下载|继续)|"
            r"也可[^。；\n]{0,80}(?:筛选|查看|查找|检索|排序|定位|复核|关联|载入|导入|打开|下载|继续|在)|"
            r"可(?:导入|载入|打开|下载)[^。；\n]{0,80}|"
            r"可在\s*(?:R/Python|Python|R|Excel|Cytoscape)[^。；\n]{0,80}"
            r")",
        ),
    ),
    (
        "comment-like-caveat",
        re.compile(
            r"(?:"
            r"该(?:描述|分析|结果|图|图表|表|指标)[^。；\n]{0,24}仅(?:反映|作为|用于|展示|说明)|"
            r"该描述来自[^。；\n]{0,80}|"
            r"仅作为[^。；\n]{0,60}(?:指标|参考|说明|展示)使用?|"
            r"仅供参考|"
            r"不将[^。；\n]{0,80}解释为|"
            r"不直接解释为|"
            r"不代表[^。；\n]{0,80}(?:机制|因果|临床|诊断|治疗|预后|结论|意义)"
            r")",
        ),
    ),
    (
        "internal-workflow-name",
        re.compile(r"(?:\bAuto\s*(?:工作流|流程|workflow|pipeline)\b|Auto\s*工作流)", re.IGNORECASE),
    ),
    (
        "company-internal-parameter-wording",
        re.compile(r"(?:公司内部|内部自定义参数|内部参数|私有参数|私有流程|私有脚本|自定义流程|内部流程)"),
    ),
]

RESULT_HEADING_INVENTORY_RE = re.compile(
    r"^###\s+3\.\d+\s+.*(?:输出|产生|包含|五类|多类|若干).*(?:图|图表|文件|结果)"
)

DELIVERY_PRIVACY_FORBIDDEN = [
    (
        "compute-resource",
        re.compile(
            r"(?:--cpu\b|--threads?\b|--num_workers\b|--n[-_]?workers\b|"
            r"\bN_WORKERS\b|\bnum_workers\b|\bworkers\s*=|\bthreads?\s*=|"
            r"\bn_jobs\s*=|\bcores?\s*=|\bMulticoreParam\b|"
            r"\bCPU\b|线程|工作线程|并行后端|parallel backend)",
            re.IGNORECASE,
        ),
    ),
    (
        "raw-command",
        re.compile(
            r"(?:\b(?:python|python3|Rscript|bash|sh|zsh|vina|pyscenic)\s+--|"
            r"\b(?:python|python3|Rscript|bash|sh|zsh|vina|pyscenic)\s+[^\n。；]*\s--)",
            re.IGNORECASE,
        ),
    ),
    (
        "private-code-path",
        re.compile(
            r"(?:/Users/Donjae/Documents/Bioinfomatics/work_flow/Auto|"
            r"/share/CodeBase/work_flow/Auto|\bAuto/(?:scRNA|DEG_auto|Ph_net|Enrichment|WGCNA|TCGA_data_auto|GEO_data_auto)\b)"
        ),
    ),
    (
        "implementation-backend",
        re.compile(r"(?:dask_multiprocessing|运行命令|命令行|脚本路径|代码库|源码|源代码|运行脚本|运行日志)")
    ),
]

REFERENCE_HEADING_RE = re.compile(r"(?m)^##+\s*(?:\d+\.\s*)?(?:参考文献|References)\s*$", re.IGNORECASE)
CITATION_KEY_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9_]+(?:\s*;\s*[A-Za-z][A-Za-z0-9_]+)*)\]")
NUMERIC_CITATION_RE = re.compile(r"\[(\d+(?:\s*(?:[-,，;；]\s*)\d+)*)\]")
REFERENCE_ENTRY_RE = re.compile(r"(?m)^\s*(?:[-*]\s*)?\[(\d+)\]\s+(.+)$")
SUP_CITATION_RE = re.compile(r"<sup\b[^>]*>.*?</sup>", re.IGNORECASE | re.S)
REFERENCE_HREF_RE = re.compile(r"href=[\"']#ref-(\d+)[\"']", re.IGNORECASE)
REFERENCE_ANCHOR_RE = re.compile(r"id=[\"']ref-(\d+)[\"']", re.IGNORECASE)
GB_T_PUBLICATION_TYPE_RE = re.compile(r"\[[A-Z]{1,3}(?:/[A-Z]{1,3})?\]")
BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)")
BIB_ENTRY_BLOCK_RE = re.compile(r"(?ms)^@\w+\s*\{\s*([^,\s]+)\s*,(.*?)(?=^@\w+\s*\{|\Z)")
BIB_FIELD_RE = re.compile(r"(?ms)\b(title|doi|pmid|url)\s*=\s*[\{'\"](.+?)[\}'\"]\s*,?")
METHOD_SECTION_RE = re.compile(r"(?ms)^##\s+2\.\s*方法\b.*?(?=^##\s+\d+\.|\Z)")
METHOD_H3_SECTION_RE = re.compile(r"(?ms)^###\s+(2\.\d+)\s+(.+?)\s*$\n(.*?)(?=^###\s+2\.\d+\s+|\Z)")
METHOD_DEPTH_SKIP_HEADING_RE = re.compile(
    r"(?:数据获取|数据收集|对象选择|数据下载|表达数据获取|临床表型|样本信息|平台注释)"
)
METHOD_PRINCIPLE_RE = re.compile(
    r"(?:"
    r"基于|通过|模型|算法|检验|回归|估计|推断|搜索|比对|识别|构建|计算|排序|富集|评分|校正|"
    r"拟合|平滑|剪枝|去噪|解卷积|建模|负二项|经验贝叶斯|变分|自编码器|邻近图|置换|"
    r"Wilcoxon|Wald|Poisson|AUC|LDA|support\s+vector|random\s+forest|motif|probability"
    r")",
    re.IGNORECASE,
)
METHOD_CHARACTERISTIC_RE = re.compile(
    r"(?:"
    r"特点|适合|便于|能够|可用于|可将|可在|支持|提高|降低|稳健|快速|统一|可追溯|可解释|"
    r"保留|分辨率|高通量|兼容|稳定|适配|直接用于|便于后续|便于在|适用|用于"
    r")",
    re.IGNORECASE,
)
METHOD_PARAMETER_RE = re.compile(
    r"(?:"
    r"阈值|参数|数据库|版本|物种|参考基因组|分组|设计矩阵|contrast|resolution|min_dist|"
    r"n_neighbors|n_comps|n_latent|pvalue|qvalue|padj|FDR|log2FC|logFC|fold\s*change|"
    r"FC|VIP|ppm|peakwidth|maxEE|p\s*值|P\s*值|校正|cutoff|background|universe|"
    r"organism|species|batch|seed|random_state|[<>]=?|=\s*[\w.]+|\b\d+(?:\.\d+)?\b"
    r")",
    re.IGNORECASE,
)

METHOD_REFERENCE_RULES = [
    ("Scanpy", re.compile(r"\bScanpy\b", re.IGNORECASE), ("Wolf2018Scanpy",)),
    ("AnnData/anndata", re.compile(r"\b(?:AnnData|anndata|h5ad)\b", re.IGNORECASE), ("Virshup2024Anndata",)),
    ("rapids_singlecell", re.compile(r"\brapids_singlecell\b", re.IGNORECASE), ("Dicks2026RapidsSinglecell",)),
    ("Scrublet", re.compile(r"\bScrublet\b", re.IGNORECASE), ("Wolock2019Scrublet",)),
    ("scVI/scvi-tools", re.compile(r"\b(?:scVI|scvi-tools|X_scVI)\b", re.IGNORECASE), ("Lopez2018ScVI", "Gayoso2022ScviTools")),
    ("UMAP", re.compile(r"\bUMAP\b", re.IGNORECASE), ("McInnes2018UMAP",)),
    ("Leiden", re.compile(r"\bLeiden\b", re.IGNORECASE), ("Traag2019Leiden",)),
    ("scType", re.compile(r"\b(?:scType|ScTypeDB)\b", re.IGNORECASE), ("Ianevski2022ScType",)),
    ("anndataR", re.compile(r"\banndataR\b", re.IGNORECASE), ("Deconinck2025AnndataR",)),
    ("inferCNV", re.compile(r"\binferCNV\b", re.IGNORECASE), ("Tickle2019InferCNV",)),
    ("CellChat", re.compile(r"\bCellChat\b", re.IGNORECASE), ("Jin2021CellChat",)),
    ("Augur", re.compile(r"\bAugur\b", re.IGNORECASE), ("Skinnider2021Augur",)),
    ("pySCENIC", re.compile(r"\bpySCENIC\b", re.IGNORECASE), ("VanDeSande2020pySCENIC", "Aibar2017SCENIC")),
    ("GRNBoost2", re.compile(r"\bGRNBoost2\b", re.IGNORECASE), ("Moerman2019GRNBoost2",)),
    ("DESeq2", re.compile(r"\bDESeq2\b", re.IGNORECASE), ("Love2014DESeq2",)),
    ("limma", re.compile(r"\blimma\b", re.IGNORECASE), ("Ritchie2015Limma",)),
    ("edgeR", re.compile(r"\bedgeR\b", re.IGNORECASE), ("Robinson2010EdgeR",)),
    ("GEOquery", re.compile(r"\bGEOquery\b", re.IGNORECASE), ("Davis2007GEOquery",)),
    ("cBioPortalData", re.compile(r"\bcBioPortalData\b", re.IGNORECASE), ("Ramos2020cBioPortalData",)),
    ("GDC", re.compile(r"\bGDC\b"), ("Jensen2017GDC", "Wilson2017GDCAPI")),
    ("clusterProfiler", re.compile(r"\b(?:clusterProfiler|enrichGO|enrichKEGG|gseGO|gseKEGG)\b", re.IGNORECASE), ("Yu2012ClusterProfiler",)),
    ("enrichplot", re.compile(r"\b(?:enrichplot|gseaplot2|emapplot)\b", re.IGNORECASE), ("Yu2025Enrichplot",)),
    ("pathview", re.compile(r"\bpathview\b", re.IGNORECASE), ("Luo2013Pathview",)),
    ("topGO", re.compile(r"\btopGO\b", re.IGNORECASE), ("Alexa2006TopGO",)),
    ("ReactomePA/Reactome", re.compile(r"\b(?:ReactomePA|Reactome)\b", re.IGNORECASE), ("Yu2016ReactomePA",)),
    ("KEGG", re.compile(r"\bKEGG\b", re.IGNORECASE), ("Kanehisa2025KEGG",)),
    ("Gene Ontology", re.compile(r"\b(?:Gene Ontology|GO)\b"), ("GeneOntologyConsortium2026",)),
    ("org.Hs.eg.db", re.compile(r"\borg\.Hs\.eg\.db\b", re.IGNORECASE), ("Carlson2026OrgHsEgDb",)),
    ("org.Mm.eg.db", re.compile(r"\borg\.Mm\.eg\.db\b", re.IGNORECASE), ("Carlson2026OrgMmEgDb",)),
    ("org.Rn.eg.db", re.compile(r"\borg\.Rn\.eg\.db\b", re.IGNORECASE), ("Carlson2026OrgRnEgDb",)),
    ("WGCNA", re.compile(r"\bWGCNA\b", re.IGNORECASE), ("Langfelder2008WGCNA",)),
    ("ComplexHeatmap", re.compile(r"\bComplexHeatmap\b", re.IGNORECASE), ("Gu2016ComplexHeatmap",)),
    ("ggplot2", re.compile(r"\bggplot2\b", re.IGNORECASE), ("Wickham2016Ggplot2",)),
    ("pheatmap", re.compile(r"\bpheatmap\b", re.IGNORECASE), ("Kolde2025Pheatmap",)),
    ("Cytoscape", re.compile(r"\bCytoscape\b", re.IGNORECASE), ("Shannon2003Cytoscape",)),
    ("CytoHubba", re.compile(r"\bCytoHubba\b", re.IGNORECASE), ("Chin2014CytoHubba",)),
    ("starBase", re.compile(r"\bstarBase\b", re.IGNORECASE), ("Li2014StarBase",)),
    ("BATMAN-TCM", re.compile(r"\bBATMAN-TCM\b", re.IGNORECASE), ("Kong2024BATMANTCM2",)),
    ("AutoDock Vina", re.compile(r"\b(?:AutoDock\s+Vina|Vina)\b", re.IGNORECASE), ("Trott2010AutoDockVina", "Eberhardt2021AutoDockVina12")),
    ("fpocket", re.compile(r"\bfpocket\b", re.IGNORECASE), ("LeGuilloux2009Fpocket",)),
    ("PLIP", re.compile(r"\bPLIP\b", re.IGNORECASE), ("Salentin2015PLIP",)),
    ("PyMOL", re.compile(r"\bPyMOL\b", re.IGNORECASE), ("DeLano2002PyMOL",)),
    ("RDKit", re.compile(r"\bRDKit\b", re.IGNORECASE), ("RDKit2026",)),
    ("Open Babel", re.compile(r"\b(?:OpenBabel|Open\s+Babel)\b", re.IGNORECASE), ("OBoyle2011OpenBabel",)),
    ("PubChem", re.compile(r"\bPubChem\b", re.IGNORECASE), ("Kim2025PubChem",)),
    ("ChEMBL", re.compile(r"\bChEMBL\b", re.IGNORECASE), ("Zdrazil2024ChEMBL",)),
    ("RCSB PDB", re.compile(r"\b(?:RCSB|Protein\s+Data\s+Bank|PDB)\b", re.IGNORECASE), ("Berman2000PDB",)),
    ("Psi4", re.compile(r"\bPsi4\b", re.IGNORECASE), ("Smith2020Psi4",)),
    ("fastp", re.compile(r"\bfastp\b", re.IGNORECASE), ("Chen2018Fastp",)),
    ("STAR", re.compile(r"\bSTAR\b"), ("Dobin2013STAR",)),
    ("Salmon", re.compile(r"\bSalmon\b", re.IGNORECASE), ("Patro2017Salmon",)),
    ("featureCounts", re.compile(r"\bfeatureCounts\b", re.IGNORECASE), ("Liao2014FeatureCounts",)),
    ("voom", re.compile(r"\bvoom\b", re.IGNORECASE), ("Law2014Voom",)),
    ("sva", re.compile(r"\bsva\b", re.IGNORECASE), ("Leek2012SVA",)),
    ("ComBat", re.compile(r"\bComBat(?:-seq)?\b", re.IGNORECASE), ("Johnson2007ComBat",)),
    ("TCGAbiolinks", re.compile(r"\bTCGAbiolinks\b", re.IGNORECASE), ("Colaprico2016TCGAbiolinks",)),
    ("MSigDB", re.compile(r"\bMSigDB\b", re.IGNORECASE), ("Liberzon2011MSigDB", "Liberzon2015Hallmark")),
    ("GSVA/ssGSEA", re.compile(r"\b(?:GSVA|ssGSEA)\b", re.IGNORECASE), ("Hanzelmann2013GSVA", "Barbie2009ssGSEA")),
    ("CIBERSORT", re.compile(r"\bCIBERSORTx?\b", re.IGNORECASE), ("Newman2015CIBERSORT",)),
    ("xCell", re.compile(r"\bxCell\b", re.IGNORECASE), ("Aran2017xCell",)),
    ("ESTIMATE", re.compile(r"\bESTIMATE(?:Score)?\b", re.IGNORECASE), ("Yoshihara2013ESTIMATE",)),
    ("MCP-counter", re.compile(r"\bMCP-?counter\b", re.IGNORECASE), ("Becht2016MCPCounter",)),
    ("tidymass", re.compile(r"\btidymass\b", re.IGNORECASE), ("Shen2022TidyMass",)),
    ("MetaboAnalystR", re.compile(r"\bMetaboAnalystR\b", re.IGNORECASE), ("Pang2024MetaboAnalystR4",)),
    ("XCMS", re.compile(r"\bXCMS\b", re.IGNORECASE), ("Smith2006XCMS",)),
    ("MS-DIAL", re.compile(r"\bMS-?DIAL\b", re.IGNORECASE), ("Tsugawa2015MSDIAL",)),
    ("QIIME 2", re.compile(r"\bQIIME\s*2\b", re.IGNORECASE), ("Bolyen2019QIIME2",)),
    ("DADA2", re.compile(r"\bDADA2\b", re.IGNORECASE), ("Callahan2016DADA2",)),
    ("phyloseq", re.compile(r"\bphyloseq\b", re.IGNORECASE), ("McMurdie2013Phyloseq",)),
    ("vegan", re.compile(r"\bvegan\b", re.IGNORECASE), ("Oksanen2026Vegan",)),
    ("LEfSe", re.compile(r"\bLEfSe\b", re.IGNORECASE), ("Segata2011LEfSe",)),
    ("ANCOM-BC", re.compile(r"\bANCOM-BC2?\b", re.IGNORECASE), ("Lin2020ANCOMBC", "Lin2024ANCOMBC2")),
    ("MACS/MACS2", re.compile(r"\bMACS2?\b", re.IGNORECASE), ("Zhang2008MACS",)),
    ("HOMER", re.compile(r"\bHOMER\b", re.IGNORECASE), ("Heinz2010HOMER",)),
    ("ChIPseeker", re.compile(r"\bChIPseeker\b", re.IGNORECASE), ("Yu2015ChIPseeker",)),
    ("DiffBind", re.compile(r"\bDiffBind\b", re.IGNORECASE), ("Stark2026DiffBind",)),
    ("Seurat", re.compile(r"\b(?:Seurat|FindMarkers|FindAllMarkers)\b", re.IGNORECASE), ("Satija2015Seurat", "Stuart2019Seurat", "Hao2021SeuratV4", "Hao2024SeuratV5")),
    ("ClusterGVis", re.compile(r"\bClusterGVis\b", re.IGNORECASE), ("Zhang2026ClusterGVis",)),
    ("Cell Ranger", re.compile(r"\bCell\s+Ranger\b", re.IGNORECASE), ("Zheng2017SingleCell3Prime",)),
]


# ----- issue model --------------------------------------------------------

SEVERITY = ("error", "warning")


@dataclass
class Issue:
    severity: str
    line: int | None
    code: str
    message: str


@dataclass
class LintReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, line: int | None = None) -> None:
        self.issues.append(Issue(severity, line, code, message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]


# ----- checks -------------------------------------------------------------

def strip_code_fences(text: str) -> str:
    """Strip fenced code blocks so legitimate examples inside them don't trigger checks."""
    return re.sub(r"```.*?```", "", text, flags=re.S)


def check_absolute_paths(md: str, report: LintReport) -> None:
    # Strip HTML comments globally (they may span multiple lines).
    # We replace each comment with same number of newlines so line numbers stay aligned.
    def _blank_comment(m):
        return "\n" * m.group(0).count("\n")
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub(_blank_comment, md))
    cleaned = re.sub(r"https?://[^\s`)]+", "", cleaned)
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        for m in ABS_PATH_RE.finditer(line):
            report.add(
                "error", "abs-path",
                f"BLOCKED privacy leak: absolute filesystem path '{m.group(0)}' must not appear in a client report. Use a relative path.",
                line=lineno,
            )


def check_bad_patterns(md: str, patterns: list[str], report: LintReport) -> None:
    if not patterns:
        return
    for lineno, line in enumerate(md.splitlines(), start=1):
        for pat in patterns:
            if pat and pat in line:
                report.add(
                    "error", "bad-pattern",
                    f"Forbidden token '{pat}' present in report (line stripped to: '{line.strip()[:80]}').",
                    line=lineno,
                )


def check_unfilled_placeholders(md: str, report: LintReport) -> None:
    """Find [..] that look like unfilled templating tokens."""
    cleaned = HTML_COMMENT_RE.sub("", md)
    cleaned = strip_code_fences(cleaned)
    # remove markdown links [text](url) and image refs ![text](url)
    cleaned = re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", cleaned)
    # remove reference-style links [text][ref]
    cleaned = re.sub(r"\[[^\]]*\]\[[^\]]*\]", "", cleaned)
    # remove plain numeric/figure references like [图1]
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        for m in PLACEHOLDER_RE.finditer(line):
            token = m.group(0)
            inner = token[1:-1]
            if not inner.strip():
                continue
            # Skip whitelisted forms (图N, 表N, citation-like, etc.)
            if PLACEHOLDER_OK.match(token):
                continue
            # If it looks like a citation (numbers only or letter-number), skip
            if NUMERIC_CITATION_RE.match(token):
                continue
            # If it doesn't look like a placeholder hint, only complain when CJK markers
            # like 占位符, 示例, TODO, slash-options 'A / B / C', or trailing ……/...
            looks_like_placeholder = (
                any(tok in inner for tok in PLACEHOLDER_HINT_TOKENS)
                or "..." in inner
                or "……" in inner
                or " / " in inner
                or "X" in inner and "%" in inner  # [N%] / [X%]
                or re.match(r"^[A-Z\s]+\d?$", inner) and len(inner) >= 2  # all-caps shorts
                or re.match(r"^N(?:\s|$)", inner)  # [N 例 …]
                or "GSE" in inner and "x" in inner
            )
            if looks_like_placeholder:
                report.add(
                    "error", "placeholder",
                    f"Unfilled placeholder '{token}' — replace with the project's actual value.",
                    line=lineno,
                )


def check_html_comments(md: str, report: LintReport) -> None:
    """HTML comments are useful for skill instructions, but must be removed before delivery."""
    for m in HTML_COMMENT_RE.finditer(md):
        line = md.count("\n", 0, m.start()) + 1
        snippet = m.group(0).strip().splitlines()[0][:100]
        report.add(
            "warning", "html-comment",
            f"Leftover HTML comment '{snippet}' — drafting notes must be removed before delivery.",
            line=line,
        )


def check_raw_html(md: str, report: LintReport) -> None:
    cleaned = strip_code_fences(md)
    cleaned = re.sub(r"`[^`\n]+`", "", cleaned)
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        for pat in DANGEROUS_HTML:
            if pat.search(line):
                report.add(
                    "error", "raw-html",
                    f"Disallowed raw HTML / JS on this line: {line.strip()[:100]}",
                    line=lineno,
                )
                break


def check_image_resolution(md: str, asset_base: Path, report: LintReport) -> list[tuple[int, str]]:
    """Return [(line, src)] for every image reference. Side-effect: log missing files."""
    refs = []
    for lineno, line in enumerate(md.splitlines(), start=1):
        for m in IMAGE_REF_RE.finditer(line):
            src = m.group(2)
            refs.append((lineno, src))
            if URL_LIKE_RE.match(src) or ABS_PATH_RE.search(src):
                continue
            target = (asset_base / src).resolve()
            if not target.exists():
                report.add(
                    "error", "missing-image",
                    f"Image '{src}' not found under {asset_base}.",
                    line=lineno,
                )
    return refs


def _figure_panel_label(index: int) -> str:
    label = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _check_panel_caption(caption: str, image_count: int, report: LintReport, line: int) -> None:
    if image_count < 2:
        return
    caption = FIGURE_CAPTION_RE.sub("", caption, count=1).lstrip()
    expected = [_figure_panel_label(i) for i in range(image_count)]
    described = []
    pattern = r"(?:^|[。；;])\s*([A-Z]{1,3})(?:\s*[-–—]\s*([A-Z]{1,3}))?\s*[:：]"

    def number(label: str) -> int:
        value = 0
        for character in label:
            value = value * 26 + ord(character) - 64
        return value - 1

    for start, end in re.findall(pattern, caption, flags=re.MULTILINE):
        first = number(start)
        last = number(end) if end else first
        if last < first or last >= image_count:
            described.append(f"{start}-{end}" if end else start)
        else:
            described.extend(_figure_panel_label(i) for i in range(first, last + 1))
    if described != expected:
        report.add(
            "error", "figure-panel-caption",
            f"Multi-image figure has {image_count} panels; expected caption labels "
            f"{', '.join(expected)}, got {', '.join(described) or 'none'}.",
            line=line,
        )


def check_figure_numbering_and_captions(md: str, report: LintReport) -> None:
    """Verify each image is followed by a 图N./表N. caption and that the numbers are sequential."""
    lines = md.splitlines()
    # Track image groups: consecutive ![]() blocks count as one figure
    figure_groups: list[tuple[int, int]] = []  # (start_line, end_line)
    i = 0
    while i < len(lines):
        if IMAGE_REF_RE.search(lines[i]):
            start = i
            while i < len(lines) and (
                IMAGE_REF_RE.search(lines[i])
                or lines[i].strip() == ""
                and i + 1 < len(lines) and IMAGE_REF_RE.search(lines[i + 1])
            ):
                i += 1
            figure_groups.append((start, i - 1))
        else:
            i += 1

    expected_fig_no = 0
    for start, end in figure_groups:
        # Look ahead up to 5 non-empty lines for **图N.** caption
        caption_no: int | None = None
        for j in range(end + 1, min(end + 8, len(lines))):
            line = lines[j].strip()
            if not line:
                continue
            m = re.match(r"\*\*\s*(图|表)\s*(\d+)[-\d]*\.?\s*\*\*", line)
            if m:
                caption_no = int(m.group(2))
                break
            # If we hit a non-caption paragraph first, there is no caption
            if not line.startswith(("![", "[")):
                break

        if caption_no is None:
            report.add(
                "error", "missing-caption",
                f"Image group starting at line {start + 1} has no **图N.** caption immediately after.",
                line=start + 1,
            )
            continue

        image_count = sum(len(IMAGE_REF_RE.findall(value)) for value in lines[start:end + 1])
        caption_end = j + 1
        while caption_end < len(lines) and lines[caption_end].strip():
            caption_end += 1
        _check_panel_caption('\n'.join(lines[j:caption_end]), image_count, report, j + 1)

        expected_fig_no += 1
        if caption_no != expected_fig_no:
            report.add(
                "error", "figure-numbering",
                f"Figure numbering jumped or duplicated: expected 图{expected_fig_no}, got 图{caption_no}.",
                line=start + 1,
            )
            # Re-sync so we keep reporting downstream gaps relative to current
            expected_fig_no = caption_no


def check_methods_results_alignment(md: str, report: LintReport) -> None:
    """The number of `### 2.X` method subsections and `### 3.X` result subsections should match (excluding 2.1 数据获取)."""
    h3s = H3_RE.findall(md)
    methods = [h for h in h3s if re.match(r"^\s*2\.\d", h)]
    results = [h for h in h3s if re.match(r"^\s*3\.\d", h)]
    # remove the universal opener 2.1 数据获取 from comparison
    methods_minus_intro = [m for m in methods if "数据获取" not in m]
    if len(methods_minus_intro) != len(results):
        report.add(
            "warning", "structure-mismatch",
            f"Method subsections (excluding 2.1 数据获取): {len(methods_minus_intro)}; "
            f"Result subsections: {len(results)}. "
            f"Per skill convention these should match 1-to-1.",
        )


def check_results_have_figures(md: str, report: LintReport) -> None:
    """Each `### 3.X` results section should reference at least one ![]() image."""
    sections = re.split(r"(?m)^###\s+", md)
    # First chunk is anything before the first ###; skip
    for chunk in sections[1:]:
        header_line = chunk.splitlines()[0]
        if not re.match(r"^\s*3\.\d", header_line):
            continue
        # Section body = everything until the next-level heading
        body = re.split(r"(?m)^##\s+|^###\s+", chunk, maxsplit=1)[0]
        if not IMAGE_REF_RE.search(body):
            report.add(
                "warning", "result-without-figure",
                f"Results subsection '### {header_line.strip()}' references no figures — "
                f"every result section should surface at least one figure.",
            )


def check_client_scope(md: str, report: LintReport) -> None:
    """Flag biological/clinical interpretation outside the methods section."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    in_methods = False
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            title = heading.group(1).strip()
            in_methods = bool(re.match(r"^2(?:\.|\s|$)", title) or "方法" in title)
        if in_methods:
            continue
        if not line.strip():
            continue
        for code, pattern in CLIENT_SCOPE_FORBIDDEN:
            m = pattern.search(line)
            if not m:
                continue
            report.add(
                "error",
                "client-scope",
                f"Client-facing report must stay at data/bioinformatics level; forbidden {code} phrase '{m.group(0)}'.",
                line=lineno,
            )
            break


def check_report_style(md: str, report: LintReport) -> None:
    """Flag agent-note phrasing and inventory-style result headings."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    ref_match = REFERENCE_HEADING_RE.search(cleaned)
    if ref_match:
        cleaned = cleaned[:ref_match.start()]
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        stripped = line.strip()
        for code, pattern in REPORT_STYLE_FORBIDDEN:
            m = pattern.search(stripped)
            if m:
                report.add(
                    "error",
                    "report-style",
                    f"Report wording is too internal/mechanical ({code}): '{m.group(0)}'.",
                    line=lineno,
                )
                break
        if RESULT_HEADING_INVENTORY_RE.search(stripped):
            report.add(
                "error",
                "result-heading-style",
                "Result headings should be concise analysis module names, not figure-output inventory descriptions.",
                line=lineno,
            )


def check_multi_table_prose_lists(md: str, report: LintReport) -> None:
    """Multiple linked result tables must be introduced as Markdown tables, not long prose lists."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    ref_match = REFERENCE_HEADING_RE.search(cleaned)
    if ref_match:
        cleaned = cleaned[:ref_match.start()]
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        table_paths = TABLE_PATH_IN_BACKTICKS_RE.findall(stripped)
        if len(table_paths) >= 2:
            report.add(
                "error",
                "multi-table-prose-list",
                "Multiple TSV/CSV/XLSX table paths are listed in prose. Use a Markdown table with columns such as result type, table path, and content.",
                line=lineno,
            )


def check_sample_information_tables(md: str, report: LintReport) -> None:
    """Sample identifiers must be presented through tables, not prose lists."""
    cleaned = IMAGE_REF_RE.sub("", strip_code_fences(HTML_COMMENT_RE.sub("", md)))
    ref_match = REFERENCE_HEADING_RE.search(cleaned)
    if ref_match:
        cleaned = cleaned[:ref_match.start()]
    for paragraph_start, paragraph in _paragraphs_with_lines(cleaned):
        non_table_lines = [
            line
            for line in paragraph.splitlines()
            if line.strip() and not line.lstrip().startswith("|")
        ]
        if not non_table_lines:
            continue
        body = "\n".join(non_table_lines)
        sample_ids = set(SAMPLE_ID_RE.findall(body))
        if len(sample_ids) >= 4:
            report.add(
                "error",
                "sample-prose-list",
                "Sample identifiers are listed in prose. Put sample information in a Markdown table instead of enumerating samples in sentences.",
                line=paragraph_start,
            )


def _h3_sections(md: str) -> list[tuple[int, str, str]]:
    sections: list[tuple[int, str, str]] = []
    pattern = re.compile(r"(?ms)^###\s+(.+?)\s*$\n(.*?)(?=^###\s+|^##\s+|\Z)")
    for match in pattern.finditer(md):
        heading = match.group(1).strip()
        body = match.group(2)
        line = md.count("\n", 0, match.start()) + 1
        sections.append((line, heading, body))
    return sections


def check_differential_group_labels(md: str, report: LintReport) -> None:
    """Every differential/comparison analysis section must name control and experimental groups."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    ref_match = REFERENCE_HEADING_RE.search(cleaned)
    if ref_match:
        cleaned = cleaned[:ref_match.start()]
    for line, heading, body in _h3_sections(cleaned):
        if not re.match(r"^[23]\.\d+", heading):
            continue
        section_text = f"{heading}\n{body}"
        if ENRICHMENT_SECTION_RE.search(heading):
            continue
        if not DIFFERENTIAL_ANALYSIS_RE.search(section_text):
            continue
        if CONTROL_GROUP_RE.search(section_text) and EXPERIMENT_GROUP_RE.search(section_text):
            continue
        report.add(
            "error",
            "differential-groups-missing",
            f"Differential/comparison section '### {heading}' must explicitly state both 对照组 and 实验组.",
            line=line,
        )


def check_enrichment_no_comparison_wording(md: str, report: LintReport) -> None:
    """Enrichment/GSEA sections should describe input gene sets/rankings, not group comparisons."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    ref_match = REFERENCE_HEADING_RE.search(cleaned)
    if ref_match:
        cleaned = cleaned[:ref_match.start()]
    for line, heading, body in _h3_sections(cleaned):
        if not re.match(r"^[23]\.\d+", heading):
            continue
        if not ENRICHMENT_SECTION_RE.search(heading):
            continue
        section_text = f"{heading}\n{body}"
        match = ENRICHMENT_COMPARISON_WORDING_RE.search(section_text)
        if not match:
            continue
        report.add(
            "error",
            "enrichment-comparison-wording",
            (
                f"Enrichment/GSEA section '### {heading}' must identify input gene lists/rankings "
                "without adding comparison wording or 对照组/实验组 labels."
            ),
            line=line,
        )


def check_methods_no_result_content(md: str, report: LintReport) -> None:
    """Methods should describe design, software, principles, and parameters only."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    methods = _methods_section(cleaned)
    if not methods:
        return
    for lineno, line in enumerate(methods.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("###", "|")):
            continue
        if DELIVERABLE_PATH_IN_BACKTICKS_RE.search(stripped):
            report.add(
                "error",
                "method-result-path",
                "Methods must not cite concrete result file paths; keep file paths in result/file sections or sample-information tables.",
                line=lineno,
            )
        match = METHOD_RESULT_WORDING_RE.search(stripped)
        if match:
            report.add(
                "error",
                "method-result-content",
                f"Methods must not contain result observations, result counts, or delivery-file narration: '{match.group(0)}'.",
                line=lineno,
            )


def check_public_data_no_upstream_methods(md: str, report: LintReport) -> None:
    """Public processed-data reports should not copy upstream alignment methods into Methods."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    methods = _methods_section(cleaned)
    if not methods:
        return
    if not PUBLIC_DATA_SOURCE_RE.search(cleaned):
        return
    if RAW_REPROCESSING_EVIDENCE_RE.search(methods):
        return
    for lineno, line in enumerate(methods.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("###", "|")):
            continue
        match = UPSTREAM_ALIGNMENT_METHOD_RE.search(stripped)
        if not match:
            continue
        report.add(
            "error",
            "public-data-upstream-method",
            (
                "Public processed-data methods should describe current project analyses only; "
                f"remove upstream alignment/base-calling/quantification wording such as '{match.group(0)}' "
                "unless the current project reprocessed raw reads."
            ),
            line=lineno,
        )


def check_delivery_privacy(md: str, report: LintReport) -> None:
    """Block implementation-only details that should not appear in client reports."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for code, pattern in DELIVERY_PRIVACY_FORBIDDEN:
            match = pattern.search(stripped)
            if not match:
                continue
            report.add(
                "error",
                "delivery-privacy",
                f"Client report exposes {code} detail '{match.group(0)}'. "
                "Remove compute-resource settings, raw commands, private paths, or code-internal wording.",
                line=lineno,
            )
            break


def _norm_manifest_path(path: str) -> str:
    path = path.strip().strip('"').strip("'")
    while path.startswith("./"):
        path = path[2:]
    return path.replace("\\", "/")


def _split_manifest_paths(value: str) -> list[str]:
    return [
        _norm_manifest_path(item)
        for item in re.split(r"[;；]", value)
        if _norm_manifest_path(item)
    ]


def _manifest_required(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "n", "skip", "optional", "否"}


def parse_figure_manifest(manifest_path: Path, report: LintReport) -> dict[str, list[str]]:
    """Parse TSV/CSV figure manifest into figure_type -> representative paths."""
    if not manifest_path.exists():
        report.add("error", "manifest-missing", f"Figure manifest not found: {manifest_path}")
        return {}

    text = manifest_path.read_text(encoding="utf-8-sig")
    non_comment = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not non_comment:
        report.add("error", "manifest-empty", f"Figure manifest is empty: {manifest_path}")
        return {}

    delimiter = "\t" if "\t" in non_comment[0] else ","
    rows = list(csv.reader(non_comment, delimiter=delimiter))
    if not rows:
        report.add("error", "manifest-empty", f"Figure manifest is empty: {manifest_path}")
        return {}

    first = [cell.strip().lower() for cell in rows[0]]
    has_header = any(cell in {"figure_type", "type", "图类型"} for cell in first)
    if has_header:
        header = first
        data_rows = rows[1:]
        type_idx = next((i for i, key in enumerate(header) if key in {"figure_type", "type", "图类型"}), None)
        path_idx = next(
            (
                i
                for i, key in enumerate(header)
                if key in {"representative_path", "path", "paths", "file", "filename", "image", "图片路径"}
            ),
            None,
        )
        required_idx = next((i for i, key in enumerate(header) if key in {"required", "include", "必选"}), None)
    else:
        data_rows = rows
        type_idx = 0
        path_idx = 1
        required_idx = 2 if rows and len(rows[0]) > 2 else None

    if type_idx is None or path_idx is None:
        report.add(
            "error",
            "manifest-format",
            "Figure manifest must include figure_type and representative_path columns.",
        )
        return {}

    manifest: dict[str, list[str]] = {}
    for offset, row in enumerate(data_rows, start=2 if has_header else 1):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) <= max(type_idx, path_idx):
            report.add(
                "error",
                "manifest-format",
                f"Manifest row {offset} must contain figure type and representative path.",
            )
            continue
        required_value = row[required_idx] if required_idx is not None and len(row) > required_idx else None
        if not _manifest_required(required_value):
            continue
        figure_type = row[type_idx].strip()
        paths = _split_manifest_paths(row[path_idx])
        if not figure_type or not paths:
            report.add(
                "error",
                "manifest-format",
                f"Manifest row {offset} must contain non-empty figure_type and representative_path.",
            )
            continue
        manifest.setdefault(figure_type, []).extend(paths)
    return manifest


def check_figure_type_coverage(md: str, manifest_path: Path, report: LintReport) -> None:
    """Verify each required figure type has at least one representative image in the report."""
    manifest = parse_figure_manifest(manifest_path, report)
    if not manifest:
        return

    referenced = {_norm_manifest_path(src) for _, src in check_image_resolution(md, Path("."), LintReport())}
    referenced_names = {Path(src).name for src in referenced}
    for figure_type, paths in manifest.items():
        matched = False
        for path in paths:
            normalized = _norm_manifest_path(path)
            if normalized in referenced or Path(normalized).name in referenced_names:
                matched = True
                break
        if not matched:
            report.add(
                "error",
                "figure-type-missing",
                f"Figure type '{figure_type}' is required by the manifest but none of its representative paths "
                f"appear in the report: {', '.join(paths[:3])}",
            )


def _citation_keys(text: str) -> set[str]:
    text = IMAGE_REF_RE.sub("", text)
    keys: set[str] = set()
    for match in CITATION_KEY_RE.finditer(text):
        for key in match.group(1).split(";"):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def _numeric_citations(text: str) -> set[int]:
    numbers: set[int] = set()
    for match in NUMERIC_CITATION_RE.finditer(text):
        raw = match.group(1)
        parts = re.split(r"\s*[,，;；]\s*", raw)
        for part in parts:
            if "-" in part:
                left, right = [item.strip() for item in part.split("-", 1)]
                if left.isdigit() and right.isdigit():
                    start, end = int(left), int(right)
                    if start <= end:
                        numbers.update(range(start, end + 1))
                    else:
                        numbers.update((start, end))
                continue
            if part.strip().isdigit():
                numbers.add(int(part.strip()))
    return numbers


def _linked_citation_numbers(text: str) -> set[int]:
    numbers: set[int] = set()
    for match in SUP_CITATION_RE.finditer(text):
        sup_html = match.group(0)
        if not REFERENCE_HREF_RE.search(sup_html):
            continue
        numbers.update(_numeric_citations(sup_html))
    return numbers


def _reference_anchor_numbers(text: str) -> set[int]:
    return {int(match.group(1)) for match in REFERENCE_ANCHOR_RE.finditer(text)}


def _reference_entries(reference_text: str) -> dict[int, tuple[int, str]]:
    entries: dict[int, tuple[int, str]] = {}
    for match in REFERENCE_ENTRY_RE.finditer(reference_text):
        number = int(match.group(1))
        line = reference_text.count("\n", 0, match.start()) + 1
        entries[number] = (line, match.group(2).strip())
    return entries


def _bib_keys(bib_path: Path, report: LintReport) -> set[str]:
    if not bib_path.exists():
        report.add("error", "references-bib-missing", f"Reference library not found: {bib_path}")
        return set()
    text = bib_path.read_text(encoding="utf-8")
    return {m.group(1).strip() for m in BIB_ENTRY_RE.finditer(text)}


def _bib_records(bib_path: Path, report: LintReport) -> dict[str, dict[str, str]]:
    if not bib_path.exists():
        report.add("error", "references-bib-missing", f"Reference library not found: {bib_path}")
        return {}
    text = bib_path.read_text(encoding="utf-8")
    records: dict[str, dict[str, str]] = {}
    for match in BIB_ENTRY_BLOCK_RE.finditer(text):
        key = match.group(1).strip()
        block = match.group(2)
        fields: dict[str, str] = {}
        for field_match in BIB_FIELD_RE.finditer(block):
            field = field_match.group(1).lower()
            value = re.sub(r"\s+", " ", field_match.group(2).strip())
            fields[field] = value
        records[key] = fields
    return records


def _record_backed_by_reference(record: dict[str, str], reference_text: str) -> bool:
    haystack = reference_text.lower()
    for field in ("doi", "pmid", "url"):
        value = record.get(field, "").strip()
        if value and value.lower() in haystack:
            return True
    title = re.sub(r"\s+", " ", record.get("title", "").strip()).lower()
    if title and title in haystack:
        return True
    # Some GB/T entries may shorten subtitles or omit punctuation. Require a
    # reasonably specific title prefix before treating it as the same source.
    if title:
        title_words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", title)
        if len(title_words) >= 5:
            prefix = " ".join(title_words[:6])
            normalized_ref = " ".join(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", haystack))
            if prefix in normalized_ref:
                return True
    return False


def _methods_section(md: str) -> str:
    match = METHOD_SECTION_RE.search(md)
    return match.group(0) if match else ""


def _method_subsections(methods: str) -> list[tuple[int, str, str]]:
    sections: list[tuple[int, str, str]] = []
    for match in METHOD_H3_SECTION_RE.finditer(methods):
        heading = match.group(2).strip()
        body = match.group(3).strip()
        line = methods.count("\n", 0, match.start()) + 1
        sections.append((line, heading, body))
    return sections


def check_method_depth(methods: str, report: LintReport) -> None:
    for line, heading, body in _method_subsections(methods):
        if METHOD_DEPTH_SKIP_HEADING_RE.search(heading):
            continue
        plain_body = re.sub(r"`[^`]+`", "", body)
        if len(plain_body.strip()) < 80:
            report.add(
                "error",
                "method-depth",
                f"Methods subsection '### {heading}' is too short to document method principle, characteristics, and parameters.",
                line=line,
            )
            continue
        if not _numeric_citations(plain_body):
            report.add(
                "error",
                "method-depth-citation",
                f"Methods subsection '### {heading}' lacks a numeric literature citation.",
                line=line,
            )
        if not METHOD_PRINCIPLE_RE.search(plain_body):
            report.add(
                "error",
                "method-depth-principle",
                f"Methods subsection '### {heading}' must explain the algorithm/statistical/scoring principle.",
                line=line,
            )
        if not METHOD_CHARACTERISTIC_RE.search(plain_body):
            report.add(
                "error",
                "method-depth-characteristic",
                f"Methods subsection '### {heading}' must state a concise method characteristic or suitability.",
                line=line,
            )
        if not METHOD_PARAMETER_RE.search(plain_body):
            report.add(
                "error",
                "method-depth-parameter",
                f"Methods subsection '### {heading}' must include actual reportable parameters, thresholds, databases, organism codes, or design settings.",
                line=line,
            )


def _paragraphs_with_lines(text: str) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    current: list[str] = []
    current_start = 1
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not current:
                current_start = lineno
            current.append(line)
            continue
        if current:
            paragraphs.append((current_start, "\n".join(current)))
            current = []
    if current:
        paragraphs.append((current_start, "\n".join(current)))
    return paragraphs


def check_references(md: str, bib_path: Path, report: LintReport) -> None:
    """Check numeric GB/T 7714-2005 citations and final reference section."""
    cleaned = strip_code_fences(HTML_COMMENT_RE.sub("", md))
    methods = _methods_section(cleaned)
    if not methods:
        report.add("error", "references", "Could not locate the `## 2. 方法` section for reference checks.")
        return

    reference_heading = REFERENCE_HEADING_RE.search(cleaned)
    if not reference_heading:
        report.add("error", "references-missing", "Report must include `## 5. 参考文献` or `## References`.")
        return

    body_text = cleaned[:reference_heading.start()]
    reference_text = cleaned[reference_heading.start():]
    body_keys = _citation_keys(body_text)
    reference_keys = _citation_keys(reference_text)
    for key in sorted(body_keys):
        report.add("error", "reference-style", f"Citation key '[{key}]' must be converted to numeric GB/T 7714-2005 style.")
    for key in sorted(reference_keys):
        report.add("error", "reference-style", f"Reference section key '[{key}]' must be converted to numeric GB/T 7714-2005 style.")

    body_numbers = _numeric_citations(body_text)
    method_numbers = _numeric_citations(methods)
    linked_numbers = _linked_citation_numbers(body_text)
    reference_entries = _reference_entries(reference_text)
    reference_numbers = set(reference_entries)
    reference_anchor_numbers = _reference_anchor_numbers(reference_text)
    bib_records = _bib_records(bib_path, report)

    check_method_depth(methods, report)

    if not method_numbers:
        report.add("error", "references-missing", "Methods section contains no numeric GB/T-style citations such as [1].")

    unlinked_numbers = sorted(body_numbers - linked_numbers)
    for number in unlinked_numbers:
        report.add(
            "error",
            "reference-link",
            f"Body citation '[{number}]' must be rendered as a clickable superscript link to '#ref-{number}'.",
        )

    missing_in_reference = sorted(body_numbers - reference_numbers)
    for number in missing_in_reference:
        report.add("error", "reference-missing", f"Numeric citation '[{number}]' is used in the body but missing from the reference section.")

    missing_reference_anchor = sorted(reference_numbers - reference_anchor_numbers)
    for number in missing_reference_anchor:
        report.add(
            "error",
            "reference-anchor",
            f"Reference entry '[{number}]' must include an HTML anchor with id='ref-{number}' for citation jumps.",
        )

    unused_references = sorted(reference_numbers - body_numbers)
    for number in unused_references:
        report.add("error", "reference-unused", f"Reference section contains uncited numeric entry '[{number}]'.")

    if reference_numbers:
        expected = set(range(1, max(reference_numbers) + 1))
        missing_sequence = sorted(expected - reference_numbers)
        for number in missing_sequence:
            report.add("error", "reference-sequence", f"GB/T numeric references should be consecutive; missing '[{number}]'.")

    seen_reference_numbers: set[int] = set()
    reference_line_offset = cleaned.count("\n", 0, reference_heading.start())
    for match in REFERENCE_ENTRY_RE.finditer(reference_text):
        number = int(match.group(1))
        line = reference_line_offset + reference_text.count("\n", 0, match.start()) + 1
        if number in seen_reference_numbers:
            report.add("error", "reference-duplicate", f"Duplicate reference entry '[{number}]'.", line=line)
        seen_reference_numbers.add(number)
        entry_text = match.group(2)
        if not GB_T_PUBLICATION_TYPE_RE.search(entry_text):
            report.add(
                "error",
                "reference-format",
                f"Reference '[{number}]' should include a GB/T publication type marker such as [J], [M], or [EB/OL].",
                line=line,
            )

    for label, pattern, required_keys in METHOD_REFERENCE_RULES:
        method_match = pattern.search(methods)
        if not method_match:
            continue
        missing_keys = [key for key in required_keys if key not in bib_records]
        for key in missing_keys:
            report.add(
                "error",
                "method-reference-library-missing",
                f"Reference library is missing required key '{key}' for method {label}.",
            )
        available_records = [bib_records[key] for key in required_keys if key in bib_records]
        if not available_records:
            continue
        if any(_record_backed_by_reference(record, reference_text) for record in available_records):
            continue
        line = methods.count("\n", 0, method_match.start()) + 1
        report.add(
            "error",
            "method-reference-not-backed",
            f"Methods mention {label}, but the References section does not contain a matching citation from references.bib.",
            line=line,
        )

    for paragraph_start, paragraph in _paragraphs_with_lines(methods):
        paragraph_body = "\n".join(line for line in paragraph.splitlines() if not line.lstrip().startswith("#"))
        if not paragraph_body.strip():
            continue
        paragraph_numbers = _numeric_citations(paragraph_body)
        for label, pattern, required_keys in METHOD_REFERENCE_RULES:
            if not pattern.search(paragraph_body):
                continue
            if paragraph_numbers:
                continue
            report.add(
                "error",
                "method-reference-missing",
                f"Methods paragraph mentions {label} but lacks a numeric GB/T-style citation.",
                line=paragraph_start,
            )


# ----- orchestration ------------------------------------------------------

def lint(
    md_path: Path,
    asset_base: Path,
    bad_patterns: list[str],
    figure_manifest: Path | None = None,
    strict_client_scope: bool = False,
    strict_references: bool = False,
    reference_bib: Path | None = None,
) -> LintReport:
    md = md_path.read_text(encoding="utf-8")
    report = LintReport()
    check_absolute_paths(md, report)
    check_bad_patterns(md, bad_patterns, report)
    check_unfilled_placeholders(md, report)
    check_html_comments(md, report)
    check_raw_html(md, report)
    check_image_resolution(md, asset_base, report)
    check_figure_numbering_and_captions(md, report)
    check_methods_results_alignment(md, report)
    check_results_have_figures(md, report)
    check_report_style(md, report)
    check_multi_table_prose_lists(md, report)
    check_sample_information_tables(md, report)
    check_differential_group_labels(md, report)
    check_enrichment_no_comparison_wording(md, report)
    check_methods_no_result_content(md, report)
    check_public_data_no_upstream_methods(md, report)
    check_delivery_privacy(md, report)
    if strict_client_scope:
        check_client_scope(md, report)
    if figure_manifest is not None:
        check_figure_type_coverage(md, figure_manifest, report)
    if strict_references:
        bib_path = reference_bib if reference_bib is not None else Path(__file__).with_name("references.bib")
        check_references(md, bib_path, report)
    return report


def render_report(report: LintReport, md_path: Path) -> str:
    if not report.issues:
        return f"✓ {md_path}: no issues found."
    lines = [f"Linting {md_path}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)."]
    for issue in report.issues:
        loc = f"L{issue.line}" if issue.line else "—"
        tag = "✗" if issue.severity == "error" else "⚠"
        lines.append(f"  {tag} [{issue.code}] {loc}: {issue.message}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Lint an omics-analysis Markdown report.")
    parser.add_argument("input", help="Input Markdown report")
    parser.add_argument("--asset-base", default=None,
                        help="Directory to resolve image paths against. Defaults to the Markdown file's parent directory.")
    parser.add_argument("--bad-pattern", action="append", default=[],
                        help="Forbidden substring to flag (case-sensitive). Repeatable. "
                             "Use for project codenames, internal identifiers, etc.")
    parser.add_argument("--warnings-as-errors", action="store_true",
                        help="Also exit non-zero on warnings.")
    parser.add_argument("--strict-client-scope", action="store_true",
                        help="Error on biology/mechanism/clinical interpretation outside the methods section.")
    parser.add_argument("--figure-manifest", default=None,
                        help="TSV/CSV manifest requiring each figure_type to have a representative image in the report.")
    parser.add_argument("--strict-references", action="store_true",
                        help="Require method citations and a matching References section backed by references.bib.")
    parser.add_argument("--reference-bib", default=None,
                        help="BibTeX library used by --strict-references. Defaults to references.bib next to this script.")
    args = parser.parse_args()

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"Error: input file not found: {md_path}", file=sys.stderr)
        sys.exit(2)

    asset_base = Path(args.asset_base).resolve() if args.asset_base else md_path.parent

    figure_manifest = Path(args.figure_manifest).resolve() if args.figure_manifest else None
    reference_bib = Path(args.reference_bib).resolve() if args.reference_bib else None
    report = lint(
        md_path,
        asset_base,
        args.bad_pattern,
        figure_manifest,
        args.strict_client_scope,
        args.strict_references,
        reference_bib,
    )
    print(render_report(report, md_path))

    fail = bool(report.errors) or (args.warnings_as_errors and report.warnings)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
