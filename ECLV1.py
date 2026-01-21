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

st.set_page_config(page_title="Issue Escalation V3.4", layout="wide")

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
    .status-badge { padding: 4px 8px; border-radius: 5px; font-weight: bold; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
        return df_raw
    except:
        return pd.DataFrame()

# --- 4. Excel Export Function (With Photos & Split DateTime) ---
def export_excel_with_images(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # เตรียมข้อมูลสำหรับ Export
        df_ex = dataframe.copy()
        df_ex['id'] = df_ex['id'].apply(lambda x: f"{x:03d}")
        df_ex['created_date'] = df_ex['created_at'].dt.strftime('%d-%b-%y')
        df_ex['created_time'] = df_ex['created_at'].dt.strftime('%I:%M:%S %p')
        
        # จัดเรียงคอลัมน์ตามภาพตัวอย่าง
        cols = ['id', 'staff_name', 'issue_detail', 'related_to', 'status', 'created_date', 'created_time']
        df_final = df_ex[cols]
        df_final.to_excel(writer, sheet_name='Report', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Report']
        worksheet.set_column('F:F', 15) # Image Column Space
        worksheet.set_default_row(80)   # Row Height for Images
        
        # ใส่รูปภาพลงในช่อง
        for i, url in enumerate(df_ex['image_url']):
            if url and url.startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(i + 1, 7, url, {'image_data': img_data, 'x_scale': 0.1, 'y_scale': 0.1, 'x_offset': 5, 'y_offset': 5})
                except: continue
    return output.getvalue()

df = load_data()

# --- 5. Main UI ---
st.title("🚨 Issue Escalation V3.4")

c1, c2, c3 = st.columns(3)
op = len(df[df['status'] == 'Open']) if not df.empty else 0
cl = len(df[df['status'] == 'Closed']) if not df.empty else 0
can = len(df[df['status'] == 'Cancel']) if not df.empty else 0

c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 6. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** Fill Name (50 characters)")
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    u_detail = st.text_area("** Issue Detail description (500 characters)", height=100)
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

# --- 7. Dashboard ---
if not df.empty:
    st.divider()
    st.subheader("📋 Dashboard")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name/Detail")
    f_stat = f2.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    if f3.button("🚀 Prepare Excel with Photos"):
        with st.spinner("กำลังสร้างไฟล์พร้อมรูปภาพ..."):
            excel_data = export_excel_with_images(df_f)
            st.download_button("📥 Click to Download", data=excel_data, file_name=f"Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

    # ส่วนการแสดงผลรายการ
    now = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info, c_admin = st.columns([1.5, 3.5, 1])
            with c_img:
                if r['image_url']: st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
                else: st.write("🖼️ No Image")
            
            with c_info:
                # ข้อ 2: ใส่ ID 001-999 หน้าชื่อ
                st.markdown(f"### {r['id']:03d} - {r['staff_name']}")
                
                # ข้อ 3: คำนวณวัน Pending
                created_at = r['created_at'].replace(tzinfo=timezone.utc) if r['created_at'].tzinfo is None else r['created_at']
                diff = (now - created_at).days
                pending_text = f"{diff} days pending" if r['status'] != 'Closed' else "Completed"
                
                st.write(f"**Detail:** {r['issue_detail']}")
                st.caption(f"🏷️ {r['related_to']} | 📅 {created_at.strftime('%d %b %Y')} | ⏳ {pending_text}")
                st.markdown(f"Status: `{r['status']}`")

            # ข้อ 2: Admin แก้ไข status ตรงนี้เลย
            with c_admin:
                if st.sidebar.text_input("Admin Password", type="password", key="side_pwd") == "pm1234":
                    new_stat = st.selectbox("Update", ["Open", "Closed", "Cancel"], index=["Open", "Closed", "Cancel"].index(r['status']), key=f"sel_{r['id']}")
                    if st.button("Confirm", key=f"btn_{r['id']}"):
                        supabase.table("issue_escalation").update({"status": new_stat}).eq("id", r['id']).execute()
                        st.rerun()
            st.divider()

# --- 8. Sidebar Admin Logged In Status ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if st.session_state.get('side_pwd') == "pm1234":
        st.success("Admin Logged In ✅")
    else:
        st.info("กรุณาใส่รหัสผ่านเพื่อแก้ไขข้อมูล")
