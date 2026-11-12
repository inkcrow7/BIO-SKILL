# IPF 来源与版本演进

实际来源目录是 `/share/data/Projects/20260727-IPF`；用户所写 `/share/data/projects/IPF` 为项目简称。文件摘要保存在 [来源清单](source-manifest.json)，采集日期为2026-10-21。本 skill 不依赖该项目继续存在才能执行建轨脚本。

| 来源 | 提取内容 | 使用边界 |
|---|---|---|
| `Scripts/60.trajectory_refresh/prepare.py`、`config.yaml` | 当前 counts 与标签合并、完整 library totals、供体感知排序基因、marker 根评分 | 2000 HVG、具体基因程序及细胞数是 IPF 实例 |
| `Scripts/60.trajectory_refresh/infer.R` | 稀疏整数 counts → Monocle2/DDRTree → donor 等权根状态证据 → 重定向及缓存核验 | 原脚本拟合四种模型；当前通用入口只联合建轨 |
| `Scripts/60.trajectory_refresh/analyze.R`、`validate_models.R` | donor 汇总、条件比较、State 比例补零、分箱 bootstrap、原计数/根/图核验 | 保留设计适用性，不把旧敏感性图作为当前默认交付 |
| `Scripts/62.shared_trajectory/README.md`、`config.yaml` | 当前共同轨迹政策，保留所有定稿细胞，单组/均衡轨迹归档 | 不再按 Control、IPF 或 donor 单独建轨/高亮出图 |
| `Scripts/62.shared_trajectory/plot.R`、`validate.R` | 原生逐基因平滑、原生热图局部适配、实际显示数据与矩阵独立核验 | 当前实例固定20候选；数量与排序不是通用默认 |
| `Scripts/67.gse213001_trajectory_drivers/screen.R`、`config.yaml` | 在 Joint 时间轴的目标条件子集重算样条、donor 趋势、早晚配对及覆盖 | 参考队列、候选数和阈值由新项目确定 |

第60步是三 AT2 标签后的重新建模；第61步曾按 IPF 独立模型画基因模式；第62步更新为两组共同展示，并把旧 IPF 统计标为 historical，未把它改称 Joint 检验；第67步才在 Joint 时间轴目标条件子集上重算新候选。复用时沿用这一证据区分，不把各阶段代码简单拼接后全部执行。

实际 IPF Joint 模型为4072细胞/60供体，细胞标签为三个 AT2 亚型、AT1、异常基底样；这些数值仅用于来源核验。构建本 skill 未重跑 IPF 分析或修改项目文件。

方法原始资料：[Monocle2 官方文档](https://cole-trapnell-lab.github.io/monocle-release/docs/)。具体调用以目标环境真实 API 为准。
