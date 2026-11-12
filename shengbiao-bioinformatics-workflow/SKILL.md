---
name: shengbiao-bioinformatics-workflow
description: Design, audit, or revise provincial-standard bioinformatics projects（省标/省级课题生信方案）covering Bulk RNA-seq or microarray differential expression, enrichment, GSEA, WGCNA, scRNA-seq annotation and composition plausibility, Augur, AUCell, pseudobulk, selection of one trajectory method from DPT, Monocle3, Slingshot, or CellRank, pySCENIC, decoupler, transcription-factor analysis（转录因子分析）, cell communication, Bulk–single-cell integration, candidate genes, LASSO, random forest, and SVM-RFE. Use when a project needs a defensible analysis sequence, method boundary, evidence hierarchy, risk audit, or implementation plan rather than a list of disconnected analyses.
---

# 省标生信分析工作流

把分析组织成“问题—数据—统计单位—证据—验证”的闭环。优先保证设计可识别、供体级推断和验证独立性，再扩展机制分析与图形。

## 优先级与冲突裁决

- 以用户给定或项目指定的参考方案确定 Bulk 与单细胞的分析范围、模块组合、先后顺序和是否汇合；其流程优先级高于本技能的 [Bulk 默认流程](references/bulk-workflow.md) 和 [单细胞默认流程](references/scrna-workflow.md)。把两个默认流程当作已选模块的条件性实施模板，不当作必做清单。
- 参考方案未纳入的分析模块保持不启动，不因本技能出现该模块而自动追加。例如，方案未要求 Bulk–单细胞整合或取交集时，不建立跨组学交集、候选证据矩阵、Venn/UpSet 或依赖该交集的后续分支。
- 只对参考方案已纳入的分析模块，使用本技能选择具体分析工具和正式出图类型；这两项优先级高于参考方案中的建议性软件、示例图和默认参数。高优先级的工具与图型规则只约束已选模块，不反向扩大分析范围。
- 依次裁决冲突：用户明确要求与不可降低的质量门槛 > 参考方案的流程范围 > 本技能对已选模块的工具与图型选择 > 本技能的默认流程。将每次取舍和理由写入方案或运行摘要。

## 纳入细胞注释时的最高优先级

- 只要任务涉及细胞注释、标签复核、marker判定、注释UMAP、注释后细胞组成或标签变更，第一步必须完整读取 `/share/skills/bio-scrna-cluster-annotation-audit/SKILL.md` 并按其流程执行。
- 运行该技能附带脚本时，以共享根目录 `/share/skills/bio-scrna-cluster-annotation-audit/` 解析 `scripts/` 和 `references/`；只有确认技能已安装后才使用其文档中的 `~/.codex/skills/...` 示例路径。
- 该外部注释技能的生物学背景门槛、de novo marker证据、UMAP空间审查、保守标签和独立复核要求，高于本技能、已有项目标签及其他注释约定。完成其审计门槛后，若结论与当前注释冲突，直接以其最终结论覆盖当前注释字段和cluster-to-label映射；其他规范只能补充，不得降低、绕过或反向覆盖它。
- 覆盖时把原标签保存在独立previous字段并写出逐cluster变更表；将依赖旧标签的比例、marker、差异、轨迹、调控、通讯和整合结果标为失效，使用覆盖后的最终标签重算并重绘。
- 先完成外部技能要求的注释审计与标签定稿，再按 [references/annotation-composition-audit.md](references/annotation-composition-audit.md) 生成注释后 `scop` 正式图和供体级组成审查；审计图不能被正式展示图替代。

## 先加载适用规范

- 先读取用户给定的参考方案；若参考位于 `/share/lijl`，用 `rg --files /share/lijl` 定位与当前 Bulk 或单细胞分支直接相关的 README、配置和脚本。先锁定其要求的分析范围，再从本技能为已选模块选择工具和图型。保留当前项目的数据语义、统计设计和路径，不照搬示例输入、环境路径或比较方向。
- 始终同时使用 `bioinfo-delivery` 约束目录、编号、结果表、图形和运行摘要。
- 肿瘤单细胞项目同时使用 `tumor-infercnv-purification`；恶性细胞下游分析必须经过 inferCNV 纯度门槛。
- 多样本或多队列单细胞整合同时使用 `scrna-dual-integration-benchmark`。
- 完成、修订或审查真实项目结果时，同时使用 `bioinfo-mermaid-audit` 更新全局逻辑审计。

## 1. 固定研究问题与证据角色

1. 读取样本表、临床表、数据来源和实际分析对象。
2. 明确主要比较、结局、协变量、配对关系、组织来源和排除标准。
3. 区分细胞、文库、样本、供体和患者；以供体/患者作为组间推断单位。
4. 为每个数据集登记发现、内部支持、外部验证或机制探索角色。
5. 标记同一数据的重复利用；同源结果不得包装成独立验证。

完成标准：每个主要结论都能对应具体数据集、比较、统计单位和验证角色；缺失信息明确标为待确认。

## 2. 路由分析分支

- 参考方案纳入 Bulk RNA-seq、芯片、DEG、富集、GSEA 或 WGCNA 时，完整读取 [references/bulk-workflow.md](references/bulk-workflow.md)，只实施被纳入的模块。
- 参考方案纳入单细胞注释、Augur、AUCell、pseudobulk、marker、轨迹、pySCENIC、decoupler 或细胞通讯时，完整读取 [references/scrna-workflow.md](references/scrna-workflow.md)，只实施被纳入的模块。
- 进行或审查细胞注释时，先执行最高优先级外部注释技能，再完整读取 [references/annotation-composition-audit.md](references/annotation-composition-audit.md)，并完成医学常识、`scop` 注释后图形和组成异常审查。
- 只在参考方案明确纳入 Bulk–单细胞比对、候选基因整合或机器学习时，完整读取 [references/integration-ml.md](references/integration-ml.md)。
- 创建或重绘热图时，完整读取 [references/plotting-style.md](references/plotting-style.md)，默认优先使用 ComplexHeatmap。

只加载当前分支需要的参考，但所有实际使用分支必须读完。

## 3. 建立证据主线

按以下层级组织结果：

1. 设计与质控证据；
2. 供体级差异或组成证据；
3. 细胞类型、细胞状态和空间/调控定位；
4. 跨方法一致性；
5. 独立队列验证；
6. 实验验证。

把探索性细胞级检验标为发现证据。将 pseudobulk、混合模型或供体级汇总作为组间推断主证据。把轨迹、regulon、通路活性和配体—受体关系表述为计算推断，保留因果边界。

## 4. 执行强制质量门槛

下列门槛只对参考方案已纳入的模块生效；它们约束实施质量，不用于启动方案外模块。

- 差异方向由设计矩阵和对比定义确认；热图只用于验证样本模式，不用于决定 logFC 正负。
- ORA 使用显著基因，GSEA 使用全部可检验基因的有方向排序；WGCNA 不以 DEG 预筛作为输入。
- WGCNA疾病相关模块基因与GSEA基因集的交集为空、过小或不满足后续分析条件时，直接交付空结果和原因；不得为得到图或候选基因而放宽阈值、改换模块或扩大集合。
- 单细胞关键状态必须由多个供体支持；检查供体集中、批次、细胞周期、应激和双细胞驱动。
- 注释完成后必须审查细胞类型占比是否符合组织来源和医学常识。大量不合组织来源的 AT2、Unknown 或单样本垄断群体触发复核，不直接删除或强制改名。
- 未限定精细注释层级时，允许将巨噬/单核相关细胞保守标注为上位 `Myeloid`；需要巨噬细胞特异结论时再以充分marker和跨供体证据细分。
- 肿瘤上皮的恶性亚型、轨迹、pySCENIC 和恶性细胞差异必须在 inferCNV 净化后运行。
- Wilcoxon、`sc.tl.rank_genes_groups(method="wilcoxon")` 与 marker 筛选属于同一类细胞级发现分析，不计作多重独立证据。
- pseudobulk 放在关键细胞筛选前后的主统计链路，不作为末端补充。
- 拟时序仅在存在合理连续过程时运行。实施前评估 DPT、Monocle3、Slingshot 与 CellRank 的问题匹配、拓扑假设、方向先验、数据层和供体覆盖，只选择一种最适配的方法；不得为增加结果数量而并行堆叠方法。全部不适配时停止拟时序并交付不实施原因。横断面病例—对照差异不等于真实时间进展。
- LASSO、随机森林和 SVM-RFE 的预处理与筛选必须封装在嵌套交叉验证内；细胞数不计作机器学习样本量。

完成标准：所有强制门槛均有可核查表格、图形或审计记录；未满足门槛的下游结论降级或停止。

## 5. 条件性汇合而不堆叠

只在参考方案明确要求跨组学整合、候选基因汇合或集合关系时执行本节；否则跳过本节，保留 Bulk 与单细胞的各自结果。

为候选基因建立证据矩阵，至少记录：数据集、细胞类型、方向、效应、调整后 P 值、模块归属、GSEA leading-edge、pseudobulk、轨迹动态、pySCENIC regulon、decoupler 活性、通讯支持、机器学习稳定性和外部验证。

使用 Venn（不超过四组）或 UpSet（超过四组）展示集合关系，同时交付交集计数和成员表。交集用于优先级排序，不自动等于最终机制基因；连续表型、效应方向和证据质量应进入加权评分。

## 6. 交付审计

最终方案或结果必须回答通用问题及参考方案已纳入模块的对应问题：

- 数据能否识别所声称的生物学问题？
- 组间推断是否以生物学重复为单位？
- 关键细胞及其比例是否符合组织与疾病常识？
- 关键亚型是否跨供体复现？
- DPT、Monocle3、Slingshot 与 CellRank 是否已完成方法适配性评估；为何选择当前唯一方法，其他方法为何不选？
- pySCENIC、decoupler、轨迹和细胞通讯是否被正确标为推断证据？
- 参考方案是否要求 Bulk–单细胞汇合；如要求，是否仅在证据层汇合而未错误合并表达矩阵？
- 机器学习是否避免泄漏并完成锁定的外部验证？
- 哪些结论是观察、关联、计算假说或因果证据？

完成标准：交付物包含可追溯流程、风险及残余限制和下一步验证；仅在参考方案要求候选整合时交付候选证据矩阵。任何中央结论均不得只由单一探索性图形支撑。
