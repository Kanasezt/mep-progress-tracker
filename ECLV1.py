import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timezone

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V2.4", layout="wide")

# --- 2. CSS Styling (ปรับสี Card ตามโจทย์: ส้มเข้ม/เขียวเข้ม/เทาเข้ม) ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 55px; font-size: 22px; font-weight: bold; border-radius: 10px;
    }
    .img-square { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd; }
    
    /* Overall Status Cards */
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 30px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching (Fix Timezone Error) ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            # แปลงวันที่ให้เป็น timezone-aware (UTC) เพื่อป้องกัน Error ตอนลบกัน
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_convert('UTC')
        return df_raw
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. UI: Overall Status (ส้มเข้ม/เขียวเข้ม/เทาเข้ม) ---
st.title("🚨 Issue Escalation Portal V2.4")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'><b>Open</b><br><span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'><b>Closed</b><br><span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'><b>Cancel</b><br><span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 5. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** fill the name (50 characters)", max_chars=50)
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    
    u_detail = st.text_area("** Issue detail description (500 characters)", max_chars=500, height=120)
    
    c_up, c_empty = st.columns([2, 1])
    up_file = c_up.file_uploader("** browse the photo to upload", type=['jpg', 'png', 'jpeg'])
    
    if st.form_submit_button("Submit"):
        if u_name and u_detail:
            try:
                img_url = ""
                if up_file:
                    f_name = f"esc_{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, up_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                
                supabase.table("issue_escalation").insert({
                    "staff_name": u_name, "issue_detail": u_detail, 
                    "related_to": u_related, "image_url": img_url, "status": "Open"
                }).execute()
                st.success("Reported Successfully!"); st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()

# --- 6. Dashboard Table ---
if not df.empty:
    st.subheader("📋 All Issue Created")
    
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name / Description")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    # Export CSV
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    f3.markdown("<br>", unsafe_allow_html=True)
    f3.download_button("📥 Export CSV", data=csv_data, file_name="issue_report.csv")

    # Filter Logic
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False) | df_f['issue_detail'].str.contains(search, case=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # Table Display
    t_h = st.columns([0.5, 1.2, 2.5, 1, 1, 1.2, 0.8, 1.2])
    cols = ["no.", "name", "issue description", "Related", "status", "date created", "days", "image"]
    for col, label in zip(t_h, cols): col.markdown(f"**{label}**")

    now_utc = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        st.write("---")
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.5, 1.2, 2.5, 1, 1, 1.2, 0.8, 1.2])
        c1.write(i+1)
        c2.write(r['staff_name'])
        c3.write(r['issue_detail'])
        c4.write(r['related_to'])
        c5.write(r['status'])
        
        # Date & Day Calculation (Fixed Timezone Error)
        created_at = r['created_at']
        c6.write(created_at.strftime('%d-%b-%y'))
        days = (now_utc - created_at).days
        c7.write(f"{days} d")
        
        if r['image_url']:
            c8.markdown(f'<img src="{r["image_url"]}" class="img-square">', unsafe_allow_html=True)
            c8.markdown(f"[🔗 Open]({r['image_url']})")
        else:
            c8.write("No image")

# --- 7. Admin Control ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    if pwd == "pm1234":
        if not df.empty:
            target = st.selectbox("Select ID to update", options=df['id'].tolist())
            new_status = st.selectbox("New Status", ["Open", "Closed", "Cancel"])
            if st.button("Update Status"):
                supabase.table("issue_escalation").update({"status": new_status}).eq("id", target).execute()
                st.rerun()
