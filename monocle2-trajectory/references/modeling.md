# 建模、输入与起点

## 输入准备

从当前定稿 AnnData/Seurat 对象按 cell ID 提取生物学上连续的目标谱系，继承 QC、样本排除及适用的肿瘤纯度门槛。原始计数需显式来自实际 counts 层；先核对非负、有限、整数与文库非空。计数转成 **gene × cell** 稀疏 Matrix Market，第一列为 ID 的基因/细胞 TSV 顺序必须与矩阵一致。基因表有 `gene_short_name`，另保留 Ensembl 等稳定 ID。

参考 IPF 第60步：按当前细胞身份保留 AT2、AT1、异常基底样细胞；把第59步三个 AT2 标签按 cell ID 合入父对象，不重新加入已过滤细胞。新项目重新指定谱系与标签，不照抄这些名字。

- 记录全 QC 基因空间的每细胞 library total，再按表达覆盖筛基因；IPF 示例是至少10细胞检出。保留全量过滤表。
- 用实际原 counts 的 log1p(CP10k) 做 marker 程序分数与供体感知 HVG 选择，归一化分母保持为上述完整 library total。这些变换只用于选特征/根证据，传入 Monocle2 的仍是原始整数 counts。
- 参考 `scanpy.pp.highly_variable_genes(flavor="seurat", batch_key="donor")`：IPF 用每供体至少20细胞的集合估计，按 `highly_variable_nbatches`、`dispersions_norm` 稳定排序，排除物种对应线粒体、核糖体、血红蛋白及指定性别技术基因后取2000基因。数量与排除集按项目声明，不强制固定2000，也不强制删除研究目标通路。
- 根评分需与目标谱系匹配。IPF 使用 AT2 表面活性物程序均值减去 AT1/损伤基底程序均值的平均；原 marker 集见来源配置。缺失基因与覆盖要求记录，不按拟时序结果反选起点。

脚本需要 metadata 字段 donor、condition、细胞标签、粗身份、数值 root score，可通过配置映射真实列名。现成脚本假定每供体仅一个条件；配对/重复受试者跨条件时先适配该断言及统计设计。保留全 gene library totals 供后续 CP10k 统计使用。

## 正式共同建轨

在项目中初始化分析模块和 tmp/Logs。复制 [IPF 示例](../assets/ipf-example.yaml) 到项目配置并调整真实输入、物种、字段、排序基因和根参数。为新模块创建父目录，再运行：

```bash
# 项目根目录和新模块路径由当前任务确定，以下为调用形式。
Rscript /home/taojj/monocle2-trajectory/scripts/fit_shared_trajectory.R   config.yaml PROJECT_ROOT Data/Processed/NN.shared_trajectory/Output
```

`config.yaml` 路径按命令当前目录解析；其输入路径相对 PROJECT_ROOT；OUTPUT_DIR 的父目录须已存在。运行工作目录和 TMPDIR 按交付规范设置在项目内部。首次运行输出目录应为空；失败输出保留日志并归档后重跑。

原生过程：`newCellDataSet(..., expressionFamily=negbinomial.size(), lowerDetectionLimit=0.5)` → `estimateSizeFactors` → `estimateDispersions` → `setOrderingFilter` → `reduceDimension(reduction_method="DDRTree", max_components=2, norm_method="log", maxIter=100)` → `orderCells` → 根证据选择 → `orderCells(root_state=...)`。

- 种子、迭代数和参数显式配置。IPF 未在 DDRTree 残差公式中回归 donor，因为 donor 嵌套于疾病；不将回归供体视为无条件默认。新设计需判断混杂及生物结构，记录选择依据。
- 各 State 内先计算每供体平均 root score，再对供体均值等权平均。参考门槛：状态至少20细胞、候选起点身份占比至少0.5；在合格状态中选供体均值最高者，并以 State 编号打破并列。无合格状态不强制选根。
- 核对最早细胞真实身份与先验起点一致；输出候选状态、供体覆盖、评分、实际起点 cell ID 和身份。Pseudotime 最小值为0且全部有限，主图连通且边数=顶点数−1。
- 拟合、绘图和统计对象分别标注版本。仅改展示/目标基因，复用 CDS，不重新归一化、估计 size factors 或 orderCells。拟合新细胞集合时建立独立新模型，不能把旧 RDS 改名冒充新建模。

## 环境与缓存

IPF 已验证环境是 R 4.6.1、monocle 2.36.0、DDRTree 0.1.6、igraph 2.3.3、VGAM 1.1-14、Matrix 1.7-6；是来源记录，不是普遍版本锁定。运行前核对真实包、函数及兼容性。历史 Monocle2 对 igraph、Matrix、ggplot2、VGAM 版本可能敏感；先做小规模真实 API 冒烟。保留补丁来源及版本，不替换成 Monocle3，也不静默修改系统包。

本脚本缓存键含全部输入文件、配置、脚本和依赖版本，并核验模型 SHA256。输入、标签、基因集合或参数变动时停止复用，使用新模块或归档重拟合。输出缓存记录与模型同在 Output，运行摘要另按项目规范记录。

验证范围：本 skill 的参数化脚本已通过当前环境中360细胞、400基因模拟 counts 的完整建轨、根/时间/图检查、原计数与 ID 保留、缓存复用及变更输入拒绝测试。另一个120细胞模拟输入曾在 igraph 的重定向 DFS 中触发原生崩溃；这不构成通用最少细胞阈值，也不意味着所有小数据都会失败。正式运行前应在目标数据规模和隔离 R 进程中验证兼容性；失败保留日志并检查依赖版本，不通过增删真实细胞来绕过问题。未据此重跑或修改 IPF 项目。
