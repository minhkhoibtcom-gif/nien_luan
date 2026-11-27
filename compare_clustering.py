"""So sánh K-Prototypes với K-Means, K-Modes và Hierarchical trên cùng dataset Gen Z Việt Nam (361 người).

Chạy:  venv\\Scripts\\python compare_clustering.py
Kết quả: figures/so_sanh/*.png và so_sanh_chi_so.csv

Cách đưa dữ liệu hỗn hợp (4 cột số + 3 cột phân loại) vào từng thuật toán:
- K-Prototypes: cột số chuẩn hóa z-score + cột phân loại giữ nguyên (giống segmentation.py).
- K-Means: cột số z-score + one-hot cột phân loại (K-Means chỉ làm việc với số).
- K-Modes: chỉ làm việc với dữ liệu phân loại nên 4 cột số (tuổi, thu nhập, thái độ, ý định đặt tiếp)
  được chia thành tối đa 4 nhóm theo tứ phân vị.
- Hierarchical: average linkage trên ma trận khoảng cách Gower (Gower xử lý được dữ liệu hỗn hợp;
  Ward không dùng được vì Ward cần khoảng cách Euclid).

Chỉ số đánh giá (tính chung cho mọi thuật toán để so sánh công bằng):
- Silhouette trên khoảng cách Gower (cao là tốt, trong [-1, 1]).
- Davies-Bouldin và Calinski-Harabasz trên cùng một biểu diễn số (z-score + one-hot):
  DB thấp là tốt, CH cao là tốt.
Hình chiếu 2D: FAMD (PCA cho dữ liệu hỗn hợp: cột số z-score, cột one-hot chia căn tần suất rồi trừ trung bình).
"""
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from kmodes.kmodes import KModes
from kmodes.kprototypes import KPrototypes
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import squareform
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                             silhouette_samples, silhouette_score)
from sklearn.preprocessing import StandardScaler

from segmentation import CAT_COLS, CAT_IDX, K, NUM_COLS, load_customers

HERE = Path(__file__).parent
OUT = HERE / "figures" / "so_sanh"
CSV = HERE / "so_sanh_chi_so.csv"
K_RANGE = range(2, 9)
SEED = 42
ALGOS = ["K-Prototypes", "K-Means", "K-Modes", "Hierarchical"]
COLOR = {"K-Prototypes": "#d62828", "K-Means": "#2f6db5", "K-Modes": "#2a9d8f", "Hierarchical": "#8a6fd1"}
CLUSTER_COLORS = ["#d62828", "#2f6db5", "#2a9d8f", "#f6aa1c", "#8a6fd1", "#6c757d", "#e76f51", "#264653"]

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .3, "font.size": 10})


# ---------- Chuẩn bị dữ liệu ----------
def prepare():
    df = load_customers()
    data = df[NUM_COLS + CAT_COLS].copy()
    z = StandardScaler().fit_transform(data[NUM_COLS])
    onehot = pd.get_dummies(data[CAT_COLS].astype(str)).to_numpy(float)

    mixed = data.copy()                       # K-Prototypes
    mixed[NUM_COLS] = z
    numeric = np.hstack([z, onehot])          # K-Means, DB, CH
    binned = data[CAT_COLS].astype(str).copy()  # K-Modes
    for col in NUM_COLS:
        binned[col] = pd.qcut(data[col], 4, duplicates="drop").astype(str)

    # FAMD: chia cột one-hot cho căn tần suất rồi trừ trung bình, ghép với cột số z-score
    p = onehot.mean(axis=0)
    famd_input = np.hstack([z, (onehot / np.sqrt(p)) - np.sqrt(p)])
    pca = PCA(n_components=2, random_state=SEED).fit(famd_input)
    return dict(data=data, mixed=mixed.to_numpy(), numeric=numeric, binned=binned.to_numpy(),
                gower=gower_matrix(data), famd=pca.transform(famd_input), famd_var=pca.explained_variance_ratio_)


def gower_matrix(data):
    """Khoảng cách Gower: trung bình |x-y|/khoảng giá trị (cột số) và 0/1 khác nhau (cột phân loại)."""
    n = len(data)
    D = np.zeros((n, n), dtype=np.float64)
    for col in NUM_COLS:
        x = data[col].to_numpy(float)
        D += np.abs(x[:, None] - x[None, :]) / (x.max() - x.min())
    for col in CAT_COLS:
        x = data[col].astype("category").cat.codes.to_numpy()
        D += x[:, None] != x[None, :]
    D /= len(NUM_COLS) + len(CAT_COLS)
    np.fill_diagonal(D, 0)
    return D


# ---------- Chạy thuật toán ----------
def run(algo, k, X, Z=None):
    if algo == "K-Prototypes":
        return KPrototypes(n_clusters=k, init="Cao", n_init=5, random_state=SEED).fit_predict(
            X["mixed"], categorical=CAT_IDX)
    if algo == "K-Means":
        return KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X["numeric"])
    if algo == "K-Modes":
        return KModes(n_clusters=k, init="Cao", n_init=5, random_state=SEED).fit_predict(X["binned"])
    return fcluster(Z, k, criterion="maxclust") - 1  # Hierarchical: cắt cây đã dựng sẵn


def metrics(X, labels):
    if len(set(labels)) < 2:
        return dict(silhouette=np.nan, davies_bouldin=np.nan, calinski_harabasz=np.nan)
    return dict(silhouette=silhouette_score(X["gower"], labels, metric="precomputed"),
                davies_bouldin=davies_bouldin_score(X["numeric"], labels),
                calinski_harabasz=calinski_harabasz_score(X["numeric"], labels))


def align(reference, labels):
    """Đổi số thứ tự cụm cho khớp nhiều nhất với cụm tham chiếu (để màu các hình tương ứng nhau)."""
    k = max(reference.max(), labels.max()) + 1
    table = np.zeros((k, k))
    for r, l in zip(reference, labels):
        table[l, r] += 1
    rows, cols = linear_sum_assignment(-table)
    mapping = dict(zip(rows, cols))
    return np.array([mapping[l] for l in labels])


# ---------- Biểu đồ ----------
def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    if fig._suptitle is not None:  # đẩy tiêu đề chung lên trên tiêu đề 2 dòng của từng ô
        fig._suptitle.set_y(1.08 if any("\n" in ax.get_title() for ax in fig.axes) else 1.02)
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)
    print("  đã lưu", (OUT / name).relative_to(HERE))


def plot_metrics_by_k(table):
    specs = [("silhouette", "Silhouette (Gower) — cao là tốt"),
             ("davies_bouldin", "Davies–Bouldin — thấp là tốt"),
             ("calinski_harabasz", "Calinski–Harabasz — cao là tốt")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, (col, title) in zip(axes, specs):
        for algo in ALGOS:
            t = table[table.algorithm == algo]
            ax.plot(t.k, t[col], marker="o", lw=2.4 if algo == "K-Prototypes" else 1.6,
                    color=COLOR[algo], label=algo)
        ax.axvline(K, color="#999", ls="--", lw=1)
        ax.set(title=title, xlabel="Số cụm K", xticks=list(K_RANGE))
    axes[0].legend(frameon=False)
    fig.suptitle("Chỉ số đánh giá theo số cụm K", fontweight="bold")
    save(fig, "1_chi_so_theo_K.png")


def plot_metrics_at_k(table):
    t = table[table.k == K].set_index("algorithm").loc[ALGOS]
    specs = [("silhouette", "Silhouette (Gower)\ncao là tốt", "{:.3f}"),
             ("davies_bouldin", "Davies–Bouldin\nthấp là tốt", "{:.2f}"),
             ("calinski_harabasz", "Calinski–Harabasz\ncao là tốt", "{:.0f}"),
             ("seconds", "Thời gian chạy (giây)\nthấp là tốt", "{:.2f}")]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    for ax, (col, title, fmt) in zip(axes, specs):
        bars = ax.bar(ALGOS, t[col], color=[COLOR[a] for a in ALGOS])
        ax.bar_label(bars, labels=[fmt.format(v) for v in t[col]], padding=2, fontsize=9)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="x", visible=False)
    fig.suptitle(f"So sánh 4 thuật toán tại K = {K}", fontweight="bold")
    save(fig, f"2_chi_so_tai_K{K}.png")


def plot_famd(X, labels):
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.4), sharex=True, sharey=True)
    for ax, algo in zip(axes, ALGOS):
        lab = labels[algo]
        for c in range(K):
            m = lab == c
            ax.scatter(X["famd"][m, 0], X["famd"][m, 1], s=7, alpha=.55, color=CLUSTER_COLORS[c],
                       label=f"Cụm {c} ({m.sum()})")
        ax.set_title(algo, color=COLOR[algo], fontweight="bold")
        ax.legend(markerscale=2.5, fontsize=8, frameon=False, loc="best")
    v = X["famd_var"]
    axes[0].set_ylabel(f"Thành phần 2 ({v[1]:.0%})")
    for ax in axes:
        ax.set_xlabel(f"Thành phần 1 ({v[0]:.0%})")
    fig.suptitle(f"Hình chiếu FAMD 2 chiều, tô màu theo cụm (K = {K}; màu đã khớp theo K-Prototypes)",
                 fontweight="bold")
    save(fig, "3_famd_scatter.png")


def plot_silhouette(X, labels):
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.6), sharex=True)
    for ax, algo in zip(axes, ALGOS):
        lab = labels[algo]
        s = silhouette_samples(X["gower"], lab, metric="precomputed")
        y = 0
        for c in range(K):
            vals = np.sort(s[lab == c])
            ax.fill_betweenx(np.arange(y, y + len(vals)), 0, vals, color=CLUSTER_COLORS[c], alpha=.8)
            ax.text(-0.02, y + len(vals) / 2, str(c), ha="right", va="center", fontsize=9)
            y += len(vals) + 40
        ax.axvline(s.mean(), color="#333", ls="--", lw=1)
        ax.set_title(f"{algo}\nTB = {s.mean():.3f} · điểm âm {(s < 0).mean():.1%}", color=COLOR[algo])
        ax.set(xlabel="Hệ số silhouette (Gower)", yticks=[])
        ax.grid(axis="y", visible=False)
    axes[0].set_ylabel("Các điểm, xếp theo cụm")
    fig.suptitle(f"Biểu đồ silhouette từng điểm (K = {K})", fontweight="bold")
    save(fig, "4_silhouette_plot.png")


def plot_ari(labels):
    n = len(ALGOS)
    M = np.array([[adjusted_rand_score(labels[a], labels[b]) for b in ALGOS] for a in ALGOS])
    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    im = ax.imshow(M, cmap="Reds", vmin=0, vmax=1)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > .6 else "#222")
    ax.set(xticks=range(n), yticks=range(n), xticklabels=ALGOS, yticklabels=ALGOS)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=.046)
    ax.set_title(f"Mức trùng khớp giữa các cách phân cụm (ARI, K = {K})", fontweight="bold")
    save(fig, "5_ari_heatmap.png")


def plot_crosstabs(labels):
    others = ALGOS[1:]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    for ax, algo in zip(axes, others):
        T = pd.crosstab(labels["K-Prototypes"], labels[algo]).reindex(index=range(K), columns=range(K),
                                                                       fill_value=0).to_numpy()
        ax.imshow(T, cmap="Reds")
        for i in range(K):
            for j in range(K):
                ax.text(j, i, T[i, j], ha="center", va="center",
                        color="white" if T[i, j] > T.max() * .6 else "#222")
        ax.set(xticks=range(K), yticks=range(K), xlabel=f"Cụm của {algo}", ylabel="Cụm của K-Prototypes",
               title=f"K-Prototypes × {algo}")
        ax.grid(False)
    fig.suptitle("Bảng chéo nhãn cụm: khách của mỗi cụm K-Prototypes rơi vào cụm nào ở thuật toán khác",
                 fontweight="bold")
    save(fig, "6_bang_cheo_nhan.png")


def plot_sizes(labels):
    fig, ax = plt.subplots(figsize=(9, 4))
    width = .2
    x = np.arange(K)
    for i, algo in enumerate(ALGOS):
        counts = np.bincount(labels[algo], minlength=K)
        bars = ax.bar(x + (i - 1.5) * width, counts, width, color=COLOR[algo], label=algo)
        ax.bar_label(bars, fontsize=7, padding=1)
    ax.set(xticks=x, xticklabels=[f"Cụm {c}" for c in range(K)], ylabel="Số khách",
           title=f"Kích thước các cụm của từng thuật toán (K = {K})")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, ncol=4)
    save(fig, "7_kich_thuoc_cum.png")


def plot_profiles(data, labels):
    """Thu nhập và ý định đặt tiếp trung bình của từng cụm: cụm có ý nghĩa kinh doanh hay không."""
    x_col, y_col = "Thu nhập", "Ý định đặt tiếp"
    fig, axes = plt.subplots(1, 4, figsize=(17, 4), sharex=True, sharey=True)
    for ax, algo in zip(axes, ALGOS):
        g = data.assign(c=labels[algo]).groupby("c")[NUM_COLS].agg(["mean", "size"])
        for c in g.index:
            ax.scatter(g.loc[c, (x_col, "mean")], g.loc[c, (y_col, "mean")],
                       s=120 + g.loc[c, (x_col, "size")] * 2, color=CLUSTER_COLORS[c], alpha=.75, edgecolor="white")
            ax.annotate(str(c), (g.loc[c, (x_col, "mean")], g.loc[c, (y_col, "mean")]),
                        ha="center", va="center", color="white", fontweight="bold")
        ax.set(title=algo, xlabel="Thu nhập trung bình (triệu/tháng)")
        ax.title.set_color(COLOR[algo])
        ax.margins(.15)
    axes[0].set_ylabel("Ý định đặt tiếp trung bình (1–7)")
    fig.suptitle(f"Tâm cụm theo thu nhập và ý định đặt tiếp (kích thước bong bóng = số khách, K = {K})",
                 fontweight="bold")
    save(fig, "8_tam_cum_thu_nhap_y_dinh.png")


def plot_dendrogram(Z):
    fig, ax = plt.subplots(figsize=(11, 4))
    dendrogram(Z, truncate_mode="lastp", p=30, ax=ax, color_threshold=Z[-(K - 1), 2],
               above_threshold_color="#999", no_labels=True)
    ax.axhline(Z[-(K - 1), 2], color="#d62828", ls="--", lw=1, label=f"Ngưỡng cắt cho K = {K}")
    ax.set(title="Cây phân cấp (average linkage, khoảng cách Gower; 30 nhánh cuối)", ylabel="Khoảng cách Gower")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False)
    save(fig, "9_dendrogram.png")


# ---------- Chương trình chính ----------
def main():
    print("Chuẩn bị dữ liệu và ma trận Gower...")
    X = prepare()
    Z = linkage(squareform(X["gower"], checks=False), method="average")

    rows, at_k = [], {}
    for algo in ALGOS:
        for k in K_RANGE:
            start = time.perf_counter()
            labels = np.asarray(run(algo, k, X, Z))
            seconds = time.perf_counter() - start
            rows.append(dict(algorithm=algo, k=k, seconds=seconds, clusters=len(set(labels)),
                             smallest=np.bincount(labels).min(), **metrics(X, labels)))
            if k == K:
                at_k[algo] = labels
            print(f"  {algo:13} K={k}: silhouette={rows[-1]['silhouette']:.3f}  ({seconds:.1f}s)")
    # Hierarchical cắt cây đã dựng sẵn nên cộng thêm thời gian dựng cây cho công bằng
    start = time.perf_counter()
    linkage(squareform(X["gower"], checks=False), method="average")
    build = time.perf_counter() - start
    table = pd.DataFrame(rows)
    table.loc[table.algorithm == "Hierarchical", "seconds"] += build

    for algo in ALGOS[1:]:
        at_k[algo] = align(at_k["K-Prototypes"], at_k[algo])

    table.round(4).to_csv(CSV, index=False, encoding="utf-8-sig")
    print("Đã lưu", CSV.name)
    print(table[table.k == K].round(3).to_string(index=False))

    print("Vẽ biểu đồ...")
    plot_metrics_by_k(table)
    plot_metrics_at_k(table)
    plot_famd(X, at_k)
    plot_silhouette(X, at_k)
    plot_ari(at_k)
    plot_crosstabs(at_k)
    plot_sizes(at_k)
    plot_profiles(X["data"], at_k)
    plot_dendrogram(Z)


if __name__ == "__main__":
    main()
