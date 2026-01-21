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

st.set_page_config(page_title="Issue Escalation V2.1", layout="wide")

# --- 2. CSS Styling (ทำให้รูปเป็น Square และจัด Layout ตามสั่ง) ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 60px; font-size: 22px; font-weight: bold; border-radius: 10px;
    }
    .img-square {
        width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd;
    }
    .status-box {
        background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #d1d5db;
    }
    .status-val { font-size: 24px; font-weight: bold; color: #0047AB; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching & Processing ---
def fetch_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
            # คำนวณระยะเวลา (ถ้าสถานะยังไม่ปิด ใช้เวลาปัจจุบัน - เวลาสร้าง)
            df_raw['days_elapsed'] = (datetime.now().astimezone() - df_raw['created_at']).dt.days
        return df_raw
    except:
        return pd.DataFrame()

df = fetch_data()

# --- 4. UI: Header & Overall Status ---
st.title("🚨 Issue Escalation Portal")
st.write("แจ้งปัญหาที่ไม่สามารถแก้ไขได้ถึง Project Management Team")

if not df.empty:
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1: st.markdown(f"<div class='status-box'>🔴 Open<br><span class='status-val'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    with s_col2: st.markdown(f"<div class='status-box'>🔵 In Progress<br><span class='status-val'>{len(df[df['status'] == 'In Progress'])}</span></div>", unsafe_allow_html=True)
    with s_col3: st.markdown(f"<div class='status-box'>🟢 Closed<br><span class='status-val'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    with s_col4: st.markdown(f"<div class='status-box'>⚪ Cancel<br><span class='status-val'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 5. UI: Form Input ---
with st.form("main_form", clear_on_submit=True):
    c_name, c_rel = st.columns([2, 1])
    u_name = c_name.text_input("** fill the name (50 ตัวอักษร)", max_chars=50, placeholder="ระบุชื่อผู้แจ้ง")
    u_related = c_rel.selectbox("Related to:", ["IFS", "CSC", "HW", "other"])
    
    u_detail = st.text_area("** Issue detail description (500 ตัวอักษร)", max_chars=500, height=150)
    
    c_file, c_btn = st.columns([3, 1])
    up_file = c_file.file_uploader("** browse the photo to upload", type=['jpg', 'png', 'jpeg'])
    
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
            st.success("ส่งข้อมูลเรียบร้อย!"); st.rerun()

st.divider()

# --- 6. Dashboard & Filter ---
st.subheader("📊 All Issue Created")

if not df.empty:
    # Filter Row
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    search = f1.text_input("🔍 ค้นหาชื่อหรือรายละเอียด")
    f_rel = f2.selectbox("Filter Related", ["All"] + list(df['related_to'].unique()))
    f_stat = f3.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    # Apply Filtering
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False) | df_f['issue_detail'].str.contains(search, case=False)]
    if f_rel != "All":
        df_f = df_f[df_f['related_to'] == f_rel]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # Download Button
    csv = df_f.to_csv(index=False).encode('utf-8-sig')
    f4.download_button("📥 Export CSV", data=csv, file_name="issue_report.csv", mime='text/csv')

    # --- 7. Table Display (ตามรูปแบบรูปที่ 0efad4) ---
    st.write("---")
    # หัวตารางแบบ Custom
    t_h = st.columns([0.5, 1.5, 3, 1, 1, 1.5, 1.5, 1.5])
    labels = ["no.", "name", "issue description", "Related", "status", "date created", "ระยะเวลา (day)", "image"]
    for col, label in zip(t_h, labels): col.markdown(f"**{label}**")

    for i, r in df_f.reset_index(drop=True).iterrows():
        st.divider()
        c_no, c_name, c_desc, c_rel, c_stat, c_date, c_day, c_img = st.columns([0.5, 1.5, 3, 1, 1, 1.5, 1.5, 1.5])
        
        c_no.write(i + 1)
        c_name.write(r['staff_name'])
        c_desc.write(r['issue_detail'])
        c_rel.write(r['related_to'])
        c_stat.write(r['status'])
        c_date.write(r['created_at'].strftime('%d-%b-%y'))
        c_day.write(f"{r['days_elapsed']} days")
        
        if r['image_url']:
            c_img.markdown(f'<img src="{r["image_url"]}" class="img-square">', unsafe_allow_html=True)
            c_img.markdown(f"[🔗 Open]({r['image_url']})")
        else:
            c_img.write("No Photo")

# --- 8. Admin Control (Closed/Cancel Only) ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    if pwd == "pm1234":
        st.success("Admin Mode")
        if not df.empty:
            target_id = st.selectbox("Select No. to Update", options=df['id'].tolist())
            new_stat = st.selectbox("Update Status", ["Open", "In Progress", "Closed", "Cancel"])
            if st.button("Update Status", type="primary"):
                supabase.table("issue_escalation").update({"status": new_stat}).eq("id", target_id).execute()
                st.rerun()
