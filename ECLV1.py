import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timedelta, timezone
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

st.set_page_config(page_title="Issue Escalation V4.0", layout="wide")

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
    .related-tag { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 5px; font-size: 14px; font-weight: bold; margin-left: 10px; border: 1px solid #ddd; }
    /* สไตล์ปุ่ม Like */
    .like-container { display: flex; align-items: center; gap: 5px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Data Fetching ---
@st.cache_data(ttl=10) # ลดเวลาเพื่อให้ยอด Like อัปเดตไวขึ้น
def load_data():
    try:
        res = supabase.table("issue_escalation").select("*").order("id", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
        if not df_raw.empty:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.tz_convert('Asia/Bangkok')
            if 'updated_at' in df_raw.columns:
                df_raw['updated_at'] = pd.to_datetime(df_raw['updated_at']).dt.tz_convert('Asia/Bangkok')
            else:
                df_raw['updated_at'] = df_raw['created_at']
            # ถ้าไม่มีคอลัมน์ likes ให้ตั้งเป็น 0
            if 'likes' not in df_raw.columns:
                df_raw['likes'] = 0
        return df_raw
    except:
        return pd.DataFrame()

# ฟังก์ชันกด Like
def add_like(record_id, current_likes):
    new_likes = int(current_likes) + 1
    supabase.table("issue_escalation").update({"likes": new_likes}).eq("id", record_id).execute()
    st.cache_data.clear()

# --- 4. Header & Refresh ---
col_t, col_r = st.columns([5, 1])
with col_t: st.title("🚨 Issue Escalation V4.0")
with col_r:
    st.write("##")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear(); st.rerun()

df = load_data()

# --- 5. Sidebar Admin ---
with st.sidebar:
    st.header("🔐 Admin Access")
    admin_pwd = st.text_input("Enter Password", type="password")
    is_admin = (admin_pwd == "pm1234")
    if is_admin: st.success("Admin Mode ON ✅")

# --- 6. Cards & Form ---
if not df.empty:
    c1, c2, c3 = st.columns(3)
    op = len(df[df['status'] == 'Open']); cl = len(df[df['status'] == 'Closed']); can = len(df[df['status'] == 'Cancel'])
    c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()
with st.form("issue_form", clear_on_submit=True):
    col_n, col_r = st.columns([2, 1])
    u_name = col_n.text_input("** Fill Your Name")
    u_related = col_r.radio("Related to:", options=["IFS", "CSC", "HW", "other"], horizontal=True)
    u_detail = st.text_area("** Issue Detail", height=100)
    up_file = st.file_uploader("** Upload Photo", type=['jpg', 'png', 'jpeg'])
    if st.form_submit_button("Submit Report"):
        if u_name and u_detail:
            img_url = ""
            if up_file:
                f_name = f"esc_{uuid.uuid4()}.jpg"
                supabase.storage.from_('images').upload(f_name, up_file.read())
                img_url = supabase.storage.from_('images').get_public_url(f_name)
            supabase.table("issue_escalation").insert({"staff_name": u_name, "issue_detail": u_detail, "related_to": u_related, "image_url": img_url, "status": "Open", "likes": 0}).execute()
            st.cache_data.clear(); st.success("✅ Success!"); st.rerun()

# --- 7. Dashboard ---
if not df.empty:
    st.divider(); st.subheader("📋 Dashboard")
    # ... (ส่วน Filter เหมือนเดิม)
    
    now_th = datetime.now(timezone(timedelta(hours=7)))
    for i, r in df.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info, c_admin = st.columns([1.5, 3.5, 1.5])
            with c_img:
                if r['image_url']: st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
            with c_info:
                st.markdown(f"### {r['id']:03d} - {r['staff_name']} <span class='related-tag'>Related: {r['related_to']}</span>", unsafe_allow_html=True)
                st.write(f"**Detail:** {r['issue_detail']}")
                st.markdown(f"Status: **{r['status']}**")
                
                # แสดงเวลา และปุ่ม Like
                time_str = r['created_at'].strftime('%d %b %y | %H:%M:%S')
                c_like1, c_like2 = st.columns([2, 1])
                with c_like1:
                    st.caption(f"📅 {time_str}")
                with c_like2:
                    # Logic: กดได้ไม่จำกัดครั้ง
                    if st.button(f"❤️ {r.get('likes', 0)}", key=f"like_{r['id']}"):
                        add_like(r['id'], r.get('likes', 0))
                        st.rerun()

            with c_admin:
                if is_admin:
                    new_stat = st.selectbox("Update", ["Open", "Closed", "Cancel"], index=["Open", "Closed", "Cancel"].index(r['status']), key=f"st_{r['id']}")
                    b1, b2 = st.columns(2)
                    if b1.button("Confirm ✅", key=f"ok_{r['id']}"):
                        try:
                            supabase.table("issue_escalation").update({"status": new_stat, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", r['id']).execute()
                        except:
                            supabase.table("issue_escalation").update({"status": new_stat}).eq("id", r['id']).execute()
                        st.cache_data.clear(); st.rerun()
                    if b2.button("Delete 🗑️", key=f"del_{r['id']}"):
                        supabase.table("issue_escalation").delete().eq("id", r['id']).execute()
                        st.cache_data.clear(); st.rerun()
            st.divider()