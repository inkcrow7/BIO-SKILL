---
name: pyscenic-plot
description: 已有 pySCENIC 结果的 regulon/AUCell/TF 绘图兼容入口；规范已迁入 bioinfo-plotting，Marsilea 热图与 ytbiokit 评分图遵循统一规则。不运行推断流程。
---

# Regulon 绘图兼容入口

先读取 [统一绘图 skill](/home/taojj/.agents/skills/bioinfo-plotting/SKILL.md)，再读取 [regulon 绘图](/home/taojj/.agents/skills/bioinfo-plotting/references/regulon-plots.md)。保留本目录旧资源用于溯源；旧 plot_pyscenic.py 会重算 UMAP且可静默回退表达层，不能直接作为当前绘图入口。采用最终坐标、明确表达层和统一语义图片名。
