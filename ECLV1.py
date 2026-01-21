import streamlit as st
import pandas as pd
from supabase import create_client, Client
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

st.set_page_config(page_title="Issue Escalation V2", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    /* ปุ่ม Submit สีน้ำเงิน */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold;
    }
    /* รูป Thumbnail จตุรัส */
    .img-thumbnail {
        width: 80px; height: 80px; object-fit: cover; border-radius: 5px;
    }
    /* ตกแต่ง Metric Card */
    .metric-card {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def fetch_data():
    res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data)

df = fetch_data()

# --- 4. Header & Overall Status ---
st.title("🚨 Issue Escalation Portal V2.0")

if not df.empty:
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'>🟢 <b>Open</b><br><h2>{len(df[df['status'] == 'Open'])}</h2></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'>🔵 <b>In Progress</b><br><h2>{len(df[df['status'] == 'In Progress'])}</h2></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'>✅ <b>Closed</b><br><h2>{len(df[df['status'] == 'Closed'])}</h2></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'>❌ <b>Cancel</b><br><h2>{len(df[df['status'] == 'Cancel'])}</h2></div>", unsafe_allow_html=True)

st.divider()

# --- 5. Submit Form ---
with st.expander("➕ Create New Issue", expanded=True):
    with st.form("issue_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        u_name = col1.text_input("** fill the name (50 characters)", max_chars=50)
        # Related To เป็นปุ่มเลือก (Radio Horizontal)
        u_related = col2.radio("Related to:", options=["CSC", "IFS", "Safety", "Site", "Other"], horizontal=True)
        
        u_detail = st.text_area("** Issue detail description (500 characters)", max_chars=500)
        
        c_up, c_sub = st.columns([3, 1])
        up_file = c_up.file_uploader("Browse the photo", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("Submit"):
            if u_name and u_detail:
                img_url = ""
                if up_file:
                    f_name = f"esc_{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, up_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                
                supabase.table("issue_escalation").insert({
                    "staff_name": u_name, "issue_detail": u_detail, 
                    "related_to": u_related, "image_url": img_url, "status": "Open"
                }).execute()
                st.success("Issue Reported!"); st.rerun()

st.divider()

# --- 6. Dashboard & Filter ---
st.subheader("📋 All Issues Created")

if not df.empty:
    # Filter Row
    f_col1, f_col2, f_col3, f_export = st.columns([1, 1, 1, 1])
    search = f_col1.text_input("🔍 Search Staff / Detail")
    f_status = f_col2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    f_rel = f_col3.selectbox("Filter Related to", ["All"] + list(df['related_to'].unique()))

    # Apply Filters
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False) | df_f['issue_detail'].str.contains(search, case=False)]
    if f_status != "All":
        df_f = df_f[df_f['status'] == f_status]
    if f_rel != "All":
        df_f = df_f[df_f['related_to'] == f_rel]

    # Export CSV
    csv = df_f.to_csv(index=False).encode('utf-8-sig')
    f_export.download_button("📥 Export CSV", data=csv, file_name=f"issues_{datetime.now().date()}.csv", mime='text/csv')

    # --- 7. Table with Square Images ---
    # สร้างหัวตาราง
    h1, h2, h3, h4, h5, h6 = st.columns([0.5, 1, 1, 2.5, 1, 1])
    h1.write("**No.**"); h2.write("**Related**"); h3.write("**Name**"); h4.write("**Detail**"); h5.write("**Status**"); h6.write("**Photo**")
    
    for i, r in df_f.iterrows():
        st.divider()
        c1, c2, c3, c4, c5, c6 = st.columns([0.5, 1, 1, 2.5, 1, 1])
        c1.write(i+1)
        c2.info(r['related_to'])
        c3.write(r['staff_name'])
        c4.write(r['issue_detail'])
        
        # Status Color Logic
        st_color = {"Open": "🔴", "In Progress": "🔵", "Closed": "🟢", "Cancel": "⚪"}
        c5.write(f"{st_color.get(r['status'], '')} {r['status']}")
        
        # Square Photo & Link
        if r['image_url']:
            # แสดงรูปเล็กจตุรัส
            c6.markdown(f'<img src="{r["image_url"]}" class="img-thumbnail">', unsafe_allow_html=True)
            c6.markdown(f"[🔗 Open Image]({r['image_url']})")
        else:
            c6.write("No Photo")

    # --- 8. Admin Only: Change Status ---
    st.sidebar.header("🔐 Admin Control")
    admin_pass = st.sidebar.text_input("Admin Password", type="password")
    if admin_pass == "pm1234":
        st.sidebar.success("Logged In")
        target_id = st.sidebar.selectbox("Select ID to Update", options=df['id'].tolist())
        new_status = st.sidebar.selectbox("Change Status to", ["Open", "In Progress", "Closed", "Cancel"])
        if st.sidebar.button("Update Status"):
            supabase.table("issue_escalation").update({"status": new_status}).eq("id", target_id).execute()
            st.rerun()
else:
    st.info("No issues found.")
