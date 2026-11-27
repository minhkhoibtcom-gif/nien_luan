"""Mở rộng bộ dữ liệu gốc lên TARGET mẫu (sau khi làm sạch, mặc định 3000) bằng dữ liệu tổng hợp.

Cách sinh: lấy ngẫu nhiên một khách hàng có thật trong dữ liệu gốc làm "mẫu gốc",
rồi tạo khách hàng mới gần giống mẫu đó:
- Age lệch ngẫu nhiên -2..+2 tuổi, Family size lệch ±1 với xác suất 30%
  (giới hạn trong khoảng giá trị của dữ liệu gốc).
- Mỗi thuộc tính phân loại có xác suất 5% được thay bằng giá trị của một khách
  khác cùng Occupation, để giữ quan hệ giữa các thuộc tính.
- Customer Type tính lại từ Family size theo đúng quy tắc của dữ liệu gốc.
- Vị trí (latitude, longitude, Pin code) lấy theo một khách cùng Pin code ngẫu nhiên.
Mẫu mới trùng hoàn toàn với mẫu đã có sẽ bị bỏ, nên sau bước drop_duplicates
trong segmentation.load_customers còn đúng TARGET mẫu.

Toàn bộ 388 dòng gốc được giữ nguyên ở đầu file kết quả.
Chạy lại: python generate_dataset.py [số_mẫu]  -> "online food delivery dataset <số_mẫu>.csv"
Seed cố định nên kết quả không đổi; các mẫu tổng hợp sinh theo cùng một thứ tự, nên bộ nhỏ
(ví dụ 1000) là phần đầu của bộ lớn (ví dụ 3000).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
SOURCE = HERE / "online food delivery dataset.csv"
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
OUTPUT = HERE / f"online food delivery dataset {TARGET}.csv"
SEED = 42

CAT_SWAP = ["Gender", "Marital Status", "Monthly Income", "Educational Qualifications",
            "Output", "Feedback"]


def customer_type(family_size):
    """Quy tắc có sẵn trong dữ liệu gốc: 1 người là New, 2-3 là Regular, từ 4 là Frequent."""
    return "New" if family_size == 1 else "Regular" if family_size <= 3 else "Frequent"


def _key(row):
    """Khóa so trùng giống cách làm sạch: bỏ khoảng trắng thừa."""
    return tuple(str(v).strip() for v in row)


def main():
    raw = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
    cols = list(raw.columns)
    rng = np.random.default_rng(SEED)

    clean = raw.apply(lambda c: c.str.strip())
    unique = clean.drop_duplicates().reset_index(drop=True)
    seen = {_key(r) for r in clean.itertuples(index=False)}
    need = TARGET - len(seen)

    ages = unique["Age"].astype(int)
    sizes = unique["Family size"].astype(int)
    age_lo, age_hi = ages.min(), ages.max()
    size_lo, size_hi = sizes.min(), sizes.max()
    location = unique[["Pin code", "latitude", "longitude"]].drop_duplicates("Pin code")
    by_occupation = {occ: g for occ, g in unique.groupby("Occupation")}

    new_rows = []
    while len(new_rows) < need:
        base = unique.iloc[rng.integers(len(unique))].copy()

        base["Age"] = str(int(np.clip(int(base["Age"]) + rng.integers(-2, 3), age_lo, age_hi)))
        if rng.random() < 0.3:
            size = int(base["Family size"]) + rng.choice([-1, 1])
            base["Family size"] = str(int(np.clip(size, size_lo, size_hi)))

        peers = by_occupation[base["Occupation"]]
        for col in CAT_SWAP:
            if rng.random() < 0.05:
                base[col] = peers.iloc[rng.integers(len(peers))][col]

        base["Customer Type"] = customer_type(int(base["Family size"]))

        loc = location.iloc[rng.integers(len(location))]
        base[["Pin code", "latitude", "longitude"]] = loc[["Pin code", "latitude", "longitude"]]

        key = _key(base[cols])
        if key in seen:
            continue
        seen.add(key)
        new_rows.append(base[cols])

    out = pd.concat([raw, pd.DataFrame(new_rows, columns=cols)], ignore_index=True)
    out.columns = ["" if c.startswith("Unnamed") else c for c in cols]  # giữ header trống như file gốc
    out.to_csv(OUTPUT, index=False)
    print(f"Gốc: {len(raw)} dòng ({len(unique)} không trùng), "
          f"thêm {len(new_rows)} dòng tổng hợp -> {len(out)} dòng, "
          f"{len(seen)} mẫu sau làm sạch. Đã lưu {OUTPUT.name}")


if __name__ == "__main__":
    main()
