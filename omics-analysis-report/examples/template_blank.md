# [项目标题：研究对象 + 组学方法 + 核心问题]

<!--
omics-neutral skeleton.

仅在最终交付前删除 HTML 注释（report_lint.py 会以 warning 提示）。

为不同组学项目准备的细分模板见同目录:
  template_scrna.md       单细胞转录组（scRNA-seq + pySCENIC）
  template_bulk_deg.md    Bulk RNA-seq 差异表达 + 富集
  template_wgcna.md       WGCNA 模块识别 + 性状关联
  template_tcga.md        TCGA 队列差异分析
  template_geo.md         GEO 公共数据集差异分析
  template_cerna.md       lncRNA-miRNA-mRNA ceRNA 网络
  template_phnet.md       中药网络药理学 + 分子对接

本 blank 用于自由拼装：当模块组合不属于上述任一标准管线时，从本模板起步。
-->

## 1. 背景

[3–6 句话。要素：
- 第一句：样本/数据来源、分组与分析范围
- 第二句：本报告包含的分析模块和主要输出类型
- 第三句：本报告将说明每类图表怎么看、结果文件如何使用
- 末尾：本报告只说明数据结果、图表读法和输出文件使用方式
禁止：内部路径、合作单位的内部项目编号、未公开数据集的内部命名、流程版本号、内部 ticket]

## 2. 方法

### 2.1 数据获取

[从 methods-snippets.md 的「2.1 数据获取」选择匹配变体后填入：
  - Variant A — 公共数据库已发表队列
  - Variant B — TCGA / GDC
  - Variant C — GEO 数据集
  - Variant D — 自有/委托测序
  - Variant E — 网络药理学 (in-silico)]

### 2.2 [模块二方法标题]

[从 methods-snippets.md 复制对应模块段落，替换占位符。
方法节顺序必须与结果节顺序一致，且与图序号一致。]

### 2.3 [模块三方法标题]

[...]

### 2.X [按需追加，每个 ### 3.X 结果都应有一个 ### 2.X 方法与之对应]

[...]

## 3. 结果

### 3.1 [分析项目名称 —— 例如「样本概览与数据质控」]

我们首先对 [N] 例 [研究对象] 的 [组学] 数据进行 [预处理流程概述]，最终获得 [关键中间产物，如「N 个高质量细胞」「N 个表达稳定基因」]。基于 [分析方法] 进行 [核心步骤]，鉴定出 [N 个分组/N 个模块/N 个差异基因]（图1A）。[一句话给出第一个关键观察，描述至此为止]。

进一步比较 [实验组] 与 [对照组] 的 [关注变量]（图1B）。[对照组] 中以 [类别 X] 占比最高（[N%]），其次为 [类别 Y]（[N%]）；相比之下，[实验组] 中 [类别 Z] 升高至 [N%]，[类别 X] 下降至 [N%]。[一句话观察性总结，不引申机制、疾病意义或应用价值]。

![](Figures/[模块].overview.png)
![](Figures/[模块].comparison.png)

**图1.** A：[图 A 内容描述]，展示 [N 个对象] 的分布；B：[图 B 内容描述]。

### 3.2 [分析项目名称 —— 例如「差异表达分析」]

在 [前序结果] 基础上，我们进一步评估 [新维度问题]。采用 [分析方法] 对 [对象] 进行 [量化指标] 评分（图2A）。结果显示，[类别 P] 评分最高（[数值]），其次为 [类别 Q]（[数值]）和 [类别 R]（[数值]）。该图展示 [对象] 在 [量化指标] 下的排序结构。

[第二段，若有支持性图（heatmap、ranking、网络）在此衔接。一句话总结观察，不引申机制、疾病意义或应用价值]。

![](Figures/[模块].quantification.png)
![](Figures/[模块].supporting_heatmap.png)

**图2.** A：[各类别] 在 [比较条件] 下的 [量化指标] 图；B：[支持性证据图说明]。

### 3.3 [分析项目名称 —— 例如「细胞通讯分析」]

在明确 [前序观察] 之后，我们进一步聚焦 [群体/模块/通路] 进行再分析。对 [目标对象] 进行 [二次分析方法]，得到 [N 个亚群/N 个 hub 基因/N 条通路条目]（图3）。

各 [亚群/hub] 呈现差异化的 [标志特征]。[一两句话描述差异的具体表现，但不进行机制、疾病意义或应用价值推断]。

![](Figures/[模块].refined.png)

**图3.** [目标对象] 二次分析 [图类型]，展示 [N 个对象] 的特征。

### 3.4 [分析项目名称 —— 例如「功能富集分析」]

在上述结果基础上，我们进一步从 [新分析维度] 解析 [研究目标]。基于 [分析方法] 的 [评分/富集] 显示，[关键观察]（图4A）。

[第二段：补充比较或排序结果，给出数据层面总结，并说明结果表或图文件如何继续使用。不展开机制、疾病意义或应用价值]。

![](Figures/[模块].upstream_panel_A.png)
![](Figures/[模块].upstream_panel_B.png)

**图4.** A：[图 A 说明]；B：[图 B 说明]。

<!--
后续若需追加 3.5 / 3.6 …，按相同节奏：
  1) 数据层面标题
  2) 「在 XX 基础上 / 随后 …」开篇
  3) 2 段，每段 2–4 句，先描述图再陈述观察，止步于数据层面
  4) 1–4 张 ![]() 连排
  5) 紧跟 **图N.** 图注（A/B/C 与图块顺序匹配）
-->

---

## 5. 参考文献

[仅保留正文实际引用的条目。方法段中每个软件/数据库 citation key 必须出现在这里，格式示例：]

- [Wolf2018Scanpy] Wolf FA, Angerer P, Theis FJ. SCANPY: large-scale single-cell gene expression data analysis. Genome Biology. 2018. doi:10.1186/s13059-017-1382-0.

<!--
使用说明（最终交付前请删除整段注释）：

1. 复制本模板为新文件，例如 cohort_X_report.md
2. 按 [...] 占位符逐段替换；保持方法/结果/图序号三者顺序一致
3. 方法（2.1–2.X）：从 methods-snippets.md 复制对应模块的段落
4. 图表：先建立 figure_manifest.tsv；每种图类型至少在报告中展示一个代表图，图很多时用某个通路/比较举例
5. 图注：每张 figure 紧跟 **图N.** A：…；B：…；C：…。 段落（report_lint.py 会校验编号连续性）
6. 渲染为 HTML：
   python ~/.claude/skills/omics-analysis-report/md_to_html.py \
     cohort_X_report.md -o cohort_X_report.html
7. 渲染前先跑 lint：
   python omics-analysis-report/report_lint.py cohort_X_report.md \
     --figure-manifest figure_manifest.tsv --strict-client-scope --strict-references --warnings-as-errors
8. 检查清单（参考 SKILL.md「Quality checks before delivery」）：
   - 方法顺序 = 结果顺序 = 图序号
   - 每个 ![]() 路径相对 HTML 输出位置可解析
   - 每个 figure 紧跟 **图N.** 图注
   - figure_manifest.tsv 里每个图类型都在正文或附录中呈现
   - 没有超出数据展示范围的研究方向解释
   - 没有任何绝对路径、内部命名、流程版本号、未公开数据集编号
-->
