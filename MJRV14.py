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

# --- 2. การตั้งค่าหน้าจอและ CSS สำหรับ iPhone (สำคัญมาก) ---
st.set_page_config(page_title="MEP Tracker V24", layout="wide")

# เช็คว่าเป็นหน้า Upload หรือไม่
is_upload_only = st.query_params.get("page") == "upload"

# CSS บังคับ iPhone ให้ไม่ล้น และจัดระเบียบหน้าจอ
st.markdown(f"""
    <style>
    /* บังคับขนาดหน้าจอสำหรับมือถือ */
    @media (max-width: 640px) {{
        .block-container {{
            padding-top: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}
        .stMetric {{ background-color: #f0f2f6; padding: 10px; border-radius: 10px; }}
        /* ปรับปุ่มให้ใหญ่ขึ้น กดง่ายใน iPhone */
        div.stButton > button:first-child {{
            width: 100%;
            height: 3em;
            margin-top: 20px;
        }}
        /* ซ่อน Sidebar ในมือถือถ้าเป็นหน้า Upload */
        {"[data-testid='stSidebar'] {display: none;}" if is_upload_only else ""}
    }}
    /* ซ่อน Header/Footer ของ Streamlit เพื่อความคลีน */
    header, footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# --- 3. ดึงข้อมูล ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)
if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    df_raw = df_raw.sort_values('created_at', ascending=False)

# --- 4. ฟังก์ชันบันทึกข้อมูล ---
def show_upload_form():
    st.header("🏗️ บันทึกงาน (Site Update)")
    task_name = st.text_input("Task name / Code name", key="task_input_mobile")
    
    current_progress = 0
    if task_name and not df_raw.empty:
        last_rec = df_raw[df_raw['task_name'] == task_name]
        if not last_rec.empty:
            current_progress = last_rec.iloc[0]['status']
            st.warning(f"ความคืบหน้าเดิม: {current_progress}%")

    with st.form("mobile_form", clear_on_submit=True):
        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("ชื่อผู้รายงาน", options=staff_list)
        status = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_progress))
        uploaded_file = st.file_uploader("ถ่ายภาพหน้างาน", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("ส่งข้อมูลอัปเดต")

        if submitted:
            if not task_name or not update_by:
                st.error("กรุณากรอกชื่อสถาปัตย์และชื่อผู้รายงาน")
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

# --- 5. แยกส่วนการแสดงผล ---
if is_upload_only:
    # หน้าจอสำหรับมือถือลูกน้อง (Add to Home Screen หน้าเฉพาะนี้)
    show_upload_form()
else:
    # หน้าจอ Dashboard สำหรับ Admin
    with st.sidebar:
        show_upload_form()

    st.title("🚧 MEP Construction Dashboard")
    
    # ส่วนของ กราฟ (เหมือนเดิมที่ปรับจูนแล้ว)
    if not df_raw.empty:
        st.subheader("📊 Progress Overview")
        df_latest = df_raw.sort_values('created_at', ascending=False).drop_duplicates('task_name')
        df_latest['display_label'] = df_latest.apply(lambda x: f"{x['update_by'] : <12} {x['task_name']}", axis=1)

        fig = px.bar(df_latest, x='status', y='display_label', orientation='h', 
                     text=df_latest['status'].apply(lambda x: f'{x}%'),
                     range_x=[0, 115], color_discrete_sequence=['#FFD1D1'])
        fig.update_traces(textposition='outside', width=0.7)
        fig.update_layout(height=max(400, len(df_latest) * 35), bargap=0.2, margin=dict(l=220),
                          yaxis=dict(autorange="reversed", tickfont=dict(family="Courier New, monospace", size=12)))
        st.plotly_chart(fig, use_container_width=True)
        
        # แสดงตาราง Admin (Edit/Delete)
        st.divider()
        st.subheader("🔐 Admin Panel")
        st.data_editor(df_raw[['id', 'task_name', 'update_by', 'status']], use_container_width=True)
