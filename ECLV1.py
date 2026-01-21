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
# --- 2. CSS Styling (ปรับปรุงเพื่อ Mobile) ---
st.markdown("""
    <style>
    /* ปรับแต่งปุ่ม Submit */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    
    /* รูปภาพให้มีขนาดพอดี */
    .img-square { 
        width: 100%; 
        max-width: 150px; 
        aspect-ratio: 1/1; 
        object-fit: cover; 
        border-radius: 8px; 
        border: 1px solid #ddd; 
    }

    /* สไตล์ของ Card สำหรับมือถือ */
    .issue-card {
        background-color: #f9f9f9;
        border-left: 5px solid #0047AB;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    
    .status-tag {
        padding: 2px 8px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        color: white;
    }
    
    /* ซ่อนตารางปกติในมือถือ (ใช้การปรับ column width ของ streamlit) */
    @media (max-width: 640px) {
        .stHorizontalBlock {
            flex-direction: column !important;
        }
    }
    </style>
""", unsafe_allow_html=True)True)

# --- 3. Function: Load Data ---
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], errors='coerce')
        return df_raw
    except Exception as e:
        st.error(f"การดึงข้อมูลมีปัญหา: {e}")
        return pd.DataFrame()

# --- 4. Function: Export Excel with Images ---
def export_to_excel_with_photos(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Issue_Report', index=False)
        workbook  = writer.book
        worksheet = writer.sheets['Issue_Report']
        
        # ตั้งความกว้างคอลัมน์ H (Index 7) สำหรับแปะรูป
        worksheet.set_column('H:H', 25) 
        worksheet.set_default_row(80) 
        
        for i, url in enumerate(dataframe['image_url']):
            if url and isinstance(url, str) and url.startswith("http"):
                try:
                    response = requests.get(url, timeout=5)
                    img_data = io.BytesIO(response.content)
                    # แทรกรูปลงใน Excel คอลัมน์ H (Index 7)
                    worksheet.insert_image(i + 1, 7, url, {
                        'image_data': img_data,
                        'x_scale': 0.15, 
                        'y_scale': 0.15,
                        'x_offset': 5,
                        'y_offset': 5
                    })
                except:
                    continue
    return output.getvalue()

# --- 5. เริ่มดึงข้อมูลมาใช้งาน ---
df = load_data()

# --- 6. Main Content UI ---
st.title("🚨 Issue Escalation Portal V2.8")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{len(df[df['status'] == 'Open'])}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{len(df[df['status'] == 'Closed'])}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{len(df[df['status'] == 'Cancel'])}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 7. Submission Form ---
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

# --- 8. Table & Export ---
if not df.empty:
    st.subheader("📋 All Issue Created")
    
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name / Description")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    f3.markdown("<br>", unsafe_allow_html=True)
    if f3.button("🚀 Prepare Excel with Photos"):
        with st.spinner('กำลังประมวลผลรูปภาพลงไฟล์ Excel...'):
            try:
                excel_file = export_to_excel_with_photos(df_f)
                st.download_button(
                    label="📥 Click to Download Excel",
                    data=excel_file,
                    file_name=f"Issue_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}. กรุณาตรวจสอบ xlsxwriter ใน requirements.txt")

    # Web Table Display
    # --- 7. Table Display (ปรับให้ดูง่ายในมือถือ) ---
    if not df_f.empty:
        now_utc = datetime.now(timezone.utc)
        
        for i, r in df_f.reset_index(drop=True).iterrows():
            # สร้างกล่องสี่เหลี่ยมสำหรับแต่ละรายการ
            with st.container():
                # ใช้ columns แค่ 2 ฝั่ง (รูป | รายละเอียด) เพื่อให้ในมือถือไม่บีบเกินไป
                col_img, col_txt = st.columns([1, 3])
                
                with col_img:
                    if r['image_url']:
                        st.markdown(f'<img src="{r["image_url"]}" class="img-square">', unsafe_allow_html=True)
                    else:
                        st.write("🖼️ No Image")
                
                with col_txt:
                    # แสดง Status เป็นสีๆ
                    st.markdown(f"**{r['staff_name']}** | Status: `{r['status']}`")
                    st.write(f"💬 {r['issue_detail']}")
                    
                    # ข้อมูลเล็กๆ ด้านล่าง
                    date_str = "-"
                    day_str = "-"
                    if pd.notnull(r['created_at']):
                        c_utc = r['created_at'].replace(tzinfo=timezone.utc) if r['created_at'].tzinfo is None else r['created_at'].astimezone(timezone.utc)
                        date_str = c_utc.strftime('%d %b %y')
                        day_str = f"{(now_utc - c_utc).days} days ago"
                    
                    st.caption(f"📅 {date_str} ({day_str}) | 🏷️ {r['related_to']}")
                
                st.divider() # ขีดเส้นใต้แต่ละรายการ

# --- 8. Sidebar Admin (เวอร์ชันแก้ KeyError) ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    
    if pwd == "pm1234":
        st.success("Admin Access Granted")
        if not df.empty:
            st.write("---")
            
            # ตรวจสอบว่ามีคอลัมน์ id หรือไม่ ถ้าไม่มีให้ใช้ index แทน
            id_column = 'id' if 'id' in df.columns else df.columns[0] 
            
            try:
                # สร้างรายการให้เลือกโดยใช้ข้อมูลที่มีอยู่
                options = {row[id_column]: f"Row:{i+1} - {row['staff_name']}" for i, row in df.iterrows()}
                
                target_id = st.selectbox("1. เลือกรายการที่จะแก้ไข", 
                                        options=options.keys(), 
                                        format_func=lambda x: options[x])
                
                new_status = st.selectbox("2. เปลี่ยนเป็นสถานะ", ["Open", "Closed", "Cancel"])
                
                if st.button("🚀 บันทึกการเปลี่ยนแปลง", type="primary"):
                    # อัปเดตข้อมูลโดยอ้างอิงจากคอลัมน์ ID ที่หาเจอ
                    supabase.table("issue_escalation").update({"status": new_status}).eq(id_column, target_id).execute()
                    
                    st.success("อัปเดตเรียบร้อย!")
                    st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการดึง ID: {e}")
                st.info("คำแนะนำ: ตรวจสอบใน Supabase ว่าคอลัมน์ ID สะกดอย่างไร (เช่น id, ID, หรือ No)")
                
    elif pwd != "":
        st.error("รหัสผ่านไม่ถูกต้อง")



