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

# ตัวเลือกเวลาเข้างานสำหรับ Dropdown
SHIFT_OPTIONS = [
    "09.30",
    "12.30",
    "13.00",
    "OFF",
    "ปิดสต็อก"
]

# รายชื่อคอลัมน์วันทั้งหมด
DAYS_COLS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ข้อมูลตารางงานเริ่มต้น (สำรอง)
DEFAULT_DATA = [
    {"Name": "BOSS", "Mon": "09.30", "Tue": "09.30", "Wed": "OFF", "Thu": "09.30", "Fri": "09.30", "Sat": "12.30", "Sun": "OFF"},
    {"Name": "MIN", "Mon": "OFF", "Tue": "13.00", "Wed": "13.00", "Thu": "13.00", "Fri": "OFF", "Sat": "13.00", "Sun": "12.30"}
]

# สีพาสเทลประจำวันสำหรับหัวตาราง
DAY_HEADER_COLORS = {
    "Name": "background-color: #eeeeee; color: #212121;",
    "Mon": "background-color: #fff9c4; color: #f57f17;",  # เหลือง
    "Tue": "background-color: #f8bbd0; color: #c2185b;",  # ชมพู
    "Wed": "background-color: #c8e6c9; color: #2e7d32;",  # เขียว
    "Thu": "background-color: #ffe0b2; color: #e65100;",  # ส้ม
    "Fri": "background-color: #bbdefb; color: #0d47a1;",  # ฟ้า
    "Sat": "background-color: #e1bee7; color: #6a1b9a;",  # ม่วง
    "Sun": "background-color: #ffcdd2; color: #b71c1c;"   # แดง
}

def get_shift_style(val):
    """ส่งคืนสไตล์ Inline CSS สีพาสเทลตามกะงาน"""
    val_str = str(val).strip()
    if val_str in ["09.30", "9.30"]:
        return "background-color: #e8f5e9; color: #1b5e20; font-weight: bold;"  # เขียวพาสเทล
    elif val_str in ["12.30", "13.00", "13.0"]:
        return "background-color: #fffde7; color: #f57f17; font-weight: bold;"  # เหลืองพาสเทล
    elif val_str == "OFF":
        return "background-color: #ffebee; color: #b71c1c; font-weight: bold;"  # แดงพาสเทล
    elif val_str == "ปิดสต็อก":
        return "background-color: #e3f2fd; color: #0d47a1; font-weight: bold;"  # ฟ้า/น้ำเงินพาสเทล
    return "background-color: #ffffff; color: #333333;"

def render_html_table(df):
    """สร้างตาราง HTML Custom ที่กำหนดหัวตารางแยกสีตามวัน ชัดเจนและสบายตา"""
    html = """
    <style>
        .custom-roster-table {
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            border-radius: 8px;
            overflow: hidden;
        }
        .custom-roster-table th {
            font-weight: 900 !important;
            font-size: 16px !important;
            padding: 12px 8px;
            text-align: center;
            border: 1px solid #d6d6d6;
        }
        .custom-roster-table td {
            padding: 12px 8px;
            text-align: center;
            font-size: 15px;
            border: 1px solid #e0e0e0;
        }
        .custom-roster-table td.name-cell {
            background-color: #ffffff;
            color: #111111;
            font-weight: bold;
            text-align: left;
            padding-left: 12px;
        }
    </style>
    <div style="overflow-x: auto;">
    <table class="custom-roster-table">
        <thead>
            <tr>
    """
    
    # วนลูปสร้างหัวตารางพร้อมใส่สีประจำวัน
    headers = ["Name"] + DAYS_COLS
    for h in headers:
        style = DAY_HEADER_COLORS.get(h, "")
        html += f'<th style="{style}">{h}</th>'
        
    html += """
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in df.iterrows():
        html += "<tr>"
        name_val = row.get("Name", "")
        html += f'<td class="name-cell">{name_val}</td>'
        
        for day in DAYS_COLS:
            val = row.get(day, "")
            style = get_shift_style(val)
            html += f'<td style="{style}">{val}</td>'
        html += "</tr>"
        
    html += """
        </tbody>
    </table>
    </div>
    """
    return html

def clean_dataframe_types(df):
    """แปลงคอลัมน์วันให้เป็นข้อความ (String) ทั้งหมด"""
    for col in DAYS_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"9.3": "09.30", "9.300000": "09.30", "13.0": "13.00", "13.000000": "13.00", "12.3": "12.30", "12.300000": "12.30"})
    return df

def save_data(df):
    """ฟังก์ชันบันทึกข้อมูลตารางงานกลับไปยัง GitHub Gist"""
    if not GIST_ID or not GITHUB_TOKEN:
        st.warning("⚠️️ ยังไม่ได้ตั้งค่า GIST_ID หรือ GITHUB_TOKEN ใน Secrets")
        return False
    
    df = clean_dataframe_types(df)
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
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
        df_default = pd.DataFrame(DEFAULT_DATA)
        return clean_dataframe_types(df_default)
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            files = res.json().get("files", {})
            if "schedule.json" in files:
                content = files["schedule.json"]["content"].strip()
                if not content or content == "[]":
                    df_default = pd.DataFrame(DEFAULT_DATA)
                    save_data(df_default)
                    return clean_dataframe_types(df_default)
                
                df = pd.read_json(io.StringIO(content), dtype=str)
                return clean_dataframe_types(df)
            else:
                df_default = pd.DataFrame(DEFAULT_DATA)
                save_data(df_default)
                return clean_dataframe_types(df_default)
        else:
            st.error(f"ไม่สามารถดึงข้อมูลจาก GitHub ได้ (Status Code: {res.status_code})")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        
    df_default = pd.DataFrame(DEFAULT_DATA)
    return clean_dataframe_types(df_default)

# โหลดข้อมูลตารางงาน
df_schedule = load_data()

# ส่วนแสดงผลตารางงานสำหรับทุกคน (ใช้ Custom HTML Table หัวตารางแยกสีตามวัน)
st.subheader("📋 ตารางกะงานปัจจุบัน")
st.markdown(render_html_table(df_schedule), unsafe_allow_html=True)

st.divider()

# ส่วนแก้ไขตารางงาน (สำหรับผู้จัดการ)
with st.expander("✏️ แก้ไข/อัปเดตตารางงาน (สำหรับผู้จัดการ)"):
    
    column_config = {
        "Name": st.column_config.TextColumn("ชื่อพนักงาน", required=True),
        "Mon": st.column_config.SelectboxColumn("Mon", options=SHIFT_OPTIONS, required=True),
        "Tue": st.column_config.SelectboxColumn("Tue", options=SHIFT_OPTIONS, required=True),
        "Wed": st.column_config.SelectboxColumn("Wed", options=SHIFT_OPTIONS, required=True),
        "Thu": st.column_config.SelectboxColumn("Thu", options=SHIFT_OPTIONS, required=True),
        "Fri": st.column_config.SelectboxColumn("Fri", options=SHIFT_OPTIONS, required=True),
        "Sat": st.column_config.SelectboxColumn("Sat", options=SHIFT_OPTIONS, required=True),
        "Sun": st.column_config.SelectboxColumn("Sun", options=SHIFT_OPTIONS, required=True),
    }

    edited_df = st.data_editor(
        df_schedule,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor"
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลงไป GitHub", type="primary"):
        with st.spinner("กำลังบันทึกข้อมูลลง GitHub..."):
            if save_data(edited_df):
                st.success("บันทึกตารางงานเรียบร้อยแล้ว!")
                st.rerun()
            else:
                st.error("บันทึกไม่สำเร็จ กรุณาตรวจสอบ GIST_ID และ GITHUB_TOKEN อีกครั้ง")
