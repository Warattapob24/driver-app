import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import json
import os
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ", page_icon="🚗", layout="wide")
SETTINGS_FILE = "settings.json"

# 🟢 [สำคัญ] กำหนดชื่อชีทให้ตรงกันทั้งตอนอ่านและตอนบันทึก 
# ต้องตรงกับชื่อ Tab ด้านล่างใน Google Sheet เป๊ะๆ (ในภาพของคุณคือ "Drivers")
SHEET_NAME = "Drivers" 

# --- TIMEZONE ---
def get_thai_time():
    tz_thai = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz_thai)

def get_thai_date():
    return get_thai_time().date()

# --- 2. SETTINGS ---
def load_settings():
    default_settings = {"ev_rate": 40.0}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        except: return default_settings
    return default_settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)

# --- 3. DATA LOADING ---
def load_and_clean_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 🟢 แก้ไข: ระบุชื่อ worksheet ชัดเจน เพื่อความชัวร์
        df = conn.read(worksheet=SHEET_NAME, ttl=0)
        
        required_cols = [
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ]
        
        # ถ้าโหลดมาแล้ว Col ไม่ครบ หรือเป็น DataFrame ว่าง ให้สร้างใหม่
        if df.empty or len(df.columns) < len(required_cols):
             return pd.DataFrame(columns=required_cols)
        
        # Clean Data & Rename
        col_map = {
            'Date': 'วันที่', 'Time': 'เวลา', 'Platform': 'แอป',
            'Category': 'หมวดหมู่', 'SubCategory': 'รายการ',
            'Amount_Gross': 'ยอดเต็ม/หน้าแอป', 'Deduction': 'หัก/จ่าย',
            'Tip': 'ทิป', 'Net_Income': 'คงเหลือ/สุทธิ',
            'Distance_Km': 'ระยะทาง(กม.)', 'Note': 'หมายเหตุ',
            'Odometer': 'เลขไมล์',
            'Payment_Method': 'ช่องทางรับเงิน',
            'Cash_In': 'เงินสดเข้าตัว'
        }
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)
        
        # เติม Column ที่ขาด
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0 if col in ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์'] else ""
        
        # จัดการ Type ตัวเลข (ป้องกัน Error เวลาคำนวณ)
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        if 'วันที่' in df.columns:
            df['วันที่'] = pd.to_datetime(df['วันที่'], errors='coerce').dt.date
            
        # กรองเอาเฉพาะ Column ที่เราใช้จริง (ป้องกันขยะจาก Sheet)
        return df[required_cols]
        
    except Exception as e:
        # กรณีเชื่อมต่อไม่ได้ ให้คืนค่าว่างเพื่อให้ App รันต่อได้และแสดง Error
        st.error(f"⚠️ ไม่พบชีทชื่อ '{SHEET_NAME}' หรือเชื่อมต่อไม่ได้: {e}")
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

# --- ฟังก์ชันบันทึก ---
def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_save = df.copy()
        if 'วันที่' in df_save.columns:
            df_save['วันที่'] = df_save['วันที่'].astype(str)
            
        # 🟢 บันทึกลงชื่อ Worksheet เดียวกับตอนอ่าน (สำคัญมาก)
        conn.update(worksheet=SHEET_NAME, data=df_save)
    except Exception as e:
        st.error(f"บันทึกไม่สำเร็จ: {e}")

if 'data' not in st.session_state:
    st.session_state.data = load_and_clean_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"เวลา: {get_thai_time().strftime('%H:%M')}")
    
    if st.button("🔄 รีเฟรชข้อมูล (Cloud)"):
        st.cache_data.clear() # เคลียร์ cache
        st.session_state.data = load_and_clean_data()
        st.rerun()
    
    current_settings = load_settings()
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=float(current_settings.get("ev_rate", 40.0)), step=5.0)
    
    if new_ev_rate != current_settings.get("ev_rate"):
        save_settings({"ev_rate": new_ev_rate})
        st.toast("บันทึกค่าไฟแล้ว!")
    
    ev_home_rate = new_ev_rate

    st.divider()
    st.markdown("### 🎯 เป้าหมายรายวัน")
    target_income = st.number_input("ตั้งเป้ารายได้ (บาท)", value=2000, step=100)
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูลทั้งหมด", type="primary"):
        st.session_state.data = st.session_state.data.iloc[0:0] # ล้างข้อมูลแต่เก็บ Header ไว้
        save_data(st.session_state.data)
        st.rerun()

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 สรุปผลละเอียด", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (ปรับปรุงให้กรอกไว ไม่ต้องลบเลข 0)
# ==========================================
with tab1:
    col_type, col_form = st.columns([1, 2])
    with col_type:
        st.subheader("เลือกรายการ")
        entry_type = st.radio(
            "ประเภทรายการ",
            ["🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "💳 เติมเครดิตแอป", "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)", "🛠️ จ่ายอื่นๆ"],
        )

    with col_form:
        st.container(border=True)
        
        # 1. รับงาน
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            # clear_on_submit=True จะช่วยล้างข้อมูลให้เป็นสีเทาหลังกดปุ่ม
            with st.form(key="form_income", clear_on_submit=True):
                c_app, c_pay = st.columns(2)
                with c_app:
                    platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                with c_pay:
                    pay_method = st.selectbox("ช่องทางรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])

                c1, c2 = st.columns(2)
                with c1: 
                    # 🟢 แก้จุดที่ 1: ใส่ value=None และ placeholder="0"
                    app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0, value=None, placeholder="0")
                with c2: 
                    # 🟢 แก้จุดที่ 2: ใส่ value=None
                    real_receive = st.number_input("เงินที่รับจริง (รวมทิป)", min_value=0.0, step=10.0, value=None, placeholder="0")
                
                note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
                
                # ปุ่มบันทึกขนาดใหญ่ กดง่าย
                submitted = st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True)
                
                if submitted:
                    # แปลงค่า None (ช่องว่าง) ให้เป็น 0.0 เพื่อคำนวณ
                    price_val = app_price if app_price is not None else 0.0
                    real_val = real_receive if real_receive is not None else 0.0
                    
                    if price_val > 0 or real_val > 0:
                        # Logic: ถ้าไม่ได้กรอกช่องรับจริง ให้ถือว่ารับเท่าหน้าแอป
                        if real_val == 0 and price_val > 0: real_val = price_val 
                        
                        tip = max(0, real_val - price_val)
                        cash_in_hand = real_val if pay_method == "💵 เงินสด/โอน" else 0.0
                        
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method,
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': 0, 'ทิป': tip, 
                            'คงเหลือ/สุทธิ': real_val, 'เงินสดเข้าตัว': cash_in_hand, 
                            'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast(f"บันทึกรายได้ {real_val:.0f} บาท")
                        st.rerun()
                    else: st.warning("กรุณากรอกยอดเงิน")

        # 2. เติมเครดิต
        elif entry_type == "💳 เติมเครดิตแอป":
            st.markdown("#### 💳 เติมเงินเข้าแอป")
            with st.form(key="form_topup", clear_on_submit=True):
                sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
                # 🟢 แก้จุดที่ 3: ช่องกรอกเงินเป็นสีเทา (ว่าง)
                cost = st.number_input("จำนวนเงินที่เติม", min_value=0.0, value=None, placeholder="0")
                submitted = st.form_submit_button("บันทึกรายจ่าย 💾", type="primary", use_container_width=True)
                
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 'เงินสดเข้าตัว': -cost_val, 'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast("บันทึกแล้ว")
                        st.rerun()

        # 3. พลังงาน
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            with st.form(key="form_energy", clear_on_submit=True):
                e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
                
                # Logic: ถ้าเลือกชาร์จบ้าน ให้ขึ้นราคาเหมา (มีตัวเลข) แต่ถ้าอย่างอื่นให้ว่างไว้
                default_val = float(ev_home_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
                
                # 🟢 แก้จุดที่ 4: ช่องกรอกเงินเป็นสีเทา (ว่าง)
                cost = st.number_input("จำนวนเงิน", min_value=0.0, value=default_val, placeholder="0")
                note = st.text_input("สถานที่")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 'เงินสดเข้าตัว': -cost_val, 'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()

        # 4. ไมล์
        elif entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            with st.form(key="form_odom", clear_on_submit=True):
                shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
                # 🟢 แก้จุดที่ 5: ช่องเลขไมล์ว่างไว้
                odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0, value=None, placeholder="กรอกเลขไมล์")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                
                if submitted:
                    odom_val = odometer if odometer is not None else 0.0
                    if odom_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': shift_type, 'ช่องทางรับเงิน': '-',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                            'เลขไมล์': odom_val, 'หมายเหตุ': f"เลขไมล์ {shift_type}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()

        # 5. จ่ายอื่น
        elif entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### 🛠️ จ่ายทั่วไป")
            with st.form(key="form_other", clear_on_submit=True):
                sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
                # 🟢 แก้จุดที่ 6: ช่องจ่ายอื่นว่างไว้
                cost = st.number_input("จำนวนเงิน", min_value=0.0, value=None, placeholder="0")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 'เงินสดเข้าตัว': -cost_val, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()
    st.markdown("<br>" * 5, unsafe_allow_html=True)

# ==========================================
# TAB 2: สรุปผล (Upgrade: ใส่ key ป้องกัน Error 100%)
# ==========================================
import calendar

with tab2:
    st.markdown("### 📊 แดชบอร์ดวิเคราะห์ผลงาน")
    
    # 1. ตัวเลือกช่วงเวลา
    c_filter, c_blank = st.columns([2, 3])
    with c_filter:
        # 🟢 ใส่ key="unique_time_filter" เพื่อระบุตัวตน ไม่ให้ซ้ำกับใคร
        time_filter = st.selectbox("📅 เลือกช่วงเวลา:", 
                                 ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง"],
                                 key="unique_time_filter_tab2")
    
    custom_start, custom_end = None, None
    if time_filter == "กำหนดเอง":
        # 🟢 ใส่ key="unique_date_picker"
        dr = st.date_input("ช่วงวันที่:", 
                         value=(get_thai_date(), get_thai_date()),
                         key="unique_date_picker_tab2")
        if len(dr) == 2: custom_start, custom_end = dr
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        f_df = df.copy()
        
        # ตัวแปรสำหรับคำนวณเป้าหมาย (Days Multiplier)
        days_count = 1 
        
        # Filter Logic & Days Calculation
        if time_filter == "วันนี้": 
            f_df = df[df['วันที่'] == today]
            days_count = 1
        elif time_filter == "เมื่อวาน": 
            f_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
            days_count = 1
        elif time_filter == "สัปดาห์นี้":
            start = today - datetime.timedelta(days=today.weekday())
            f_df = df[(df['วันที่'] >= start) & (df['วันที่'] <= start + datetime.timedelta(days=6))]
            days_count = 7
        elif time_filter == "เดือนนี้": 
            f_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
            days_count = calendar.monthrange(today.year, today.month)[1]
        elif time_filter == "เดือนที่แล้ว":
            first = today.replace(day=1); last_prev = first - datetime.timedelta(days=1); start_prev = last_prev.replace(day=1)
            f_df = df[(df['วันที่'] >= start_prev) & (df['วันที่'] <= last_prev)]
            days_count = calendar.monthrange(start_prev.year, start_prev.month)[1]
        elif time_filter == "ปีนี้": 
            f_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
            days_count = 365
        elif time_filter == "กำหนดเอง" and custom_start and custom_end:
            f_df = df[(df['วันที่'] >= custom_start) & (df['วันที่'] <= custom_end)]
            days_count = (custom_end - custom_start).days + 1

        if not f_df.empty:
            # --- คำนวณตัวเลข ---
            inc_df = f_df[f_df['หมวดหมู่'] == 'รายรับ']
            exp_df = f_df[f_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            total_exp = exp_df['หัก/จ่าย'].sum()
            net = total_inc - total_exp
            cash = f_df['เงินสดเข้าตัว'].sum()
            
            # คำนวณระยะทาง
            odom_df = f_df[f_df['เลขไมล์'] > 0]
            dist = 0
            if not odom_df.empty:
                d_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                dist = (d_odom['max'] - d_odom['min']).sum()
            
            # คำนวณชั่วโมง
            hours = 0
            shift_df = f_df[f_df['หมวดหมู่'] == 'กะงาน']
            if not shift_df.empty:
                for d in shift_df['วันที่'].unique():
                    ds = shift_df[shift_df['วันที่'] == d]
                    s = ds[ds['รายการ'].str.contains("เริ่ม")]['เวลา']
                    e = ds[ds['รายการ'].str.contains("เลิก")]['เวลา']
                    if not s.empty and not e.empty:
                        try:
                            ts = pd.to_datetime(s.min(), format='%H:%M')
                            te = pd.to_datetime(e.max(), format='%H:%M')
                            h = (te - ts).total_seconds()/3600
                            if h < 0: h += 24
                            hours += h
                        except: pass
            
            # --- 🎯 ส่วนเป้าหมาย ---
            # ใช้ target_income จาก Sidebar
            # (ถ้า Sidebar error ให้เช็คว่าตัวแปร target_income ถูกประกาศข้างบนแล้วหรือไม่)
            if 'target_income' not in locals(): target_income = 2000 # ค่า Default กัน Error

            total_target = target_income * days_count
            
            st.markdown(f"**🎯 เป้าหมาย ({time_filter}): {total_inc:,.0f} / {total_target:,.0f} บาท**")
            progress = min(total_inc / total_target, 1.0) if total_target > 0 else 0
            st.progress(progress, text=f"ทำได้แล้ว {progress*100:.1f}% ({total_inc:,.0f} บาท)")

            # --- 📈 ส่วนแสดงผล Metrics ---
            st.markdown("#### 💎 ประสิทธิภาพการขับ")
            
            baht_per_km = net / dist if dist > 0 else 0
            baht_per_hr = net / hours if hours > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f} บ.", help="รายรับ - รายจ่าย")
            m2.metric("🛣️ ระยะทาง", f"{dist:,.0f} กม.")
            m3.metric("⚡ บาท / กม.", f"{baht_per_km:.2f} บ.", delta_color="normal", help="ควรมากกว่า 5-10 บาท")
            m4.metric("⏱️ บาท / ชม.", f"{baht_per_hr:.0f} บ.", help="ค่าแรงต่อชั่วโมง")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 เงินสดเข้าตัว", f"{cash:,.0f} บ.")
            c2.metric("💸 รายจ่ายรวม", f"{total_exp:,.0f} บ.")
            c3.metric("⏳ ชั่วโมงขับ", f"{hours:.1f} ชม.")
            c4.metric("📝 จำนวนงาน", f"{len(inc_df)} งาน")
            
            st.divider()

            # --- 📊 กราฟ ---
            APP_COLORS = { "Grab": "#00B14F", "Line Man": "#06C755", "Bolt": "#34D186", "Maxim": "#FFD600", "Robinhood": "#9D2398", "Win": "#FF6B00", "งานนอก": "#7F8C8D", "ระบบ": "#95A5A6" }

            col_g1, col_g2 = st.columns([2, 1])
            with col_g1:
                if not inc_df.empty:
                    daily = inc_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
                    st.plotly_chart(px.area(daily, x='วันที่', y='คงเหลือ/สุทธิ', title="📈 เส้นทางรายได้ (Net Income)", markers=True, color_discrete_sequence=['#2E86C1']), use_container_width=True)
            with col_g2:
                if not inc_df.empty:
                    fig = px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', title="🍩 สัดส่วนรายได้", hole=0.4, color='แอป', color_discrete_map=APP_COLORS)
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)

            col_g3, col_g4 = st.columns(2)
            with col_g3:
                if not inc_df.empty:
                    temp = inc_df.copy()
                    temp['Hour'] = pd.to_datetime(temp['เวลา'], format='%H:%M').dt.hour
                    hm = temp.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                    if not hm.empty:

# ==========================================
# TAB 2: สรุปผล (แก้ไข Bug: ย้าย import calendar ให้ถูกต้อง)
# ==========================================
import calendar  # 🟢 เพิ่มบรรทัดนี้เพื่อเรียกใช้ปฏิทิน

with tab2:
    st.markdown("### 📊 แดชบอร์ดวิเคราะห์ผลงาน")
    
    # 1. ตัวเลือกช่วงเวลา
    c_filter, c_blank = st.columns([2, 3])
    with c_filter:
        time_filter = st.selectbox("📅 เลือกช่วงเวลา:", ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง"])
    
    custom_start, custom_end = None, None
    if time_filter == "กำหนดเอง":
        dr = st.date_input("ช่วงวันที่:", value=(get_thai_date(), get_thai_date()))
        if len(dr) == 2: custom_start, custom_end = dr
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        f_df = df.copy()
        
        # ตัวแปรสำหรับคำนวณเป้าหมาย (Days Multiplier)
        days_count = 1 
        
        # Filter Logic & Days Calculation
        if time_filter == "วันนี้": 
            f_df = df[df['วันที่'] == today]
            days_count = 1
        elif time_filter == "เมื่อวาน": 
            f_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
            days_count = 1
        elif time_filter == "สัปดาห์นี้":
            start = today - datetime.timedelta(days=today.weekday())
            f_df = df[(df['วันที่'] >= start) & (df['วันที่'] <= start + datetime.timedelta(days=6))]
            days_count = 7
        elif time_filter == "เดือนนี้": 
            f_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
            # 🟢 คำนวณวันในเดือนนี้ (ใช้ calendar ได้แล้ว)
            days_count = calendar.monthrange(today.year, today.month)[1]
        elif time_filter == "เดือนที่แล้ว":
            first = today.replace(day=1); last_prev = first - datetime.timedelta(days=1); start_prev = last_prev.replace(day=1)
            f_df = df[(df['วันที่'] >= start_prev) & (df['วันที่'] <= last_prev)]
            # 🟢 คำนวณวันในเดือนที่แล้ว
            days_count = calendar.monthrange(start_prev.year, start_prev.month)[1]
        elif time_filter == "ปีนี้": 
            f_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
            days_count = 365
        elif time_filter == "กำหนดเอง" and custom_start and custom_end:
            f_df = df[(df['วันที่'] >= custom_start) & (df['วันที่'] <= custom_end)]
            days_count = (custom_end - custom_start).days + 1

        if not f_df.empty:
            # --- คำนวณตัวเลข ---
            inc_df = f_df[f_df['หมวดหมู่'] == 'รายรับ']
            exp_df = f_df[f_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            total_exp = exp_df['หัก/จ่าย'].sum()
            net = total_inc - total_exp
            cash = f_df['เงินสดเข้าตัว'].sum()
            
            # คำนวณระยะทาง
            odom_df = f_df[f_df['เลขไมล์'] > 0]
            dist = 0
            if not odom_df.empty:
                d_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                dist = (d_odom['max'] - d_odom['min']).sum()
            
            # คำนวณชั่วโมง
            hours = 0
            shift_df = f_df[f_df['หมวดหมู่'] == 'กะงาน']
            if not shift_df.empty:
                for d in shift_df['วันที่'].unique():
                    ds = shift_df[shift_df['วันที่'] == d]
                    s = ds[ds['รายการ'].str.contains("เริ่ม")]['เวลา']
                    e = ds[ds['รายการ'].str.contains("เลิก")]['เวลา']
                    if not s.empty and not e.empty:
                        try:
                            ts = pd.to_datetime(s.min(), format='%H:%M')
                            te = pd.to_datetime(e.max(), format='%H:%M')
                            h = (te - ts).total_seconds()/3600
                            if h < 0: h += 24
                            hours += h
                        except: pass
            
            # --- 🎯 ส่วนเป้าหมาย ---
            total_target = target_income * days_count
            
            st.markdown(f"**🎯 เป้าหมาย ({time_filter}): {total_inc:,.0f} / {total_target:,.0f} บาท**")
            progress = min(total_inc / total_target, 1.0) if total_target > 0 else 0
            st.progress(progress, text=f"ทำได้แล้ว {progress*100:.1f}% ({total_inc:,.0f} บาท)")

            # --- 📈 ส่วนแสดงผล Metrics ---
            st.markdown("#### 💎 ประสิทธิภาพการขับ")
            
            baht_per_km = net / dist if dist > 0 else 0
            baht_per_hr = net / hours if hours > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f} บ.", help="รายรับ - รายจ่าย")
            m2.metric("🛣️ ระยะทาง", f"{dist:,.0f} กม.")
            m3.metric("⚡ บาท / กม.", f"{baht_per_km:.2f} บ.", delta_color="normal", help="ควรมากกว่า 5-10 บาท")
            m4.metric("⏱️ บาท / ชม.", f"{baht_per_hr:.0f} บ.", help="ค่าแรงต่อชั่วโมง")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 เงินสดเข้าตัว", f"{cash:,.0f} บ.")
            c2.metric("💸 รายจ่ายรวม", f"{total_exp:,.0f} บ.")
            c3.metric("⏳ ชั่วโมงขับ", f"{hours:.1f} ชม.")
            c4.metric("📝 จำนวนงาน", f"{len(inc_df)} งาน")
            
            st.divider()

            # --- 📊 กราฟ ---
            APP_COLORS = { "Grab": "#00B14F", "Line Man": "#06C755", "Bolt": "#34D186", "Maxim": "#FFD600", "Robinhood": "#9D2398", "Win": "#FF6B00", "งานนอก": "#7F8C8D", "ระบบ": "#95A5A6" }

            col_g1, col_g2 = st.columns([2, 1])
            with col_g1:
                if not inc_df.empty:
                    daily = inc_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
                    st.plotly_chart(px.area(daily, x='วันที่', y='คงเหลือ/สุทธิ', title="📈 เส้นทางรายได้ (Net Income)", markers=True, color_discrete_sequence=['#2E86C1']), use_container_width=True)
            with col_g2:
                if not inc_df.empty:
                    fig = px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', title="🍩 สัดส่วนรายได้", hole=0.4, color='แอป', color_discrete_map=APP_COLORS)
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)

            col_g3, col_g4 = st.columns(2)
            with col_g3:
                if not inc_df.empty:
                    temp = inc_df.copy()
                    temp['Hour'] = pd.to_datetime(temp['เวลา'], format='%H:%M').dt.hour
                    hm = temp.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                    if not hm.empty:
                        fig_hm = px.imshow(hm, title="🔥 ช่วงเวลาทำเงิน", aspect="auto", color_continuous_scale="Greens", labels=dict(x="เวลา (น.)", y="แอป", color="บาท"))
                        st.plotly_chart(fig_hm, use_container_width=True)
            
            with col_g4:
                if not exp_df.empty:
                    exp_sum = exp_df.groupby('รายการ')['หัก/จ่าย'].sum().reset_index()
                    fig_exp = px.bar(exp_sum, x='รายการ', y='หัก/จ่าย', title="💸 รายจ่ายแยกตามประเภท", color='รายการ', text_auto=True)
                    st.plotly_chart(fig_exp, use_container_width=True)
                else:
                    st.info("ไม่มีรายจ่ายในช่วงนี้")

        else: st.warning("ไม่พบข้อมูลในช่วงเวลานี้")
    else: st.info("ยังไม่มีข้อมูลในระบบ")
                        
# ==========================================
# TAB 3: ฐานข้อมูล (ปรับปรุง Logic การแก้ข้อมูล)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        # ตรวจสอบว่ามีข้อมูลก่อนสร้าง Multiselect เพื่อกัน Error
        apps = st.session_state.data['แอป'].unique() if not st.session_state.data.empty else []
        cats = st.session_state.data['หมวดหมู่'].unique() if not st.session_state.data.empty else []
        
        f_app = c1.multiselect("แอป", apps)
        f_cat = c2.multiselect("หมวดหมู่", cats)
        f_date = c3.selectbox("วันที่", ["ทั้งหมด", "วันนี้", "เดือนนี้"])

    df_show = st.session_state.data.copy()
    if not df_show.empty:
        if f_app: df_show = df_show[df_show['แอป'].isin(f_app)]
        if f_cat: df_show = df_show[df_show['หมวดหมู่'].isin(f_cat)]
        if f_date == "วันนี้": df_show = df_show[df_show['วันที่'] == get_thai_date()]
        elif f_date == "เดือนนี้": 
            t = get_thai_date()
            df_show = df_show[(pd.to_datetime(df_show['วันที่']).dt.month == t.month) & (pd.to_datetime(df_show['วันที่']).dt.year == t.year)]

        # 🟢 ปรับปรุง: ใช้ st.data_editor รับค่ากลับมาตรงๆ (วิธีนี้เสถียรกว่า)
        edited_df = st.data_editor(
            df_show, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="editor",
            column_config={
                "คงเหลือ/สุทธิ": st.column_config.NumberColumn(format="%.0f ฿"),
                "ยอดเต็ม/หน้าแอป": st.column_config.NumberColumn(format="%.0f ฿"),
                "วันที่": st.column_config.DateColumn(format="YYYY-MM-DD")
            }
        )
        
        if st.button("💾 บันทึกการเปลี่ยนแปลง", type="primary"):
            try:
                # ถ้ามีการกรองข้อมูลอยู่ ระบบจะเตือน (เพราะถ้า Save ทับ ข้อมูลที่ซ่อนอยู่อาจหาย)
                if len(df_show) != len(st.session_state.data):
                     st.warning("⚠️ คุณกำลังกรองข้อมูลอยู่ ระบบจะบันทึกเฉพาะข้อมูลที่เห็นเท่านั้น (แนะนำให้เลือก 'วันที่: ทั้งหมด' ก่อนทำการลบหรือแก้ไข)")
                     st.session_state.data.update(edited_df) # อัปเดตเฉพาะที่เห็น
                else:
                     st.session_state.data = edited_df # แทนที่ข้อมูลทั้งหมดได้เลย (เพราะไม่ได้กรอง)
                
                save_data(st.session_state.data)
                st.success("บันทึกสำเร็จ!")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    else:
        st.info("ไม่มีข้อมูลให้แสดง")







