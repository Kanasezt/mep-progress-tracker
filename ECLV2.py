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
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V2", layout="wide")

# =========================
# 2. CSS
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
.displayno-tag {
    background-color: #fff3cd;
    color: #7a5d00;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 14px;
    font-weight: bold;
    margin-left: 10px;
    border: 1px solid #ead58a;
}
.small-note {
    font-size: 12px;
    color: #999;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 3. HELPERS
# =========================
@st.cache_data(ttl=10)
def load_data():
    try:
        res = supabase.table(TABLE_NAME).select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)

        if not df_raw.empty:
            if "created_at" in df_raw.columns:
                df_raw["created_at"] = pd.to_datetime(df_raw["created_at"], utc=True).dt.tz_convert("Asia/Bangkok")
            else:
                df_raw["created_at"] = pd.Timestamp.now(tz="Asia/Bangkok")

            if "updated_at" in df_raw.columns:
                df_raw["updated_at"] = pd.to_datetime(df_raw["updated_at"], utc=True).dt.tz_convert("Asia/Bangkok")
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
    new_likes = int(current_likes) + 1
    supabase.table(TABLE_NAME).update({"likes": new_likes}).eq("id", record_id).execute()
    st.cache_data.clear()


def generate_category_number(category):
    """
    Pending -> P-001, P-002, ...
    Defect  -> D-001, D-002, ...
    """
    try:
        res = (
            supabase.table(TABLE_NAME)
            .select("category_seq")
            .eq("category", category)
            .order("category_seq", desc=True)
            .limit(1)
            .execute()
        )

        if res.data and len(res.data) > 0 and res.data[0].get("category_seq") is not None:
            next_seq = int(res.data[0]["category_seq"]) + 1
        else:
            next_seq = 1

        prefix = "P" if category == "Pending" else "D"
        display_no = f"{prefix}-{next_seq:03d}"

        return next_seq, display_no

    except Exception:
        prefix = "P" if category == "Pending" else "D"
        return 1, f"{prefix}-001"


def export_excel_with_images(dataframe):
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
            "display_no",
            "staff_name",
            "category",
            "issue_detail",
            "related_to",
            "status",
            "likes",
            "Create Date",
            "Create Time",
            "Complete Date",
            "Pending Days"
        ]

        df_final = df_ex[cols]
        df_final.columns = [
            "Running No",
            "Staff Name",
            "Category",
            "Detail",
            "Severity",
            "Status",
            "Likes",
            "Create Date",
            "Create Time",
            "Complete Date",
            "Pending Days"
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
        worksheet.set_column("H:J", 15)
        worksheet.set_column("K:K", 15)
        worksheet.set_column("L:L", 20)

        worksheet.write(0, 11, "Image")
        worksheet.set_default_row(80)

        for i, url in enumerate(df_ex["image_url"]):
            if url and str(url).startswith("http"):
                try:
                    resp = requests.get(url, timeout=8)
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(
                        i + 1,
                        11,
                        url,
                        {
                            "image_data": img_data,
                            "x_scale": 0.12,
                            "y_scale": 0.12,
                            "x_offset": 5,
                            "y_offset": 5
                        }
                    )
                except:
                    continue

    return output.getvalue()


# =========================
# 4. HEADER
# =========================
col_t, col_r = st.columns([5, 1])

with col_t:
    st.title("🚨 Issue Escalation V2")

with col_r:
    st.write("##")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

df = load_data()

# =========================
# 5. ADMIN
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
# 6. SUMMARY CARDS
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
# 7. SUBMIT FORM
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

                st.cache_data.clear()
                st.success(f"✅ Success! New record: {display_no}")
                st.rerun()

            except Exception as e:
                st.error(f"Insert failed: {e}")
        else:
            st.error("Please fill your name and issue detail.")

st.divider()

# =========================
# 8. FILTER / EXPORT
# =========================
if not df.empty:
    c_search, c_status, c_cat, c_export = st.columns([2, 1, 1, 1.2])

    with c_search:
        search_text = st.text_input("🔍 Search keyword")

    with c_status:
        status_filter = st.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])

    with c_cat:
        category_filter = st.selectbox("Filter Category", ["All", "Pending", "Defect"])

    with c_export:
        st.write("")
        st.write("")
        excel_data = export_excel_with_images(df)
        st.download_button(
            label="📥 Export Excel",
            data=excel_data,
            file_name=f"issue_escalation_v2_{datetime.now().strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    df_show = df.copy()

    if search_text:
        kw = search_text.lower()
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

    st.markdown(f"### Total Records: {len(df_show)}")

    now_th = datetime.now(timezone(timedelta(hours=7)))

    for _, r in df_show.iterrows():
        c_img, c_info, c_admin = st.columns([1.2, 4, 1.8])

        with c_img:
            if r.get("image_url"):
                st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)

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
                like_val = r.get("likes", 0)
                if st.button(f"❤️ {int(like_val)}", key=f"like_btn_{r['id']}"):
                    update_likes(r["id"], like_val)
                    st.rerun()

            st.caption(
                f"DB ID: {r['id']} | Category Seq: {r.get('category_seq', '')}"
            )

        with c_admin:
            if is_admin:
                new_stat = st.selectbox(
                    "Update Status",
                    ["Open", "Closed", "Cancel"],
                    index=["Open", "Closed", "Cancel"].index(r["status"]),
                    key=f"st_{r['id']}"
                )

                b1, b2 = st.columns(2)

                if b1.button("Confirm ✅", key=f"ok_{r['id']}"):
                    try:
                        supabase.table(TABLE_NAME).update({
                            "status": new_stat,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", r["id"]).execute()

                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

                if b2.button("Delete 🗑️", key=f"del_{r['id']}"):
                    try:
                        supabase.table(TABLE_NAME).delete().eq("id", r["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

        st.divider()

else:
    st.info("No data found in issue_escalation_v2.")