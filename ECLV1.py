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

st.set_page_config(page_title="Issue Escalation V2.6", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-square { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 32px; font-weight: bold; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], errors='coerce')
        return df_raw
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. Function: Export Excel with Images ---
def export_to_excel(dataframe):
    output = io.BytesIO()
    # ใช้ XlsxWriter เป็น Engine
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Issues', index=False)
        workbook  = writer.book
        worksheet = writer.sheets['Issues']
        
        # ปรับความกว้างคอลัมน์และแถว
        worksheet.set_column('H:H', 20) # คอลัมน์รูปภาพ
        worksheet.set_default_row(70)    # ความสูงแถวเพื่อให้เห็นรูปชัด
        
        for i, url in enumerate(dataframe['image_url']):
            if url:
                try:
                    response = requests.get(url)
                    image_data = io.BytesIO(response.content)
                    # แทรกรูปภาพ (ย่อขนาดให้พอดีช่อง)
                    worksheet.insert_image(i + 1, 7, url, {
                        'image_data': image_data,
                        'x_scale': 0.15, 
                        'y_scale': 0.15,
                        'x_offset': 5,
                        'y_offset': 5
                    })
                except:
                    worksheet.write(i + 1, 7, "Image Error")
    return output.getvalue()

# --- 5. UI Header & Status Cards ---
st.title("🚨 Issue Escalation Portal V2.6")
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 6. Form & Dashboard (เหมือน V2.5 แต่แก้ปุ่ม Export) ---
# ... [ส่วน Code Submit Form เหมือนเดิม] ...

if not df.empty:
    st.subheader("📋 All Issue Created")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name / Description")
    f_stat = f2.selectbox("Filter Status", ["All", "Open", "Closed", "Cancel"])
    
    # Filter Data
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # --- ปุ่ม Export Excel (ที่มาแทน CSV) ---
    excel_file = export_to_excel(df_f)
    f3.markdown("<br>", unsafe_allow_html=True)
    f3.download_button(
        label="📥 Export Excel (With Photos)",
        data=excel_file,
        file_name=f"Issue_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- ส่วนตาราง Dashboard แสดงผลบนเว็บ ---
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
        else:
            c8.write("No image")

# --- 7. Admin Panel ---
with st.sidebar:
    st.header("🔐 Admin")
    pwd = st.text_input("Password", type="password")
    if pwd == "pm1234":
        if not df.empty:
            target_id = st.selectbox("Update ID", options=df['id'].tolist())
            new_status = st.selectbox("New Status", ["Open", "Closed", "Cancel"])
            if st.button("Update"):
                supabase.table("issue_escalation").update({"status": new_status}).eq("id", target_id).execute()
                st.cache_data.clear()
                st.rerun()
