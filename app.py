import io
import pandas as pd
import requests
import streamlit as st

# ตั้งค่าหน้าจอ Streamlit
st.set_page_config(
    page_title="ตารางทำงานประจำสัปดาห์",
    page_icon="📅",
    layout="wide"
)

st.title("📅 ตารางทำงานประจำสัปดาห์ (Weekly Roster)")
st.caption("ระบบดึงข้อมูลและอัปเดตตารางงานผ่าน GitHub")

# ดึงค่า Secrets จาก Streamlit
GIST_ID = st.secrets.get("GIST_ID", "").strip()
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "").strip()

# ข้อมูลตารางงานเริ่มต้น (สำรอง)
DEFAULT_DATA = [
    {"Name": "สมชาย", "Mon": "08:00 - 17:00", "Tue": "08:00 - 17:00", "Wed": "OFF", "Thu": "08:00 - 17:00", "Fri": "08:00 - 17:00", "Sat": "10:00 - 19:00", "Sun": "OFF"},
    {"Name": "สมหญิง", "Mon": "OFF", "Tue": "13:00 - 22:00", "Wed": "13:00 - 22:00", "Thu": "13:00 - 22:00", "Fri": "OFF", "Sat": "13:00 - 22:00", "Sun": "10:00 - 19:00"}
]

def save_data(df):
    """ฟังก์ชันบันทึกข้อมูลตารางงานกลับไปยัง GitHub Gist"""
    if not GIST_ID or not GITHUB_TOKEN:
        st.warning("⚠️ ยังไม่ได้ตั้งค่า GIST_ID หรือ GITHUB_TOKEN ใน Secrets")
        return False
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    # แปลง DataFrame เป็น JSON String โดยรองรับภาษาไทย
    json_data = df.to_json(orient="records", indent=2, force_ascii=False)
    
    payload = {
        "files": {
            "schedule.json": {
                "content": json_data
            }
        }
    }
    
    try:
        res = requests.patch(url, headers=headers, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ GitHub: {e}")
        return False

def load_data():
    """ฟังก์ชันดึงข้อมูลตารางงานจาก GitHub Gist"""
    if not GIST_ID:
        return pd.DataFrame(DEFAULT_DATA)
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            files = res.json().get("files", {})
            
            # ตรวจสอบว่ามีไฟล์ schedule.json ใน Gist หรือไม่
            if "schedule.json" in files:
                content = files["schedule.json"]["content"].strip()
                
                # ถ้าไฟล์ว่าง หรือมีแค่ [] ให้สร้างข้อมูลเริ่มต้นส่งไปบันทึก
                if not content or content == "[]":
                    df_default = pd.DataFrame(DEFAULT_DATA)
                    save_data(df_default)
                    return df_default
                
                # อ่าน JSON ผ่าน io.StringIO เพื่อป้องกัน Pandas มองเนื้อหาเป็นชื่อไฟล์
                return pd.read_json(io.StringIO(content))
            else:
                st.warning("⚠️ ไม่พบไฟล์ schedule.json ใน Gist ระบบกำลังสร้างไฟล์เริ่มต้นให้...")
                df_default = pd.DataFrame(DEFAULT_DATA)
                save_data(df_default)
                return df_default
        else:
            st.error(f"ไม่สามารถดึงข้อมูลจาก GitHub ได้ (Status Code: {res.status_code})")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        
    return pd.DataFrame(DEFAULT_DATA)

# โหลดข้อมูลตารางงาน
df_schedule = load_data()

# ส่วนแสดงผลตารางงานสำหรับทุกคน (Read-only View)
st.subheader("📋 ตารางกะงานปัจจุบัน")
st.dataframe(df_schedule, use_container_width=True)

st.divider()

# ส่วนแก้ไขตารางงาน (สำหรับผู้จัดการ)
with st.expander("✏️ แก้ไข/อัปเดตตารางงาน (สำหรับผู้จัดการ)"):
    edited_df = st.data_editor(
        df_schedule,
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor"
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลงไป GitHub", type="primary"):
        with st.spinner("กำลังบันทึกข้อมูลลง GitHub..."):
            if save_data(edited_df):
                st.success("บันทึกตารางงานเรียบร้อยแล้ว! ข้อมูลจะอัปเดตให้น้องๆ เห็นทันที")
                st.rerun()
            else:
                st.error("บันทึกไม่สำเร็จ กรุณาตรวจสอบ GIST_ID และ GITHUB_TOKEN ใน Secrets อีกครั้ง")
