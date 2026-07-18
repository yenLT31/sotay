import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# ================== CẤU HÌNH & GIAO DIỆN ==================
st.set_page_config(page_title="Quản lý công việc", page_icon="✅", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; max-width: 900px; }
    h1 { color: #1f2937; }
    div[data-testid="stExpander"] {
        border: 1px solid #e5e7eb; border-radius: 12px; margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stButton button { border-radius: 8px; }
    .metric-box {
        background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px;
        padding: 14px 8px; text-align: center;
    }
    .metric-num { font-size: 26px; font-weight: 700; }
    .metric-label { font-size: 12px; color: #6b7280; }
    .han-do { color:#dc2626; font-weight:600; }
    .han-cam { color:#ea580c; font-weight:600; }
    .han-thuong { color:#6b7280; }
    </style>
""", unsafe_allow_html=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("✅ Công cụ quản lý công việc")
hom_nay = date.today()

# ================== HÀM TIỆN ÍCH ==================
def lay_dau_viec(task_id):
    return supabase.table("subtasks").select("*").eq("task_id", task_id).order("sort_order").execute().data

def tinh_trang_thai(dv):
    tong = len(dv)
    xong = len([d for d in dv if d["is_done"]])
    if tong == 0:
        return "chua_kich_hoat", "⚪ Chưa kích hoạt", tong, xong
    if xong == tong:
        return "hoan_thanh", "✅ Hoàn thành", tong, xong
    return "dang_tien_hanh", f"🔄 Đang tiến hành ({xong}/{tong})", tong, xong

def hien_han(han_str):
    if not han_str:
        return ""
    d = pd.to_datetime(han_str).date()
    con = (d - hom_nay).days
    if con < 0:
        return f'<span class="han-do">⏰ {d} (quá hạn {abs(con)}n)</span>'
    if con <= 7:
        return f'<span class="han-cam">⏰ {d} (còn {con}n)</span>'
    return f'<span class="han-thuong">⏰ {d}</span>'

# ================== LẤY & TỔNG HỢP DỮ LIỆU ==================
tasks = supabase.table("tasks").select("*").order("start_date").execute().data
tong_hop = []
for t in tasks:
    dv = lay_dau_viec(t["id"])
    loai, nhan, tong, xong = tinh_trang_thai(dv)
    cac_dl = [d["deadline"] for d in dv if (not d["is_done"]) and d["deadline"]]
    dl_gan = min(cac_dl) if cac_dl else None
    tong_hop.append({"t": t, "dv": dv, "loai": loai, "nhan": nhan,
                     "tong": tong, "xong": xong, "dl_gan": dl_gan})

# ================== SỐ LIỆU TỔNG QUAN ==================
so_dang = len([x for x in tong_hop if x["loai"] == "dang_tien_hanh"])
so_kh = len([x for x in tong_hop if x["loai"] == "chua_kich_hoat"])
so_xong = len([x for x in tong_hop if x["loai"] == "hoan_thanh"])
sap_han = 0
for x in tong_hop:
    if x["dl_gan"] and (pd.to_datetime(x["dl_gan"]).date() - hom_nay).days <= 7:
        sap_han += 1

c1, c2, c3, c4 = st.columns(4)
for col, num, label, color in [
    (c1, so_dang, "Đang tiến hành", "#2563eb"),
    (c2, sap_han, "Sắp/quá hạn", "#dc2626"),
    (c3, so_kh, "Chưa kích hoạt", "#9333ea"),
    (c4, so_xong, "Hoàn thành", "#16a34a")]:
    col.markdown(f'<div class="metric-box"><div class="metric-num" style="color:{color}">{num}</div>'
                 f'<div class="metric-label">{label}</div></div>', unsafe_allow_html=True)
st.write("")

# ================== NHẮC NHỞ ==================
nhac = []
for x in tong_hop:
    if x["dl_gan"]:
        d = pd.to_datetime(x["dl_gan"]).date()
        con = (d - hom_nay).days
        if con < 0:
            nhac.append(("🔴", x["t"]["name"], f"quá hạn {abs(con)} ngày", d))
        elif con <= 7:
            nhac.append(("🟠", x["t"]["name"], f"còn {con} ngày", d))
if nhac:
    with st.container(border=True):
        st.markdown("#### 🔔 Nhắc nhở")
        for icon, ten, mt, d in sorted(nhac, key=lambda k: k[3]):
            st.markdown(f"{icon} **{ten}** — hạn {d} ({mt})")

# ================== TẠO KẾ HOẠCH MỚI ==================
with st.expander("➕ Tạo kế hoạch mới"):
    with st.form("form_tao", clear_on_submit=True):
        ten = st.text_input("Tên kế hoạch")
        mo_ta = st.text_area("Ghi chú (không bắt buộc)")
        ngay = st.date_input("Ngày triển khai", value=hom_nay)
        if st.form_submit_button("Lưu kế hoạch", type="primary"):
            if ten.strip() == "":
                st.warning("Bạn cần nhập tên kế hoạch.")
            else:
                supabase.table("tasks").insert({"name": ten, "description": mo_ta,
                                                "start_date": str(ngay)}).execute()
                st.success("Đã lưu: " + ten); st.rerun()

st.divider()

# ================== BỘ LỌC ==================
col_loc, col_tim = st.columns([2, 3])
with col_loc:
    che_do = st.radio("Hiển thị:", ["Đang tiến hành", "Tất cả"], horizontal=True)
with col_tim:
    tu_khoa = st.text_input("🔍 Tìm kiếm", placeholder="Nhập từ khóa...")

# ---------- HÀM VẼ MỘT CÔNG VIỆC ----------
def ve_cong_viec(x):
    t = x["t"]; task_id = t["id"]; dv = x["dv"]
    tieu_de = f'📌 {t["name"]}   —   {x["nhan"]}'
    if x["dl_gan"]:
        tieu_de += f'   ⏰ {x["dl_gan"]}'
    with st.expander(tieu_de):
        st.caption(f'🗓️ Ngày triển khai: {t["start_date"]}')
        if t.get("description"):
            st.write(t["description"])
        if x["tong"] > 0:
            st.progress(x["xong"] / x["tong"], text=f'{x["xong"]}/{x["tong"]} đầu việc')

        # Danh sách đầu việc: tick trái - nội dung - hạn phải
        for d in dv:
            col_tick, col_han = st.columns([5, 2])
            with col_tick:
                moi = st.checkbox(d["content"], value=d["is_done"], key=f'cb_{d["id"]}')
                if moi != d["is_done"]:
                    supabase.table("subtasks").update({"is_done": moi}).eq("id", d["id"]).execute()
                    st.rerun()
            with col_han:
                if d["deadline"]:
                    st.markdown(hien_han(d["deadline"]), unsafe_allow_html=True)

        # Thêm đầu việc mới
        with st.form(f"add_{task_id}", clear_on_submit=True):
            ca, cb, cc = st.columns([4, 2, 1])
            nd = ca.text_input("Đầu việc mới", label_visibility="collapsed",
                               placeholder="Nhập đầu việc mới...")
            han = cb.date_input("Hạn", value=None, label_visibility="collapsed")
            if cc.form_submit_button("➕") and nd.strip():
                supabase.table("subtasks").insert({
                    "task_id": task_id, "content": nd.strip(),
                    "deadline": str(han) if han else None}).execute()
                st.rerun()

        st.write("")
        b1, b2 = st.columns(2)
        if b1.button("📄 Nhân bản", key=f"clone_{task_id}", use_container_width=True):
            moi_t = supabase.table("tasks").insert({
                "name": t["name"] + " (bản sao)", "description": t.get("description"),
                "start_date": str(hom_nay)}).execute().data[0]
            for d in dv:
                supabase.table("subtasks").insert({
                    "task_id": moi_t["id"], "content": d["content"],
                    "is_done": False, "deadline": None}).execute()
            st.rerun()

        with b2.popover("✏️ Sửa / 🗑️ Xóa", use_container_width=True):
            with st.form(f"edit_{task_id}"):
                tn = st.text_input("Tên", value=t["name"])
                mt = st.text_area("Ghi chú", value=t.get("description") or "")
                ng = st.date_input("Ngày triển khai", value=pd.to_datetime(t["start_date"]).date())
                if st.form_submit_button("Cập nhật", type="primary"):
                    supabase.table("tasks").update({"name": tn, "description": mt,
                                                    "start_date": str(ng)}).eq("id", task_id).execute()
                    st.rerun()
            if st.button("🗑️ Xóa kế hoạch này", key=f"del_{task_id}"):
                supabase.table("tasks").delete().eq("id", task_id).execute()
                st.rerun()

# ================== HIỂN THỊ ==================
st.subheader("📋 Công việc đang tiến hành")
co_viec = False
for x in tong_hop:
    if x["loai"] != "dang_tien_hanh":
        continue
    if tu_khoa.strip() and tu_khoa.lower() not in x["t"]["name"].lower():
        continue
    ve_cong_viec(x); co_viec = True
if not co_viec:
    st.info("Không có công việc nào đang tiến hành.")

if che_do == "Tất cả":
    st.subheader("⚪ Kế hoạch chưa kích hoạt")
    co = False
    for x in tong_hop:
        if x["loai"] == "chua_kich_hoat":
            ve_cong_viec(x); co = True
    if not co:
        st.caption("Không có.")

    st.subheader("✅ Đã hoàn thành")
    co = False
    for x in tong_hop:
        if x["loai"] == "hoan_thanh":
            ve_cong_viec(x); co = True
    if not co:
        st.caption("Không có.")
