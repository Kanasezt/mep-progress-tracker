import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime

# --- 1. Connection (Security Check) ---
try:
    URL = st.secrets["https://sizcmbmkbnlolguiulsv.supabase.co"]
    KEY = st.secrets["sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Tracker V14", layout="wide")

# --- 2. ดึงข้อมูลทั้งหมดจาก Database ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    # เรียงจากใหม่ไปเก่าเพื่อให้ค่าบนสุดคือค่าล่าสุดเสมอ
    df_raw = df_raw.sort_values('created_at', ascending=False)

# --- 3. เช็คหน้า Mobile (Query Param) ---
is_upload_only = st.query_params.get("page") == "upload"

# --- 4. ฟังก์ชันหน้าฟอร์ม (เวอร์ชันดึง Progress ล่าสุดตามรูป 33) ---
def show_upload_form():
    st.header("🏗️ บันทึกความคืบหน้า")
    
    # ดึงรายชื่อ Task ทั้งหมดที่มีอยู่แล้วมาทำเป็น Auto-complete (ช่วยให้พิมพ์ง่ายขึ้น)
    existing_tasks = []
    if not df_raw.empty:
        existing_tasks = sorted(df_raw['task_name'].unique().tolist())

    with st.form("progress_form", clear_on_submit=True):
        # ใช้ text_input สำหรับรับชื่อ Task
        task_name = st.text_input("ชื่องาน / รหัสงาน (MEP Task)", help="พิมพ์ชื่อเดิมเพื่อดึง Progress ล่าสุด")
        
        # --- จุดสำคัญ: ระบบดึง Progress ล่าสุดมาตั้งต้น ---
        current_progress = 0
        if task_name and not df_raw.empty:
            # ค้นหาว่างานชื่อนี้ เคยกรอกไว้ไหม
            last_record = df_raw[df_raw['task_name'] == task_name]
            if not last_record.empty:
                current_progress = last_record.iloc[0]['status']
                st.info(f"🔍 ตรวจพบข้อมูลเดิม: งานนี้ทำค้างไว้ที่ {current_progress}%")

        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("ชื่อผู้รายงาน", options=staff_list)
        
        # ช่อง Progress จะดึงค่า current_progress มาใส่ให้เลย
        status = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_progress), step=1)
        
        uploaded_file = st.file_uploader("ถ่ายภาพหน้างาน", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("ส่งข้อมูลอัปเดต")

        if submitted:
            if not task_name or not update_by:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
                image_url = ""
                if uploaded_file:
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                    image_url = supabase.storage.from_('images').get_public_url(file_name)

                data = {"task_name": task_name, "update_by": update_by, "status": status, "image_url": image_url}
                supabase.table("construction_progress").insert(data).execute()
                st.success("บันทึกสำเร็จ!")
                st.rerun()

# --- 5. การแสดงผล Dashboard ---
if is_upload_only:
    show_upload_form()
else:
    with st.sidebar:
        show_upload_form()

    st.title("🚧 MEP Construction Progress Update")
    
    # กรองวันที่
    st.subheader("🗓️ กรองข้อมูลย้อนหลัง")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        start_date = st.date_input("ตั้งแต่วันที่", datetime.now())
    with col_f2:
        end_date = st.date_input("จนถึงวันที่", datetime.now())

    if not df_raw.empty:
        mask = (df_raw['created_at'].dt.date >= start_date) & (df_raw['created_at'].dt.date <= end_date)
        df_filtered = df_raw[mask].copy()

        if not df_filtered.empty:
            # กราฟ
            df_latest = df_filtered.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            st.subheader("📊 Dashboard & รายงาน")
            # --- แก้ไขส่วนกราฟแท่ง (เพิ่มเครื่องหมาย %) ---
            fig = px.bar(
                df_latest, 
                x='status', 
                y='task_name', 
                orientation='h', 
                text=df_latest['status'].apply(lambda x: f'{x}%'), # เพิ่ม % หลังตัวเลขบนแท่ง
                range_x=[0, 115], # ขยายขอบเขต X เล็กน้อยเพื่อให้เครื่องหมาย % ไม่โดนตัด
                color_discrete_sequence=['#FFD1D1'],
                hover_data={'status': True} # ให้โชว์ข้อมูลเวลาเอาเมาส์ไปชี้
            )
            
            # ปรับแต่งให้ตัวเลข % อยู่ข้างนอกแท่งกราฟเพื่อให้มองเห็นชัดเจน
            fig.update_traces(textposition='outside')
            
            # ปรับแต่งแกน X ให้โชว์เครื่องหมาย % ด้วย
            fig.update_layout(
                xaxis_ticksuffix="%", 
                height=400, 
                yaxis_title=""
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # ตารางข้อมูลและปุ่ม Export
            st.divider()
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1: st.subheader("📋 ตารางข้อมูล (Data Table)")
            with col_t2:
                csv = df_filtered[['task_name', 'update_by', 'status', 'created_at']].to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Export CSV", data=csv, file_name="MEP_Export.csv", mime="text/csv")
            
            st.dataframe(df_filtered[['task_name', 'update_by', 'status', 'created_at']], use_container_width=True)

            # Gallery รูปภาพ (แถวละ 5 รูป)
            st.divider()
            st.subheader("📸 ภาพความคืบหน้าหน้างาน")
            for task in df_latest['task_name'].unique():
                img_data = df_filtered[(df_filtered['task_name'] == task) & (df_filtered['image_url'] != "")]
                if not img_data.empty:
                    st.markdown(f"📍 **งาน: {task}**")
                    cols = st.columns(5)
                    for i, (_, row) in enumerate(img_data.iterrows()):
                        with cols[i % 5]:
                            st.image(row['image_url'], use_container_width=True)
                            st.caption(f"{row['created_at'].strftime('%d/%m/%y %H:%M')}")
        else:
            st.warning("ไม่พบข้อมูลในช่วงวันที่เลือก")
    else:

        st.info("ยังไม่มีข้อมูล")

