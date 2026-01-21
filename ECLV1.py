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

st.set_page_config(page_title="Issue Escalation V2.3", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 60px; font-size: 24px; font-weight: bold; border-radius: 10px;
    }
    .img-square {
        width: 80px; height: 80px; object-fit: cover; border-radius: 8px;
    }
    .status-card {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. Overall Status ---
st.title("🚨 Issue Escalation Portal")
st.write("แจ้งปัญหาที่ไม่สามารถแก้ไขได้ถึง Project Management Team")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='status-card'><b>Open</b><br><h2>{len(df[df['status'] == 'Open'])}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><b>Closed</b><br><h2>{len(df[df['status'] == 'Closed'])}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='status-card'><b>Cancel</b><br><h2>{len(df[df['status'] == 'Cancel'])}</h2></div>", unsafe_allow_html=True)

st.divider()

# --- 5. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_name, col_rel = st.columns([2, 1])
    u_name = col_name.text_input("** fill the name (50 ตัวอักษร)", max_chars=50)
    u_related = col_rel.selectbox("Related to:", ["IFS", "CSC", "HW", "other"])
    
    u_detail = st.text_area("** Issue detail description (500 ตัวอักษร)", max_chars=500, height=150)
    
    c_up, c_btn = st.columns([3, 1])
    up_file = c_up.file_uploader("** browse the photo to upload", type=['jpg', 'png', 'jpeg'])
    
    if st.form_submit_button("Submit"):
        if u_name and u_detail:
            try:
                img_url = ""
                if up_file:
                    f_name = f"esc_{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, up_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                
                # บันทึกข้อมูล
                supabase.table("issue_escalation").insert({
                    "staff_name": u_name, "issue_detail": u_detail, 
                    "related_to": u_related, "image_url": img_url, "status": "Open"
                }).execute()
                st.success("✅ Reported Successfully!"); st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()

# --- 6. Dashboard Table ---
if not df.empty:
    st.subheader("📊 All Issue Created")
    
    # Filters & Export
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name/Description")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    f3.download_button("📥 Export CSV", data=csv, file_name="issue_report.csv")

    # Filter Logic
    df_disp = df.copy()
    if search:
        df_disp = df_disp[df_disp['staff_name'].str.contains(search, case=False) | df_disp['issue_detail'].str.contains(search, case=False)]
    if f_stat != "All":
        df_disp = df_disp[df_disp['status'] == f_stat]

    # Table Header
    cols = st.columns([0.5, 1.5, 3, 1, 1, 1.5, 1, 1.5])
    header = ["no.", "name", "issue description", "Related", "status", "date created", "days", "image"]
    for c, h in zip(cols, header): c.markdown(f"**{h}**")

    # Table Rows
    for i, r in df_disp.reset_index(drop=True).iterrows():
        st.write("---")
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.5, 1.5, 3, 1, 1, 1.5, 1, 1.5])
        c1.write(i+1)
        c2.write(r['staff_name'])
        c3.write(r['issue_detail'])
        c4.write(r['related_to'])
        c5.write(r['status'])
        
        # Date & Day calculation
        dt = pd.to_datetime(r['created_at'])
        c6.write(dt.strftime('%d-%b-%y'))
        days = (datetime.now().date() - dt.date()).days
        c7.write(f"{days} d")
        
        if r['image_url']:
            c8.markdown(f'<img src="{r["image_url"]}" class="img-square">', unsafe_allow_html=True)
            c8.markdown(f"[🔗 Open]({r['image_url']})")
        else:
            c8.write("No image")

# --- 7. Admin Update ---
with st.sidebar:
    st.header("🔐 Admin")
    pw = st.text_input("Password", type="password")
    if pw == "pm1234":
        target = st.selectbox("Select ID", options=df['id'].tolist()) if not df.empty else None
        new_s = st.selectbox("Status", ["Open", "Closed", "Cancel"])
        if st.button("Update Status") and target:
            supabase.table("issue_escalation").update({"status": new_s}).eq("id", target).execute()
            st.rerun()
