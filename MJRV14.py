import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import uuid
from datetime import datetime, timedelta, timezone
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
    /* Target the Refresh Button specifically */
    .refresh-container div[data-testid="stButton"] > button {
        background-color: #002366 !important; /* Dark Blue */
        color: white !important;
        border: 1px solid #004366 !important;
        padding: 5px 10px !important;
        height: 35px !important; /* Smaller height */
        width: auto !important;   /* Smaller width */
        font-size: 13px !important;
    }
            
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .dashboard-link {
        float: right; text-decoration: none !important; background-color: #FF4B4B !important;
        color: white !important; padding: 10px 20px; border-radius: 8px;
        font-weight: bold; font-size: 14px; display: inline-block; border: none;
    }
    /* Style for the Refresh Button on Dashboard */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    .refresh-container {
        display: flex;
        justify-content: flex-end;
        margin-bottom: -45px;
    }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; 
        color: white !important;
        border: 1px solid #0047AB !important;
        width: 100%; height: 45px; font-weight: bold;
    }
    .qty-hint { color: #666; font-size: 0.85rem; margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Data Fetching ---
@st.cache_data(ttl=5)
def load_all_data():
    try:
        res_prog = supabase.table("construction_progress").select("*").execute()
        res_task = supabase.table("task_master").select("*").execute()
        return pd.DataFrame(res_prog.data), pd.DataFrame(res_task.data)
    except:
        return pd.DataFrame(), pd.DataFrame()

df_raw, df_tasks = load_all_data()

# Project start date default
min_date = datetime(2026, 3, 1).date()

if not df_raw.empty:
    df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_convert('Asia/Bangkok').dt.tz_localize(None)

# --- 3. Function: Upload Form ---
def show_upload_form(show_dash_btn=False):
    col_t, col_b = st.columns([3, 1])
    with col_t: st.header("🏗️ Update Progress")
    if show_dash_btn:
        with col_b: st.markdown('<br><a href="/?page=dashboard" target="_self" class="dashboard-link">📊 View Dashboard</a>', unsafe_allow_html=True)

    if df_tasks.empty:
        st.warning("⚠️ No Task Master data found. Admin must import 'Import V1.xlsx' in the sidebar first.")
        return

    cats = sorted(df_tasks['category'].unique().tolist())
    u_cat = st.selectbox("Select Category", options=[""] + cats)

    task_opts = []
    if u_cat:
        task_opts = df_tasks[df_tasks['category'] == u_cat]['task_name'].tolist()
    
    task_name = st.selectbox("Task Name (Recommended from Excel)", options=[""] + task_opts)

    current_p = 0.0
    total_max = 100.0
    u_unit = "%"
    
    if task_name:
        t_info = df_tasks[df_tasks['task_name'] == task_name].iloc[0]
        total_max = float(t_info['total_qty'])
        u_unit = t_info['unit']
        
        if not df_raw.empty:
            last_task = df_raw[df_raw['task_name'] == task_name].sort_values('created_at', ascending=False)
            if not last_task.empty:
                current_p = float(last_task.iloc[0]['status'])
        
        st.info(f"🔍 Current: {current_p} {u_unit} | Total Max: {total_max} {u_unit}")

    with st.form("progress_form", clear_on_submit=True):
        staff_list = ["", "Puwanai Torpradit", "Zhangxi (Sea)", "Puripat Nammontree", "Ravicha Thaisiam", "Kraiwut Chaiyarak", "Sakda Suwan", "Thanadol Chanpattanakij", "Thanakit Thundon", "Anu Yaemsajja", "Chawalit Posrima", "Amnat Pagamas", "Thotsapon Sripornwong", "Tanupat mongkholkan", "Putthipong Niyomkitjakankul", "Ekkapol Tangngamsakul", "Natthaphat Suwanmanee", "Kantapon Phasee", "Chatchai Sripradoo", "Chatchai Chanprasert", "Jirapat Phobtavorn", "Thanadon Tuydoi (Tontan)", "Pimchanok Janjamsai"]
        u_by = st.selectbox("Select Your Name", options=staff_list)
        stat = st.number_input(f"New Progress ({u_unit})", min_value=0.0, max_value=float(total_max), value=float(current_p))
        st.markdown(f"<div class='qty-hint'>Cannot be less than {current_p} or more than {total_max}</div>", unsafe_allow_html=True)
        up_file = st.file_uploader("Photo Progress", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("Submit Progress"):
            if task_name and u_by:
                if stat < current_p:
                    st.error(f"❌ Cannot fill less than current progress ({current_p})")
                elif stat > total_max:
                    st.error(f"❌ Cannot exceed total quantity ({total_max})")
                else:
                    img_url = ""
                    if up_file:
                        f_name = f"{uuid.uuid4()}.jpg"
                        supabase.storage.from_('images').upload(f_name, up_file.read())
                        img_url = supabase.storage.from_('images').get_public_url(f_name)
                    
                    now_th = datetime.now(timezone(timedelta(hours=7))).isoformat()
                    supabase.table("construction_progress").insert({
                        "task_name": task_name, "update_by": u_by, 
                        "status": stat, "image_url": img_url,
                        "category": u_cat, "unit": u_unit, "total_qty": total_max,
                        "created_at": now_th
                    }).execute()
                    st.cache_data.clear(); st.success("Recorded!"); st.rerun()
            else: st.error("Please fill Name and select a Task")

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
            st.divider()
            st.subheader("📥 Import Task Master")
            imp_file = st.file_uploader("Upload 'Import V1.xlsx'", type=['xlsx'])
            if imp_file and st.button("Confirm Excel Import"):
                df_imp = pd.read_excel(imp_file)
                df_imp = df_imp.iloc[:, 0:4]
                df_imp.columns = ['task_name', 'category', 'total_qty', 'unit']
                supabase.table("task_master").delete().neq("id", -1).execute()
                for _, row in df_imp.iterrows():
                    supabase.table("task_master").insert(row.to_dict()).execute()
                st.success("Task Master Updated!"); st.cache_data.clear(); st.rerun()
            st.divider(); show_upload_form(False)

    # --- Dashboard View ---
    # Changed ratio to [5, 1] to make the button column smaller
    col_title, col_refresh = st.columns([5, 1]) 
    with col_title:
        st.title("🚧 MEP Construction Dashboard")
    with col_refresh:
        st.markdown('<br>', unsafe_allow_html=True)
        # Wrap in a div to apply the specific CSS from Step A
        st.markdown('<div class="refresh-container">', unsafe_allow_html=True)
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if not st.session_state.admin_logged_in:
        st.markdown('<a href="/?page=upload" target="_self" style="color:#ff4b4b; text-decoration:none;">⬅️ Back to Upload Photo</a>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    start_d = c1.date_input("From date", min_date) 
    today_th = (datetime.now(timezone(timedelta(hours=7)))).date()
    end_d = c2.date_input("To date", today_th)

    if not df_raw.empty:
        mask = (df_raw['created_at'].dt.date >= start_d) & (df_raw['created_at'].dt.date <= end_d)
        df_f = df_raw[mask].copy()

        if not df_f.empty:
            csv_data = df_f.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 Export Progress (CSV)", data=csv_data, file_name=f"MEP_Report_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')

            df_latest = df_f.sort_values('created_at', ascending=False).drop_duplicates('task_name')
            df_latest['status'] = pd.to_numeric(df_latest['status'], errors='coerce').fillna(0)
            df_latest['total_qty'] = pd.to_numeric(df_latest['total_qty'], errors='coerce').fillna(1)
            df_latest['pct'] = (df_latest['status'] / df_latest['total_qty']) * 100
            df_latest['display_label'] = df_latest.apply(lambda x: f"{x['update_by'] : <12} | {x['task_name']}", axis=1)
            
            st.subheader("📊 Progress Overview (%)")
            fig = px.bar(df_latest, x='pct', y='display_label', orientation='h', range_x=[0, 125], color_discrete_sequence=['#FFD1D1'])
            fig.update_traces(
                text=df_latest.apply(lambda x: f"{x['pct']:.1f}% ({x['status']}/{x['total_qty']} {x.get('unit', '')})", axis=1), 
                textposition='outside', textfont_size=16, cliponaxis=False 
            )
            fig.update_layout(xaxis_title="Completion (%)", height=max(400, len(df_latest)*50), yaxis_title="", margin=dict(l=280, r=60, t=20, b=20), yaxis=dict(autorange="reversed", tickfont=dict(family="Candara", size=16)))
            st.plotly_chart(fig, use_container_width=True)

            st.divider(); st.subheader("📸 Photo Progress")
            for t in df_latest['task_name'].unique():
                imgs = df_f[(df_f['task_name'] == t) & (df_f['image_url'].str.startswith('http', na=False))].sort_values('created_at', ascending=False)
                if not imgs.empty:
                    st.markdown(f"📍 **Task: {t}**")
                    cols = st.columns(5)
                    for i, (_, r) in enumerate(imgs.iterrows()):
                        with cols[i%5]: 
                            st.image(r['image_url'], use_container_width=True)
                            st.caption(r['created_at'].strftime('%d/%m %H:%M'))