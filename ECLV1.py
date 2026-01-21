import streamlit as st
import pandas as pd
from supabase import create_client, Client
import uuid
from datetime import datetime, timezone
import io

# --- 1. Connection ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://sizcmbmkbnlolguiulsv.supabase.co"
    KEY = "sb_publishable_ef9RitB16Z7aD683MVo_5Q_oWsnAsel"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Issue Escalation V3.2", layout="wide")

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important; color: white !important;
        width: 100%; height: 50px; font-size: 20px; font-weight: bold; border-radius: 10px;
    }
    .img-card { width: 100%; max-width: 120px; aspect-ratio: 1/1; object-fit: cover; border-radius: 10px; border: 1px solid #eee; }
    .card-open { background-color: #E65100; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-closed { background-color: #1B5E20; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .card-cancel { background-color: #424242; color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .val-text { font-size: 30px; font-weight: bold; display: block; }
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

# --- 4. Main UI ---
st.title("🚨 Issue Escalation V3.2")

c1, c2, c3 = st.columns(3)
op = len(df[df['status'] == 'Open']) if not df.empty else 0
cl = len(df[df['status'] == 'Closed']) if not df.empty else 0
can = len(df[df['status'] == 'Cancel']) if not df.empty else 0

c1.markdown(f"<div class='card-open'>OPEN<span class='val-text'>{op}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card-closed'>CLOSED<span class='val-text'>{cl}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='card-cancel'>CANCEL<span class='val-text'>{can}</span></div>", unsafe_allow_html=True)

st.divider()

# --- 5. Submit Form ---
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
            st.cache_data.clear()
            st.success("✅ Success!"); st.rerun()

# --- 6. Dashboard & Export ---
if not df.empty:
    st.divider()
    st.subheader("📋 Dashboard")
    f1, f2, f3 = st.columns([2, 1, 1])
    search = f1.text_input("🔍 Search Name/Detail")
    f_stat = f2.selectbox("Filter Status", ["All"] + list(df['status'].unique()))
    
    df_f = df.copy()
    if search:
        df_f = df_f[df_f['staff_name'].str.contains(search, case=False, na=False) | df_f['issue_detail'].str.contains(search, case=False, na=False)]
    if f_stat != "All":
        df_f = df_f[df_f['status'] == f_stat]

    # Quick Export Excel (No Image Waiting)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_f.to_excel(writer, index=False, sheet_name='Sheet1')
    
    f3.markdown("<br>", unsafe_allow_html=True)
    f3.download_button("📥 Download Excel", data=output.getvalue(), file_name="report.xlsx", mime="application/vnd.ms-excel")

    now_utc = datetime.now(timezone.utc)
    for i, r in df_f.reset_index(drop=True).iterrows():
        with st.container():
            c_img, c_info = st.columns([1, 4])
            with c_img:
                if r['image_url']: st.markdown(f'<img src="{r["image_url"]}" class="img-card">', unsafe_allow_html=True)
                else: st.write("No Image")
            with c_info:
                st.markdown(f"**{r['staff_name']}** | `{r['status']}`")
                st.write(r['issue_detail'])
                st.caption(f"🏷️ {r['related_to']} | 📅 {r['created_at'].strftime('%d %b %y') if pd.notnull(r['created_at']) else '-'}")
            st.divider()

# --- 7. Admin Panel (Fixed Login) ---
with st.sidebar:
    st.header("🔐 Admin Panel")
    pwd = st.text_input("Password", type="password")
    
    if pwd == "pm1234":
        st.success("Admin Logged In")
        # แสดงเมนู Admin เสมอถ้าใส่รหัสผ่านถูก
        st.write("---")
        if not df.empty:
            id_col = 'id' if 'id' in df.columns else df.columns[0]
            # แสดงรายชื่อคนแจ้งเพื่อให้เลือกง่ายขึ้น
            options = {row[id_col]: f"{row['staff_name']} (ID:{row[id_col]})" for _, row in df.iterrows()}
            target = st.selectbox("Select Record", options=options.keys(), format_func=lambda x: options[x])
            new_stat = st.selectbox("Update Status", ["Open", "Closed", "Cancel"])
            
            if st.button("🚀 Confirm Update", type="primary"):
                supabase.table("issue_escalation").update({"status": new_stat}).eq(id_col, target).execute()
                st.cache_data.clear()
                st.success("Updated!")
                st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลให้แก้ไข")
    elif pwd != "":
        st.error("รหัสผ่านไม่ถูกต้อง")
