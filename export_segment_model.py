"""Xuất mô hình phân khúc ra JSON để chương trình khác (web PHP) tự xếp khách vào cụm.

Xếp cụm của K-Prototypes chỉ cần: tham số chuẩn hóa, gamma và 4 tâm cụm.
Khoảng cách từ khách x đến tâm c (giống kmodes.KPrototypes.predict):
    d = sum((x_num_chuẩn_hóa - c_num)^2) + gamma * (số thuộc tính phân loại khác c_cat)
Khách thuộc cụm có d nhỏ nhất (bằng nhau thì lấy cụm có chỉ số nhỏ hơn).

Kèm theo là file test: toàn bộ khách trong dữ liệu và cụm mà Python dự đoán,
để bên dùng JSON kiểm tra cho ra đúng kết quả.

Chạy: python export_segment_model.py [thư_mục_đích]
"""
import json
import sys
from datetime import date
from pathlib import Path

import segmentation as seg


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    model = seg.train()
    kp = model.kp
    num_centroids, cat_centroids = kp.cluster_centroids_[:, :len(seg.NUM_COLS)], \
        kp.cluster_centroids_[:, len(seg.NUM_COLS):]

    data = {
        "source": seg.DATA_FILE.name,
        "exported": date.today().isoformat(),
        "num_cols": seg.NUM_COLS,
        "cat_cols": seg.CAT_COLS,
        "scaler": {"mean": model.scaler.mean_.tolist(), "scale": model.scaler.scale_.tolist()},
        "gamma": float(kp.gamma),
        "categories": {c: seg.CATEGORY_ORDER[c] for c in seg.CAT_COLS},
        "centroids": [
            {
                "cluster": k,
                "segment": model.segment_names[k],
                "num": [float(v) for v in num_centroids[k]],
                "cat": [str(v) for v in cat_centroids[k]],
            }
            for k in range(seg.K)
        ],
    }
    (out_dir / "segment_model.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    customers = model.customers
    cases = customers[seg.NUM_COLS + seg.CAT_COLS].copy()
    cases["Segment"] = seg.predict(model, customers)
    cases.to_csv(out_dir / "segment_testcases.csv", index=False)

    print(f"Đã xuất segment_model.json và segment_testcases.csv ({len(cases)} khách) vào {out_dir}")


if __name__ == "__main__":
    main()
