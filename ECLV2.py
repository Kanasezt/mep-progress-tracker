import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timedelta, timezone
import io
import requests

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V4.1", layout="wide")

# --- 2. CSS Styling ---
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
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
@st.cache_data(ttl=10)
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)

        if not df_raw.empty:
            df_raw["created_at"] = pd.to_datetime(df_raw["created_at"]).dt.tz_convert("Asia/Bangkok")

            if "updated_at" in df_raw.columns:
                df_raw["updated_at"] = pd.to_datetime(df_raw["updated_at"]).dt.tz_convert("Asia/Bangkok")
            else:
                df_raw["updated_at"] = df_raw["created_at"]

            if "likes" not in df_raw.columns:
                df_raw["likes"] = 0

            if "category" not in df_raw.columns:
                df_raw["category"] = ""

        return df_raw
    except:
        return pd.DataFrame()

# --- 3.1 Like Logic ---
def update_likes(record_id, current_likes):
    new_likes = int(current_likes) + 1
    supabase.table("issue_escalation").update({"likes": new_likes}).eq("id", record_id).execute()
    st.cache_data.clear()

# --- 4. Excel Export Function ---
def export_excel_with_images(dataframe):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_ex = dataframe.copy()
        now_th = datetime.now(timezone(timedelta(hours=7)))

        df_ex["id_str"] = df_ex["id"].apply(lambda x: f"{x:03d}")
        df_ex["Create Date"] = df_ex["created_at"].dt.strftime("%d-%b-%y")
        df_ex["Create Time"] = df_ex["created_at"].dt.strftime("%H:%M:%S")

        def calc_status(row):
            c_date = row["created_at"]
            if row["status"] == "Closed":
                return row["updated_at"].strftime("%d-%b-%y"), f"{max(0, (row['updated_at'] - c_date).days)} days"
            return "Processing", f"{max(0, (now_th - c_date).days)} days"

        df_ex[["Complete Date", "Pending Days"]] = df_ex.apply(lambda x: pd.Series(calc_status(x)), axis=1)

        cols = [
            "id_str",
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
            "ID",
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
        worksheet.set_column("L:L", 20)
        worksheet.write(0, 11, "Image")
        worksheet.set_default_row(80)

        for i, url in enumerate(df_ex["image_url"]):
            if url and str(url).startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
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

# --- 5. Header & Refresh Button ---
col_t, col_r = st.columns([5, 1])

with col_t:
    st.title("🚨 Issue Escalation V4.1")

with col_r:
    st.write("##")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

df = load_data()

# --- 6. Sidebar Admin ---
with st.sidebar:
    st.header("🔐 Admin Access")
    admin_pwd = st.text_input("Enter Password", type="password")
    is_admin = (admin_pwd == "pm1234")
    if is_admin:
        st.success("Admin Mode ON ✅")

# --- 7. Cards ---
if not df.empty:
    c1, c2, c3 = st.columns(3)
    op = len(df[df["status"] == "Open"])
    cl = len(df[df["status"] == "Closed"])
    can = len(df[df["status"] == "Cancel"])

    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 8. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_s = st.columns([2, 1])

    u_name = col_n.text_input("** Fill Your Name")
    u_related = col_s.radio("Severity:", options=["Critical", "Major", "Minor"], horizontal=True)

    col_cat, = st.columns(1)
    u_category = col_cat.selectbox("** Category", ["Pending", "Defect"])

    u_detail = st.text_area("** Issue Detail", height=100)
    up_file = st.file_uploader("** Upload Photo", type=["jpg", "png", "jpeg"])

    if st.form_submit_button("Submit Report"):
        if u_name and u_detail:
            img_url = ""

            if up_file:
                f_name = f"esc_{uuid.uuid4()}.jpg"
                supabase.storage.from_("images").upload(f_name, up_file.read())
                img_url = supabase.storage.from_("images").get_public_url(f_name)

            supabase.table("issue_escalation").insert({
                "staff_name": u_name,
                "category": u_category,
                "issue_detail": u_detail,
                "related_to": u_related,
                "image_url": img_url,
                "status": "Open",
                "likes": 0
            }).execute()

            st.cache_data.clear()
            st.success("✅ Success!")
            st.rerun()
        else:
            st.error("Please fill your name and issue detail.")

st.divider()

# --- 9. Search / Filter / Export ---
if not df.empty:
    c_search, c_filter, c_export = st.columns([2, 1, 1])

    with c_search:
        search_text = st.text_input("🔍 Search keyword")

    with c_filter:
        status_filter = st.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])

    with c_export:
        st.write("")
        st.write("")
        excel_data = export_excel_with_images(df)
        st.download_button(
            label="📥 Export Excel",
            data=excel_data,
            file_name="issue_escalation_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    df_show = df.copy()

    if search_text:
        search_text = search_text.lower()
        df_show = df_show[
            df_show["staff_name"].astype(str).str.lower().str.contains(search_text, na=False) |
            df_show["issue_detail"].astype(str).str.lower().str.contains(search_text, na=False) |
            df_show["related_to"].astype(str).str.lower().str.contains(search_text, na=False) |
            df_show["category"].astype(str).str.lower().str.contains(search_text, na=False)
        ]

    if status_filter != "All":
        df_show = df_show[df_show["status"] == status_filter]

    st.markdown(f"### Total Records: {len(df_show)}")

    now_th = datetime.now(timezone(timedelta(hours=7)))

    for _, r in df_show.iterrows():
        c_img, c_info, c_admin = st.columns([1.2, 4, 1.8])

        with c_img:
            if r.get("image_url"):
                st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)

        with c_info:
            category_text = r.get("category", "")
            if category_text:
                st.markdown(
                    f"### {r['id']:03d} - {r['staff_name']} "
                    f"<span class='category-tag'>Category: {category_text}</span>"
                    f"<span class='related-tag'>Severity: {r['related_to']}</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"### {r['id']:03d} - {r['staff_name']} "
                    f"<span class='related-tag'>Severity: {r['related_to']}</span>",
                    unsafe_allow_html=True
                )

            days = (now_th - r["created_at"]).days

            st.write(f"**Detail:** {r['issue_detail']}")
            st.markdown(f"Status: **{r['status']}**")

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
                        supabase.table("issue_escalation").update({
                            "status": new_stat,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", r["id"]).execute()
                    except:
                        supabase.table("issue_escalation").update({
                            "status": new_stat
                        }).eq("id", r["id"]).execute()

                    st.cache_data.clear()
                    st.rerun()

                if b2.button("Delete 🗑️", key=f"del_{r['id']}"):
                    supabase.table("issue_escalation").delete().eq("id", r["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
else:
    st.info("No data found.")