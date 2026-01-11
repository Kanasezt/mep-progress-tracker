import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Tracker V16", layout="wide")

# --- 2. ดึงข้อมูล ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    df_raw = df_raw.sort_values('created_at', ascending=False)

# --- 3. แยกหน้า Mobile ---
is_upload_only = st.query_params.get("page") == "upload"

# --- 4. ฟังก์ชันบันทึกข้อมูล (ปรับเพื่อแก้ปัญหา Auto Progress) ---
def show_upload_form():
    st.header("🏗️ บันทึกความคืบหน้า")
    
    # 4.1 ดึงค่าล่าสุดออกมาคำนวณก่อนสร้างฟอร์ม
    task_name = st.text_input("ชื่องาน / รหัสงาน (MEP Task)", key="task_input_key")
    
    current_progress = 0
    if task_name and not df_raw.empty:
        last_record = df_raw[df_raw['task_name'] == task_name]
        if not last_record.empty:
            current_progress = last_record.iloc[0]['status']
            st.markdown(f"""
                <div style="background-color: #FFD1D1; padding: 10px; border-radius: 5px; color: black; margin-bottom: 10px;">
                    🔍 Found previosly progress is : <b>{current_progress}%</b>
                </div>
            """, unsafe_allow_html=True)

    # 4.2 เริ่มส่วนฟอร์มบันทึก
    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("Select Your Name", options=staff_list)
        
        # ใส่ค่า current_progress ที่ดึงมาได้ลงไปในช่องนี้
        status = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_progress))
        
        uploaded_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("Submit Progress")

        if submitted:
            if not task_name or not update_by:
                st.error("Fill the Task and select Your Name")
            else:
                image_url = ""
                if uploaded_file:
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                    image_url = supabase.storage.from_('images').get_public_url(file_name)

                data = {"task_name": task_name, "update_by": update_by, "status": status, "image_url": image_url}
                supabase.table("construction_progress").insert(data).execute()
                st.success("Recorded success")
                st.rerun()

# --- 5. การแสดงผล Dashboard ---
if is_upload_only:
    show_upload_form()
else:
    with st.sidebar:
        show_upload_form()

    st.title("🚧 MEP Construction Dashboard")
    
    st.subheader("🗓️ History Search")
    col_f1, col_f2 = st.columns(2)
    with col_f1: start_date = st.date_input("From date", datetime.now())
    with col_f2: end_date = st.date_input("To date", datetime.now())

    if not df_raw.empty:
        mask = (df_raw['created_at'].dt.date >= start_date) & (df_raw['created_at'].dt.date <= end_date)
        df_filtered = df_raw[mask].copy()

        if not df_filtered.empty:
            df_latest = df_filtered.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            
            st.subheader("📊 Dashboard & Report")
            # กราฟแท่งสีชมพู #FFD1D1 ตามรูป 337af4
            fig = px.bar(
                df_latest, 
                x='status', 
                y='task_name', 
                orientation='h', 
                text=df_latest['status'].apply(lambda x: f'{x}%'),
                range_x=[0, 115],
                color_discrete_sequence=['#FFD1D1']
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(xaxis_ticksuffix="%", height=400, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

            # Table & Export
            st.divider()
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1: st.subheader("📋 Raw data table")
            with col_t2:
                csv = df_filtered[['created_at', 'task_name', 'status', 'update_by', 'image_url']].to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Export CSV", data=csv, file_name="MEP_Export.csv", mime="text/csv")
            st.dataframe(df_filtered[['created_at', 'task_name', 'status', 'update_by']], use_container_width=True)

            # Gallery
            st.divider()
            st.subheader("📸 Photo Progress")
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
            st.warning("ไม่พบข้อมูลในช่วงที่เลือก")
    else:
        st.info("ยังไม่มีข้อมูล")

