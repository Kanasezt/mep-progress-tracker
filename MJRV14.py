import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime
import io

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="MEP Tracker V45", layout="wide")

# --- CSS Styling ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important; border-radius: 8px; width: 100%;
    }
    .qty-hint { color: #666; font-size: 0.85rem; margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Data Fetching ---
@st.cache_data(ttl=10)
def fetch_all_data():
    res_progress = supabase.table("construction_progress").select("*").execute()
    res_tasks = supabase.table("task_master").select("*").execute()
    return pd.DataFrame(res_progress.data), pd.DataFrame(res_tasks.data)

df_raw, df_tasks = fetch_all_data()

# --- 3. Upload & Validation Logic ---
def show_upload_form():
    st.header("🏗️ Update Progress")
    
    if df_tasks.empty:
        st.warning("Please import Task Master data in Admin mode first.")
        return

    # 1. Category Filter
    categories = sorted(df_tasks['category'].unique().tolist())
    selected_cat = st.selectbox("Select Category", options=[""] + categories)

    # 2. Task Name (Filtered by Category)
    task_options = []
    if selected_cat:
        task_options = df_tasks[df_tasks['category'] == selected_cat]['task_name'].tolist()
    
    task_name = st.selectbox("Task name / Code name", options=[""] + task_options)

    if task_name:
        task_info = df_tasks[df_tasks['task_name'] == task_name].iloc[0]
        total_qty = float(task_info['total_qty'])
        unit = task_info['unit']
        
        # Get Current Progress
        current_p = 0
        if not df_raw.empty:
            last_entry = df_raw[df_raw['task_name'] == task_name].sort_values('created_at', ascending=False)
            if not last_entry.empty:
                current_p = float(last_entry.iloc[0]['status'])
        
        st.info(f"📊 Current Progress: {current_p} / {total_qty} {unit}")

        with st.form("progress_form", clear_on_submit=True):
            staff_list = ["", "Puwanai Torpradit", "Zhangxi (Sea)", "Puripat Nammontree", "Ravicha Thaisiam", "Kraiwut Chaiyarak", "Sakda Suwan", "Thanadol Chanpattanakij", "Thanakit Thundon", "Anu Yaemsajja", "Chawalit Posrima", "Amnat Pagamas", "Thotsapon Sripornwong", "Tanupat mongkholkan", "Putthipong Niyomkitjakankul", "Ekkapol Tangngamsakul", "Natthaphat Suwanmanee", "Kantapon Phasee", "Chatchai Sripradoo", "Chatchai Chanprasert", "Jirapat Phobtavorn", "Thanadon Tuydoi (Tontan)", "Pimchanok Janjamsai"]
            u_by = st.selectbox("Select Your Name", options=staff_list)
            
            new_stat = st.number_input(f"Enter New Progress ({unit})", min_value=0.0, max_value=total_qty, value=float(current_p), step=0.1)
            st.markdown(f"<div class='qty-hint'>Max allowed: {total_qty} {unit}</div>", unsafe_allow_html=True)
            
            up_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("Submit Progress"):
                if not u_by:
                    st.error("Please select your name.")
                elif new_stat < current_p:
                    st.error(f"Cannot fill less than current progress ({current_p} {unit})")
                elif new_stat > total_qty:
                    st.error(f"Cannot exceed total quantity ({total_qty} {unit})")
                else:
                    img_url = ""
                    if up_file:
                        f_name = f"{uuid.uuid4()}.jpg"
                        supabase.storage.from_('images').upload(f_name, up_file.read())
                        img_url = supabase.storage.from_('images').get_public_url(f_name)
                    
                    supabase.table("construction_progress").insert({
                        "task_name": task_name, "update_by": u_by, 
                        "status": new_stat, "image_url": img_url,
                        "unit": unit, "total_qty": total_qty
                    }).execute()
                    st.cache_data.clear()
                    st.success("Recorded Successfully!"); st.rerun()

# --- 4. Admin Function: Import Excel ---
def admin_panel():
    st.divider()
    st.subheader("⚙️ Admin Settings")
    
    # Import Excel Function
    st.markdown("### 📥 Import Task Master")
    import_file = st.file_uploader("Upload 'Import V1.xlsx'", type=['xlsx'])
    if import_file and st.button("Confirm Import Data"):
        df_imp = pd.read_excel(import_file)
        # Column mapping based on your request
        # A=Description, B=Category, C=Total, D=Unit
        df_imp = df_imp.iloc[:, 0:4]
        df_imp.columns = ['task_name', 'category', 'total_qty', 'unit']
        
        # Clear old Task Master and Insert New
        supabase.table("task_master").delete().neq("id", -1).execute() # Delete all
        for _, row in df_imp.iterrows():
            supabase.table("task_master").insert(row.to_dict()).execute()
        
        st.success("Task Master Updated!"); st.cache_data.clear(); st.rerun()

# --- 5. Main Logic ---
page = st.query_params.get("page", "dashboard")

if page == "upload":
    show_upload_form()
    st.markdown('<br><a href="/?page=dashboard" target="_self">📊 View Dashboard</a>', unsafe_allow_html=True)
else:
    with st.sidebar:
        if "admin_logged_in" not in st.session_state: st.session_state.admin_logged_in = False
        if not st.session_state.admin_logged_in:
            st.title("🔐 Admin Login")
            u, p = st.text_input("User"), st.text_input("Pass", type="password")
            if st.button("Login"):
                if u == "admin" and p == "mep1234": 
                    st.session_state.admin_logged_in = True; st.rerun()
                else: st.error("Invalid")
        else:
            if st.button("🚪 Logout"): st.session_state.admin_logged_in = False; st.rerun()
            admin_panel()

    st.title("🚧 MEP Construction Dashboard")
    # ... Dashboard Visualization Logic (Remains similar to your V44) ...
    if not df_raw.empty:
        # Progress Calculation logic using df_tasks to get units and totals
        df_latest = df_raw.sort_values('created_at', ascending=False).drop_duplicates('task_name')
        # (Visualize with Plotly here using 'total_qty' as the 100% mark)