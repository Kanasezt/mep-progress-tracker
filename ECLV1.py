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

st.set_page_config(page_title="Issue Escalation V2.7", layout="wide")

# --- 2. CSS Styling (ส้มเข้ม / เขียวเข้ม / เทาเข้ม) ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-square { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 32px; font-weight: bold; display: block; }
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

df = load_data()

# --- 4. Function: Export Excel with Images ---
def export_to_excel(dataframe):
    output = io.BytesIO()
    # ระบุ engine='xlsxwriter' ให้ชัดเจน
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Issues', index=False)
        workbook  = writer.book
        worksheet = writer.sheets['Issues']
        
        # ปรับหัวตารางและขนาด
        worksheet.set_column('H:H', 25) # คอลัมน์ image_url
        worksheet.set_default_row(80)    # ความสูงแถว
        
        for i, url in enumerate(dataframe['image_url']):
            if url and isinstance(url, str) and url.startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        img_data = io.BytesIO(resp.content)
                        # แทรกรูปในคอลัมน์ I (index 8)
                        worksheet.insert_image(i + 1, 8, url, {
                            'image_data': img_data,
                            'x_scale': 0.15, 
                            'y_scale': 0.15,
                            'x_offset': 5,
                            'y_offset': 5,
                            'positioning': 1
                        })
                except:
                    continue
    return output.getvalue()

# --- 5. UI Header ---
st.title("🚨 Issue Escalation Portal V2.7")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 6. Form & Table (ส่วนเดิม) ---
# ... [ใส่ Code ส่วน Form และ Dashboard ของคุณพี่ไว้ตรงนี้] ...

if not df.empty:
    st.subheader("📋 All Issue Created")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name / Description")
    f_stat = f2.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # ปุ่ม Export Excel
    if st.button("🚀 Prepare Excel with Photos"):
        with st.spinner('กำลังสร้างไฟล์พร้อมรูปภาพ...'):
            excel_file = export_to_excel(df_f)
            st.download_button(
                label="📥 Click here to Download Excel",
                data=excel_file,
                file_name=f"Issue_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ส่วนแสดงผลตาราง Dashboard...
