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

st.set_page_config(page_title="MEP Tracker V28 Admin", layout="wide")

# --- CSS สำหรับ iPhone (Responsive Fix) ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    .stPlotlyChart { width: 100% !important; }
    @media (max-width: 640px) {
        div.stButton > button { width: 100% !important; }
    }
    .stTextInput, .stSelectbox, .stNumberInput { width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Login System ---
def admin_login():
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        if st.query_params.get("page") != "upload":
            st.title("🔐 MEP Admin Login")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Login"):
                if user == "admin" and pw == "mep1234":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            return False
    return True

# --- 3. Data Fetching ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)
if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    df_raw = df_raw.sort_values('created_at', ascending=False)

is_upload_only = st.query_params.get("page") == "upload"

# --- 4. ฟังก์ชันบันทึกข้อมูล (เพิ่มแสดงชื่อผู้รายงานเดิม) ---
def show_upload_form():
    st.header("🏗️ Update Progress")
    task_name = st.text_input("Task name / Code name (MEP Task)", key="task_input_key")
    
    current_progress = 0
    previous_updater = "N/A"
    
    if task_name and not df_raw.empty:
        # ดึงข้อมูลล่าสุดของ Task นี้
        last_record = df_raw[df_raw['task_name'] == task_name]
        if not last_record.empty:
            current_progress = last_record.iloc[0]['status']
            previous_updater = last_record.iloc[0]['update_by']
            # แสดงข้อความตามที่คุณพี่ต้องการ: "Current progress is X% by Updater"
            st.info(f"🔍 Current progress is {current_progress}% by \"{previous_updater}\"")

    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Autapol", "Suppawat", "Jirapat", "Puwanai", "Anu", "Chatchai(Art)", "Chatchai(P'Pok)", "Pimchanok"]
        update_by = st.selectbox("Select Your Name", options=staff_list)
        status = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_progress))
        uploaded_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
        submitted = st.form_submit_button("Submit Progress")

        if submitted:
            if not task_name or not update_by:
                st.error("Please fill Task Name and Select Your Name")
            else:
                image_url = ""
                if uploaded_file:
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(file_name, uploaded_file.read())
                    image_url = supabase.storage.from_('images').get_public_url(file_name)

                data = {"task_name": task_name, "update_by": update_by, "status": status}
                supabase.table("construction_progress").insert(data).execute()
                st.success("Recorded!")
                st.rerun()

# --- 5. Dashboard Logic ---
if is_upload_only:
    show_upload_form()
else:
    if admin_login():
        with st.sidebar:
            if st.button("🚪 Logout"):
                st.session_state.admin_logged_in = False
                st.rerun()
            st.divider()
            show_upload_form()

        st.title("🚧 MEP Construction Dashboard")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1: start_date = st.date_input("From date", datetime.now())
        with col_f2: end_date = st.date_input("To date", datetime.now())

        if not df_raw.empty:
            mask = (df_raw['created_at'].dt.date >= start_date) & (df_raw['created_at'].dt.date <= end_date)
            df_filtered = df_raw[mask].copy()

            if not df_filtered.empty:
                df_latest = df_filtered.sort_values('created_at', ascending=False).drop_duplicates('task_name')
                df_latest['display_label'] = df_latest.apply(lambda x: f"{x['update_by'] : <15} {x['task_name']}", axis=1)

                st.subheader("📊 Progress Overview")
                fig = px.bar(df_latest, x='status', y='display_label', orientation='h', 
                             text=df_latest['status'].apply(lambda x: f'{x}%'),
                             range_x=[0, 115], color_discrete_sequence=['#FFD1D1'])
                fig.update_traces(textposition='outside', width=0.6)
                
                fig.update_layout(
                    xaxis_ticksuffix="%", 
                    height=max(400, len(df_latest) * 30), 
                    yaxis_title="", 
                    bargap=0.2, 
                    margin=dict(l=250),
                    yaxis=dict(
                        autorange="reversed", 
                        tickfont=dict(family="Calibri, monospace", size=16)
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

                # --- 6. Admin Panel ---
                st.divider()
                st.subheader("🔐 Admin Control Panel (Edit / Delete)")
                edited_df = st.data_editor(
                    df_filtered[['id', 'task_name', 'update_by', 'status', 'created_at']],
                    column_config={
                        "id": None, 
                        "image_url": st.column_config.LinkColumn("Photo Link"),
                        "status": st.column_config.NumberColumn("Progress %", min_value=0, max_value=100),
                        "created_at": st.column_config.DatetimeColumn("Date Time", disabled=True)
                    },
                    key="admin_editor",
                    use_container_width=True,
                    num_rows="dynamic"
                )

                if st.button("💾 Save All Changes", type="primary"):
                    for index, row in edited_df.iterrows():
                        supabase.table("construction_progress").update({
                            "task_name": row['task_name'], "update_by": row['update_by'],
                            "status": row['status'], "image_url": row['image_url']
                        }).eq("id", row['id']).execute()
                    st.success("Updates saved successfully!")
                    st.rerun()

                st.divider()
                st.warning("⚠️ Delete Records")
                id_to_delete = st.selectbox("Select ID to Delete", options=df_filtered['id'].tolist(), 
                                            format_func=lambda x: f"ID: {x} | {df_filtered[df_filtered['id']==x]['task_name'].values[0]}")
                if st.button(f"🗑️ Delete Record {id_to_delete}"):
                    supabase.table("construction_progress").delete().eq("id", id_to_delete).execute()
                    st.rerun()

                # 7. Gallery
                st.divider()
                st.subheader("📸 Photo Progress")
                for task in df_latest['task_name'].unique():
                    img_data = df_filtered[(df_filtered['task_name'] == task) & (df_filtered['image_url'] != "")]
                    if not img_data.empty:
                        st.markdown(f"📍 **Task: {task}**")
                        cols = st.columns(5)
                        for i, (_, row) in enumerate(img_data.iterrows()):
                            with cols[i % 5]:
                                st.image(row['image_url'], use_container_width=True)
                                st.caption(f"{row['created_at'].strftime('%d/%m/%y %H:%M')}")
            else: st.warning("No data found.")
        else: st.info("No data available.")
