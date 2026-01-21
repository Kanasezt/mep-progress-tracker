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

st.set_page_config(page_title="Issue Escalation V3.7", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-card { width: 100%; max-width: 150px; aspect-ratio: 1/1; object-fit: cover; border-radius: 10px; border: 1px solid #eee; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 30px; font-weight: bold; display: block; }
    .related-tag { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 5px; font-size: 14px; font-weight: bold; margin-left: 10px; border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_convert('Asia/Bangkok')
            df_raw['updated_at'] = pd.to_datetime(df_raw.get('updated_at', df_raw['created_at'])).dt.tz_convert('Asia/Bangkok')
        return df_raw
    except:
        return pd.DataFrame()

# --- 4. Excel Export Function (V3.7: With Full Dates & Thai Time) ---
def export_excel_with_images(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_ex = dataframe.copy()
        now_th = datetime.now(timezone(timedelta(hours=7)))
        
        df_ex['id_str'] = df_ex['id'].apply(lambda x: f"{x:03d}")
        df_ex['Create Date'] = df_ex['created_at'].dt.strftime('%d-%b-%y')
        df_ex['Create Time'] = df_ex['created_at'].dt.strftime('%H:%M:%S')
        
        def get_status_info(row):
            c_date = row['created_at']
            if row['status'] == 'Closed':
                comp_date = row['updated_at'].strftime('%d-%b-%y')
                days = (row['updated_at'] - c_date).days
                return comp_date, f"{max(0, days)} days"
            else:
                days = (now_th - c_date).days
                return "Processing", f"{max(0, days)} days"

        df_ex[['Complete Date', 'Pending Days']] = df_ex.apply(lambda x: pd.Series(get_status_info(x)), axis=1)
        
        cols = ['id_str', 'staff_name', 'issue_detail', 'related_to', 'status', 'Create Date', 'Create Time', 'Complete Date', 'Pending Days']
        df_final = df_ex[cols]
        df_final.columns = ['ID', 'Staff Name', 'Detail', 'Related to', 'Status', 'Create Date', 'Create Time', 'Complete Date', 'Pending Days']
        
        df_final.to_excel(writer, sheet_name='Issue_Report', index=False)
        worksheet = writer.sheets['Issue_Report']
        worksheet.set_column('J:J', 20)
        worksheet.write(0, 9, 'Image')
        worksheet.set_default_row(80)
        
        for i, url in enumerate(df_ex['image_url']):
            if url and url.startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(i + 1, 9, url, {'image_data': img_data, 'x_scale': 0.12, 'y_scale': 0.12, 'x_offset': 5, 'y_offset': 5})
                except: continue
    return output.getvalue()

df = load_data()

# --- 5. Sidebar Admin ---
with st.sidebar:
    st.header("🔐 Admin Access")
    admin_pwd = st.text_input("Enter Password", type="password")
    is_admin = (admin_pwd == "pm1234")
    if is_admin: st.success("Admin Mode ON ✅")

# --- 6. Main UI ---
st.title("🚨 Issue Escalation V3.7")
c1, c2, c3 = st.columns(3)
op = len(df[df['status'] == 'Open']) if not df.empty else 0
cl = len(df[df['status'] == 'Closed']) if not df.empty else 0
can = len(df[df['status'] == 'Cancel']) if not df.empty else 0

c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 7. Form ---
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
            st.success("✅ Success!"); st.rerun()

# --- 8. Dashboard ---
if not df.empty:
    st.divider()
    st.subheader("📋 Dashboard")
    f1, f2, f3 = st.columns([2, 1, 1.2])
    search = f1.text_input("🔍 Search Name/Detail")
    f_stat = f2.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    if f3.button("📥 Download Excel with Photos"):
        with st.spinner("กำลังสรุปข้อมูล..."):
            excel_file = export_excel_with_images(df_f)
            st.download_button("💾 Save Excel", data=excel_file, file_name=f"Report_V37_{datetime.now().strftime('%d%m%Y')}.xlsx")

    now_th = datetime.now(timezone(timedelta(hours=7)))
    for i, r in df_f.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info, c_admin = st.columns([1.5, 3.5, 1.2])
            with c_img:
                if r['image_url']: st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
            
            with c_info:
                # แสดง ID, ชื่อ และ ฝ่ายที่เกี่ยวข้อง (Related to)
                st.markdown(f"### {r['id']:03d} - {r['staff_name']} <span class='related-tag'>Related to: {r['related_to']}</span>", unsafe_allow_html=True)
                days = (now_th - r['created_at']).days
                st.write(f"**Detail:** {r['issue_detail']}")
                st.markdown(f"Status: **{r['status']}**")
                
                # แสดงวันเวลาไทยและสถานะ
                if r['status'] == 'Closed':
                    st.success(f"✅ Completed | 📅 {r['created_at'].strftime('%d %b %y')} | 🕒 {r['created_at'].strftime('%H:%M:%S')}")
                else:
                    st.warning(f"⏳ {max(0, days)} days pending | 📅 {r['created_at'].strftime('%d %b %y')} | 🕒 {r['created_at'].strftime('%H:%M:%S')}")

            with c_admin:
                if is_admin:
                    new_stat = st.selectbox("Update", ["Open", "Closed", "Cancel"], 
                                          index=["Open", "Closed", "Cancel"].index(r['status']), 
                                          key=f"st_{r['id']}")
                    if st.button("Confirm ✅", key=f"btn_{r['id']}"):
                        supabase.table("issue_escalation").update({
                            "status": new_stat, 
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", r['id']).execute()
                        st.rerun()
            st.divider()
