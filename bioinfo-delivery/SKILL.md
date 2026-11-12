---
name: bioinfo-delivery
description: 生物信息分析交付规范 v2.5（Python/R/Bash/Nextflow）。当进行生物信息分析、生信项目初始化 prj_init、组织 Data/Results/Scripts 目录、命名编号分析步骤（如 01.exprs、02.DEGs）、筛选可交付模块、生成交付结果（Tables、Figures、中文 README）、编写运行摘要 run_summary、交付验收或客户结果整理时使用。Use when doing any bioinformatics analysis or preparing analysis deliverables.
---

# 生物信息分析交付规范 v2.5

进行生物信息分析时，必须遵守本规范。完整规范全文见同目录下的 `生物信息分析交付规范v2.5.md`，以下为执行要点速查。

肿瘤单细胞项目必须同时使用 `tumor-infercnv-purification`：先以 inferCNV 建立恶性细胞纯度门槛，再开展肿瘤细胞下游分析。

## 现有流程优先

所有生信分析与绘图优先复用既有项目流程、个人环境的 ytbiokit 及其扩展；已有流程可完成时，不另写分析函数。需修饰、调整、后处理或补充分析实现时，动手前先告知用户现有入口、原因、拟改内容及影响。完整执行规则见[现有流程优先](/home/taojj/bioinfo-plotting/SKILL.md#现有流程优先所有生信分析适用)。

## 目录结构（prj_init 初始化，不得手工另造同级目录）

```
.
├── analysis.ipynb        # 交互式草稿本，不得保存唯一分析逻辑
├── Data
│   ├── Raw               # 原始数据 + manifest + 校验和，不得覆盖/清洗
│   └── Processed         # 清洗数据、编号分析目录（Input/Output/run_summary.yaml）、缓存
├── Results               # 仅客户最终结果：表格、图形、源数据、README
└── Scripts               # 脚本、测试、公共函数、config/colors.yaml
```

## 编号与命名

- 内部分析步骤使用 `NN.short_name`（如 `02.DEGs`），编号两位数字、唯一递增；Processed 与 Scripts 同名同号对齐。Results 按下述大类树状结构组织，仅收录通过模块准入闸门的结果；大类编号用于交付导航，不要求与单个内部步骤同名同号。内部步骤到交付分支的对应关系记录在 Processed 的 `run_summary.yaml`。
- 新增分析追加编号，不重排旧编号。
- 图形文件名直接写明对象、比较与图形类型，例如 `myeloid_SPI1_expression_GBM_vs_control_boxplot`；不得使用 `Figure1`、`Fig1`、`panel_A` 或仅靠流水号区分内容。
- 文件夹与各级子目录命名：项目分析目录及交付目录均按分析内容、数据集、分组比较或分析对象命名，不使用软件包或绘图库名字（包括 ytbiokit），也不把包名作为目录名的一部分。例如 `21.ytbiokit_scrna` 应命名为 `21.expression_scores`，细胞通讯用 `CellCommunication`，调控网络用 `RegulatoryNetwork`。内部步骤沿用原编号，Scripts 与 Data/Processed 的对应目录同名同号；交付大类按自身编号管理。重命名既有目录时先检查重名冲突，再同步脚本配置、输入输出路径、运行记录、图形索引和 HTML/README 的全部引用，并验证链接与流程有效。此规则约束项目目录命名，不重命名软件安装目录、Python/R 包目录、skill 名称或真实基因/通路标识。
- 文件名用稳定语义名，禁止 `final_v7_new2`。

## 出图模块按大类树状组织

目录规范可参考套用整个 `/data/Projects/Examples/`：根据项目类型选择 `scRNA-Results`、`Bulk-Results`、`网药-Results` 等对应示例，查看其 Results 和报告目录的实际组织方式，采用适合当前分析内容的层级与命名；仅创建实际有交付内容的模块，继续遵守本规范的结果准入及文件内容要求。

主文件夹名称和编号格式可直接套用对应示例，Results 不强制两位编号：

- Bulk 使用四个主类：`1.exprs`、`2.DEGs`、`3.GSEA`、`4.Coexpression`。
- 网药使用五个主类：`1.Venn`、`2.Drug_net`、`3.PPI`、`4.GO_KEGG`、`5.Docking`。
- scRNA 可直接套用八个主类的目录名：`1.QC`、`2.Cluster`、`3.CellAnnot`、`4.CNV`、`5.CellCommunication`、`6.CellPrioritization`、`7.Subtypes`、`8.RegulatoryNetwork`。
- 同类分析的多个数据集、比较或子任务放入对应主类下；未开展的类别不生成空壳目录，示例之外的实际分析按其大类追加。

参考 `/data/Projects/Examples/scRNA-Results/Results/` 的组织方式：Results 一级目录用一个能概括分析内容的大类名称，如 `1.QC`、`2.Cluster`、`3.CellAnnot`、`5.CellCommunication`；同类内容归入同一个大类，再按数据集、样本、细胞类型或子任务逐层分支。QC 涉及多个数据集时，各数据集的 QC 子目录放在同一个 QC 大类下，不拆成多个一级模块。仅在实际有多个分析对象时增加分支层级。

```text
Results/
├── 1.QC/
│   ├── README.md
│   ├── dataset_A/
│   │   ├── README.md
│   │   ├── Tables/
│   │   └── Figures/
│   └── dataset_B/
│       ├── README.md
│       ├── Tables/
│       └── Figures/
└── 2.Cluster/
    ├── README.md
    ├── Tables/
    └── Figures/
```

大类及中间分支 README 提供中文导航；实际承载分析结果的叶子目录使用 `Tables/`、`Figures/` 及对应中文 README，并在 `Tables/figure_index.tsv` 用相对路径关联图表。没有细分对象的大类可直接承载这些内容。下文“交付模块”及其准入闸门均指实际承载结果的叶子目录；不得用其他分支的有效图形为无图分支取得准入。此示例路径仅作为组织参考，不写入客户结果；参考目录不可访问时仍按上述树状规则执行。

## 可复现与缓存

- 工具/版本、全部关键参数、参考数据库名称/版本/发布日期/校验和、随机 seed、输入摘要必须记录在 `Data/Processed/NN.analysis/run_summary.yaml`（不得进 Results）。
- 参考基因组、数据库、物种不得隐式写死；配置声明默认值、允许值、实际值。
- 缓存只用于高成本步骤；命中前验证 key 与结构；写 `*.tmp` 校验后原子 rename；损坏时明确报错并提示 `--force`。
- 失败返回非零并说明步骤/对象/原因/建议；正常完成但零结果可保留带稳定表头的空表。
- 所有正式分析图的输入必须是结果证据链中的当前定稿分析数据集：已按既定流程完成适用且可追溯的质控、过滤、标准化、批次校正或标签/注释修订；不得擅自回退到证据链中已被替代的旧版本绕过上游修订。方法要求使用原始计数时，使用定稿样本与特征集合所对应的原始计数层，并明确记录该口径。`run_summary.yaml` 与来源记录须追踪输入版本、处理步骤和摘要。对分析数据的处理仅限预先定义或有科学依据的处理，禁止为提高 AUC、显著性或迎合预期结论而改动数据、删样本或调标签。

## 聚类与注释后的 marker 复核

- 每次聚类、谱系二次聚类及细胞类型/亚型注释完成或修订后，必须基于最新定稿对象及分组重新运行 FindMarkers；全簇可使用 FindAllMarkers。核验并更新 marker 全量/筛选表及注释对应关系，不能仅改旧表标签或沿用旧检测缓存。具体执行读取[聚类与注释后的 marker 重跑规则](/home/taojj/.agents/skills/bioinfo-plotting/references/post-annotation-markers.md)，通过后再完成该版注释及可视化。

## 代码门槛

- Python：类型注解、无裸 except/硬编码路径；`ruff check Scripts && pytest`。
- R：可 parse、不保存 .RData/完整 workspace；`parse()` + lintr + testthat。
- Bash：`#!/usr/bin/env bash`；`set -euo pipefail`；引用加引号；`mktemp -d` + trap；`bash -n` + shellcheck。
- Nextflow：DSL2、版本固定、参数集中、容器/publishDir 显式、stub/smoke test。
- 所有图形配色统一读取 `Scripts/config/colors.yaml`，禁止脚本内硬编码颜色。
- 单细胞多样本合并 AnnData 时必须 `ad.concat(join="outer")` 保留基因并集，禁止默认 inner 交集丢基因；合并前先 `var_names_make_unique()` 并给 barcode 加样本前缀。
- 连续数值配色规则：相关性、z-score 标准化值、logFC 等含正负且以零为中心的热图统一使用 `RdBu_r` 发散配色（红正蓝负、零为白）；网络图中的度值（degree）映射统一使用 `Spectral`；具有明确“小→大”顺序的非负或单调连续数值（如表达量）统一使用 `Reds` 或 `magma` 顺序色图，不使用发散色图。热图单元格尽量保持正方形。

## 结果交付

- 模块准入闸门：每个交付叶子目录必须至少包含一对可解释的真实 PDF/PNG 图，且该图直接呈现生物学分析结果，或呈现解释下游生物学结果所必需的 QC、整合、验证证据。仅做下载、文件获取、checksum、格式转换、来源/provenance、字段审计或流程 `go/no-go` 门控，且不产生上述图形的模块只保留在 `Data/Processed/` 与 `Scripts/`，不创建 Results 模块、空 `Figures/`、空图形索引或占位图。
- 每个交付叶子目录固定使用 `Tables/` 与 `Figures/`；该模块的全部 TSV（包括 `figure_index.tsv` 与统计表）只能放在 `Tables/`，全部 PDF/PNG/SVG 放在 `Figures/`。HTML 图库放在模块根目录。`figure_index.tsv` 只记录图形 ID、路径、说明和来源，不设置 `recommend` 或 `recommended` 列。
- HTML 展示：交付 HTML 的正文、标题、导航、图注、文件卡片、表格预览、提示文字及辅助阅读文本均按分析内容描述，不出现软件包或绘图库名字（如 ytbiokit），也不展示内部文件子目录名、目录树或路径。例如以“基因表达与评分”代替“ytbiokit”，以“下载差异表达结果表”代替“21.ytbiokit_scrna/Tables/DEGs.full.tsv”。链接及图片加载所需的真实相对路径可保留在 href/src 等资源属性中，页面上的链接文字使用结果名称，不把路径输出为可见文字、title、alt 或 aria-label。软件包名、版本和实现细节仅写入内部运行记录；分析方法使用相应的分析名称描述。若其他报告规范要求直接展示包名或完整文件子目录，以本条 HTML 展示规则为准。交付前检查页面、导航、图注、文件卡片、预览及提示文字，并验证相对链接有效。
- 表格：UTF-8 TSV；全量/筛选分别 `*.full.tsv` / `*.filtered.tsv` 并写明筛选规则；保留稳定 ID（Ensembl/Entrez）；禁止只交显著条目；排序与列顺序确定。
- 图形：所有正式分析图必须由 `Scripts/` 中可复现的 R/Python 等代码直接从结果证据链中的当前定稿分析数据集生成，并由脚本导出 PDF/PNG；不得使用生成式图片或 AI 图像工具、手工拼图、截图或图像编辑软件合成正式分析图。论文型图形同时交 PDF + 300 dpi PNG；`Tables/figure_index.tsv` 逐图关联来源表且不含推荐列；可在源 Results 按需提供 `figure_gallery.html`，不设置图片数量门槛，打包时按 `bioinfo-project-packaging` 排除 gallery；适用图形类型尽量覆盖总览/分组/细节/比较视角；面向高分 SCI 发表，配色、字体、留白和排版需有高级感，禁止默认主题直出；**图形一律不加 title 与 subtitle**；**不附 source.tsv**。
- 单图单义：能独立阅读的可视化必须拆成独立文件，不制作多面板拼图或 facet；多个基因的表达图必须按基因逐张输出，每个基因分别生成同名 PDF/PNG。
- 表达量统计：凡表达量图包含组间、条件间或时间点间比较（包括箱线图、提琴图、散点/抖动图、柱状图、雨云图等），图内必须同时显示显著性符号和精确 P 值数字；优先用 R `rstatix` 按实验设计计算、用 `ggpubr`（如 `stat_pvalue_manual`）添加。检验以 donor/sample 等生物学重复为统计单位，配对设计使用配对检验；多重比较以校正后 P 值同时生成数字和星号。每项分析必须保留可核对的 `*.stat.full.tsv`，至少含基因/指标、比较组、各组样本量、统计单位、检验方法、配对状态、原始 P 值、校正 P 值、校正方法、显著性标签及作图位置，并由 `figure_index.tsv` 关联。无组间比较的 FeaturePlot/UMAP、仅展示模式的热图或样本量不足时，在 stat 表记录 `not_applicable` 或 `insufficient_n`，不得伪造显著性。
- 箱线图统计：凡样本量支持组间检验，图内必须显示 `ns`、`*`、`**`、`***`、`****`；默认映射为 `ns ≥ 0.05`、`* < 0.05`、`** < 0.01`、`*** < 0.001`、`**** < 0.0001`。多重比较优先按校正后 P 值映射星号，并在结果表或 README 记录检验方法、精确 P 值、校正方法和统计单位。样本不足或比较不成立时标注 `not tested` 或 `insufficient n`，不得伪造显著性。
- ROC：二分类结局继续使用 R `pROC`，生存结局继续使用 R `timeROC`；所有正式展示曲线必须平滑。每条候选曲线均先生成可核对统计表，至少包含模型/指标、队列、终点或时间点、样本量/事件数、AUC、置信区间及方法、阈值、敏感度、特异度和训练/验证角色。训练、内部验证和外部验证分别使用各自的无数据泄漏评估 AUC 独立判定：仅当对应 AUC ≥ 0.70 时，ROC 图及其统计表才可进入 Results；AUC < 0.70 的 ROC 图不交付，对应统计结果和内部图仅保留在 `Data/Processed/` 归档并记录排除原因，不得用训练 AUC 替代任一验证 AUC。不同终点、队列或时间点分别输出语义命名的单图，不使用 facet。平滑仅用于曲线展示，不使用平滑后的展示曲线重新计算 AUC、置信区间、阈值、敏感度或特异度。
- 涉及集合交集/共有元素比较（多基因集、多 cluster marker、多队列 DEG 等）时，必须提供 Venn 图（≤4 个集合）或 UpSet 图（>4 个集合），并附交集计数表。
- 空结果：可保留空表；**不得生成或保留占位图**。
- README：项目级、模块级、`Tables/README.md` 与 `Figures/README.md` 全部使用中文。模块 README 说明目的、方法、阈值和目录导航；`Tables/README.md` 逐类说明表格的分析对象、统计单位、关键字段、筛选口径、生物学问题与证据边界；`Figures/README.md` 逐类说明图的视觉编码、来源表、生物学意义、正确解读方式与不能推出的结论。可写数据直接支持的结果，但不得把相关性写成因果、把技术质控写成生物结论，或越过样本量和参考组边界。
- 解释性门槛：每个交付图表必须能明确回答“对象是谁、比较什么、统计单位是什么、来源和阈值是什么、能支持什么结论、不能支持什么结论”。任一项无法说明时，不把该图表放入 Results；将其保留在 `Data/Processed/NN.analysis/` 的内部归档并记录排除原因，不以删除代替归档。

## Results 红线

Results 只含最终结果 + 源数据 + README。禁止：日志、缓存、命令、运行摘要、状态码、脚本、内部绝对路径、用户名/主机名/凭据。缓存与临时文件不得提交 Git（gitignore 规则见规范全文 08）。

## 交付前验收清单

逐项核对规范全文 07 节的打勾项：Results 不含纯获取/审计/转换且无有效图形的内部模块，每个 Results 模块至少有一对可解释 PDF/PNG；Results 一级目录按分析大类组织、同类数据集/样本/子任务树状分支，Processed/Scripts 编号对齐且 run_summary 记录到交付分支的对应关系；run_summary 齐备、全部 TSV 位于各模块 `Tables/`、全部图位于 `Figures/`、项目、大类/中间分支、叶子及 Tables/Figures README 均为中文且逐类说明生物学意义和证据边界、无法解释的资产已从 Results 排除并内部归档、full/filtered 命名正确、图形均由 Scripts 中可复现代码从证据链当前定稿分析数据集直接生成并由脚本导出且输入版本/处理步骤/摘要可追溯、无擅自回退证据链中已被替代的旧版本，需要原始计数的方法使用定稿样本与特征集合对应的原始计数层、无为结果导向改动数据/删样本/调标签、无生成式/AI 图像工具、手工拼图、截图或图像编辑软件合成、图形 PDF+PNG 与配色合规、图名语义明确、可拆图已拆分、无 facet、多基因表达图已逐基因输出、所有可检验表达量图均显示星号与精确 P 值且保留 `*.stat.full.tsv`、ROC 按训练/内部验证/外部验证分别以无泄漏 AUC ≥ 0.70 判定且平滑仅用于展示、AUC<0.70 图及其统计结果已在 Data/Processed 归档并记录排除原因、`Tables/figure_index.tsv` 不含推荐列、gallery 不进入打包、无 source.tsv、无占位图、smoke test 通过、Results 无内部信息、日志无隐私数据、HTML 可见内容不含软件包名（如 ytbiokit）、内部文件子目录名或路径，链接和文件卡片使用分析结果名称，资源相对链接有效、项目文件夹及各级子目录按分析内容命名且不含软件包名（包括 ytbiokit），相关编号、上下游路径及报告引用保持一致、文件名稳定。
