import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timezone
import io
import requests

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V3.5", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-card { width: 100%; max-width: 150px; aspect-ratio: 1/1; object-fit: cover; border-radius: 10px; border: 1px solid #eee; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 30px; font-weight: bold; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
        return df_raw
    except:
        return pd.DataFrame()

# --- 4. Excel Export Function ---
def export_excel_with_images(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_ex = dataframe.copy()
        df_ex['id_str'] = df_ex['id'].apply(lambda x: f"{x:03d}")
        df_ex['created_date'] = df_ex['created_at'].dt.strftime('%d-%b-%y')
        df_ex['created_time'] = df_ex['created_at'].dt.strftime('%I:%M:%S %p')
        
        # คอลัมน์ตามหัวตารางที่พี่ต้องการ
        cols = ['id_str', 'staff_name', 'issue_detail', 'related_to', 'status', 'created_date', 'created_time']
        df_final = df_ex[cols]
        df_final.columns = ['id', 'staff_name', 'issue_detail', 'related_to', 'status', 'created_date', 'created_time']
        df_final.to_excel(writer, sheet_name='Report', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Report']
        worksheet.set_column('H:H', 20) # ช่องสำหรับรูปภาพ (คอลัมน์ Image)
        worksheet.write(0, 7, 'Image')
        worksheet.set_default_row(80)
        
        for i, url in enumerate(df_ex['image_url']):
            if url and url.startswith("http"):
                try:
                    resp = requests.get(url, timeout=5)
                    img_data = io.BytesIO(resp.content)
                    worksheet.insert_image(i + 1, 7, url, {'image_data': img_data, 'x_scale': 0.1, 'y_scale': 0.1, 'x_offset': 5, 'y_offset': 5})
                except: continue
    return output.getvalue()

df = load_data()

# --- 5. Sidebar Admin (ย้ายออกมาอยู่นี่เพื่อแก้ Error) ---
with st.sidebar:
    st.header("🔐 Admin Access")
    admin_pwd = st.text_input("Enter Password", type="password")
    is_admin = (admin_pwd == "pm1234")
    if is_admin:
        st.success("Admin Mode ON ✅")
    elif admin_pwd:
        st.error("Wrong Password ❌")

# --- 6. Main UI Summary ---
st.title("🚨 Issue Escalation V3.5")
c1, c2, c3 = st.columns(3)
op = len(df[df['status'] == 'Open']) if not df.empty else 0
cl = len(df[df['status'] == 'Closed']) if not df.empty else 0
can = len(df[df['status'] == 'Cancel']) if not df.empty else 0

c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 7. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** Fill Name")
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    u_detail = st.text_area("** Issue Detail", height=100)
    up_file = st.file_uploader("** Upload Photo", type=['jpg', 'png', 'jpeg'])
    
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
            st.success("✅ Reported!"); st.rerun()

# --- 8. Dashboard ---
if not df.empty:
    st.divider()
    st.subheader("📋 Dashboard")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name/Detail")
    f_stat = f2.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    if f3.button("📥 Download Excel with Photos"):
        with st.spinner("Processing..."):
            excel_file = export_excel_with_images(df_f)
            st.download_button("💾 Save Excel File", data=excel_file, file_name=f"Report_{datetime.now().strftime('%d%m%Y')}.xlsx")

    now = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info, c_admin = st.columns([1.5, 3.5, 1.2])
            with c_img:
                if r['image_url']: st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
                else: st.write("No Image")
            
            with c_info:
                # 1. แสดง ID (001) หน้าชื่อ
                st.markdown(f"### {r['id']:03d} - {r['staff_name']}")
                
                # 2. คำนวณวัน Pending (นับจาก created_at ถึงปัจจุบัน ถ้ายังไม่ Closed)
                c_time = r['created_at'].replace(tzinfo=timezone.utc) if r['created_at'].tzinfo is None else r['created_at']
                days_pending = (now - c_time).days
                
                st.write(f"**Detail:** {r['issue_detail']}")
                st.markdown(f"Status: **{r['status']}**")
                
                # แสดงวันค้างรับเคส
                if r['status'] == 'Closed':
                    st.caption(f"✅ Completed | 📅 {c_time.strftime('%d %b %y')}")
                else:
                    st.warning(f"⏳ {days_pending} days pending | 🏷️ {r['related_to']}")

            # 3. Admin แก้ไขสถานะข้างรายการ
            with c_admin:
                if is_admin:
                    new_stat = st.selectbox("Update Status", ["Open", "Closed", "Cancel"], 
                                          index=["Open", "Closed", "Cancel"].index(r['status']), 
                                          key=f"status_{r['id']}")
                    if st.button("Confirm ✅", key=f"btn_{r['id']}"):
                        supabase.table("issue_escalation").update({"status": new_stat}).eq("id", r['id']).execute()
                        st.rerun()
            st.divider()
