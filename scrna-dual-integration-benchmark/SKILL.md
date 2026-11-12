---
name: scrna-dual-integration-benchmark
description: Run both Harmony and scVI integrations for multi-sample or multi-cohort scRNA-seq, cluster and annotate both independently, then quantitatively select exactly one primary result set for Results and report delivery; retain the unselected route only as internal sensitivity evidence. Use whenever Codex performs, revises, diagnoses, or reviews single-cell batch correction, dataset integration, joint UMAP/Leiden clustering, cell-type annotation, label transfer, or cross-cohort cell-state comparison with AnnData/Scanpy.
---

# scRNA Dual Integration Benchmark

把 Harmony 与 scVI 视为两条必须完整执行的候选路线。使用相同的 QC 后细胞和可比基因空间，分别建模、聚类、注释和审查；根据量化指标选择且只选择一条主路线。`Results/`、报告和交付包只保留获选路线的一套正式结果，另一条路线仅保存在 `Data/Processed` 和内部 comparison 记录中，作为敏感性与审计证据。

同时使用 `bioinfo-delivery` 组织可复现产物。

## 1. 固定输入与设计边界

1. 核实 accession、样本、供体、疾病、区域、平台、文库和配对关系。区分 donor、sample、library 和 cell。
2. 对所有样本执行一致的 QC、双细胞和污染处理。保留原始整数 counts layer，给 barcode 添加样本前缀，并用 `ad.concat(join="outer")` 合并。
3. 在整合前统一基因 ID 和参考版本。记录各数据集共有基因、缺失基因和 ID 转换损失；对 PCA/HVG 使用真实可比较的基因空间，避免把“某队列未测量”当作生物学零表达。
4. 将 accession、建库批次或已知技术流程作为候选 batch。将 disease、region、treatment、timepoint 和目标细胞状态保留为生物变量。
5. 若 batch 与目标条件完全混杂，将 intended cross-batch biological comparison 标记为 `BLOCKER`；整合算法不能恢复设计中不存在的可识别性。

完成标准：两条路线接收同一组通过 QC 的细胞，原始 counts 可用，技术批次和目标生物变量被明确区分。

## 2. Harmony 路线

1. 对 counts 做 library-size normalization 和 log1p。
2. 按 batch 识别 HVG，并报告 HVG 在 1、2、…、全部 batch 中的可变数量。优先使用跨多个 batch 可复现的 HVG；对只在单一 batch 变化的特征进行敏感性分析。
3. 在可比较 HVG 上执行合适的 scaling/centering 和 PCA。记录 zero-centering、PC 数、随机 seed 和稀疏矩阵处理方式。
4. 只用技术批次变量运行 Harmony。记录 theta、lambda、迭代和收敛信息，不用 disease/region 作为批次变量追求视觉混合。
5. 基于 Harmony 表征独立构建 neighbors、UMAP 和 Leiden；输出稳定语义的 `harmony` AnnData 对象。

完成标准：Harmony 分支有独立 latent/PCA、neighbors、UMAP、cluster、参数记录和可读取对象。

## 3. scVI 路线

1. 从相同细胞的原始整数 counts 建模；验证输入不是 log-normalized 或批次校正后的值。
2. 设置技术 batch key，并按证据加入测序深度、线粒体比例或其他技术 covariates。将 disease/region 作为保留的生物变量，而非需要消除的 batch。
3. 固定 seed，记录 scvi-tools、PyTorch、CUDA/CPU 环境、基因数、latent dimension、训练轮次、early stopping、batch size 和训练/验证损失。
4. 检查训练稳定性、异常 loss、NaN 和过拟合。资源不足或依赖缺失时请求安装/算力授权；不得静默跳过 scVI。
5. 基于 scVI latent 独立构建 neighbors、UMAP 和 Leiden；输出稳定语义的 `scvi` AnnData 对象。

完成标准：scVI 分支有独立 latent、neighbors、UMAP、cluster、训练记录和可读取对象。

## 4. 两套结果独立注释

对 Harmony 和 scVI 的 cluster 分别执行完整注释，不把一条路线的 cluster ID 或标签直接复制到另一条路线。

1. 先注释 broad lineage，再在每个纯化 lineage 内重新聚类和细分状态。
2. 对每个标签同时检查：正标志、负标志、lineage-exclusion markers、差异 marker、程序分数、细胞数、供体数和 accession 支持。
3. 把 cluster-level marker、reference mapping 和 gene-set score 作为互补证据。reference label transfer 不作为唯一依据。
4. 对污染、ambient RNA、双细胞、应激和细胞周期程序单独标记或排除，避免将技术状态命名为新细胞类型。
5. 要求正式细胞状态至少得到多个供体支持；跨队列共享状态应在至少两个 accession 中获得一致 marker 支持。稀有或单队列状态使用 `candidate`、`dataset-specific` 或 `low-confidence` 标签。
6. 软骨中的肥大、矿化或成骨样 marker 只支持 `hypertrophic/mineralizing/osteogenic-like chondrocyte`，除非有完整谱系证据证明真正 osteoblast 身份。
7. 完成独立注释后，生成 Harmony↔scVI cluster overlap、标签混淆矩阵、marker 一致性和 donor/accession 支持表。

完成标准：两条路线各有独立 annotation 表和 marker 证据；每个最终标签有置信度、供体支持及不一致说明。

## 5. 量化比较

对校正前 PCA、Harmony 和 scVI 三种表征使用相同细胞抽样和相同邻居参数。

### 批次去除

- graph neighbor mixing 与同 batch 邻居比例；同时报告按实际 batch 构成计算的随机期望。
- iLISI、kBET、batch ASW，以及 cluster dominant-batch fraction/entropy。
- 每个 cluster 的 accession、sample 和 donor 支持；标记由单一 batch 或单一 donor 主导的 cluster。
- 在同一 disease、同一 broad lineage 和主要细胞类型内重复评估，避免组成差异伪装成批次效应。

### 生物学保留

- cell-type/state ASW 或 cLISI、经典 marker 保留和 lineage 分离。
- disease、region 和 treatment 信号在同一细胞类型内的保留程度。
- 稀有群体、连续状态、轨迹端点和关键基因表达是否被压平或拆散。
- donor-level pseudobulk 效应方向、亚群组成和候选基因在两条路线间的稳定性。

### 注释一致性

- broad lineage 与细分标签的一致率、ARI/NMI、cluster overlap 和 label confusion。
- 每个标签的正/负 marker 得分、供体数、accession 数和最低细胞数。
- Harmony-only、scVI-only 和共同支持的状态清单。

完成标准：至少有一张整合指标表、一张注释一致性表和一份 cluster donor/accession 支持表；不能只提供 UMAP 视觉判断。

## 6. 选择主结果

1. 在查看生物学结论前声明选择规则。批次混合和生物学保留必须同时达标。
2. UMAP 外观不参与单独决策。充分混合但丢失 disease/lineage 信号属于过度校正；保留 marker 但近邻仍由 accession 主导属于校正不足。
3. 选择综合指标更优且关键状态有跨供体/跨队列支持的路线作为唯一 primary；另一条路线只保留为内部 sensitivity evidence，不形成第二套正式结果。
4. 若两条路线对关键标签、细胞比例或候选基因结论不一致，不强行合并标签。将该结论降级，并在内部 selection table 中记录两条路线的差异；正式结果仍只呈现 primary 路线。
5. 所有差异表达和细胞比例统计使用 donor/sample 作为重复单位；联合嵌入中的 cell 不作为独立生物学重复。
6. 用可审计的 selection table 记录获选路线、批次去除、生物学保留、供体支持、注释一致性和决策理由。正式 `Results/`、`Report_delivery` 与报告中的 UMAP、cluster、annotation、marker/program 表图只保留 primary 路线；sensitivity 路线图、轻量对象和冲突诊断仅保存在 `Data/Processed` 或内部 comparison 目录，不进入正式交付。
7. 若两条路线均未达到预声明标准，或现有证据不足以选出一条主路线，将正式交付标记为待决并补充诊断；不得把两套路线同时放入正式结果来替代选择。

完成标准：主路线选择可由表格复核，正式图只来自获选路线，另一条路线的支持或冲突被明确记录，关键结论完成双路线敏感性检查。

## 7. 最低交付物

- Harmony 与 scVI 两个独立、可读取的 AnnData 对象，均作为内部分析对象保存在 `Data/Processed`。
- 两套路线的诊断 UMAP 和各自的 cluster annotation、marker、donor/accession support 表，仅保存在 `Data/Processed` 或内部 comparison 目录。
- 校正前、Harmony、scVI 的 integration metrics 表，以及 Harmony↔scVI 标签混淆/overlap 和主路线选择表，作为单份选择审计记录。
- 正式 `Results`、`Report_delivery` 和报告仅交付 primary 路线的 batch/accession、donor、disease/region、cluster、broad annotation、refined annotation、marker/program 及下游结果。
- 两种表征的关键 donor-level pseudobulk 或组成结论用于内部敏感性核验；正式结果只呈现 primary 路线，并在选择审计表中记录一致性或冲突。
- 内部 run summary 记录参数、版本、seed、输入摘要和风险；Results README 仅说明方法、阈值和文件用途。

保留现有正式结果，除非用户明确授权覆盖。重分析时使用稳定的 `harmony`、`scvi` 和 `comparison` 文件名，不创建 `final_v2`、`new` 或日期副本。

## 8. 停止条件

以下任一项未完成时，不得声称跨队列整合或统一注释已经完成：

- Harmony 或 scVI 任一路线缺失。
- 两套结果没有独立聚类和独立注释。
- 没有定量批次混合与生物学保留指标。
- 关键 cluster 由单一 accession/donor 主导但仍被称为共享状态。
- 主路线仅按 UMAP 外观选择。
- Harmony 与 scVI 的表图或下游结果同时进入 `Results`、`Report_delivery` 或正式报告，未按量化效果二选一。
- 关键 OA/正常结论没有 donor-level 统计或双路线敏感性检查。
