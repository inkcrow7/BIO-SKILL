---
name: scanpy-merge-samples
description: scanpy 合并多个样本 AnnData 时用 ad.concat(join="outer")。当用 scanpy/anndata 做多样本单细胞合并（concatenate samples、merge h5ad、整合多个 10x 样本）、遇到 concat 丢基因或 var_names 不唯一报错、或写单细胞读取/合并流程时使用。
---

# scanpy 多样本合并：用 outer join

## 规则

逐样本读入 AnnData 后合并时，**必须**用 `join="outer"`：

```python
import anndata as ad

adatas = []
for sample_dir in sorted(input_dir.glob("GSM*")):
    a = read_10x_dir(sample_dir)          # 逐样本读取
    a.var_names_make_unique()             # 先保证 var_names 唯一（见坑 2）
    a.obs["sample"] = sample_dir.name     # 保留样本来源
    a.obs_names = [f"{sample_dir.name}_{bc}" for bc in a.obs_names]
    adatas.append(a)

adata = ad.concat(adatas, join="outer")   # 不要用默认 inner
```

## 为什么

- `ad.concat` 默认 `join="inner"`，只保留所有样本共有的基因。多样本 10x
  数据的基因列表常有细微差异（参考版本、伪基因、样本特异检出），inner
  会静默丢弃这些基因，细胞数不变但矩阵悄悄缩水。
- `join="outer"` 保留全部基因的并集，缺失处补 0/NaN，不丢信息。

## 常见坑

1. **`InvalidIndexError: Reindexing only valid with uniquely valued Index objects`**
   —— 基因 symbol 在单个样本内重复（如多个 Ensembl 对应同一 symbol）。
   在 concat **之前**对每个样本 `a.var_names_make_unique()`。
2. **cell barcode 冲突** —— 不同样本 barcode 相同，concat 后 obs_names
   重复。拼接样本前缀：`f"{sample}_{barcode}"`。
3. **样本来源丢失** —— concat 前务必写入 `obs["sample"]`，下游分组/
   批次分析都依赖它。
4. **scanpy ≥1.12 读旧版 10x** —— 旧数据是 2 列 `genes.tsv`（无
   feature_type 列），`sc.read_10x_mtx` 会 `KeyError: 2`。用
   `scipy.io.mmread` 手动读 `matrix.mtx.gz` + `barcodes.tsv.gz` +
   `genes.tsv.gz`（取第 2 列作 symbol），或把 `genes.tsv.gz` 软链为
   `features.tsv.gz`。
