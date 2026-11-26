"""Giao diện cửa hàng đồ ăn nhanh FASTBITE (tên giả định của đồ án): tông đỏ - vàng, thanh trên cùng có logo,
banner, thẻ món, thẻ combo, chân trang. Bố cục theo web bán sữa La Che Fresca (đồ án CT275).

Các khối Streamlit được đặt key (st.container(key=...)) để CSS nhắm đúng lớp .st-key-<key>.
"""
import base64
import html
import mimetypes
from datetime import date
from pathlib import Path

import streamlit as st

import combos
from menu import CATEGORY_ICON, GROUP_ICON, MENU_SOURCE, combo_lines, image_path, list_price

ASSETS = Path(__file__).parent / "assets"
LOGO = ASSETS / "logo.png"
SITE_NAME = "FASTBITE"
SLOGAN = "Đồ ăn nhanh ngon, giao nhanh cho mọi nhà."

# Bảng màu (khớp .streamlit/config.toml)
RED = "#d62828"
RED_DARK = "#9d0208"
YELLOW = "#f6aa1c"
CREAM = "#fff3e0"
INK = "#2b2d42"

CSS = f"""
<style>
/* Ẩn thanh header mặc định của Streamlit (vẽ đè một đường kẻ ngang lên thanh menu) */
header[data-testid="stHeader"], [data-testid="stDecoration"] {{ display: none; }}
.block-container {{ padding-top: 1.5rem; max-width: 1200px; }}
/* Ẩn dòng "Press Enter to submit form" và bộ đếm ký tự dưới ô nhập */
[data-testid="InputInstructions"] {{ display: none !important; }}

/* Thanh trên cùng: container xếp ngang, các nhóm tự giãn đều, chữ không bị cắt */
.st-key-navbar {{
  background: linear-gradient(135deg, #fff8ec 0%, {CREAM} 50%, #ffffff 100%);
  border: 1px solid rgba(214, 40, 40, .15); border-radius: 14px; padding: .55rem 1rem;
}}
.st-key-navbar [data-testid="stPageLink"] a {{ font-weight: 600; white-space: nowrap; }}
.st-key-navbar [data-testid="stPageLink"] a p {{ color: {INK}; white-space: nowrap; }}
.st-key-navbar [data-testid="stPageLink"] a:hover p {{ color: {RED}; }}
.st-key-navbar [data-testid="stMarkdownContainer"] p {{ margin: 0; }}
/* Logo + tên cửa hàng là một nút: bấm vào về trang chủ */
.st-key-brand button {{
  background: url("{{logo}}") left center / 40px 40px no-repeat !important;
  padding: 0 0 0 52px !important; min-height: 40px; border: none !important; box-shadow: none !important;
}}
.st-key-brand button p {{ color: {RED} !important; font-size: 1.35rem !important; font-weight: 800; letter-spacing: .5px; }}
.st-key-brand button:hover p {{ color: {RED_DARK} !important; }}
.lcf-brand-row {{ display: flex; align-items: center; gap: .6rem; }}
.lcf-brand-row img {{ width: 40px; height: 40px; border-radius: 10px; object-fit: cover; }}
.lcf-brand {{ color: {RED}; font-size: 1.35rem; font-weight: 800; line-height: 1; white-space: nowrap; letter-spacing: .5px; }}
.lcf-hello {{ font-weight: 600; color: {INK}; white-space: nowrap; }}

/* Banner */
.st-key-hero, .lcf-hero {{
  background: linear-gradient(135deg, #fff1e6 0%, #ffffff 55%, #fff6d6 100%);
  border-radius: 14px; padding: 1.8rem 2rem;
}}
.lcf-hero h1, .st-key-hero h1 {{ color: {RED_DARK}; font-weight: 800; margin: .5rem 0; padding: 0; }}
.lcf-hero p {{ margin: 0; color: {INK}; }}
.lcf-badge {{
  display: inline-block; background: {CREAM}; color: {RED_DARK};
  border-radius: 999px; padding: .25rem .8rem; font-size: .8rem; font-weight: 600; margin-right: .35rem;
}}
.lcf-lead {{ font-size: 1.15rem; color: {INK}; margin-bottom: 1rem; }}
.lcf-hero-art {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; justify-items: center; }}
.lcf-hero-art span {{ font-size: 4.2rem; width: 6.5rem; height: 6.5rem; display: flex; align-items: center;
  justify-content: center; background: #fff; border-radius: 50%; box-shadow: 0 .5rem 1rem rgba(214, 40, 40, .15); }}

/* Thẻ: trắng, không viền, đổ bóng, bo góc */
div[data-testid="stMetric"], div[data-testid="stForm"], .st-key-card, .st-key-auth_card,
.st-key-profile_card, .st-key-segment_card {{
  background: #fff; border: none !important; border-radius: 12px;
  box-shadow: 0 .125rem .5rem rgba(0, 0, 0, .08); padding: 1rem 1.2rem;
}}
div[data-testid="stMetricValue"] {{ color: {RED_DARK}; }}

.lcf-section-title {{ text-align: center; font-weight: 800; font-size: 1.8rem; color: {INK}; margin: 2rem 0 1rem; }}
.lcf-section-soft {{ background: {CREAM}; border-radius: 14px; padding: 1rem 1.2rem; margin: .5rem 0 1rem; }}

/* Nhóm món */
.lcf-cats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; }}
.lcf-cat {{ background: #fff; border-radius: 12px; padding: 1rem .5rem; text-align: center;
  box-shadow: 0 .125rem .5rem rgba(0, 0, 0, .08); transition: transform .15s, box-shadow .15s; }}
.lcf-cat:hover {{ transform: translateY(-4px); box-shadow: 0 .5rem 1rem rgba(214, 40, 40, .2); }}
.lcf-cat .lcf-cat-icon {{ font-size: 2.2rem; }}
.lcf-cat div {{ font-weight: 600; margin-top: .3rem; color: {INK}; }}
.lcf-cat small {{ color: #6c757d; }}

/* Thẻ món / combo */
.lcf-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; margin: .5rem 0 1rem; }}
.lcf-grid.lcf-grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
@media (max-width: 900px) {{ .lcf-grid, .lcf-grid.lcf-grid-3, .lcf-cats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.lcf-card {{
  background: #fff; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column;
  box-shadow: 0 .125rem .5rem rgba(0, 0, 0, .08); transition: transform .15s, box-shadow .15s;
}}
.lcf-card:hover {{ transform: translateY(-4px); box-shadow: 0 .75rem 1.5rem rgba(214, 40, 40, .18); }}
.lcf-card.lcf-highlight {{ outline: 3px solid {YELLOW}; }}
.lcf-badge.lcf-day {{ background: #eef1f6; color: #555; }}
.lcf-badge.lcf-day-on {{ background: #e3f6e8; color: #1b7a3a; }}
/* Thẻ trong cột Streamlit: cao bằng nhau để nút Thêm vào giỏ thẳng hàng */
.lcf-card.lcf-combo {{ min-height: 500px; margin-bottom: .5rem; }}
.lcf-card.lcf-item {{ min-height: 300px; margin-bottom: .5rem; }}
.lcf-card img {{ width: 100%; height: 160px; object-fit: cover; background: #fff; }}
.lcf-emoji {{ height: 160px; display: flex; align-items: center; justify-content: center; font-size: 4rem;
  background: linear-gradient(135deg, {CREAM} 0%, #fff8ec 100%); }}
.lcf-card-body {{ padding: .8rem 1rem 1rem; display: flex; flex-direction: column; gap: .3rem; flex: 1; }}
.lcf-card-name {{ font-weight: 700; color: {INK}; font-size: 1rem; line-height: 1.3; }}
.lcf-card-meta {{ color: #6c757d; font-size: .82rem; }}
.lcf-card ul {{ margin: .2rem 0 .2rem 1rem; padding: 0; font-size: .85rem; color: {INK}; }}
.lcf-offer {{ font-size: .82rem; color: {RED_DARK}; background: #fff1e6; border-radius: 8px; padding: .4rem .6rem; }}
.lcf-price-row {{ margin-top: auto; display: flex; align-items: baseline; gap: .5rem; flex-wrap: wrap; }}
.lcf-price {{ color: {RED}; font-weight: 800; font-size: 1.2rem; }}
.lcf-old {{ color: #9aa0a6; text-decoration: line-through; font-size: .9rem; }}
.lcf-save {{ background: {YELLOW}; color: {INK}; border-radius: 999px; padding: .05rem .5rem; font-size: .75rem; font-weight: 700; }}

/* Cam kết dịch vụ */
.lcf-features {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.5rem; text-align: center;
  background: {CREAM}; border-radius: 14px; padding: 2rem 1.5rem; margin-top: 2rem; }}
@media (max-width: 700px) {{ .lcf-features {{ grid-template-columns: 1fr; }} }}
.lcf-features .lcf-feat-icon {{ font-size: 2.6rem; margin-bottom: .5rem; }}
.lcf-features h5 {{ font-weight: 700; color: {INK}; }}
.lcf-features p {{ color: #6c757d; margin: 0; }}

/* Trang đăng nhập / đăng ký */
.lcf-auth-hero {{
  background: linear-gradient(160deg, {RED} 0%, {RED_DARK} 100%); color: #fff; text-align: center;
  border-radius: 18px; padding: 4rem 2rem; min-height: 520px;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
}}
.lcf-auth-hero img {{ width: 160px; height: 160px; border-radius: 28px; object-fit: cover;
  box-shadow: 0 .5rem 1.5rem rgba(0, 0, 0, .25); margin-bottom: 1rem; }}
.lcf-auth-hero h1 {{ color: #fff; font-weight: 800; font-size: 2.6rem; }}
.lcf-auth-hero p {{ font-size: 1.2rem; margin-top: .8rem; }}
.st-key-auth_card {{ margin-top: 2.5rem; padding: 1.5rem 1.8rem; border-radius: 28px; }}
/* Form nằm trong thẻ đăng nhập/đăng ký: không vẽ thêm khung thứ hai */
.st-key-auth_card div[data-testid="stForm"] {{ box-shadow: none; padding: 0; }}

/* Chân trang: nền đỏ sẫm, 3 cột (thương hiệu | thực đơn | liên hệ) + dải bản quyền */
.st-key-footer {{
  margin-top: 3rem; padding: 2rem 2rem 1.1rem; border-radius: 18px; gap: .6rem;
  background: linear-gradient(135deg, #2b0a0a 0%, #4a1010 60%, #5c1414 100%); color: #f3d6b0;
  border-top: 4px solid {YELLOW};
}}
.st-key-footer [data-testid="stMarkdownContainer"] p {{ margin: 0; }}
.lcf-f-brand {{ display: flex; align-items: center; gap: .6rem; margin-bottom: .7rem; }}
.lcf-f-brand img {{ width: 42px; height: 42px; border-radius: 11px; object-fit: cover; }}
.lcf-f-brand b {{ color: #fff; font-size: 1.3rem; letter-spacing: .04em; }}
.lcf-f-text {{ font-size: .9rem; line-height: 1.6; color: #f3d6b0; }}
.lcf-f-title {{
  color: {YELLOW}; font-weight: 800; font-size: .82rem; letter-spacing: .08em; text-transform: uppercase;
  margin-bottom: .55rem;
}}
.lcf-f-list {{ list-style: none; padding: 0; margin: 0; font-size: .9rem; line-height: 2; color: #f3d6b0; }}
.lcf-f-list li {{ margin: 0; padding: 0; }}
.lcf-f-list.nowrap li {{ white-space: nowrap; }}
.lcf-f-chips {{ display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .9rem; }}
.lcf-f-chips span {{
  border: 1px solid rgba(246, 170, 28, .45); color: #ffe2ad; border-radius: 999px;
  padding: .15rem .65rem; font-size: .75rem; white-space: nowrap;
}}
.lcf-f-bottom {{
  border-top: 1px solid rgba(255, 255, 255, .14); margin-top: 1.2rem; padding-top: .9rem;
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: .4rem 1.5rem;
  font-size: .78rem; color: #d9b48a;
}}
.lcf-f-bottom b {{ color: #fff; }}
</style>
"""


@st.cache_data(show_spinner=False)
def data_uri(path):
    if path is None or not Path(path).is_file():
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def html_block(markup):
    st.markdown(markup, unsafe_allow_html=True)


def esc(text):
    return html.escape(str(text))


def vnd(n):
    return f"{int(n):,}".replace(",", ".") + "₫"


def apply_theme():
    html_block(CSS.replace("{logo}", data_uri(LOGO)))


def brand_button():
    """Logo + tên cửa hàng trên thanh menu; trả về True khi được bấm (nơi gọi chuyển về trang chủ)."""
    return st.button(SITE_NAME, key="brand", type="tertiary", help="Về trang chủ")



def hero(title, text, badges=()):
    """Banner tiêu đề của trang (dùng cho trang quản trị, tài khoản)."""
    tags = "".join(f'<span class="lcf-badge">{esc(b)}</span>' for b in badges)
    html_block(f'<div class="lcf-hero">{tags}<h1>{esc(title)}</h1><p>{esc(text)}</p></div>')


def hero_art():
    icons = "".join(f"<span>{i}</span>" for i in ("🍗", "🍝", "🍔", "🍟", "🥤", "🍨"))
    html_block(f'<div class="lcf-hero-art">{icons}</div>')


def section_title(text):
    html_block(f'<div class="lcf-section-title">{esc(text)}</div>')


def soft_note(markup):
    """Khối nền kem; markup đã được escape ở nơi gọi."""
    html_block(f'<div class="lcf-section-soft">{markup}</div>')


def categories(menu):
    """Ô nhóm lớn của thực đơn: Món chính (gà giòn, mì Ý, cơm, burger), Món thêm, Món phụ, Thức uống."""
    counts = menu["group"].value_counts()
    tiles = "".join(f'<div class="lcf-cat"><div class="lcf-cat-icon">{icon}</div><div>{esc(group)}</div>'
                    f'<small>{counts.get(group, 0)} món</small></div>' for group, icon in GROUP_ICON.items())
    html_block(f'<div class="lcf-cats">{tiles}</div>')


def features():
    items = [
        ("🛵", "Giao nhanh trong 30 phút", "Đơn trong nội thành được giao nóng hổi tới tận nơi."),
        ("🍗", "Chế biến mới mỗi ngày", "Gà và món chính được chế biến trong ngày, đóng gói kín."),
        ("💳", "Thanh toán linh hoạt", "Thanh toán khi nhận hàng hoặc chuyển khoản."),
    ]
    cols = "".join(f'<div><div class="lcf-feat-icon">{i}</div><h5>{esc(t)}</h5><p>{esc(d)}</p></div>'
                   for i, t, d in items)
    html_block(f'<div class="lcf-features">{cols}</div>')


def auth_hero():
    html_block(f'<div class="lcf-auth-hero"><img src="{data_uri(LOGO)}" alt="">'
               f'<h1>{SITE_NAME}</h1><p>{SLOGAN}</p></div>')


def _picture(code, icon):
    img = data_uri(image_path(code))
    return f'<img src="{img}" alt="">' if img else f'<div class="lcf-emoji">{icon}</div>'


def _card_grid(entries, columns, key_prefix, on_add):
    """Vẽ thẻ theo hàng `columns` cột; mỗi thẻ kèm nút "Thêm vào giỏ" (on_add=None thì không có nút).
    entries: [(mã, tên hiển thị, html thẻ, đặt được hôm nay?, ghi chú khi chưa đặt được)]."""
    for start in range(0, len(entries), columns):
        cols = st.columns(columns, gap="medium")
        for col, (code, label, card, ok, note) in zip(cols, entries[start:start + columns]):
            with col:
                html_block(card)
                if not on_add:
                    continue
                if not ok:
                    st.button(note, key=f"{key_prefix}_{code}", icon=":material/event_busy:", disabled=True,
                              width="stretch")
                elif st.button("Thêm vào giỏ", key=f"{key_prefix}_{code}", icon=":material/add_shopping_cart:",
                               type="primary", width="stretch"):
                    on_add(code, label)


def item_cards(items, key_prefix="item", on_add=None, columns=4):
    """Thẻ món lẻ: ảnh (hoặc biểu tượng nhóm món), nhóm món, tên, giá."""
    entries = [(r.item_id, r.name,
                f'<div class="lcf-card lcf-item">{_picture(r.item_id, CATEGORY_ICON.get(r.category, "🍽️"))}'
                f'<div class="lcf-card-body"><span class="lcf-badge" style="align-self:flex-start">{esc(r.category)}</span>'
                f'<div class="lcf-card-name">{esc(r.name)}</div>'
                f'<div class="lcf-price-row"><span class="lcf-price">{vnd(r.price)}</span></div></div></div>',
                True, "")
               for r in items.itertuples()]
    _card_grid(entries, columns, key_prefix, on_add)


def combo_cards(combo_list, menu, highlight=None, extra_offer=None, columns=4, key_prefix="combo", on_add=None):
    """Thẻ combo: thành phần, ưu đãi, giá lẻ gạch ngang, giá combo, % tiết kiệm.
    highlight: combo_id được viền vàng (combo của khách); extra_offer: ưu đãi riêng của khách."""
    entries = []
    for c in combo_list:
        lp = list_price(c, menu)
        lines = "".join(f"<li>{esc(x)}</li>" for x in combo_lines(c, menu))
        parts = [esc(c.offer)] if c.offer else []
        if extra_offer and c.combo_id == highlight:
            parts.append(f"<b>Dành riêng cho bạn:</b> {esc(extra_offer)}")
        offer = f'<div class="lcf-offer">{"<br>".join(parts)}</div>' if parts else ""
        cls = "lcf-card lcf-combo lcf-highlight" if c.combo_id == highlight else "lcf-card lcf-combo"
        ok = combos.is_available(c)
        day = "" if c.day_type == "all" else (
            f'<span class="lcf-badge lcf-day{" lcf-day-on" if ok else ""}">{esc(combos.DAY_SHORT[c.day_type])}'
            f'{" · hôm nay" if ok and c.day_type == "weekend" else ""}</span>')
        entries.append((c.combo_id, f"Combo {c.name}",
            f'<div class="{cls}">{_picture(c.combo_id, c.icon)}<div class="lcf-card-body">'
            f'<div><span class="lcf-badge">{esc(c.people)}</span>{day}</div>'
            f'<div class="lcf-card-name">Combo {esc(c.name)}</div><ul>{lines}</ul>'
            f'{offer}'
            f'<div class="lcf-price-row"><span class="lcf-price">{vnd(c.price)}</span>'
            f'<span class="lcf-old">{vnd(lp)}</span><span class="lcf-save">-{1 - c.price / lp:.0%}</span></div>'
            f'</div></div>', ok, f"Chỉ áp dụng {combos.DAY_SHORT.get(c.day_type, '')}"))
    _card_grid(entries, columns, key_prefix, on_add)


# Thông tin liên hệ của cửa hàng giả định (không phải của doanh nghiệp thật)
CONTACT = {
    "Địa chỉ": "Đường 3/2, Ninh Kiều, Cần Thơ",
    "Hotline": "1900 0000",
    "Email": "hotro@fastbite.vn",
    "Giờ mở cửa": "08:00 – 22:00, tất cả các ngày",
}


def footer(about=""):
    """Chân trang kiểu web bán hàng: thương hiệu | thực đơn | liên hệ, dải bản quyền bên dưới."""
    def title(text):
        html_block(f'<div class="lcf-f-title">{esc(text)}</div>')

    with st.container(key="footer"):
        brand, menu_col, contact = st.columns([1.6, 1, 1.4], gap="large")
        with brand:
            html_block(f'<div class="lcf-f-brand"><img src="{data_uri(LOGO)}" alt=""><b>{SITE_NAME}</b></div>'
                       f'<div class="lcf-f-text">{esc(SLOGAN)} Gà giòn, mì Ý, burger và combo tiết kiệm '
                       'được gợi ý riêng theo nhóm khách hàng của bạn.</div>'
                       '<div class="lcf-f-chips"><span>💵 Thanh toán khi nhận hàng</span>'
                       '<span>🏦 Chuyển khoản</span><span>⭐ Đánh giá sau mỗi đơn</span></div>')
        with menu_col:
            title("Thực đơn")
            items = "".join(f"<li>{icon} {esc(group)}</li>" for group, icon in GROUP_ICON.items())
            html_block(f'<ul class="lcf-f-list nowrap">{items}<li>🎁 Combo khuyến mãi</li></ul>')
        with contact:
            title("Liên hệ")
            icons = {"Địa chỉ": "📍", "Hotline": "📞", "Email": "✉️", "Giờ mở cửa": "🕘"}
            rows = "".join(f"<li>{icons[k]} {esc(v)}</li>" for k, v in CONTACT.items())
            html_block(f'<ul class="lcf-f-list">{rows}</ul>')
        html_block(f'<div class="lcf-f-bottom"><span>© {date.today().year} <b>{SITE_NAME}</b>. {esc(about)}</span>'
                   f'<span>{esc(MENU_SOURCE)} {SITE_NAME} và thông tin liên hệ là giả định của đồ án, '
                   'không liên quan tới Jollibee.</span></div>')
