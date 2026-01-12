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

st.set_page_config(page_title="MEP Tracker V32", layout="wide")

# --- CSS Styling ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    .stPlotlyChart { width: 100% !important; }
    @media (max-width: 640px) { div.stButton > button { width: 100% !important; } }
    
    /* ปุ่ม Dashboard สำหรับหน้า Upload */
    .dashboard-link {
        float: right; text-decoration: none; background-color: #262730; color: #ff4b4b !important;
        padding: 8px 15px; border-radius: 10px; border: 1px solid #ff4b4b; font-weight: bold; font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. State Management & Logic ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ตรวจสอบ Parameter หน้า
page = st.query_params.get("page", "dashboard") # default เป็น dashboard

# --- 3. Data Fetching ---
response = supabase.table("construction_progress").select("*").execute()
df_raw = pd.DataFrame(response.data)
if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_localize(None)
    df_raw = df_raw.sort_values('created_at', ascending=False)

# --- 4. Function: Upload Form (สำหรับลูกน้อง) ---
def show_upload_form():
    col_t, col_b = st.columns([3, 1])
    col_t.header("🏗️ Update Progress")
    # ปุ่มไปหน้า Dashboard (View Only)
    col_b.markdown('<br><a href="/?page=dashboard" target="_self" class="dashboard-link">📊 View Dashboard</a>', unsafe_allow_html=True)

    task_name = st.text_input("Task name / Code name (MEP Task)", key="task_input_key")
    current_progress, prev_updater = 0, "N/A"
    
    if task_name and not df_raw.empty:
        last = df_raw[df_raw['task_name'] == task_name]
        if not last.empty:
            current_progress, prev_updater = last.iloc[0]['status'], last.iloc[0]['update_by']
            st.info(f"🔍 Current progress is {current_progress}% by \"{prev_updater}\"")

    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Puwanai Torpradit", "Zhangxi (Sea)", "Puripat Nammontree", "Ravicha Thaisiam", "Kraiwut Chaiyarak", "Sakda Suwan", "Thanadol Chanpattanakij", "Thanakit Thundon", "Anu Yaemsajja", "Chawalit Posrima", "Amnat Pagamas", "Thotsapon Sripornwong", "Tanupat mongkholkan", "Putthipong Niyomkitjakankul", "Ekkapol Tangngamsakul", "Natthaphat Suwanmanee", "Kantapon Phasee", "Chatchai Sripradoo", "Chatchai Chanprasert", "Jirapat Phobtavorn", "Thanadon Tuydoi (Tontan)", "Pimchanok Janjamsai"]
        update_by = st.selectbox("Select Your Name", options=staff_list)
        status = st.number_input("Progress (%)", min_value=0, max_value=100, value=int(current_progress))
        uploaded_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("Submit Progress"):
            if task_name and update_by:
                img_url = ""
                if uploaded_file:
                    f_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, uploaded_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                supabase.table("construction_progress").insert({"task_name": task_name, "update_by": update_by, "status": status, "image_url": img_url}).execute()
                st.success("Recorded!")
                st.rerun()
            else: st.error("Please fill Name and Task")

# --- 5. Main Routing ---

# --- หน้า UPLOAD (ลูกน้อง) ---
if page == "upload":
    show_upload_form()

# --- หน้า DASHBOARD ---
else:
    # 5.1 Sidebar สำหรับ Admin Login
    with st.sidebar:
        if not st.session_state.admin_logged_in:
            st.subheader("🔐 Admin Access")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Login"):
                if u == "admin" and p == "mep1234":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else: st.error("Wrong pass")
        else:
            st.success("Admin Mode")
            if st.button("Logout"):
                st.session_state.admin_logged_in = False
                st.rerun()
            st.divider()
            # ในโหมด Admin ให้โชว์ฟอร์มแก้/เพิ่มงานใน Sidebar
            show_upload_form()

    # 5.2 เนื้อหา Dashboard
    st.title("🚧 MEP Construction Dashboard")
    
    # ปุ่มไปหน้า Upload (สำหรับลูกน้องที่หลงมาหน้า View)
    if not st.session_state.admin_logged_in:
        st.markdown('<a href="/?page=upload" target="_self" style="text-decoration:none; color:#ff4b4b;">⬅️ Back to Upload Photo</a>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    start_d = c1.date_input("From", datetime.now())
    end_d = c2.date_input("To", datetime.now())

    if not df_raw.empty:
        df_f = df_raw[(df_raw['created_at'].dt.date >= start_d) & (df_raw['created_at'].dt.date <= end_d)].copy()
        if not df_f.empty:
            # กราฟ (View Only)
            df_l = df_f.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            df_l['label'] = df_l.apply(lambda x: f"{x['update_by'] : <12} | {x['task_name']}", axis=1)
            
            st.subheader("📊 Progress Overview")
            fig = px.bar(df_l, x='status', y='label', orientation='h', text=df_l['status'].apply(lambda x: f'{x}%'), range_x=[0, 115], color_discrete_sequence=['#FFD1D1'])
            fig.update_layout(xaxis_ticksuffix="%", height=max(400, len(df_l)*35), yaxis_title="", margin=dict(l=280), yaxis=dict(autorange="reversed", tickfont=dict(family="Calibri", size=16)))
            st.plotly_chart(fig, use_container_width=True)

            # ส่วนแกลเลอรี่ (View Only)
            st.divider()
            st.subheader("📸 Photo Gallery")
            for t in df_l['task_name'].unique():
                imgs = df_f[(df_f['task_name'] == t) & (df_f['image_url'].str.startswith('http', na=False))]
                if not imgs.empty:
                    st.write(f"📍 {t}")
                    cols = st.columns(5)
                    for i, (_, r) in enumerate(imgs.iterrows()):
                        with cols[i%5]:
                            st.image(r['image_url'], use_container_width=True)
                            st.caption(r['created_at'].strftime('%d/%m %H:%M'))

            # --- 6. Admin Control Panel (เฉพาะ Admin เท่านั้นที่เห็น) ---
            if st.session_state.admin_logged_in:
                st.divider()
                st.subheader("🛠️ Admin Edit/Delete (Management Only)")
                edit_df = st.data_editor(
                    df_f[['id', 'task_name', 'update_by', 'status', 'image_url', 'created_at']],
                    column_config={"id":None, "created_at":st.column_config.DatetimeColumn(disabled=True)},
                    key="admin_edit", use_container_width=True
                )
                if st.button("💾 Save Changes"):
                    for _, r in edit_df.iterrows():
                        supabase.table("construction_progress").update({"task_name":r['task_name'], "update_by":r['update_by'], "status":r['status'], "image_url":r['image_url']}).eq("id", r['id']).execute()
                    st.rerun()
                
                del_id = st.selectbox("Select ID to Delete", options=df_f['id'].tolist())
                if st.button("🗑️ Delete"):
                    supabase.table("construction_progress").delete().eq("id", del_id).execute()
                    st.rerun()
        else: st.warning("No data.")
