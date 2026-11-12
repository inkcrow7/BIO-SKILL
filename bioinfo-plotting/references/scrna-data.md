# 单细胞绘图的数据口径与适配

- 检查 cell ID 唯一、sample/group/cell_type 对应关系、定稿注释、分组顺序与有限的既有 UMAP 坐标。表达与评分图使用主 skill 指定入口，按真实接口适配；不为绘图重算邻居或 UMAP。
- 核实 AnnData X、raw、layers 的实际含义，不凭层名猜测。明确 counts、归一化、log1p、scaled 的区别，选择与研究问题匹配的层。缺少所需层时明确失败或说明可用替代尺度，不能静默回退。
- 用 backed 读取和稀疏切片控制内存，只把绘图所需基因/细胞子矩阵转为 dense。确认 var_names 唯一及物种 ID；不创建伪造 counts 来适配绘图库。
- obs 中的评分若入口要求矩阵，可创建临时绘图 AnnData，按同一 cell ID 复制必要元数据和最终坐标，评分值保持原尺度及负值；不覆盖原始表达矩阵。以环境中真实函数签名确定调用。
- 阳性比例的阈值基于有意义的表达尺度，通常归一化/真实 log1p 表达的 >0；标准化 Z-score 的 >0 不能称为检测率。
- 样本汇总至少保留 sample、group、cell_type、gene/score、n_cells、mean、median、positive_n、positive_fraction。先按样本汇总，再等样本权重汇总组；预设细胞数门槛并保留排除记录。
- 只有确认为真实 log1p 值时才可 expm1 恢复对应丰度；其恢复值不是原始 counts。pseudobulk 推断从真实 raw counts 按样本累加，不能从缩放矩阵或评分反推。
- 图中分组切片使用同一值域便于比较，但不对 UMAP 追加样式调节。按请求选择图种，分别输出；不自动选取优先细胞类型、增加密度图或固定数量的图。
