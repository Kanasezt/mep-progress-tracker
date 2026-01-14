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

st.set_page_config(page_title="MEP Tracker V41", layout="wide")

# --- CSS Styling ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .dashboard-link {
        float: right; text-decoration: none !important; background-color: #FF4B4B !important;
        color: white !important; padding: 10px 20px; border-radius: 8px;
        font-weight: bold; font-size: 14px; display: inline-block; border: none;
    }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; 
        color: white !important;
        border: 1px solid #0047AB !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. Data Fetching ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)

min_date = datetime.now().date()
if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    min_date = df_raw['created_at'].min().date()

# --- 3. Function: Upload Form ---
def show_upload_form(show_dash_btn=False):
    col_t, col_b = st.columns([3, 1])
    with col_t: st.header("🏗️ Update Progress")
    if show_dash_btn:
        with col_b: st.markdown('<br><a href="/?page=dashboard" target="_self" class="dashboard-link">📊 View Dashboard</a>', unsafe_allow_html=True)

    task_name = st.text_input("Task name / Code name (MEP Task)", key="task_input_key")
    current_p = 0
    if task_name and not df_raw.empty:
        last_task = df_raw[df_raw['task_name'] == task_name].sort_values('created_at', ascending=False)
        if not last_task.empty:
            current_p = last_task.iloc[0]['status']
            st.info(f"🔍 Current progress is {current_p}%")

    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Puwanai Torpradit", "Zhangxi (Sea)", "Puripat Nammontree", "Ravicha Thaisiam", "Kraiwut Chaiyarak", "Sakda Suwan", "Thanadol Chanpattanakij", "Thanakit Thundon", "Anu Yaemsajja", "Chawalit Posrima", "Amnat Pagamas", "Thotsapon Sripornwong", "Tanupat mongkholkan", "Putthipong Niyomkitjakankul", "Ekkapol Tangngamsakul", "Natthaphat Suwanmanee", "Kantapon Phasee", "Chatchai Sripradoo", "Chatchai Chanprasert", "Jirapat Phobtavorn", "Thanadon Tuydoi (Tontan)", "Pimchanok Janjamsai"]
        u_by = st.selectbox("Select Your Name", options=staff_list)
        stat = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_p))
        up_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
        if st.form_submit_button("Submit Progress"):
            if task_name and u_by:
                img_url = ""
                if up_file:
                    f_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, up_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                supabase.table("construction_progress").insert({"task_name": task_name, "update_by": u_by, "status": stat, "image_url": img_url}).execute()
                st.success("Recorded!"); st.rerun()
            else: st.error("Please fill Name and Task")

# --- 4. Main App Logic ---
page = st.query_params.get("page", "dashboard")

if page == "upload":
    show_upload_form(show_dash_btn=True)
else:
    with st.sidebar:
        if "admin_logged_in" not in st.session_state: st.session_state.admin_logged_in = False
        if not st.session_state.admin_logged_in:
            st.title("🔐 Admin Login")
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.button("Login"):
                if u == "admin" and p == "mep1234": st.session_state.admin_logged_in = True; st.rerun()
                else: st.error("Invalid")
        else:
            if st.button("🚪 Logout"): st.session_state.admin_logged_in = False; st.rerun()
            st.divider(); show_upload_form(False)

    st.title("🚧 MEP Construction Dashboard")
    if not st.session_state.admin_logged_in:
        st.markdown('<a href="/?page=upload" target="_self" style="color:#ff4b4b; text-decoration:none;">⬅️ Back to Upload Photo</a>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    start_d = c1.date_input("From date", min_date) 
    end_d = c2.date_input("To date", datetime.now())

    if not df_raw.empty:
        mask = (df_raw['created_at'].dt.date >= start_d) & (df_raw['created_at'].dt.date <= end_d)
        df_f = df_raw[mask].copy()

        if not df_f.empty:
            df_latest = df_f.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            df_latest['display_label'] = df_latest.apply(lambda x: f"{x['update_by'] : <12} | {x['task_name']}", axis=1)
            
            st.subheader("📊 Progress Overview")
            # บังคับ range_x ให้กว้างขึ้นเพื่อให้เลข % ที่อยู่ข้างนอกไม่หลุดขอบ
            fig = px.bar(df_latest, x='status', y='display_label', orientation='h', 
                         range_x=[0, 125], color_discrete_sequence=['#FFD1D1'])
            
            # ✅ แก้ไขตรงนี้: เอาเลขออกนอก Bar และขยายฟอนต์
            fig.update_traces(
                texttemplate='%{x}%', 
                textposition='outside', 
                textfont_size=20, # ขนาดฟอนต์ใหญ่สะใจ
                cliponaxis=False  # ป้องกันเลขโดนตัดถ้าอยู่ใกล้ขอบ
            )

            fig.update_layout(
                xaxis_ticksuffix="%", height=max(400, len(df_latest)*45), 
                yaxis_title="", margin=dict(l=280, r=60), 
                yaxis=dict(autorange="reversed", tickfont=dict(family="Calibri", size=16))
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- Gallery ---
            st.divider(); st.subheader("📸 Photo Progress")
            for t in df_latest['task_name'].unique():
                imgs = df_f[(df_f['task_name'] == t) & (df_f['image_url'].str.startswith('http', na=False))].sort_values('created_at', ascending=False)
                if not imgs.empty:
                    st.markdown(f"📍 **Task: {t}**")
                    cols = st.columns(5)
                    for i, (_, r) in enumerate(imgs.iterrows()):
                        with cols[i%5]: st.image(r['image_url'], use_container_width=True); st.caption(r['created_at'].strftime('%d/%m %H:%M'))

            # --- Admin Panel ---
            if st.session_state.admin_logged_in:
                st.divider(); st.subheader("🛠️ Admin Panel")
                df_admin = df_f.sort_values('id', ascending=False)
                edited_df = st.data_editor(
                    df_admin[['id', 'task_name', 'update_by', 'status', 'image_url', 'created_at']],
                    column_config={"id": st.column_config.NumberColumn("Real ID", disabled=True), "created_at": st.column_config.DatetimeColumn("Date Time", disabled=True)},
                    hide_index=True, use_container_width=True
                )
                if st.button("💾 Save Changes", type="primary"):
                    for _, r in edited_df.iterrows():
                        supabase.table("construction_progress").update({"task_name":r['task_name'], "update_by":r['update_by'], "status":r['status'], "image_url":r['image_url']}).eq("id", r['id']).execute()
                    st.success("Saved!"); st.rerun()

                del_id = st.selectbox("Select ID to Delete", options=df_admin['id'].tolist())
                if st.button(f"🗑️ Confirm Delete ID: {del_id}"):
                    supabase.table("construction_progress").delete().eq("id", del_id).execute()
                    st.rerun()
