import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timedelta, timezone
import io
import requests

# =========================
# 1. CONFIG
# =========================
TABLE_NAME = "issue_escalation_v2"
BUCKET_NAME = "images"

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V2", layout="wide")

# =========================
# 2. SESSION STATE
# =========================
if "preview_image_url" not in st.session_state:
    st.session_state.preview_image_url = ""
if "preview_record_no" not in st.session_state:
    st.session_state.preview_record_no = ""

# =========================
# 3. CSS
# =========================
st.markdown("""
<style>
div[data-testid="stFormSubmitButton"] > button {
    background-color: #0047AB !important;
    color: white !important;
    width: 100%;
    height: 50px;
    font-size: 20px;
    font-weight: bold;
    border-radius: 10px;
}
.img-card {
    width: 100%;
    max-width: 150px;
    aspect-ratio: 1/1;
    object-fit: cover;
    border-radius: 10px;
    border: 1px solid #eee;
}
.card-open {
    background-color: #E65100;
    color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
.card-closed {
    background-color: #1B5E20;
    color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
.card-cancel {
    background-color: #424242;
    color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
.val-text {
    font-size: 30px;
    font-weight: bold;
    display: block;
}
.related-tag {
    background-color: #f0f2f6;
    color: #31333F;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 14px;
    font-weight: bold;
    margin-left: 10px;
    border: 1px solid #ddd;
}
.category-tag {
    background-color: #e8f0fe;
    color: #1a73e8;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 14px;
    font-weight: bold;
    margin-left: 10px;
    border: 1px solid #c6dafc;
}
.small-note {
    font-size: 12px;
    color: #999;
}
.like-wrap div[data-testid="stButton"] > button {
    width: 100%;
}
.preview-note {
    font-size: 11px;
    color: #888;
    text-align: center;
    margin-top: 6px;
}
.admin-box {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px;
    background: #fafafa;
}
.preview-box {
    border: 1px solid #d9d9d9;
    border-radius: 12px;
    padding: 14px;
    background: #fcfcfc;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 4. HELPERS
# =========================
@st.cache_data(ttl=30)
def load_data():
    try:
        cols = (
            "id,display_no,category_seq,staff_name,category,issue_detail,"
            "related_to,image_url,status,likes,created_at,updated_at"
        )
        res = (
            supabase.table(TABLE_NAME)
            .select(cols)
            .order("id", desc=True)
            .execute()
        )
        df_raw = pd.DataFrame(res.data)

        if df_raw.empty:
            return pd.DataFrame()

        if "created_at" in df_raw.columns:
            df_raw["created_at"] = pd.to_datetime(
                df_raw["created_at"], utc=True, errors="coerce"
            ).dt.tz_convert("Asia/Bangkok")
        else:
            df_raw["created_at"] = pd.Timestamp.now(tz="Asia/Bangkok")

        if "updated_at" in df_raw.columns:
            df_raw["updated_at"] = pd.to_datetime(
                df_raw["updated_at"], utc=True, errors="coerce"
            ).dt.tz_convert("Asia/Bangkok")
        else:
            df_raw["updated_at"] = df_raw["created_at"]

        if "likes" not in df_raw.columns:
            df_raw["likes"] = 0

        if "category" not in df_raw.columns:
            df_raw["category"] = ""

        if "related_to" not in df_raw.columns:
            df_raw["related_to"] = ""

        if "display_no" not in df_raw.columns:
            df_raw["display_no"] = df_raw["id"].apply(lambda x: f"{x:03d}")

        if "category_seq" not in df_raw.columns:
            df_raw["category_seq"] = None

        return df_raw

    except Exception as e:
        st.error(f"Load data error: {e}")
        return pd.DataFrame()


def update_likes(record_id, current_likes):
    new_likes = int(current_likes or 0) + 1
    supabase.table(TABLE_NAME).update({"likes": new_likes}).eq("id", record_id).execute()
    st.cache_data.clear()


def generate_category_number(category):
    try:
        res = (
            supabase.table(TABLE_NAME)
            .select("category_seq")
            .eq("category", category)
            .order("category_seq", desc=True)
            .limit(1)
            .execute()
        )

        if res.data and res.data[0].get("category_seq") is not None:
            next_seq = int(res.data[0]["category_seq"]) + 1
        else:
            next_seq = 1

        prefix = "P" if category == "Pending" else "D"
        display_no = f"{prefix}-{next_seq:03d}"
        return next_seq, display_no

    except Exception:
        prefix = "P" if category == "Pending" else "D"
        return 1, f"{prefix}-001"


@st.cache_data(ttl=300, show_spinner=False)
def export_excel_plain(dataframe: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_ex = dataframe.copy()
        now_th = datetime.now(timezone(timedelta(hours=7)))

        if "display_no" not in df_ex.columns:
            df_ex["display_no"] = df_ex["id"].apply(lambda x: f"{x:03d}")

        df_ex["Create Date"] = df_ex["created_at"].dt.strftime("%d-%b-%y")
        df_ex["Create Time"] = df_ex["created_at"].dt.strftime("%H:%M:%S")

        def calc_status(row):
            c_date = row["created_at"]
            if row["status"] == "Closed":
                return row["updated_at"].strftime("%d-%b-%y"), f"{max(0, (row['updated_at'] - c_date).days)} days"
            return "Processing", f"{max(0, (now_th - c_date).days)} days"

        df_ex[["Complete Date", "Pending Days"]] = df_ex.apply(
            lambda x: pd.Series(calc_status(x)), axis=1
        )

        cols = [
            "display_no", "staff_name", "category", "issue_detail", "related_to",
            "status", "likes", "Create Date", "Create Time", "Complete Date", "Pending Days"
        ]
        df_final = df_ex[cols]
        df_final.columns = [
            "Running No", "Staff Name", "Category", "Detail", "Severity",
            "Status", "Likes", "Create Date", "Create Time", "Complete Date", "Pending Days"
        ]

        df_final.to_excel(writer, sheet_name="Issue_Report", index=False)

    return output.getvalue()


def export_excel_with_images(dataframe: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_ex = dataframe.copy()
        now_th = datetime.now(timezone(timedelta(hours=7)))

        if "display_no" not in df_ex.columns:
            df_ex["display_no"] = df_ex["id"].apply(lambda x: f"{x:03d}")

        df_ex["Create Date"] = df_ex["created_at"].dt.strftime("%d-%b-%y")
        df_ex["Create Time"] = df_ex["created_at"].dt.strftime("%H:%M:%S")

        def calc_status(row):
            c_date = row["created_at"]
            if row["status"] == "Closed":
                return row["updated_at"].strftime("%d-%b-%y"), f"{max(0, (row['updated_at'] - c_date).days)} days"
            return "Processing", f"{max(0, (now_th - c_date).days)} days"

        df_ex[["Complete Date", "Pending Days"]] = df_ex.apply(
            lambda x: pd.Series(calc_status(x)), axis=1
        )

        cols = [
            "display_no", "staff_name", "category", "issue_detail", "related_to",
            "status", "likes", "Create Date", "Create Time", "Complete Date", "Pending Days"
        ]

        df_final = df_ex[cols]
        df_final.columns = [
            "Running No", "Staff Name", "Category", "Detail", "Severity",
            "Status", "Likes", "Create Date", "Create Time", "Complete Date", "Pending Days"
        ]

        df_final.to_excel(writer, sheet_name="Issue_Report", index=False)

        worksheet = writer.sheets["Issue_Report"]
        worksheet.set_column("A:A", 14)
        worksheet.set_column("B:B", 20)
        worksheet.set_column("C:C", 12)
        worksheet.set_column("D:D", 40)
        worksheet.set_column("E:E", 12)
        worksheet.set_column("F:F", 12)
        worksheet.set_column("G:G", 10)
        worksheet.set_column("H:K", 15)
        worksheet.write(0, 11, "Image")
        worksheet.set_default_row(80)

        for i, url in enumerate(df_ex["image_url"]):
            if url and str(url).startswith("http"):
                try:
                    resp = requests.get(url, timeout=4)
                    resp.raise_for_status()
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(
                        i + 1, 11, url,
                        {
                            "image_data": img_data,
                            "x_scale": 0.12,
                            "y_scale": 0.12,
                            "x_offset": 5,
                            "y_offset": 5
                        }
                    )
                except Exception:
                    continue

    return output.getvalue()


def apply_filters(df, search_text, status_filter, category_filter):
    df_show = df.copy()

    if search_text:
        kw = search_text.lower().strip()
        df_show = df_show[
            df_show["staff_name"].astype(str).str.lower().str.contains(kw, na=False) |
            df_show["issue_detail"].astype(str).str.lower().str.contains(kw, na=False) |
            df_show["related_to"].astype(str).str.lower().str.contains(kw, na=False) |
            df_show["category"].astype(str).str.lower().str.contains(kw, na=False) |
            df_show["display_no"].astype(str).str.lower().str.contains(kw, na=False)
        ]

    if status_filter != "All":
        df_show = df_show[df_show["status"] == status_filter]

    if category_filter != "All":
        df_show = df_show[df_show["category"] == category_filter]

    return df_show


def clear_runtime_cache():
    st.cache_data.clear()
    if "excel_with_images_ready" in st.session_state:
        del st.session_state["excel_with_images_ready"]


# =========================
# 5. HEADER
# =========================
col_t, col_r = st.columns([5, 1])

with col_t:
    st.title("🚨 Pending and Defect V1.3")

with col_r:
    st.write("##")
    if st.button("🔄 Refresh Data"):
        clear_runtime_cache()
        st.rerun()

df = load_data()

# =========================
# 6. ADMIN
# =========================
with st.sidebar:
    st.header("🔐 Admin Access")
    admin_pwd = st.text_input("Enter Password", type="password")
    is_admin = (admin_pwd == "pm1234")
    if is_admin:
        st.success("Admin Mode ON ✅")

    st.markdown("---")
    st.markdown(f"**Current Table:** `{TABLE_NAME}`")
    st.caption("This version is separated from old app/table.")

# =========================
# 7. SUMMARY CARDS
# =========================
if not df.empty:
    c1, c2, c3 = st.columns(3)
    op = len(df[df["status"] == "Open"])
    cl = len(df[df["status"] == "Closed"])
    can = len(df[df["status"] == "Cancel"])

    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# =========================
# 8. SUBMIT FORM
# =========================
with st.form("issue_form", clear_on_submit=True):
    col_n, col_s = st.columns([2, 1])

    u_name = col_n.text_input("** Fill Your Name")
    u_related = col_s.radio("Severity:", options=["Critical", "Major", "Minor"], horizontal=True)

    u_category = st.selectbox("** Category", ["Pending", "Defect"])
    u_detail = st.text_area("** Issue Detail", height=100)
    up_file = st.file_uploader("** Upload Photo", type=["jpg", "png", "jpeg"])

    if st.form_submit_button("Submit Report"):
        if u_name and u_detail:
            img_url = ""

            if up_file:
                try:
                    ext = up_file.name.split(".")[-1].lower() if "." in up_file.name else "jpg"
                    f_name = f"esc_v2_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_(BUCKET_NAME).upload(f_name, up_file.read())
                    img_url = supabase.storage.from_(BUCKET_NAME).get_public_url(f_name)
                except Exception as e:
                    st.error(f"Image upload failed: {e}")
                    st.stop()

            category_seq, display_no = generate_category_number(u_category)

            try:
                supabase.table(TABLE_NAME).insert({
                    "running_no": category_seq,
                    "category_seq": category_seq,
                    "display_no": display_no,
                    "staff_name": u_name,
                    "category": u_category,
                    "issue_detail": u_detail,
                    "related_to": u_related,
                    "image_url": img_url,
                    "status": "Open",
                    "likes": 0
                }).execute()

                clear_runtime_cache()
                st.success(f"✅ Success! New record: {display_no}")
                st.rerun()

            except Exception as e:
                st.error(f"Insert failed: {e}")
        else:
            st.error("Please fill your name and issue detail.")

st.divider()

# =========================
# 9. FILTER / EXPORT
# =========================
if not df.empty:
    c_search, c_status, c_cat, c_page = st.columns([2, 1, 1, 1])

    with c_search:
        search_text = st.text_input("🔍 Search keyword")

    with c_status:
        status_filter = st.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])

    with c_cat:
        category_filter = st.selectbox("Filter Category", ["All", "Pending", "Defect"])

    with c_page:
        page_size_option = st.selectbox("Rows / page", ["All", 10, 20, 30, 50], index=4)

    df_show = apply_filters(df, search_text, status_filter, category_filter)
    page_size = len(df_show) if page_size_option == "All" else int(page_size_option)

    st.markdown(f"### Total Records: {len(df_show)}")

    # =========================
    # SAME WINDOW IMAGE PREVIEW
    # =========================
    if st.session_state.preview_image_url:
        st.markdown('<div class="preview-box">', unsafe_allow_html=True)
        p1, p2 = st.columns([6, 1])
        with p1:
            st.subheader(f"🖼️ Image Preview: {st.session_state.preview_record_no}")
        with p2:
            if st.button("Close Preview ❌"):
                st.session_state.preview_image_url = ""
                st.session_state.preview_record_no = ""
                st.rerun()

        st.image(st.session_state.preview_image_url, use_container_width=True)
        st.caption("Use browser zoom (Ctrl + / Ctrl -) if you want to inspect more closely.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Export section
    st.subheader("📥 Export")
    ex1, ex2, ex3 = st.columns([1.2, 1.2, 1.5])

    with ex1:
        csv_data = df_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="Export CSV",
            data=csv_data,
            file_name=f"issue_escalation_v2_{datetime.now().strftime('%d%m%Y')}.csv",
            mime="text/csv"
        )

    with ex2:
        plain_excel = export_excel_plain(df_show)
        st.download_button(
            label="Export Excel (fast)",
            data=plain_excel,
            file_name=f"issue_escalation_v2_fast_{datetime.now().strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with ex3:
        if st.button("Prepare Excel with Images"):
            with st.spinner("Preparing image Excel..."):
                st.session_state["excel_with_images_ready"] = export_excel_with_images(df_show)

        if "excel_with_images_ready" in st.session_state:
            st.download_button(
                label="Download Excel with Images",
                data=st.session_state["excel_with_images_ready"],
                file_name=f"issue_escalation_v2_images_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Pagination
    if page_size_option == "All":
        df_page = df_show.copy()
    else:
        total_pages = max(1, (len(df_show) + page_size - 1) // page_size)

        if "page_no" not in st.session_state:
            st.session_state.page_no = 1
        st.session_state.page_no = min(st.session_state.page_no, total_pages)

        p1, p2, p3 = st.columns([1, 2, 1])

        with p1:
            if st.button("⬅ Prev", disabled=st.session_state.page_no <= 1):
                st.session_state.page_no -= 1
                st.rerun()

        with p2:
            st.markdown(
                f"<div style='text-align:center;padding-top:8px;'>Page {st.session_state.page_no} / {total_pages}</div>",
                unsafe_allow_html=True
            )

        with p3:
            if st.button("Next ➡", disabled=st.session_state.page_no >= total_pages):
                st.session_state.page_no += 1
                st.rerun()

        start_idx = (st.session_state.page_no - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df_show.iloc[start_idx:end_idx].copy()

    now_th = datetime.now(timezone(timedelta(hours=7)))

    for _, r in df_page.iterrows():
        c_img, c_info, c_admin = st.columns([1.2, 4, 2.2])

        with c_img:
            if r.get("image_url") and str(r["image_url"]).startswith("http"):
                st.image(r["image_url"], width=150)

                if st.button("Preview 🔍", key=f"preview_{r['id']}"):
                    st.session_state.preview_image_url = r["image_url"]
                    record_no = r["display_no"] if r.get("display_no") else f"{r['id']:03d}"
                    st.session_state.preview_record_no = record_no
                    st.rerun()

                st.markdown(
                    '<div class="preview-note">Click Preview to open in same page</div>',
                    unsafe_allow_html=True
                )

        with c_info:
            record_no = r["display_no"] if r.get("display_no") else f"{r['id']:03d}"

            st.markdown(
                f"### {record_no} - {r['staff_name']}"
                f"<span class='category-tag'>Category: {r.get('category', '')}</span>"
                f"<span class='related-tag'>Severity: {r.get('related_to', '')}</span>",
                unsafe_allow_html=True
            )

            st.write(f"**Detail:** {r['issue_detail']}")
            st.markdown(f"Status: **{r['status']}**")

            days = (now_th - r["created_at"]).days
            c_time, c_like = st.columns([2.5, 1])

            with c_time:
                if r["status"] == "Closed":
                    st.success(
                        f"✅ Completed | 📅 {r['created_at'].strftime('%d %b %y')} | 🕒 {r['created_at'].strftime('%H:%M:%S')}"
                    )
                else:
                    st.warning(
                        f"⏳ {max(0, days)} days pending | 📅 {r['created_at'].strftime('%d %b %y')} | 🕒 {r['created_at'].strftime('%H:%M:%S')}"
                    )

            with c_like:
                st.markdown('<div class="like-wrap">', unsafe_allow_html=True)
                like_val = int(r.get("likes", 0))
                if st.button(f"❤️ {like_val}", key=f"like_btn_{r['id']}"):
                    update_likes(r["id"], like_val)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            st.caption(f"DB ID: {r['id']} | Category Seq: {r.get('category_seq', '')}")

        with c_admin:
            if is_admin:
                st.markdown('<div class="admin-box">', unsafe_allow_html=True)

                new_stat = st.selectbox(
                    "Update Status",
                    ["Open", "Closed", "Cancel"],
                    index=["Open", "Closed", "Cancel"].index(r["status"]),
                    key=f"st_{r['id']}"
                )

                edited_detail = st.text_area(
                    "Edit Issue Detail",
                    value=str(r["issue_detail"]) if pd.notna(r["issue_detail"]) else "",
                    height=120,
                    key=f"detail_{r['id']}"
                )

                a1, a2 = st.columns(2)
                with a1:
                    if st.button("Save Detail 💾", key=f"save_detail_{r['id']}"):
                        try:
                            supabase.table(TABLE_NAME).update({
                                "issue_detail": edited_detail,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", r["id"]).execute()

                            clear_runtime_cache()
                            st.success("Detail updated")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Save detail failed: {e}")

                with a2:
                    if st.button("Confirm Status ✅", key=f"ok_{r['id']}"):
                        try:
                            supabase.table(TABLE_NAME).update({
                                "status": new_stat,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", r["id"]).execute()

                            clear_runtime_cache()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")

                if st.button("Delete 🗑️", key=f"del_{r['id']}"):
                    try:
                        supabase.table(TABLE_NAME).delete().eq("id", r["id"]).execute()
                        clear_runtime_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

                st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

else:
    st.info("No data found in issue_escalation_v2.")