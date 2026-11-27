"""Chọn số cụm K cho K-Prototypes trên dataset Gen Z Việt Nam (361 người, Data in Brief 2023).

Chạy (từ thư mục gốc dự án):
    venv\\Scripts\\python thu_nghiem_vn\\chon_k.py [đường_dẫn_Dataset.xlsx]

Đặc trưng đưa vào mô hình (7 cột):
- Cột số (chuẩn hóa z-score): Age (giữa nhóm tuổi Q27), Income (giữa nhóm thu nhập Q29, triệu đồng/tháng),
  "Thái độ" = trung bình Q19–Q21 (mức đánh giá tích cực về việc đặt đồ ăn online, bài báo gọi là ATT),
  "Ý định đặt tiếp" = trung bình Q22–Q25 (bài báo gọi là INT), thang 1–7.
- Cột phân loại: Gender (Q26), Marital (Q30), Education (Q28).

Kết quả lưu trong thu_nghiem_vn/: du_lieu_vn.csv, chi_so_theo_K.csv, do_nhay_gamma.csv,
ty_le_theo_cum.csv (% từng thuộc tính trong mỗi cụm của K đề xuất), figures/*.png.
Script không đụng tới các file ở thư mục gốc.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from kmodes.kprototypes import KPrototypes
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                             silhouette_samples, silhouette_score)
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).parent
OUT = HERE / "figures"
DEFAULT_XLSX = Path(r"E:\hc\NLCS\nienluan\Dataset.xlsx")
K_RANGE = list(range(2, 9))
SEED = 42
N_INIT = 5
STABILITY_SEEDS = 10
GAMMAS = [0.25, 0.5, 1.0, 1.5]          # 0.5 = mặc định của kmodes khi cột số đã z-score
MIN_CLUSTER_SHARE = 0.05                # cụm nhỏ hơn 5% mẫu coi là không dùng được

ATT = "Thái độ"            # trung bình Q19–Q21
INT = "Ý định đặt tiếp"    # trung bình Q22–Q25
NUM_COLS = ["Age", "Income", ATT, INT]
CAT_COLS = ["Gender", "Marital", "Education"]
CAT_IDX = list(range(len(NUM_COLS), len(NUM_COLS) + len(CAT_COLS)))

LIKERT = {"Totally disagree": 1, "Disagree": 2, "More or less disagree": 3, "Neutral": 4,
          "More or less agree": 5, "Agree": 6, "Totally agree": 7}
AGE = {"15-18 years old": 16.5, "19-22 years old": 20.5, "23-25 years old": 24, "26-28 years old": 27}
GENDER = {"Female": "Nữ", "Male": "Nam"}
MARITAL = {"Single": "Độc thân", "Married": "Đã kết hôn"}
EDUCATION = {"High school or lesser": "THPT trở xuống", "Professional certificate": "Chứng chỉ nghề",
             "College diploma": "Cao đẳng", "University undergraduate degree": "Đại học",
             "Postgraduate degree": "Sau đại học"}

CLUSTER_COLORS = ["#d62828", "#2f6db5", "#2a9d8f", "#f6aa1c", "#8a6fd1", "#6c757d", "#e76f51", "#264653"]
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .3, "font.size": 10})


# ---------- Đọc và mã hóa dữ liệu ----------
def income_millions(text):
    """'< 10,000,000 VND' -> 5; '10,000,000 VND - 20,000,000 VND' -> 15; '> 40,000,000 VND' -> 45."""
    nums = [int(n.replace(",", "")) / 1e6 for n in pd.Series(text).str.findall(r"[\d,]{6,}").iloc[0]]
    if text.strip().startswith("<"):
        return nums[0] / 2
    if text.strip().startswith(">"):
        return nums[0] + 5
    return sum(nums) / 2


def load(xlsx):
    raw = pd.read_excel(xlsx)
    likert = raw[[f"Q{i}" for i in range(19, 26)]].apply(lambda s: s.map(LIKERT))
    if likert.isna().any().any():
        raise ValueError("Có câu trả lời Likert không nằm trong bảng mã LIKERT")
    df = pd.DataFrame({
        "Age": raw["Q27"].map(AGE),
        "Income": raw["Q29"].map(income_millions),
        ATT: likert[["Q19", "Q20", "Q21"]].mean(axis=1),
        INT: likert[["Q22", "Q23", "Q24", "Q25"]].mean(axis=1),
        "Gender": raw["Q26"].map(GENDER),
        "Marital": raw["Q30"].map(MARITAL),
        "Education": raw["Q28"].map(EDUCATION),
    })
    if df.isna().any().any():
        raise ValueError("Có giá trị không mã hóa được:\n" + str(df[df.isna().any(axis=1)].head()))
    return df


def prepare(df):
    z = StandardScaler().fit_transform(df[NUM_COLS])
    onehot = pd.get_dummies(df[CAT_COLS]).to_numpy(float)
    mixed = df[NUM_COLS + CAT_COLS].copy()
    mixed[NUM_COLS] = z
    p = onehot.mean(axis=0)
    famd_input = np.hstack([z, (onehot / np.sqrt(p)) - np.sqrt(p)])
    pca = PCA(n_components=2, random_state=SEED).fit(famd_input)
    return dict(mixed=mixed.to_numpy(dtype=object), numeric=np.hstack([z, onehot]), gower=gower_matrix(df),
                famd=pca.transform(famd_input), famd_var=pca.explained_variance_ratio_)


def gower_matrix(df):
    D = np.zeros((len(df), len(df)))
    for col in NUM_COLS:
        x = df[col].to_numpy(float)
        D += np.abs(x[:, None] - x[None, :]) / (x.max() - x.min())
    for col in CAT_COLS:
        x = df[col].astype("category").cat.codes.to_numpy()
        D += x[:, None] != x[None, :]
    D /= len(NUM_COLS) + len(CAT_COLS)
    np.fill_diagonal(D, 0)
    return D


# ---------- Chạy K-Prototypes và tính chỉ số ----------
def fit(X, k, gamma=None, seed=SEED, n_init=N_INIT):
    model = KPrototypes(n_clusters=k, init="Cao", n_init=n_init, gamma=gamma, random_state=seed)
    labels = model.fit_predict(X["mixed"], categorical=CAT_IDX)
    return model, labels


def scores(X, labels):
    return dict(silhouette=silhouette_score(X["gower"], labels, metric="precomputed"),
                davies_bouldin=davies_bouldin_score(X["numeric"], labels),
                calinski_harabasz=calinski_harabasz_score(X["numeric"], labels),
                min_share=np.bincount(labels).min() / len(labels))


def stability(X, k):
    """ARI trung bình giữa các lần chạy với hạt giống khác nhau: gần 1 = cụm ổn định."""
    runs = [fit(X, k, seed=s, n_init=1)[1] for s in range(STABILITY_SEEDS)]
    return np.mean([adjusted_rand_score(runs[i], runs[j])
                    for i in range(len(runs)) for j in range(i + 1, len(runs))])


def elbow_k(ks, costs):
    """Điểm khuỷu: điểm xa nhất so với đường thẳng nối đầu và cuối đường cost."""
    x = (np.array(ks) - ks[0]) / (ks[-1] - ks[0])
    y = (np.array(costs) - costs[-1]) / (costs[0] - costs[-1])
    return ks[int(np.argmax(np.abs(1 - x - y)))]


def recommend(table):
    """Chọn K: bỏ K có cụm < 5% mẫu, rồi lấy K có thứ hạng trung bình tốt nhất trên 4 chỉ số."""
    ok = table[table.min_share >= MIN_CLUSTER_SHARE].copy()
    ranks = pd.concat([ok.silhouette.rank(ascending=False), ok.davies_bouldin.rank(),
                       ok.calinski_harabasz.rank(ascending=False), ok.stability.rank(ascending=False)], axis=1)
    ok["rank_mean"] = ranks.mean(axis=1)
    return int(ok.rank_mean.idxmin()), ok.rank_mean


# ---------- Biểu đồ ----------
def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)
    print("  đã lưu", (OUT / name).relative_to(HERE.parent))


def plot_distributions(df):
    fig, axes = plt.subplots(2, 4, figsize=(17, 7.5))
    for ax, col in zip(axes[0], NUM_COLS):
        values = df[col].value_counts().sort_index()
        width = .8 if col in ("Age", "Income") else .2
        ax.bar(values.index, values.values, width=width * (5 if col == "Income" else 1),
               color="#2f6db5", alpha=.85)
        ax.set(title=f"{col}  (TB {df[col].mean():.2f}, ĐLC {df[col].std():.2f})", ylabel="Số người")
    for ax, col in zip(axes[1], CAT_COLS):
        values = df[col].value_counts()
        ax.barh(values.index[::-1], values.values[::-1], color="#d62828", alpha=.85)
        for i, v in enumerate(values.values[::-1]):
            ax.text(v + 2, i, f"{v} ({v / len(df):.0%})", va="center", fontsize=9)
        ax.set(title=col, xlabel="Số người")
        ax.grid(axis="y", visible=False)
    corr = df[NUM_COLS].corr()
    ax = axes[1, 3]
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set(xticks=range(4), yticks=range(4), yticklabels=NUM_COLS, title="Tương quan cột số")
    ax.set_xticklabels(NUM_COLS, rotation=30, ha="right")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=.8)
    fig.suptitle(f"Phân phối 7 đặc trưng đưa vào K-Prototypes (n = {len(df)})", fontweight="bold")
    fig.tight_layout()
    save(fig, "1_phan_phoi_dac_trung.png")


def plot_elbow(table, knee):
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(table.index, table.cost, "o-", color="#d62828", lw=2)
    ax.plot([table.index[0], table.index[-1]], [table.cost.iloc[0], table.cost.iloc[-1]],
            ":", color="#888", label="Đường nối đầu – cuối")
    ax.scatter([knee], [table.cost[knee]], s=220, facecolor="none", edgecolor="#333", lw=2, zorder=5,
               label=f"Điểm khuỷu K = {knee}")
    drop = -table.cost.pct_change() * 100
    for k in table.index[1:]:
        ax.annotate(f"-{drop[k]:.0f}%", (k, table.cost[k]), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.set(xlabel="Số cụm K", ylabel="Cost (tổng khoảng cách tới tâm)", xticks=table.index,
           title="Phương pháp Elbow (γ mặc định = 0.5)")
    ax.legend()
    save(fig, "2_elbow.png")


def plot_metrics(table, best):
    specs = [("silhouette", "Silhouette (Gower) ↑", True), ("davies_bouldin", "Davies–Bouldin ↓", False),
             ("calinski_harabasz", "Calinski–Harabasz ↑", True), ("stability", "Độ ổn định (ARI giữa 10 lần chạy) ↑", True)]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.2))
    for ax, (col, title, higher) in zip(axes, specs):
        ax.plot(table.index, table[col], "o-", color="#2f6db5", lw=2)
        top = table[col].idxmax() if higher else table[col].idxmin()
        ax.scatter([top], [table[col][top]], s=160, color="#f6aa1c", zorder=5, label=f"Tốt nhất: K = {top}")
        ax.axvline(best, color="#d62828", ls="--", lw=1, label=f"K đề xuất = {best}")
        ax.set(title=title, xlabel="Số cụm K", xticks=table.index)
        ax.legend(fontsize=8)
    fig.suptitle("Các chỉ số đánh giá theo K", fontweight="bold", y=1.03)
    save(fig, "3_chi_so_theo_K.png")


def plot_gamma(gamma_table, best):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    colors = ["#2a9d8f", "#d62828", "#2f6db5", "#8a6fd1"]
    for color, g in zip(colors, GAMMAS):
        part = gamma_table[gamma_table.gamma == g].set_index("k")
        label = f"γ = {g}" + (" (mặc định)" if g == 0.5 else "")
        axes[0].plot(part.index, part.silhouette, "o-", color=color, label=label)
        axes[1].plot(part.index, part.ari_vs_default, "o-", color=color, label=label)
    axes[0].set(title="Silhouette (Gower) theo K với các γ", xlabel="Số cụm K", ylabel="Silhouette")
    axes[1].set(title="Giống kết quả γ mặc định đến đâu (ARI)", xlabel="Số cụm K", ylabel="ARI", ylim=(0, 1.05))
    for ax in axes:
        ax.axvline(best, color="#888", ls="--", lw=1)
        ax.set_xticks(K_RANGE)
        ax.legend(fontsize=8)
    fig.suptitle("Độ nhạy theo trọng số γ (γ lớn: coi trọng cột phân loại hơn)", fontweight="bold", y=1.03)
    save(fig, "4_do_nhay_gamma.png")


def plot_sizes(all_labels):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for k, labels in all_labels.items():
        shares = np.sort(np.bincount(labels) / len(labels))[::-1]
        bottom = 0
        for i, s in enumerate(shares):
            ax.bar(k, s, bottom=bottom, color=CLUSTER_COLORS[i], edgecolor="white", width=.7)
            if s >= .06:
                ax.text(k, bottom + s / 2, f"{s:.0%}", ha="center", va="center", fontsize=8, color="white")
            bottom += s
        smallest = shares.min()
        ax.text(k, 1.02, f"nhỏ nhất\n{smallest:.0%}", ha="center", fontsize=8,
                color="#d62828" if smallest < MIN_CLUSTER_SHARE else "#333")
    ax.set(xlabel="Số cụm K", ylabel="Tỉ lệ khách", xticks=list(all_labels), ylim=(0, 1.15),
           title="Kích thước cụm theo K (xếp từ lớn đến nhỏ)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.grid(axis="x", visible=False)
    save(fig, "5_kich_thuoc_cum.png")


def plot_silhouettes(X, all_labels, ks):
    fig, axes = plt.subplots(1, len(ks), figsize=(5 * len(ks), 4.8), sharex=True)
    for ax, k in zip(np.atleast_1d(axes), ks):
        labels = all_labels[k]
        s = silhouette_samples(X["gower"], labels, metric="precomputed")
        y = 0
        for c in range(k):
            vals = np.sort(s[labels == c])
            ax.fill_betweenx(np.arange(y, y + len(vals)), 0, vals, color=CLUSTER_COLORS[c], alpha=.85)
            ax.text(-0.02, y + len(vals) / 2, str(c), ha="right", va="center", fontsize=9)
            y += len(vals) + 10
        ax.axvline(s.mean(), color="#333", ls="--", lw=1)
        ax.set_title(f"K = {k}\nTB = {s.mean():.3f} · điểm âm {(s < 0).mean():.0%}")
        ax.set(xlabel="Hệ số silhouette (Gower)", yticks=[])
        ax.grid(axis="y", visible=False)
    fig.suptitle("Biểu đồ silhouette từng khách cho các K ứng viên", fontweight="bold", y=1.06)
    save(fig, "6_silhouette_ung_vien.png")


def plot_profile(df, labels, k):
    rows = []
    for c in range(k):
        part = df[labels == c]
        row = {"Cụm": f"Cụm {c}\n(n={len(part)})"}
        row.update({col: part[col].mean() for col in NUM_COLS})
        row["% Nữ"] = (part.Gender == "Nữ").mean() * 100
        row["% Đã kết hôn"] = (part.Marital == "Đã kết hôn").mean() * 100
        row["% ĐH trở lên"] = part.Education.isin(["Đại học", "Sau đại học"]).mean() * 100
        rows.append(row)
    prof = pd.DataFrame(rows).set_index("Cụm")
    z = (prof - prof.mean()) / prof.std().replace(0, 1)
    fig, ax = plt.subplots(figsize=(11, 1.0 + .75 * k))
    ax.imshow(z, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set(xticks=range(prof.shape[1]), yticks=range(k), xticklabels=prof.columns, yticklabels=prof.index)
    for i in range(k):
        for j, col in enumerate(prof.columns):
            v = prof.iloc[i, j]
            text = f"{v:.0f}%" if col.startswith("%") else (f"{v:.1f}" if col in ("Age", "Income") else f"{v:.2f}")
            ax.text(j, i, text, ha="center", va="center", fontsize=9)
    ax.grid(False)
    ax.set_title(f"Hồ sơ từng cụm với K = {k} (màu: cao/thấp so với các cụm khác; Income tính triệu đồng)",
                 fontweight="bold")
    save(fig, "7_ho_so_cum.png")
    return prof


AGE_GROUP = {16.5: "15–18", 20.5: "19–22", 24: "23–25", 27: "26–28"}
INCOME_GROUP = {5: "< 10tr", 15: "10–20tr", 25: "20–30tr", 35: "30–40tr", 45: "> 40tr"}
LEVELS = ["Thấp (<4)", "Trung bình (4–5)", "Cao (>5)"]
EDU_ORDER = ["THPT trở xuống", "Chứng chỉ nghề", "Cao đẳng", "Đại học", "Sau đại học"]


def percent_by_cluster(df, labels, k):
    """Tỉ lệ % từng giá trị của mỗi thuộc tính trong từng cụm (mỗi cụm cộng lại 100%).
    Tuổi/thu nhập gom lại theo nhóm gốc của khảo sát; Thái độ / Ý định đặt tiếp chia 3 mức theo ngưỡng 4 và 5."""
    level = lambda s: pd.cut(s, [0, 3.999, 5, 7], labels=LEVELS)
    attrs = {
        "Nhóm tuổi": (df.Age.map(AGE_GROUP), list(AGE_GROUP.values())),
        "Thu nhập": (df.Income.map(INCOME_GROUP), list(INCOME_GROUP.values())),
        "Giới tính": (df.Gender, ["Nam", "Nữ"]),
        "Hôn nhân": (df.Marital, ["Độc thân", "Đã kết hôn"]),
        "Học vấn": (df.Education, EDU_ORDER),
        ATT: (level(df[ATT]), LEVELS),
        INT: (level(df[INT]), LEVELS),
    }
    columns = [f"Cụm {c}" for c in range(k)] + ["Toàn bộ"]
    tables = {}
    for name, (values, order) in attrs.items():
        t = pd.crosstab(values, pd.Series(labels, index=df.index), normalize="columns") * 100
        t.columns = columns[:-1]
        t["Toàn bộ"] = values.value_counts(normalize=True) * 100
        tables[name] = t.reindex(order).fillna(0)
    long = pd.concat(tables, names=["Thuộc tính", "Giá trị"]).round(1)
    long.to_csv(HERE / "ty_le_theo_cum.csv", encoding="utf-8-sig")
    print("  đã lưu", (HERE / "ty_le_theo_cum.csv").relative_to(HERE.parent))
    return tables, labels


def plot_percent(tables, labels, k):
    sizes = np.bincount(labels)
    xlabels = [f"Cụm {c}\n(n={sizes[c]})" for c in range(k)] + [f"Toàn bộ\n(n={len(labels)})"]
    palette = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]
    fig, axes = plt.subplots(2, 4, figsize=(19, 9))
    for ax, (name, t) in zip(axes.flat, tables.items()):
        colors = palette[:len(t)] if len(t) > 3 else (["#2f6db5", "#d62828"] if len(t) == 2
                                                       else ["#e76f51", "#e9c46a", "#2a9d8f"])
        bottom = np.zeros(t.shape[1])
        for color, (value, row) in zip(colors, t.iterrows()):
            ax.bar(range(t.shape[1]), row.values, bottom=bottom, color=color, edgecolor="white",
                   width=.72, label=value)
            for x, (v, b) in enumerate(zip(row.values, bottom)):
                if v >= 6:
                    ax.text(x, b + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                            color="white" if color in ("#264653", "#2a9d8f", "#2f6db5", "#d62828", "#e76f51") else "#222")
            bottom += row.values
        ax.axvline(k - .5, color="#999", lw=1, ls=":")
        ax.set(title=name, xticks=range(t.shape[1]), ylim=(0, 100))
        ax.set_xticklabels(xlabels, fontsize=8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(100))
        ax.grid(axis="x", visible=False)
        ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1, 1), frameon=False)
    axes.flat[-1].axis("off")
    fig.suptitle(f"Tỉ lệ % từng thuộc tính trong mỗi cụm (K = {k})", fontweight="bold", fontsize=13)
    fig.tight_layout()
    save(fig, "9_ty_le_theo_cum.png")


def plot_famd(X, labels, k):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for c in range(k):
        pts = X["famd"][labels == c]
        ax.scatter(pts[:, 0], pts[:, 1], s=16, alpha=.7, color=CLUSTER_COLORS[c], label=f"Cụm {c} ({len(pts)})")
    v = X["famd_var"]
    ax.set(xlabel=f"Thành phần 1 ({v[0]:.0%})", ylabel=f"Thành phần 2 ({v[1]:.0%})",
           title=f"Chiếu 2 chiều kiểu FAMD, K = {k}")
    ax.legend(fontsize=8)
    save(fig, "8_famd.png")


def main():
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    df = load(xlsx)
    df.to_csv(HERE / "du_lieu_vn.csv", index=False, encoding="utf-8-sig")
    X = prepare(df)
    print(f"Đọc {len(df)} dòng từ {xlsx}")

    rows, all_labels = [], {}
    for k in K_RANGE:
        model, labels = fit(X, k)
        all_labels[k] = labels
        rows.append(dict(k=k, cost=model.cost_, **scores(X, labels), stability=stability(X, k)))
        print(f"  K={k}: cost={model.cost_:.1f} silhouette={rows[-1]['silhouette']:.3f} "
              f"ổn định={rows[-1]['stability']:.2f} cụm nhỏ nhất={rows[-1]['min_share']:.1%}")
    table = pd.DataFrame(rows).set_index("k")

    gamma_rows = []
    for g in GAMMAS:
        for k in K_RANGE:
            labels = all_labels[k] if g == 0.5 else fit(X, k, gamma=g)[1]
            gamma_rows.append(dict(gamma=g, k=k, silhouette=silhouette_score(X["gower"], labels, metric="precomputed"),
                                   ari_vs_default=adjusted_rand_score(all_labels[k], labels)))
    gamma_table = pd.DataFrame(gamma_rows)

    knee = elbow_k(K_RANGE, table.cost.tolist())
    best, rank_mean = recommend(table)
    table["rank_mean"] = rank_mean
    table["elbow"] = table.index == knee
    table.round(4).to_csv(HERE / "chi_so_theo_K.csv", encoding="utf-8-sig")
    gamma_table.round(4).to_csv(HERE / "do_nhay_gamma.csv", index=False, encoding="utf-8-sig")

    print("\nVẽ biểu đồ:")
    plot_distributions(df)
    plot_elbow(table, knee)
    plot_metrics(table, best)
    plot_gamma(gamma_table, best)
    plot_sizes(all_labels)
    candidates = sorted({max(2, best - 1), best, min(K_RANGE[-1], best + 1)})
    plot_silhouettes(X, all_labels, candidates)
    prof = plot_profile(df, all_labels[best], best)
    plot_famd(X, all_labels[best], best)
    tables, _ = percent_by_cluster(df, all_labels[best], best)
    plot_percent(tables, all_labels[best], best)

    print("\nBảng chỉ số:\n", table.round(3).to_string())
    print(f"\nĐiểm khuỷu Elbow: K = {knee}. K đề xuất (thứ hạng trung bình, cụm ≥ 5%): K = {best}")
    print("\nHồ sơ cụm:\n", prof.round(2).to_string())


if __name__ == "__main__":
    main()
