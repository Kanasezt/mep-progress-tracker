import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime

# --- 1. Connection ---
URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Tracker V8", layout="wide")

# --- 2. Sidebar Form ---
with st.sidebar:
    st.header("🏗️ บันทึกความคืบหน้า")
    with st.form("progress_form", clear_on_submit=True):
        task_name = st.text_input("ชื่องาน / รหัสงาน (MEP Task)")
        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("ชื่อผู้รายงาน", options=staff_list)
        status = st.number_input("Progress (%)", min_value=0, max_value=100, step=1)
        uploaded_file = st.file_uploader("ถ่ายภาพหน้างาน", type=['jpg', 'png', 'jpeg'])
        
        submitted = st.form_submit_button("ส่งข้อมูล")

        if submitted:
            if not task_name or not update_by:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
                image_url = ""
                if uploaded_file:
                    try:
                        file_ext = uploaded_file.name.split('.')[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        # อัปโหลดไฟล์
                        supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                        # ดึง URL ของรูปออกมา
                        image_url = supabase.storage.from_('images').get_public_url(file_name)
                    except Exception as e:
                        st.error(f"Error Upload: {e}")

                # บันทึกลง Table
                data = {"task_name": task_name, "update_by": update_by, "status": status, "image_url": image_url}
                supabase.table("construction_progress").insert(data).execute()
                st.success("บันทึกและส่งรูปสำเร็จ!")
                st.rerun()

# --- 3. Dashboard ---
st.title("📊 MEP Progress Dashboard")

response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    
    # กรองข้อมูลล่าสุดของแต่ละงาน
    df_latest = df_raw.sort_values('created_at', ascending=False).drop_duplicates('task_name')
    
    # --- ส่วนที่ 1: กราฟแท่ง ---
    fig = px.bar(df_latest, x='status', y='task_name', orientation='h', text='status',
                 range_x=[0, 100], color_discrete_sequence=['#6c757d'])
    fig.update_layout(height=400, yaxis_title="")
    st.plotly_chart(fig, width='stretch')

    # --- ส่วนที่ 2: Gallery รูปภาพ (แก้ตามรูป 24 และ 25) ---
    st.divider()
    st.subheader("📸 ภาพถ่ายหน้างาน (เรียงตามลำดับเวลา)")
    
    for task in df_latest['task_name'].unique():
        # ดึงรูปทั้งหมดของ Task นี้
        task_images = df_raw[(df_raw['task_name'] == task) & (df_raw['image_url'] != "")].sort_values('created_at', ascending=False)
        
        if not task_images.empty:
            st.markdown(f"📍 **งาน: {task}**")
            # สร้างตาราง 6 คอลัมน์สำหรับ Preview เล็กๆ
            cols = st.columns(6) 
            for idx, (_, row) in enumerate(task_images.iterrows()):
                with cols[idx % 6]:
                    # ใช้ width='stretch' เพื่อแก้ Error ในรูป 21
                    st.image(row['image_url'], width='stretch', caption=row['created_at'].strftime('%d/%m/%y'))
            st.write("") # เว้นบรรทัด
else:
    st.info("ยังไม่มีข้อมูลในระบบ")