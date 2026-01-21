import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timezone
import io
import requests
from PIL import Image

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V2.8", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-square { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #bf4300; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #144618; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; }
    .val-text { font-size: 32px; font-weight: bold; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Function: Fetch Data ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], errors='coerce')
        return df_raw
    except:
        return pd.DataFrame()

# --- 4. Function: Export Excel with Photos ---
def export_to_excel_with_photos(dataframe):
    output = io.BytesIO()
    # ใช้ xlsxwriter เพื่อให้แปะรูปได้
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Issue_Report', index=False)
        workbook  = writer.book
        worksheet = writer.sheets['Issue_Report']
        
        # ตั้งค่าหัวตาราง และขนาด
        worksheet.set_column('H:H', 25) # คอลัมน์ image_url
        worksheet.set_column('I:I', 25) # คอลัมน์ที่จะแปะรูป (ถ้ามีเพิ่ม)
        worksheet.set_default_row(80)    # ความสูงแถว
        
        for i, url in enumerate(dataframe['image_url']):
            if url and isinstance(url, str) and url.startswith("http"):
                try:
                    response = requests.get(url, timeout=5)
                    img_data = io.BytesIO(response.content)
                    
                    # แทรกรูปลงใน Excel (คอลัมน์ I คือ Index 8)
                    worksheet.insert_image(i + 1, 8, url, {
                        'image_data': img_data,
                        'x_scale': 0.15, 
                        'y_scale': 0.15,
                        'x_offset': 5,
                        'y_offset': 5,
                        'positioning': 1
                    })
                except:
                    continue
    return output.getvalue()

# --- 5. Main UI ---
df = load_data()
st.title("🚨 Issue Escalation Portal V2.8")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 6. Submit Form ---
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** fill the name (50 characters)")
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    u_detail = st.text_area("** Issue detail description (500 characters)", height=100)
    
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
                st.success("✅ Reported Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()

# --- 7. Dashboard Table & Export ---
if not df.empty:
    st.subheader("📋 All Issue Created")
    
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name / Description")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    # Filter Data
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # Export Button (New Logic)
    f3.markdown("<br>", unsafe_allow_html=True)
    if f3.button("🚀 Prepare Excel with Photos"):
        with st.spinner('กำลังสร้างไฟล์รายงานพร้อมรูปภาพ...'):
            excel_file = export_to_excel_with_photos(df_f)
            st.download_button(
                label="📥 Download Report Now",
                data=excel_file,
                file_name=f"Issue_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Web Table Display
    t_h = st.columns([0.5, 1.2, 2.5, 1, 1, 1.2, 0.8, 1.2])
    for col, label in zip(t_h, ["no.", "name", "issue description", "Related", "status", "date created", "days", "image"]):
        col.markdown(f"**{label}**")

    now_utc = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        st.write("---")
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.5, 1.2, 2.5, 1, 1, 1.2, 0.8, 1.2])
        c1.write(i+1)
        c2.write(r['staff_name'])
        c3.write(r['issue_detail'])
        c4.write(r['related_to'])
        c5.write(r['status'])
        
        if pd.notnull(r['created_at']):
            created_utc = r['created_at'].replace(tzinfo=timezone.utc) if r['created_at'].tzinfo is None else r['created_at'].astimezone(timezone.utc)
            c6.write(created_utc.strftime('%d-%b-%y'))
            days = (now_utc - created_utc).days
            c7.write(f"{max(0, days)} d")
        else:
            c6.write("-"); c7.write("-")
        
        if r['image_url']:
            c8.markdown(f'<img src="{r["image_url"]}" class="img-square">', unsafe_allow_html=True)
            c8.markdown(f"[🔗 Open Link]({r['image_url']})")
        else:
            c8.write("No image")

# --- 8. Admin Panel ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    if pwd == "pm1234":
        st.success("Admin Access Granted")
        if not df.empty:
            options = {row['id']: f"ID:{row['id']} - {row['staff_name']}" for _, row in df.iterrows()}
            target_id = st.selectbox("Update Status ID", options=options.keys(), format_func=lambda x: options[x])
            new_status = st.selectbox("New Status", ["Open", "Closed", "Cancel"])
            if st.button("Update Status"):
                supabase.table("issue_escalation").update({"status": new_status}).eq("id", target_id).execute()
                st.rerun()
