import pandas as pd
import requests
import streamlit as st

# ตั้งค่าหน้าจอ Streamlit
st.set_page_config(
    page_title="ตารางทำงานประจำสัปดาห์", page_icon="📅", layout="wide"
)

st.title("📅 ตารางทำงานประจำสัปดาห์ (Weekly Roster)")
st.caption("ระบบดึงข้อมูลและอัปเดตตารางงานผ่าน GitHub")

# Config GitHub Gist (แนะนำให้ใส่ใน Streamlit Secrets เพื่อความปลอดภัย)
# GIST_ID คือ ID ของ Gist ที่สร้างขึ้น
# GITHUB_TOKEN คือ Personal Access Token ของ GitHub
GIST_ID = st.secrets.get("GIST_ID", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")

# ข้อมูลเริ่มต้นสำรอง (หากยังไม่ได้เชื่อม GitHub Gist)
DEFAULT_DATA = [
    {"Name": "สมชาย", "Mon": "08:00 - 17:00", "Tue": "08:00 - 17:00", "Wed": "OFF", "Thu": "08:00 - 17:00", "Fri": "08:00 - 17:00", "Sat": "10:00 - 19:00", "Sun": "OFF"},
    {"Name": "สมหญิง", "Mon": "OFF", "Tue": "13:00 - 22:00", "Wed": "13:00 - 22:00", "Thu": "13:00 - 22:00", "Fri": "OFF", "Sat": "13:00 - 22:00", "Sun": "10:00 - 19:00"}
]

# Function อ่านข้อมูลจาก GitHub Gist
def load_data():
    if not GIST_ID:
        return pd.DataFrame(DEFAULT_DATA)
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()["files"]["schedule.json"]["content"]
            return pd.read_json(content)
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลจาก GitHubได้: {e}")
    return pd.DataFrame(DEFAULT_DATA)

# Function บันทึกข้อมูลกลับไปยัง GitHub Gist
def save_data(df):
    if not GIST_ID or not GITHUB_TOKEN:
        st.warning("⚠️ ยังไม่ได้ตั้งค่า GIST_ID และ GITHUB_TOKEN ข้อมูลจะเปลี่ยนแค่ชั่วคราวเท่านั้น")
        return False
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    json_data = df.to_json(orient="records", indent=2)
    payload = {
        "files": {
            "schedule.json": {
                "content": json_data
            }
        }
    }
    res = requests.patch(url, headers=headers, json=payload)
    return res.status_code == 200

# โหลดข้อมูล
df_schedule = load_data()

# ส่วนแสดงผลสำหรับทีมงาน (Read-only View)
st.subheader("📋 ตารางกะงานปัจจุบัน")
st.dataframe(df_schedule, use_container_width=True)

st.divider()

# ส่วนจัดการ/แก้ไขตารางงาน (สำหรับบอส/ผู้จัดการ)
with st.expander("✏️ แก้ไข/อัปเดตตารางงาน (สำหรับผู้จัดการ)"):
    edited_df = st.data_editor(
        df_schedule,
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor"
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลงไป GitHub"):
        if save_data(edited_df):
            st.success("บันทึกตารางงานเรียบร้อยแล้ว! น้องๆ จะเห็นข้อมูลใหม่ทันทีที่โหลดหน้าเว็บ")
            st.rerun()
        else:
            st.error("เกิดข้อผิดพลาดในการบันทึกข้อมูล")
