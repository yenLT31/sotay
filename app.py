import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from streamlit_calendar import calendar

st.set_page_config(page_title="Sổ tay công việc", layout="wide")

# ---------- Bảng màu dịu mắt ----------
MAU_CHUA = "#6b9bd1"      # xanh dương dịu - chưa kích hoạt
MAU_DANG = "#4a5568"      # xám xanh đậm - đang tiến hành
MAU_XONG = "#cbd5e1"      # xám nhạt - hoàn thành
MAU_NOTE = "#8b7fd4"      # tím lavender - ngày quan trọng
MAU_QUA_HAN = "#c05621"   # đỏ gạch dịu - quá hạn
MAU_SAP_HAN = "#b7791f"   # cam đất dịu - sắp hạn

# ---------- CSS trang trí ----------
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1100px;}
h1 {font-weight: 800; color:#2d3748;}
div[data-testid="stMetric"] {
    background: #f7f9fc; border: 1px solid #e6eaf0;
    border-radius: 14px; padding: 12px 8px; text-align: center;
}
div[data-testid="stExpander"] {
    border: 1px solid #e6eaf0; border-radius: 12px; margin-bottom: 8px;
}
.stButton button {border-radius: 10px;}
.ghichu-nho {color:#8a94a6; font-size:0.82rem; margin-left:2px;}
</style>
""", unsafe_allow_html=True)

st.title("📒 Sổ tay công việc")

# ---------- Kết nối Supabase ----------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ---------- Hàm phụ ----------
def lay_dau_viec(task_id):
    r = supabase.table("subtasks").select("*").eq("task_id", task_id).order("sort_order").execute()
    return r.data

def tinh_trang_thai(dau_viec):
    tong = len(dau_viec)
    xong = len([d for d in dau_viec if d["is_done"]])
    if tong == 0:
        return "chua_kich_hoat", tong, xong
    if xong == tong:
        return "hoan_thanh", tong, xong
    return "dang_tien_hanh", tong, xong

def hom_nay_vn():
    # Server Streamlit Cloud chạy giờ UTC → lấy ngày theo giờ Việt Nam cho chuẩn
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()

def han_con_lai(deadline_str):
    if not deadline_str:
        return None
    d = pd.to_datetime(deadline_str).date()
    return (d - hom_nay_vn()).days

def nhan_han(d):
    if not d["deadline"] or d["is_done"]:
        return ""
    con = han_con_lai(d["deadline"])
    if con is not None and con < 0:
        return f"  🔴 {d['deadline']} (quá {abs(con)}n)"
    elif con is not None and con <= 7:
        return f"  🟠 {d['deadline']} (còn {con}n)"
    return f"  ⏰ {d['deadline']}"

def tinh_canh_bao(danh_sach):
    """Danh sách cảnh báo, sắp xếp: khẩn cấp (quá hạn nhiều nhất) lên đầu.
    - Kế hoạch CHƯA kích hoạt  -> đếm ngược tới ngày triển khai, ngưỡng 3 ngày.
    - Đầu việc kế hoạch ĐANG tiến hành -> đếm ngược tới deadline, ngưỡng 1 ngày.
    - Kế hoạch đã hoàn thành: bỏ qua.
    """
    hom_nay = hom_nay_vn()
    ds = []
    for kh in danh_sach:
        tt = kh["_trang_thai"]
        if tt == "chua_kich_hoat":
            if not kh.get("start_date"):
                continue
            ngay = pd.to_datetime(kh["start_date"]).date()
            con = (ngay - hom_nay).days
            if con <= 3:
                ds.append({"loai": "ke_hoach", "ten_kh": kh["name"],
                           "ten_dv": None, "ngay": ngay, "con": con})
        elif tt == "dang_tien_hanh":
            for d in kh["_dau_viec"]:
                if d["is_done"] or not d["deadline"]:
                    continue
                dl = pd.to_datetime(d["deadline"]).date()
                con = (dl - hom_nay).days
                if con <= 1:
                    ds.append({"loai": "dau_viec", "ten_kh": kh["name"],
                               "ten_dv": d["content"], "ngay": dl, "con": con})
    ds.sort(key=lambda x: x["con"])
    return ds

# ---------- Lấy dữ liệu ----------
ket_qua = supabase.table("tasks").select("*").order("start_date").execute()
danh_sach = ket_qua.data

for kh in danh_sach:
    dv = lay_dau_viec(kh["id"])
    tt, tong, xong = tinh_trang_thai(dv)
    kh["_dau_viec"] = dv
    kh["_trang_thai"] = tt
    kh["_tong"] = tong
    kh["_xong"] = xong

# lấy ghi chú ngày quan trọng
gc_kq = supabase.table("notes").select("*").order("ngay").execute()
ghi_chu = gc_kq.data

# ---------- Ô tổng quan ----------
so_dang = len([k for k in danh_sach if k["_trang_thai"] == "dang_tien_hanh"])
so_chua = len([k for k in danh_sach if k["_trang_thai"] == "chua_kich_hoat"])
so_xong = len([k for k in danh_sach if k["_trang_thai"] == "hoan_thanh"])

# Tính cảnh báo — dùng chung cho ô metric, nhãn tab và nội dung tab Cảnh báo
canh_bao = tinh_canh_bao(danh_sach)
so_canh_bao = len(canh_bao)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔄 Đang tiến hành", so_dang)
c2.metric("⚠️ Cần chú ý", so_canh_bao)
c3.metric("🔵 Chưa kích hoạt", so_chua)
c4.metric("✅ Hoàn thành", so_xong)

st.divider()

nhan_tab_cb = f"⚠️ Cảnh báo ({so_canh_bao})" if so_canh_bao else "⚠️ Cảnh báo"
tab_lich, tab_congviec, tab_canhbao = st.tabs(
    ["🗓️ Lịch & Kế hoạch", "📋 Danh mục công việc", nhan_tab_cb])

# ================================================================
# TAB 1: LỊCH + TẠO KẾ HOẠCH + GHI CHÚ NGÀY QUAN TRỌNG
# ================================================================
with tab_lich:
    st.header("🗓️ Lịch kế hoạch")

    su_kien = []
    for kh in danh_sach:
        tt = kh["_trang_thai"]
        if tt == "chua_kich_hoat":
            mau = MAU_CHUA
        elif tt == "dang_tien_hanh":
            mau = MAU_DANG
        else:
            mau = MAU_XONG
        su_kien.append({
            "title": kh["name"], "start": kh["start_date"],
            "allDay": True, "color": mau,
        })
    # thêm ghi chú ngày quan trọng lên lịch
    for g in ghi_chu:
        su_kien.append({
            "title": "⭐ " + g["noi_dung"], "start": g["ngay"],
            "allDay": True, "color": MAU_NOTE,
        })

    tuy_chon_lich = {
        "initialView": "dayGridMonth", "locale": "vi",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
        "height": 520,
    }
    calendar(events=su_kien, options=tuy_chon_lich, key="lich_thang")
    st.caption("🔵 Chưa kích hoạt  •  🔘 Đang tiến hành  •  ⚪ Hoàn thành  •  ⭐ Ngày quan trọng")

    st.divider()
    col_kh, col_gc = st.columns(2)

    # ----- Tạo kế hoạch -----
    with col_kh:
        with st.expander("➕ Tạo kế hoạch mới", expanded=False):
            with st.form("form_tao", clear_on_submit=True):
                ten = st.text_input("Tên kế hoạch")
                mo_ta = st.text_area("Ghi chú (không bắt buộc)")
                ngay = st.date_input("Ngày triển khai", value=date.today())
                if st.form_submit_button("Lưu kế hoạch"):
                    if ten.strip() == "":
                        st.warning("Bạn cần nhập tên kế hoạch.")
                    else:
                        supabase.table("tasks").insert({
                            "name": ten, "description": mo_ta, "start_date": str(ngay)
                        }).execute()
                        st.success("Đã lưu: " + ten)
                        st.rerun()

    # ----- Thêm ghi chú ngày quan trọng -----
    with col_gc:
        with st.expander("⭐ Thêm ghi chú ngày quan trọng", expanded=False):
            with st.form("form_note", clear_on_submit=True):
                nd_note = st.text_input("Nội dung (VD: Họp tổng kết)")
                ngay_note = st.date_input("Ngày", value=date.today())
                if st.form_submit_button("Lưu ghi chú"):
                    if nd_note.strip() == "":
                        st.warning("Bạn cần nhập nội dung ghi chú.")
                    else:
                        supabase.table("notes").insert({
                            "noi_dung": nd_note, "ngay": str(ngay_note), "mau": MAU_NOTE
                        }).execute()
                        st.success("Đã lưu ghi chú.")
                        st.rerun()

    # ----- Danh sách ghi chú (sửa/xóa) -----
    if ghi_chu:
        with st.expander("📋 Quản lý các ghi chú ngày quan trọng"):
            for g in ghi_chu:
                gc1, gc2, gc3 = st.columns([0.25, 0.6, 0.15])
                gc1.write("⭐ " + str(g["ngay"]))
                gc2.write(g["noi_dung"])
                with gc3:
                    with st.popover("⋯"):
                        with st.form(f"sua_note_{g['id']}"):
                            n_nd = st.text_input("Nội dung", value=g["noi_dung"])
                            n_ng = st.date_input("Ngày",
                                value=pd.to_datetime(g["ngay"]).date())
                            k1, k2 = st.columns(2)
                            if k1.form_submit_button("💾 Lưu"):
                                supabase.table("notes").update({
                                    "noi_dung": n_nd, "ngay": str(n_ng)
                                }).eq("id", g["id"]).execute()
                                st.rerun()
                            if k2.form_submit_button("🗑️ Xóa"):
                                supabase.table("notes").delete().eq("id", g["id"]).execute()
                                st.rerun()

# ================================================================
# TAB 2: DANH MỤC CÔNG VIỆC
# ================================================================
with tab_congviec:
    col_a, col_b = st.columns([2, 3])
    with col_a:
        che_do = st.radio("Hiển thị:", ["Đang tiến hành", "Tất cả"], horizontal=True)
    with col_b:
        tu_khoa = st.text_input("🔍 Tìm kiếm", placeholder="Nhập từ khóa...")

    st.header("📋 Danh sách công việc")

    if len(danh_sach) == 0:
        st.info("Chưa có kế hoạch nào. Sang tab '🗓️ Lịch & Kế hoạch' để tạo mới.")

    for kh in danh_sach:
        tt = kh["_trang_thai"]
        tong, xong = kh["_tong"], kh["_xong"]

        if che_do == "Đang tiến hành" and tt == "hoan_thanh":
            continue
        if tu_khoa and tu_khoa.lower() not in kh["name"].lower():
            continue

        if tt == "chua_kich_hoat":
            nhan = "🔵 Chưa kích hoạt"
        elif tt == "hoan_thanh":
            nhan = "✅ Hoàn thành"
        else:
            nhan = f"🔄 Đang tiến hành ({xong}/{tong})"

        hans = [d["deadline"] for d in kh["_dau_viec"] if not d["is_done"] and d["deadline"]]
        hng = min(hans) if hans else None
        tieu_de = f"📌 {kh['name']}  —  {nhan}"
        if hng:
            tieu_de += f"   ⏰ {hng}"

        with st.expander(tieu_de):
            st.caption("Ngày triển khai: " + str(kh["start_date"]))
            if kh["description"]:
                st.write(kh["description"])
            if tong > 0:
                st.progress(xong / tong)

            # ---- Từng đầu việc: dòng gọn ----
            for d in kh["_dau_viec"]:
                cc1, cc2, cc3 = st.columns([0.05, 0.83, 0.12])
                with cc1:
                    moi = st.checkbox(" ", value=d["is_done"], key=f"chk_{d['id']}",
                                      label_visibility="collapsed")
                    if moi != d["is_done"]:
                        supabase.table("subtasks").update({"is_done": moi}).eq("id", d["id"]).execute()
                        st.rerun()
                with cc2:
                    ten_viec = f"~~{d['content']}~~" if d["is_done"] else d["content"]
                    st.markdown(ten_viec + nhan_han(d))
                    if d.get("note"):
                        st.markdown(f"<span class='ghichu-nho'>📝 {d['note']}</span>",
                                    unsafe_allow_html=True)
                with cc3:
                    with st.popover("⋯"):
                        with st.form(f"suadv_{d['id']}"):
                            nd = st.text_input("Nội dung", value=d["content"])
                            gc = st.text_area("Ghi chú", value=d.get("note") or "")
                            hd = st.date_input("Hạn chót",
                                value=pd.to_datetime(d["deadline"]).date() if d["deadline"] else None)
                            s1, s2 = st.columns(2)
                            luu = s1.form_submit_button("💾 Lưu")
                            xoa = s2.form_submit_button("🗑️ Xóa")
                            if luu:
                                supabase.table("subtasks").update({
                                    "content": nd, "note": gc,
                                    "deadline": str(hd) if hd else None
                                }).eq("id", d["id"]).execute()
                                st.rerun()
                            if xoa:
                                supabase.table("subtasks").delete().eq("id", d["id"]).execute()
                                st.rerun()

            # ---- THÊM NHIỀU ĐẦU VIỆC, LƯU MỘT LẦN, BẢNG TRỐNG LẠI SAU KHI LƯU ----
            st.markdown("**➕ Thêm đầu việc mới (nhập nhiều dòng, chọn ngày, rồi lưu một lần)**")
            dem_key = f"reset_{kh['id']}"
            if dem_key not in st.session_state:
                st.session_state[dem_key] = 0
            bang_moi = pd.DataFrame(columns=["Đầu việc", "Hạn chót"])
            ket_qua_nhap = st.data_editor(
                bang_moi,
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Đầu việc": st.column_config.TextColumn("Đầu việc", width="large"),
                    "Hạn chót": st.column_config.DateColumn("Hạn chót", format="YYYY-MM-DD"),
                },
                key=f"editor_them_{kh['id']}_{st.session_state[dem_key]}"
            )
            if st.button("💾 Lưu tất cả đầu việc", key=f"luuall_{kh['id']}"):
                base = len(kh["_dau_viec"])
                dem = 0
                for _, dong in ket_qua_nhap.iterrows():
                    nd = str(dong["Đầu việc"]).strip()
                    if nd == "" or nd == "nan":
                        continue
                    han = str(dong["Hạn chót"]) if pd.notna(dong["Hạn chót"]) else None
                    supabase.table("subtasks").insert({
                        "task_id": kh["id"], "content": nd,
                        "deadline": han, "is_done": False,
                        "sort_order": base + dem
                    }).execute()
                    dem += 1
                if dem > 0:
                    st.session_state[dem_key] += 1
                    st.success(f"Đã thêm {dem} đầu việc.")
                    st.rerun()
                else:
                    st.warning("Bạn chưa nhập đầu việc nào.")

            st.divider()
            # ---- Nhân bản / Sửa / Xóa kế hoạch ----
            b1, b2 = st.columns(2)
            with b1:
                if st.button("📄 Nhân bản kế hoạch", key=f"nb_{kh['id']}"):
                    moi = supabase.table("tasks").insert({
                        "name": kh["name"] + " (bản sao)",
                        "description": kh["description"],
                        "start_date": kh["start_date"]
                    }).execute()
                    new_id = moi.data[0]["id"]
                    for d in kh["_dau_viec"]:
                        supabase.table("subtasks").insert({
                            "task_id": new_id, "content": d["content"],
                            "note": d.get("note"), "deadline": d["deadline"],
                            "is_done": False, "sort_order": d["sort_order"]
                        }).execute()
                    st.success("Đã nhân bản.")
                    st.rerun()
            with b2:
                with st.popover("✏️ Sửa / 🗑️ Xóa kế hoạch"):
                    with st.form(f"suakh_{kh['id']}"):
                        tn = st.text_input("Tên kế hoạch", value=kh["name"])
                        mt = st.text_area("Ghi chú", value=kh["description"] or "")
                        ng = st.date_input("Ngày triển khai",
                            value=pd.to_datetime(kh["start_date"]).date())
                        x1, x2 = st.columns(2)
                        if x1.form_submit_button("💾 Lưu"):
                            supabase.table("tasks").update({
                                "name": tn, "description": mt, "start_date": str(ng)
                            }).eq("id", kh["id"]).execute()
                            st.rerun()
                        if x2.form_submit_button("🗑️ Xóa cả kế hoạch"):
                            supabase.table("tasks").delete().eq("id", kh["id"]).execute()
                            st.rerun()

# ================================================================
# TAB 3: CẢNH BÁO (quá hạn + sắp đến hạn)
# ================================================================
with tab_canhbao:
    st.header("⚠️ Cảnh báo công việc")
    st.caption("Kế hoạch chưa kích hoạt: nhắc trước 3 ngày tới ngày triển khai  •  "
               "Đầu việc đang làm: nhắc trước 1 ngày tới hạn.")

    if not canh_bao:
        st.success("✅ Không có việc nào quá hạn hay sắp đến hạn.")
    else:
        loc = st.radio("Lọc:", ["Tất cả", "🔴 Quá hạn", "🟠 Sắp đến hạn"],
                       horizontal=True)
        if loc == "🔴 Quá hạn":
            hien = [c for c in canh_bao if c["con"] < 0]
        elif loc == "🟠 Sắp đến hạn":
            hien = [c for c in canh_bao if c["con"] >= 0]
        else:
            hien = canh_bao

        if not hien:
            st.info("Không có mục nào trong nhóm này.")

        for c in hien:
            if c["con"] < 0:
                mau, tt_txt = MAU_QUA_HAN, f"Quá hạn {abs(c['con'])} ngày"
            elif c["con"] == 0:
                mau, tt_txt = MAU_QUA_HAN, "Đến hạn hôm nay"
            else:
                mau, tt_txt = MAU_SAP_HAN, f"Còn {c['con']} ngày"

            if c["loai"] == "ke_hoach":
                dong = f"📋 <b>{c['ten_kh']}</b> — chưa có đầu việc"
                nhan_ngay = f"Ngày triển khai: {c['ngay'].strftime('%d/%m/%Y')}"
            else:
                dong = f"📋 {c['ten_kh']} › <b>{c['ten_dv']}</b>"
                nhan_ngay = f"Hạn chót: {c['ngay'].strftime('%d/%m/%Y')}"

            st.markdown(
                f"""
                <div style="border-left:4px solid {mau}; background:{mau}15;
                            padding:8px 12px; margin-bottom:6px; border-radius:8px;">
                  <span style="color:{mau}; font-weight:700;">● {tt_txt}</span>
                  &nbsp;·&nbsp; {dong}
                  <br><span style="color:#8a94a6; font-size:0.85em;">{nhan_ngay}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
