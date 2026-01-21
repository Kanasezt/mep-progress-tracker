import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime

# --- 1. Connection (ใช้ Key เดิมจาก Project MEP ได้เลยครับ) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation Portal", layout="centered")

# --- 2. CSS Custom Styling (เน้นปุ่ม Submit สีน้ำเงินขนาดใหญ่) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #1E64B4 !important; 
        color: white !important;
        width: 100% !important;
        height: 60px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
    }
    .stTextArea textarea { font-size: 16px; }
    .header-text { color: #1E64B4; font-weight: bold; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 3. GUI Layout ---
st.markdown("<h1 class='header-text'>🚨 Issue Escalation Portal</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>แจ้งปัญหาที่ไม่สามารถแก้ไขได้ถึง Project Management Team</p>", unsafe_allow_html=True)
st.divider()

with st.form("issue_form", clear_on_submit=True):
    # ส่วนบน: ชื่อ (จำกัด 50 ตัวอักษรตามแบบ)
    u_name = st.text_input("** fill the name (50 ตัวอักษร)", max_chars=50, placeholder="ระบุชื่อ-นามสกุล ของท่าน")
    
    # ส่วนกลาง: รายละเอียด (จำกัด 500 ตัวอักษรตามแบบ)
    u_detail = st.text_area("** Issue detail description (500 ตัวอักษร)", max_chars=500, height=200, placeholder="อธิบายรายละเอียดปัญหาที่เกิดขึ้น...")
    
    # ส่วนล่าง: อัปโหลดรูปภาพ
    col_img, col_sub = st.columns([1, 1])
    
    with col_img:
        up_file = st.file_uploader("** browse the photo to upload", type=['jpg', 'png', 'jpeg'])

    # ส่วนปุ่มกด Submit
    submit_btn = st.form_submit_button("Submit")

    if submit_btn:
        if u_name and u_detail:
            with st.spinner("กำลังส่งข้อมูล..."):
                img_url = ""
                # จัดการรูปภาพ (ถ้ามี)
                if up_file:
                    f_name = f"issue_{uuid.uuid4()}.jpg"
                    supabase.storage.from_('images').upload(f_name, up_file.read())
                    img_url = supabase.storage.from_('images').get_public_url(f_name)
                
                # บันทึกลงฐานข้อมูล
                data = {
                    "staff_name": u_name,
                    "issue_detail": u_detail,
                    "image_url": img_url,
                    "status": "Pending"
                }
                
                res = supabase.table("issue_escalation").insert(data).execute()
                
                if res.data:
                    st.success("✅ แจ้งเรื่องเรียบร้อยแล้ว ทีมงานจะรีบดำเนินการตรวจสอบ")
                    st.balloons()
                else:
                    st.error("เกิดข้อผิดพลาดในการส่งข้อมูล")
        else:
            st.warning("กรุณากรอกชื่อและรายละเอียดปัญหาให้ครบถ้วน")

# --- 4. สำหรับ Admin (Project Management) ดูข้อมูล ---
if st.checkbox("Show Dashboard (For PM Team Only)"):
    st.subheader("📋 Recent Issues")
    res_data = supabase.table("issue_escalation").select("*").order("created_at", desc=True).execute()
    if res_data.data:
        df = pd.DataFrame(res_data.data)
        st.dataframe(df[['created_at', 'staff_name', 'issue_detail', 'status']], use_container_width=True)
        
        # แสดงรูปภาพประกอบ
        for index, row in df.iterrows():
            if row['image_url']:
                with st.expander(f"🖼️ ดูรูปภาพจากคุณ {row['staff_name']}"):
                    st.image(row['image_url'], width=400)
    else:
        st.info("ยังไม่มีรายการแจ้งปัญหาเข้ามา")