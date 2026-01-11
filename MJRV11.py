import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime

# --- 1. Connection (รองรับทั้งรันในเครื่อง และ Online) ---
# หากรันในเครื่องให้แก้เป็น URL และ KEY ตรงๆ ได้เลยครับ
# หากรันบน Streamlit Cloud ระบบจะดึงจากช่อง Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Progress Tracker V11", layout="wide")

# --- 2. เช็คการแยกหน้า (Mobile vs Dashboard) ---
# วิธีใช้หน้า Mobile: เติม ?page=upload ต่อท้ายลิ้งค์เว็บ
query_params = st.query_params
is_upload_only = query_params.get("page") == "upload"

# ดึงข้อมูลดิบจากฐานข้อมูลเตรียมไว้
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

# --- 3. ฟังก์ชันหน้าฟอร์มบันทึกข้อมูล (ใช้ร่วมกัน) ---
def show_upload_form():
    st.header("🏗️ บันทึกความคืบหน้า")
    with st.form("progress_form", clear_on_submit=True):
        task_name = st.text_input("ชื่องาน / รหัสงาน (MEP Task)")
        
        # ฟีเจอร์ที่ 1: ตรวจสอบ Progress เดิมอัตโนมัติ
        last_val = 0
        if not df_raw.empty and task_name:
            relevant = df_raw[df_raw['task_name'] == task_name]
            if not relevant.empty:
                last_val = relevant.sort_values('created_at', ascending=False).iloc[0]['status']
                st.info(f"💡 งานนี้อัปเดตล่าสุดไว้ที่: {last_val}%")

        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("ชื่อผู้รายงาน", options=staff_list)
        
        # ใส่ค่าเริ่มต้น (value) ตาม Progress ล่าสุดที่เจอ
        status = st.number_input("Progress (%)", min_value=0, max_value=100, step=1, value=int(last_val))
        
        uploaded_file = st.file_uploader("ถ่ายภาพหน้างาน", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("ส่งข้อมูลอัปเดต")

        if submitted:
            if not task_name or not update_by:
                st.error("กรุณากรอกชื่องานและเลือกชื่อผู้รายงาน!")
            else:
                image_url = ""
                if uploaded_file:
                    try:
                        file_ext = uploaded_file.name.split('.')[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                        image_url = supabase.storage.from_('images').get_public_url(file_name)
                    except Exception as e:
                        st.error(f"Error อัปโหลดรูป: {e}")

                data = {"task_name": task_name, "update_by": update_by, "status": status, "image_url": image_url}
                supabase.table("construction_progress").insert(data).execute()
                st.success("บันทึกสำเร็จเรียบร้อย!")
                st.rerun()

# --- 4. ส่วนการแสดงผลหลัก ---
if is_upload_only:
    # --- หน้าสำหรับ Mobile (อัปเดตอย่างเดียว) ---
    show_upload_form()
else:
    # --- หน้าปกติ (Dashboard + Sidebar Form) ---
    with st.sidebar:
        show_upload_form()

    head_col1, head_col2 = st.columns([2, 1])
    with head_col1:
        st.title("📊 MEP Construction Dashboard")
        st.write(f"⏱ อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    if not df_raw.empty:
        df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
        df_latest = df_raw.sort_values('created_at', ascending=False).drop_duplicates('task_name')

        # กราฟแท่ง Progress
        fig = px.bar(df_latest, x='status', y='task_name', orientation='h', text='status',
                     range_x=[0, 100], color_discrete_sequence=['#6c757d'])
        fig.update_layout(height=400, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        # Gallery รูปภาพ (แถวละ 5 รูป ตามที่คุณพี่ต้องการ)
        st.divider()
        st.subheader("📸 ภาพถ่ายหน้างาน (เรียงตามลำดับเวลาล่าสุด)")
        
        for task in df_latest['task_name'].unique():
            task_images = df_raw[(df_raw['task_name'] == task) & (df_raw['image_url'] != "")].sort_values('created_at', ascending=False)
            
            if not task_images.empty:
                st.markdown(f"📍 **งาน: {task}**")
                cols = st.columns(5) 
                for idx, (_, row) in enumerate(task_images.iterrows()):
                    with cols[idx % 5]:
                        st.image(row['image_url'], use_container_width=True)
                        st.caption(f"{row['created_at'].strftime('%d/%m/%y')}")
                st.write("") 

        # ตารางข้อมูล
        st.subheader("📋 รายละเอียดข้อมูล")
        st.dataframe(df_raw[['task_name','update_by','status','created_at']].sort_values('created_at', ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")