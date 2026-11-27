"""Sinh đơn hàng MÔ PHỎNG cho một tháng, làm dữ liệu tạo combo khi app chưa có đủ đơn thật.

Khách lấy từ dataset Gen Z Việt Nam đã phân cụm (361 người, segmentation.train). Mỗi cụm có thói quen riêng
theo ngày thường (T2-T6) và cuối tuần (T7-CN):
- tỷ lệ đơn cuối tuần, khung giờ đặt;
- số người ăn trong một đơn (phân bố riêng của cụm: sinh viên 1–2 người, người đi làm 2–4 người, khách
  trung thành 1–3 người, cuối tuần đông hơn), vì dataset không có số người trong hộ;
- món chính / món thêm / nước / tráng miệng hay chọn (trọng số) và xác suất gọi kèm.
Khách có Ý định đặt tiếp cao hơn được cho đặt nhiều đơn hơn.

Kết quả: simulated_orders.csv, mỗi dòng là một món trong một đơn. Đây là dữ liệu giả lập để minh họa,
không phải đơn hàng thật; app ghi rõ nguồn khi dùng.
Chạy: python simulate_orders.py [số_đơn=10000] [tháng=YYYY-MM, mặc định tháng trước]
"""
import calendar
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import segmentation as seg

OUTPUT = Path(__file__).parent / "simulated_orders.csv"
SEED = 42

# Thói quen của từng cụm. main/side/drink/dessert: {mã món: trọng số}; *_rate: xác suất mỗi người gọi kèm.
# sizes: {số người trong đơn: trọng số}. hours: khung giờ (giờ bắt đầu, giờ kết thúc).
PATTERNS = {
    "Sinh viên thu nhập thấp": {
        "weekend_share": 0.35,
        "weekday": dict(sizes={1: 6, 2: 3, 3: 1}, hours=[(11, 13), (18, 22)],
                        main={"C03": 5, "B01": 4, "M01": 3, "G01": 2, "C01": 1},
                        side={"P01": 3, "P03": 1}, side_rate=0.30,
                        drink={"N01": 4, "N05": 2, "N09": 1}, drink_rate=0.85,
                        dessert={"T06": 2, "T05": 1, "T01": 1}, dessert_rate=0.15),
        "weekend": dict(sizes={1: 2, 2: 4, 3: 3}, hours=[(17, 23)],
                        main={"B01": 3, "G02": 2, "G01": 3, "M01": 3, "C03": 2},
                        side={"P02": 2, "P01": 2, "P03": 2}, side_rate=0.55,
                        drink={"N01": 3, "N03": 2, "N05": 1}, drink_rate=0.90,
                        dessert={"T03": 2, "T06": 2, "T01": 2}, dessert_rate=0.30),
    },
    "Người đi làm thu nhập khá": {
        "weekend_share": 0.55,
        "weekday": dict(sizes={1: 2, 2: 4, 3: 3, 4: 2}, hours=[(11, 13), (17, 20)],
                        main={"C01": 4, "C02": 3, "M01": 2, "G01": 2, "M03": 1},
                        side={"P05": 3, "P01": 2}, side_rate=0.45,
                        drink={"N05": 3, "N01": 2, "N06": 2, "N09": 1}, drink_rate=0.85,
                        dessert={"T06": 2, "T02": 1, "T01": 1}, dessert_rate=0.35),
        "weekend": dict(sizes={2: 3, 3: 4, 4: 4}, hours=[(17, 21)],
                        main={"G02": 4, "M01": 3, "G11": 2, "G01": 2, "C01": 1},
                        side={"P02": 3, "P04": 2, "P05": 1}, side_rate=0.45,
                        drink={"N01": 3, "N02": 2, "N07": 2}, drink_rate=0.85,
                        dessert={"T06": 4, "T02": 2, "T05": 1}, dessert_rate=0.60),
    },
    "Khách trung thành": {
        "weekend_share": 0.40,
        "weekday": dict(sizes={1: 5, 2: 4, 3: 1}, hours=[(11, 13), (18, 21)],
                        main={"C01": 3, "G01": 3, "M03": 2, "B02": 2, "C02": 1},
                        side={"P05": 3, "P01": 2, "P03": 1}, side_rate=0.55,
                        drink={"N05": 3, "N04": 2, "N07": 2}, drink_rate=0.90,
                        dessert={"T03": 2, "T01": 2, "T04": 1}, dessert_rate=0.45),
        "weekend": dict(sizes={1: 1, 2: 4, 3: 4}, hours=[(17, 22)],
                        main={"G02": 4, "M03": 3, "G12": 2, "B02": 1},
                        side={"P03": 3, "P04": 2}, side_rate=0.60,
                        drink={"N02": 3, "N04": 2, "N07": 2}, drink_rate=0.90,
                        dessert={"T04": 3, "T02": 2, "T01": 1}, dessert_rate=0.55),
    },
}


def previous_month(today=None):
    first = (today or date.today()).replace(day=1)
    return (first - timedelta(days=1)).strftime("%Y-%m")


def _pick(rng, weights, n):
    codes = list(weights)
    p = np.array([weights[c] for c in codes], dtype=float)
    return rng.choice(codes, size=n, p=p / p.sum()) if n > 0 else []


def simulate(n_orders, month, seed=SEED):
    rng = np.random.default_rng(seed)
    customers = seg.train().customers.reset_index(drop=True)
    weight = customers[seg.INT] - 2   # ý định đặt tiếp 3..7 -> trọng số 1..5
    picks = rng.choice(len(customers), size=n_orders, p=(weight / weight.sum()).to_numpy())

    year, mon = map(int, month.split("-"))
    days = [date(year, mon, d) for d in range(1, calendar.monthrange(year, mon)[1] + 1)]
    by_type = {"weekday": [d for d in days if d.weekday() < 5], "weekend": [d for d in days if d.weekday() >= 5]}

    rows = []
    for i, idx in enumerate(picks, start=1):
        c = customers.iloc[idx]
        segment = str(c["Segment"])
        pat = PATTERNS[segment]
        day_type = "weekend" if rng.random() < pat["weekend_share"] else "weekday"
        p = pat[day_type]
        sizes = list(p["sizes"])
        weights = np.array(list(p["sizes"].values()), dtype=float)
        people = int(rng.choice(sizes, p=weights / weights.sum()))

        d = by_type[day_type][rng.integers(len(by_type[day_type]))]
        start, end = p["hours"][rng.integers(len(p["hours"]))]
        created = datetime(d.year, d.month, d.day, int(rng.integers(start, end)), int(rng.integers(60)))

        items = {}
        for code in _pick(rng, p["main"], people):
            items[code] = items.get(code, 0) + 1
        for key, rate in (("side", "side_rate"), ("drink", "drink_rate"), ("dessert", "dessert_rate")):
            for code in _pick(rng, p[key], int(rng.binomial(people, p[rate]))):
                items[code] = items.get(code, 0) + 1
        for code, qty in items.items():
            rows.append({"order_id": f"S{i:06d}", "customer": int(idx), "segment": segment,
                         "party_size": people, "created_at": created.isoformat(" "),
                         "day_type": day_type, "item_id": code, "quantity": qty})
    return pd.DataFrame(rows)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    month = sys.argv[2] if len(sys.argv) > 2 else previous_month()
    df = simulate(n, month)
    df.to_csv(OUTPUT, index=False, encoding="utf-8")
    orders = df.drop_duplicates("order_id")
    print(f"Đã sinh {orders.shape[0]} đơn ({len(df)} dòng món) tháng {month} -> {OUTPUT.name}")
    print(pd.crosstab(orders["segment"], orders["day_type"]).to_string())


if __name__ == "__main__":
    main()
