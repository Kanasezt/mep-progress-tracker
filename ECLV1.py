import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timezone
import io
import requests
from PIL import Image

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V3.0", layout="wide")

# --- 2. CSS Styling (ปรับปรุงเพื่อ Mobile) ---
st.markdown("""
    <style>
    /* ปุ่ม Submit */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    /* รูปภาพ */
    .img-card { 
        width: 100%; max-width: 120px; aspect-ratio: 1/1; 
        object-fit: cover; border-radius: 10px; border: 1px solid #eee; 
    }
    /* Card Summary */
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 28px; font-weight: bold; display: block; }
    
    /* Responsive Table for Mobile */
    @media (max-width: 640px) {
        .mobile-card {
            border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-bottom: 10px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], errors='coerce')
        return df_raw
    except:
        return pd.DataFrame()

# --- 4. Export Excel Function ---
def export_to_excel_with_photos(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Report', index=False)
        workbook  = writer.book
        worksheet = writer.sheets['Report']
        worksheet.set_column('H:H', 20) 
        worksheet.set_default_row(80) 
        for i, url in enumerate(dataframe['image_url']):
            if url and isinstance(url, str) and url.startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(i + 1, 7, url, {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15})
                except: continue
    return output.getvalue()

# --- 5. Main UI ---
df = load_data()
st.title("🚨 Issue Escalation V3.0")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 6. Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** Fill Name")
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    u_detail = st.text_area("** Issue Detail", height=100)
    up_file = st.file_uploader("** Upload Photo", type=['jpg', 'png', 'jpeg'])
    
    if st.form_submit_button("Submit"):
        if u_name and u_detail:
            img_url = ""
            if up_file:
                f_name = f"esc_{uuid.uuid4()}.jpg"
                supabase.storage.from_('images').upload(f_name, up_file.read())
                img_url = supabase.storage.from_('images').get_public_url(f_name)
            supabase.table("issue_escalation").insert({
                "staff_name": u_name, "issue_detail": u_detail, 
                "related_to": u_related, "image_url": img_url, "status": "Open"
            }).execute()
            st.success("✅ Reported!"); st.rerun()

st.divider()

# --- 7. Dashboard & Filter ---
if not df.empty:
    st.subheader("📋 Dashboard")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name/Detail")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    if f3.button("🚀 Export Excel (With Photos)"):
        with st.spinner("Processing..."):
            excel_data = export_to_excel_with_photos(df_f)
            st.download_button("📥 Download Excel", data=excel_data, file_name="Report.xlsx")

    # --- Responsive List (Mobile Friendly) ---
    now_utc = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info = st.columns([1, 4])
            with c_img:
                if r['image_url']:
                    st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
                else: st.write("No Image")
            with c_info:
                st.markdown(f"**{r['staff_name']}** | `{r['status']}`")
                st.write(r['issue_detail'])
                # คำนวณวัน
                day_str = "-"
                if pd.notnull(r['created_at']):
                    c_utc = r['created_at'].replace(tzinfo=timezone.utc) if r['created_at'].tzinfo is None else r['created_at'].astimezone(timezone.utc)
                    day_str = f"{(now_utc - c_utc).days} days ago"
                st.caption(f"🏷️ {r['related_to']} | 📅 {day_str}")
            st.divider()

# --- 8. Admin Panel ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    if pwd == "pm1234":
        st.success("Logged In")
        if not df.empty:
            id_col = 'id' if 'id' in df.columns else df.columns[0]
            options = {row[id_col]: f"{row['staff_name']} ({row[id_col]})" for _, row in df.iterrows()}
            target = st.selectbox("Select Record", options=options.keys(), format_func=lambda x: options[x])
            new_stat = st.selectbox("Status", ["Open", "Closed", "Cancel"])
            if st.button("Update Status"):
                supabase.table("issue_escalation").update({"status": new_stat}).eq(id_col, target).execute()
                st.cache_data.clear(); st.rerun()
