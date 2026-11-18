"""Sinh đơn hàng MÔ PHỎNG cho một tháng, làm dữ liệu tạo combo khi app chưa có đủ đơn thật.

Khách lấy từ bộ dữ liệu đã phân cụm (3000 mẫu, segmentation.train). Mỗi cụm có thói quen riêng
theo ngày thường (T2-T6) và cuối tuần (T7-CN):
- tỷ lệ đơn cuối tuần, khung giờ đặt;
- số người ăn trong một đơn (dựa trên số người trong hộ của khách);
- món chính / món phụ / nước / tráng miệng hay chọn (trọng số) và xác suất gọi kèm.
Khách có Output = Yes (tiếp tục đặt món) và Feedback = Positive được cho đặt nhiều đơn hơn.

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
# share: xác suất mỗi thành viên khác trong hộ cùng ăn trong đơn đó. hours: khung giờ (giờ bắt đầu, giờ kết thúc).
PATTERNS = {
    "Sinh viên hộ nhỏ": {
        "weekend_share": 0.35,
        "weekday": dict(share=0.10, hours=[(11, 13), (18, 22)],
                        main={"C03": 5, "B01": 4, "M01": 3, "G01": 2, "C01": 1},
                        side={"P01": 3, "P03": 1}, side_rate=0.30,
                        drink={"N01": 4, "N05": 2, "N09": 1}, drink_rate=0.85,
                        dessert={"T06": 2, "T05": 1, "T01": 1}, dessert_rate=0.15),
        "weekend": dict(share=0.35, hours=[(17, 23)],
                        main={"B01": 3, "G02": 2, "G01": 3, "M01": 3, "C03": 2},
                        side={"P02": 2, "P01": 2, "P03": 2}, side_rate=0.55,
                        drink={"N01": 3, "N03": 2, "N05": 1}, drink_rate=0.90,
                        dessert={"T03": 2, "T06": 2, "T01": 2}, dessert_rate=0.30),
    },
    "Sinh viên hộ đông": {
        "weekend_share": 0.55,
        "weekday": dict(share=0.30, hours=[(11, 13), (18, 22)],
                        main={"B01": 3, "M01": 3, "G01": 3, "C03": 2, "C01": 1},
                        side={"P01": 2, "P03": 2}, side_rate=0.35,
                        drink={"N01": 4, "N03": 2, "N04": 1}, drink_rate=0.85,
                        dessert={"T01": 2, "T06": 1}, dessert_rate=0.15),
        "weekend": dict(share=0.75, hours=[(17, 22)],
                        main={"G02": 4, "M01": 3, "G01": 2, "G12": 1, "B01": 1},
                        side={"P03": 3, "P02": 2}, side_rate=0.45,
                        drink={"N01": 5, "N03": 1, "N04": 1}, drink_rate=0.95,
                        dessert={"T01": 3, "T03": 1}, dessert_rate=0.25),
    },
    "Người đi làm trẻ": {
        "weekend_share": 0.30,
        "weekday": dict(share=0.10, hours=[(11, 13)],
                        main={"C01": 4, "C02": 3, "M02": 1, "B02": 1},
                        side={"P05": 4, "P01": 1}, side_rate=0.55,
                        drink={"N05": 3, "N06": 2, "N09": 1}, drink_rate=0.90,
                        dessert={"T01": 1}, dessert_rate=0.10),
        "weekend": dict(share=0.60, hours=[(18, 21)],
                        main={"G11": 3, "M03": 3, "G01": 1, "B02": 1},
                        side={"P04": 3, "P02": 1}, side_rate=0.50,
                        drink={"N07": 3, "N06": 1, "N05": 1}, drink_rate=0.90,
                        dessert={"T02": 3, "T04": 1}, dessert_rate=0.45),
    },
    "Người có gia đình hộ đông": {
        "weekend_share": 0.65,
        "weekday": dict(share=0.45, hours=[(17, 20)],
                        main={"C01": 3, "M01": 3, "G01": 3, "C03": 2},
                        side={"P01": 2, "P05": 2}, side_rate=0.35,
                        drink={"N01": 3, "N09": 2, "N06": 1}, drink_rate=0.75,
                        dessert={"T06": 3, "T05": 1}, dessert_rate=0.40),
        "weekend": dict(share=0.85, hours=[(17, 20)],
                        main={"G02": 4, "M01": 3, "G01": 2, "C01": 1},
                        side={"P02": 3, "P05": 1}, side_rate=0.40,
                        drink={"N01": 3, "N02": 2, "N09": 1}, drink_rate=0.85,
                        dessert={"T06": 4, "T05": 1}, dessert_rate=0.70),
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
    weight = 1 + 0.8 * (customers["Output"] == "Yes") + 0.3 * (customers["Feedback"] == "Positive")
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
        family = int(c["Family size"])
        people = 1 + int(rng.binomial(family - 1, p["share"])) if family > 1 else 1

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
                         "family_size": family, "created_at": created.isoformat(" "),
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
