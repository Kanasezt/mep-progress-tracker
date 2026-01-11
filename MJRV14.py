import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime

# --- 1. Connection (Supabase) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Tracker V19", layout="wide")

# --- 2. Data Fetching ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    df_raw = df_raw.sort_values('created_at', ascending=False)

is_upload_only = st.query_params.get("page") == "upload"

# --- 4. Update Form Function ---
def show_upload_form():
    st.header("🏗️ Update Progress")
    
    task_name = st.text_input("Task Name / Code (MEP Task)", key="task_input_key")
    
    current_progress = 0
    if task_name and not df_raw.empty:
        last_record = df_raw[df_raw['task_name'] == task_name]
        if not last_record.empty:
            current_progress = last_record.iloc[0]['status']
            last_user = last_record.iloc[0]['update_by']
            st.markdown(f"""
                <div style="background-color: #FFD1D1; padding: 10px; border-radius: 5px; color: black; margin-bottom: 15px; border: 1px solid #ffb1b1;">
                    🔍 <b>Latest Update:</b> {current_progress}% by {last_user}
                </div>
            """, unsafe_allow_html=True)

    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("Select Your Name", options=staff_list)
        status = st.number_input("Current Progress (%)", min_value=0, max_value=100, value=int(current_progress))
        uploaded_file = st.file_uploader("Upload Site Photo", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("Submit Update")

        if submitted:
            if not task_name or not update_by:
                st.error("Please fill in all required fields.")
            else:
                image_url = ""
                if uploaded_file:
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                    image_url = supabase.storage.from_('images').get_public_url(file_name)

                data = {"task_name": task_name, "update_by": update_by, "status": status, "image_url": image_url}
                supabase.table("construction_progress").insert(data).execute()
                st.success("Record Updated!")
                st.rerun()

# --- 5. Dashboard ---
if is_upload_only:
    show_upload_form()
else:
    with st.sidebar:
        show_upload_form()

    st.title("🚧 MEP Construction Dashboard")
    
    st.subheader("🗓️ Filter History")
    col_f1, col_f2 = st.columns(2)
    with col_f1: start_date = st.date_input("Start Date", datetime.now())
    with col_f2: end_date = st.date_input("End Date", datetime.now())

    if not df_raw.empty:
        mask = (df_raw['created_at'].dt.date >= start_date) & (df_raw['created_at'].dt.date <= end_date)
        df_filtered = df_raw[mask].copy()

        if not df_filtered.empty:
            df_latest = df_filtered.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            
            st.subheader("📊 Progress Overview")
            
            # --- ปรับแต่งแกน Y ให้แยกคอลัมน์และกราฟบางลง ---
            fig = px.bar(
                df_latest, 
                x='status', 
                y=['update_by', 'task_name'], # สลับลำดับเพื่อโชว์ชื่อคนก่อนชื่อ Task ในคอลัมน์ที่แยกกัน
                orientation='h', 
                text=df_latest['status'].apply(lambda x: f'{x}%'),
                range_x=[0, 115],
                color_discrete_sequence=['#FFD1D1'],
                category_orders={"task_name": df_latest['task_name'].tolist()} 
            )
            
            fig.update_traces(
                textposition='outside',
                width=0.6 # ปรับความหนาของแท่งกราฟ (0.1 - 1.0) ยิ่งน้อยยิ่งบาง
            )
            
            fig.update_layout(
                xaxis_ticksuffix="%", 
                height=max(400, len(df_latest) * 40), # ความสูงยืดหยุ่นตามจำนวน Task
                yaxis_title="",
                bargap=0.4, # เพิ่มช่องว่างระหว่างแท่งเพื่อให้ดู Compact
                margin=dict(l=200) # เพิ่มพื้นที่ด้านซ้ายสำหรับชื่อที่แยกคอลัมน์
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Table & Gallery (เหมือนเดิม)
            st.divider()
            st.subheader("📋 Raw Data Table")
            st.dataframe(df_filtered[['created_at', 'task_name', 'status', 'update_by']], use_container_width=True)

            st.divider()
            st.subheader("📸 Site Photo Logs")
            for task in df_latest['task_name'].unique():
                img_data = df_filtered[(df_filtered['task_name'] == task) & (df_filtered['image_url'] != "")]
                if not img_data.empty:
                    st.markdown(f"📍 **Task: {task}**")
                    cols = st.columns(5)
                    for i, (_, row) in enumerate(img_data.iterrows()):
                        with cols[i % 5]:
                            st.image(row['image_url'], use_container_width=True)
                            st.caption(f"{row['created_at'].strftime('%d/%m/%y %H:%M')}")
        else:
            st.warning("No records found.")
    else:
        st.info("No data available.")
