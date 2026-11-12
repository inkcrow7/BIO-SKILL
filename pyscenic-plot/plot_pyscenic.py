import warnings
warnings.filterwarnings("ignore")

import argparse
import os
from pathlib import Path

import loompy as lp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad
import marsilea as ma
import marsilea.plotter as mp
import yaml

ALL_PLOTS = ["adj_hist", "umap", "clustermap", "matrixplot"]

parser = argparse.ArgumentParser(description="Plot figures from existing pySCENIC outputs")
parser.add_argument("--params",
                    default=str(Path(__file__).resolve().parent / "plot_params.yaml"),
                    help="path to YAML parameter file")
parser.add_argument("--only", default=None,
                    help=f"comma-separated subset of: {','.join(ALL_PLOTS)}")
args = parser.parse_args()

with open(args.params) as f:
    cfg = yaml.safe_load(f)

WORKDIR = Path(cfg["workdir"])
os.chdir(WORKDIR)
FIGURES = Path(cfg["figures_dir"])
FIGURES.mkdir(exist_ok=True)
FMT = cfg["figure_format"]
DPI = cfg["figure_dpi"]
TOP_N = cfg["top_n"]
CELLTYPE_COL = cfg["celltype_col"]
GROUP_COL = cfg["group_col"]
P = cfg["plots"]

only = set(args.only.split(",")) if args.only else set(ALL_PLOTS)

adj_mtx = None
if "adj_hist" in only:
    adj_mtx = pd.read_csv(WORKDIR / cfg["adj_csv"])

if only & {"umap", "clustermap", "matrixplot"}:
    lf = lp.connect(str(WORKDIR / cfg["auc_loom"]), mode="r", validate=False)
    auc_mtx = pd.DataFrame(lf.ca.RegulonsAUC.tolist(), index=lf.ca.CellID,
                           columns=lf.ra.Regulons.dtype.names
                           if hasattr(lf.ra.Regulons, "dtype") else None)
    lf.close()
    if auc_mtx.columns.isnull().all():
        auc_mtx.columns = [f"reg_{i}" for i in range(auc_mtx.shape[1])]

    h5 = sc.read_h5ad(cfg["h5ad"], backed="r")
    obs_meta = h5.obs.loc[auc_mtx.index.intersection(h5.obs.index), [CELLTYPE_COL, GROUP_COL]]
    auc_mtx = auc_mtx.loc[obs_meta.index]

if "adj_hist" in only:
    print("=== adj_hist ===")
    pc = P["adj_hist"]
    fig, ax = plt.subplots(figsize=tuple(pc["figsize"]))
    ax.hist(np.log10(adj_mtx["importance"] + 1e-3), bins=pc["bins"], color=pc["color"])
    ax.set_xlabel(pc["xlabel"])
    if pc.get("title"):
        ax.set_title(pc["title"])
    fig.tight_layout()
    fig.savefig(FIGURES / f"adj_importance_hist.{FMT}", dpi=DPI)
    plt.close(fig)

ad_auc = None
if "umap" in only:
    print("=== umap ===")
    pc = P["umap"]
    ad_auc = ad.AnnData(auc_mtx.astype(float))
    sc.pp.neighbors(ad_auc, n_neighbors=pc["n_neighbors"], metric=pc["metric"])
    sc.tl.umap(ad_auc, min_dist=pc["min_dist"], spread=pc["spread"],
               random_state=pc["random_state"])
    ad_auc.obs[CELLTYPE_COL] = obs_meta[CELLTYPE_COL]
    ad_auc.obs[GROUP_COL] = obs_meta[GROUP_COL]
    kwargs = {}
    if pc.get("point_size") is not None:
        kwargs["size"] = pc["point_size"]
    if pc.get("palette") is not None:
        kwargs["palette"] = pc["palette"]
    sc.pl.umap(
        ad_auc,
        color=[CELLTYPE_COL, GROUP_COL],
        show=False,
        wspace=0.8,
        legend_fontsize=8,
        **kwargs,
    )
    plt.savefig(FIGURES / f"umap_aucell_by_celltype_groups.{FMT}", dpi=DPI,
                bbox_inches="tight")
    plt.close("all")

top_tfs = None
if "clustermap" in only:
    print("=== clustermap ===")
    pc = P["clustermap"]
    mean_auc = auc_mtx.copy()
    mean_auc[CELLTYPE_COL] = obs_meta[CELLTYPE_COL]
    # AnnData categorical columns can retain levels absent from the sampled
    # cells.  ``observed=True`` prevents all-NaN phantom rows that make
    # correlation-distance clustering undefined.
    mean_auc = mean_auc.groupby(CELLTYPE_COL, observed=True).mean()
    top_tfs = mean_auc.max(axis=0).sort_values(ascending=False).head(TOP_N)
    mat = mean_auc[top_tfs.index]
    if pc.get("z_score") is not None:
        from scipy.stats import zscore
        mat = mat.apply(zscore, axis=pc["z_score"])
    cb = ma.ClusterBoard(mat.to_numpy(), width=pc["width"], height=pc["height"])
    cb.add_layer(mp.ColorMesh(mat.to_numpy(), cmap=pc["cmap"], label="AUC"))
    cb.add_dendrogram("left", method=pc["linkage_method"], metric=pc["linkage_metric"])
    cb.add_dendrogram("top", method=pc["linkage_method"], metric=pc["linkage_metric"])
    cb.add_bottom(
        mp.Labels(mat.columns, rotation=90, fontsize=8),
        size=1.6,
        pad=0.1,
    )
    cb.add_left(mp.Labels(mat.index, fontsize=8), size=2.2, pad=0.1)
    cb.add_legends()
    cb.render()
    cb.save(FIGURES / f"clustermap_top{TOP_N}_regulons.{FMT}", dpi=DPI)
    plt.close("all")

if "matrixplot" in only:
    print("=== matrixplot ===")
    pc = P["matrixplot"]
    if top_tfs is None:
        mean_auc = auc_mtx.copy()
        mean_auc[CELLTYPE_COL] = obs_meta[CELLTYPE_COL]
        mean_auc = mean_auc.groupby(CELLTYPE_COL, observed=True).mean()
        top_tfs = mean_auc.max(axis=0).sort_values(ascending=False).head(TOP_N)
    tf_names = top_tfs.index.str.replace(r"\(\+\)", "", regex=True)
    tf_names = [t for t in tf_names if t in h5.var_names]

    gene_idx = h5.var_names.get_indexer(tf_names)
    cell_idx = h5.obs.index.get_indexer(obs_meta.index)
    layer = cfg["counts_layer"] if cfg["counts_layer"] in h5.layers else None
    expr = h5.X[cell_idx, :][:, gene_idx] if layer is None \
        else h5.layers[layer][cell_idx, :][:, gene_idx]
    expr = np.asarray(expr.todense()) if hasattr(expr, "todense") else np.asarray(expr)
    if layer is not None:
        expr = np.log1p(expr)
    df = pd.DataFrame(expr, columns=tf_names, index=obs_meta.index)
    df[CELLTYPE_COL] = obs_meta[CELLTYPE_COL].values
    mat = df.groupby(CELLTYPE_COL, observed=True).mean()
    if pc["standard_scale"] == "group":
        mat = (mat - mat.mean(axis=0)) / (mat.std(axis=0) + 1e-9)
    elif pc["standard_scale"] == "var":
        mat = (mat.sub(mat.mean(axis=1), axis=0)
               .div(mat.std(axis=1) + 1e-9, axis=0))
    if pc["swap_axes"]:
        mat = mat.T
    h = ma.Heatmap(mat.to_numpy(), cmap=pc["cmap"],
                   width=pc["width"], height=pc["height"], label="expr")
    if pc["dendrogram"]:
        h.add_dendrogram("left")
        h.add_dendrogram("top")
    h.add_bottom(
        mp.Labels(mat.columns, rotation=90, fontsize=8),
        size=1.6,
        pad=0.1,
    )
    h.add_left(mp.Labels(mat.index, fontsize=8), size=2.2, pad=0.1)
    h.add_legends()
    h.render()
    h.save(FIGURES / f"matrixplot_top_tf_expr.{FMT}", dpi=DPI)
    plt.close("all")

print("=== done ===")
