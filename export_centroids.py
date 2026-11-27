"""Ghi tâm cụm qua từng vòng lặp của K-Prototypes ra file txt.

Thư viện kmodes không lưu tâm cụm của từng vòng, nên script bọc hai hàm nội bộ
(_k_prototypes_single, _k_prototypes_iter) để chụp lại tâm cụm sau mỗi vòng,
rồi huấn luyện đúng như segmentation.train (cùng dữ liệu, cùng tham số).

Chạy: python export_centroids.py  -> centroids_iterations.txt
"""
import copy
from pathlib import Path

import numpy as np
from kmodes import kprototypes as kp_module
from kmodes.util import decode_centroids

import segmentation as seg

OUTPUT = Path(__file__).parent / "centroids_iterations.txt"

runs = []  # mỗi phần tử: {"snapshots": [(vòng, tâm số, tâm phân loại, cỡ cụm, moves)], ...}

_orig_single = kp_module._k_prototypes_single
_orig_iter = kp_module._k_prototypes_iter


def _single(*args, **kwargs):
    runs.append({"snapshots": []})
    result = _orig_single(*args, **kwargs)
    runs[-1]["epoch_costs"] = result[4]
    return result


def _iter(Xnum, Xcat, centroids, cl_attr_sum, cl_memb_sum, cl_attr_freq, membship, *rest):
    snaps = runs[-1]["snapshots"]
    if not snaps:  # tâm ban đầu (sau bước khởi tạo Cao), trước vòng 1
        snaps.append((0, copy.deepcopy(centroids[0]), copy.deepcopy(centroids[1]),
                      membship.sum(axis=1).astype(int), None))
    out = _orig_iter(Xnum, Xcat, centroids, cl_attr_sum, cl_memb_sum, cl_attr_freq,
                     membship, *rest)
    new_centroids, membship, moves = out[0], out[4], out[5]
    snaps.append((len(snaps), copy.deepcopy(new_centroids[0]), copy.deepcopy(new_centroids[1]),
                  membship.sum(axis=1).astype(int), moves))
    return out


def main():
    kp_module._k_prototypes_single = _single
    kp_module._k_prototypes_iter = _iter
    try:
        model = seg.train()
    finally:
        kp_module._k_prototypes_single = _orig_single
        kp_module._k_prototypes_iter = _orig_iter

    kp = model.kp
    costs = [r["epoch_costs"][-1] for r in runs]
    best = int(np.argmin(costs))

    lines = [
        "TÂM CỤM QUA TỪNG VÒNG LẶP CỦA K-PROTOTYPES",
        f"Dữ liệu: {seg.DATA_FILE.name} ({len(model.customers)} mẫu)",
        f"Tham số: K = {seg.K}, init = 'Cao', n_init = {len(runs)}, random_state = 42, "
        f"gamma = {kp.gamma:.3f}",
        f"Biến số ({', '.join(seg.NUM_COLS)}) được chuẩn hóa khi huấn luyện; bảng dưới ghi giá trị "
        "ở thang đo gốc, kèm giá trị chuẩn hóa trong ngoặc.",
        "Vòng 0 là tâm ban đầu sau bước khởi tạo. moves = số điểm đổi cụm trong vòng đó; "
        "thuật toán dừng khi moves = 0 hoặc cost không giảm.",
        f"Lần chạy được chọn: lần {best + 1} (cost thấp nhất = {costs[best]:.1f}, "
        f"{kp.n_iter_} vòng lặp).",
        "",
    ]

    for r_idx, run in enumerate(runs):
        chosen = r_idx == best
        title = f"LẦN CHẠY {r_idx + 1}/{len(runs)}" + ("  <== ĐƯỢC CHỌN" if chosen else "")
        n_iter = len(run["snapshots"]) - 1
        lines += ["=" * 100, f"{title}   |   số vòng lặp = {n_iter}   |   "
                  f"cost cuối = {run['epoch_costs'][-1]:.1f}", "=" * 100]

        for itr, num, cat, sizes, moves in run["snapshots"]:
            cost = run["epoch_costs"][itr]
            head = "Vòng 0 (khởi tạo)" if itr == 0 else f"Vòng {itr}"
            if moves is not None:
                head += f"   moves = {moves}"
            lines += ["", f"{head}   cost = {cost:.1f}"]

            num_orig = model.scaler.inverse_transform(num)
            cat_dec = decode_centroids(cat, kp._enc_map)
            header = ["Cụm", "Số khách", *seg.NUM_COLS, *seg.CAT_COLS]
            rows = []
            for k in range(len(num)):
                label = str(k)
                if chosen:
                    label += f" ({model.segment_names[k]})"
                rows.append([label, str(sizes[k]),
                             *[f"{num_orig[k, j]:.2f} ({num[k, j]:+.3f})"
                               for j in range(num.shape[1])],
                             *[str(v) for v in cat_dec[k]]])
            widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(header)]
            fmt = lambda cells: "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()
            lines += [fmt(header), fmt(["-" * w for w in widths]), *map(fmt, rows)]
        lines.append("")

    # Kiểm tra: tâm ở vòng cuối của lần được chọn phải trùng với mô hình đã huấn luyện.
    last = runs[best]["snapshots"][-1]
    assert np.allclose(last[1], kp._enc_cluster_centroids[0])
    assert np.array_equal(last[2], kp._enc_cluster_centroids[1])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã lưu {OUTPUT.name}: {len(runs)} lần chạy, số vòng lặp mỗi lần = "
          f"{[len(r['snapshots']) - 1 for r in runs]}, lần được chọn = {best + 1}")


if __name__ == "__main__":
    main()
