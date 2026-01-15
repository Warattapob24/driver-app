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

# --- 2. SETTINGS (ฉบับ Cloud: จำค่าได้ตลอดไป) ---
def load_settings():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 🟢 เพิ่ม "target_income": 2000.0 เข้าไปในค่าเริ่มต้น
    default_settings = {"ev_rate": 50.0, "target_income": 2000.0} 
    try:
        df = conn.read(worksheet="Settings", ttl=0)
        if not df.empty and 'Key' in df.columns and 'Value' in df.columns:
            settings = dict(zip(df['Key'], df['Value']))
            return settings
    except Exception:
        pass
    return default_settings

def save_settings(settings):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        data = [{'Key': k, 'Value': str(v)} for k, v in settings.items()]
        df = pd.DataFrame(data)
        conn.update(worksheet="Settings", data=df)
    except Exception as e:
        st.error(f"บันทึกค่าตั้งต้นไม่สำเร็จ: {e}")
        
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
        st.cache_data.clear()
        st.session_state.data = load_and_clean_data()
        st.rerun()
    
    # 1. โหลดค่าล่าสุดจาก Cloud
    current_settings = load_settings()
    
    # ----------------------------------------
    # ส่วนตั้งค่าไฟ (EV Rate)
    # ----------------------------------------
    saved_rate = float(current_settings.get("ev_rate", 50.0))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=saved_rate, step=5.0)
    
    # ----------------------------------------
    # 🟢 ส่วนตั้งเป้าหมาย (Target Income) - กู้คืนกลับมาแล้ว!
    # ----------------------------------------
    st.divider()
    st.markdown("### 🎯 เป้าหมายรายวัน")
    
    saved_target = float(current_settings.get("target_income", 2000.0))
    new_target = st.number_input("ตั้งเป้ารายได้ (บาท)", value=saved_target, step=100.0)
    
    # ตัวแปรสำหรับส่งไปใช้ใน Tab 2
    target_income = new_target
    ev_home_rate = new_ev_rate

    # ----------------------------------------
    # ระบบบันทึกอัตโนมัติ (Check & Save)
    # ----------------------------------------
    # ถ้าค่าใดค่าหนึ่งเปลี่ยน -> บันทึกลง Cloud ทันที
    if new_ev_rate != saved_rate or new_target != saved_target:
        current_settings["ev_rate"] = new_ev_rate
        current_settings["target_income"] = new_target
        
        save_settings(current_settings)
        st.toast(f"บันทึกการตั้งค่าลง Cloud แล้ว! ☁️")
        
        import time
        time.sleep(1)
        st.rerun()
    
    # ----------------------------------------
    # Zone อันตราย (ล้างข้อมูล)
    # ----------------------------------------
    st.divider()
    with st.expander("⚠️ พื้นที่อันตราย (ล้างข้อมูล)"):
        st.warning("การกระทำนี้จะลบข้อมูลทั้งหมดและกู้คืนยาก")
        confirm_delete = st.checkbox("ฉันยืนยันที่จะลบข้อมูลทั้งหมด")
        
        if confirm_delete:
            if st.button("ยืนยันการล้างข้อมูล 🗑️", type="primary", use_container_width=True):
                st.session_state.data = st.session_state.data.iloc[0:0] 
                save_data(st.session_state.data)
                st.success("ล้างข้อมูลเรียบร้อยแล้ว")
                st.rerun()

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 สรุปผลละเอียด", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (UI ใหม่ + แก้ไขการบันทึกให้เป็นระเบียบ)
# ==========================================
with tab1:
    # --- ฟังก์ชันช่วย ---
    def get_last_odom():
        df = st.session_state.data
        if not df.empty:
            max_odom = df['เลขไมล์'].max()
            return float(max_odom) if max_odom > 0 else 0.0
        return 0.0

    def get_work_status():
        df = st.session_state.data
        if not df.empty:
            shift_df = df[df['หมวดหมู่'] == 'กะงาน']
            if not shift_df.empty:
                return shift_df.iloc[-1]['รายการ']
        return "🌙 เลิกงาน"

    # --- ส่วนที่ 1: แถบพลัง (บนสุด) ---
    today = get_thai_date()
    df = st.session_state.data
    
    today_income = 0.0
    if not df.empty:
        today_df = df[(df['วันที่'] == today) & (df['หมวดหมู่'] == 'รายรับ')]
        today_income = today_df['คงเหลือ/สุทธิ'].sum()
    
    current_settings = load_settings()
    target = float(current_settings.get("target_income", 2000.0))
    progress = min(today_income / target, 1.0) if target > 0 else 0
    
    # แสดงแถบพลัง
    c_prog_1, c_prog_2 = st.columns([3, 1])
    with c_prog_1:
        st.progress(progress, text=f"🎯 เป้าหมาย: {progress*100:.0f}%")
    with c_prog_2:
        st.caption(f"💰 {today_income:,.0f} / {target:,.0f}")

    st.divider()

    # --- ส่วนที่ 2: จัดการกะงาน (Expander) ---
    current_status = get_work_status()
    last_odom_val = get_last_odom()

    if "เริ่ม" in current_status:
        expander_label = f"🟢 สถานะ: วิ่งงานอยู่ (เริ่มที่ {last_odom_val:,.0f} กม.) - คลิกเพื่อจบกะ 🔽"
        expander_icon = "🚕"
    else:
        expander_label = f"🔴 สถานะ: พักผ่อน (ล่าสุด {last_odom_val:,.0f} กม.) - คลิกเพื่อเริ่มงาน 🔽"
        expander_icon = "🏠"

    with st.expander(expander_label, expanded=False, icon=expander_icon):
        if "เริ่ม" in current_status:
            c_end_1, c_end_2 = st.columns([2, 1]) 
            with c_end_1:
                end_odom = st.number_input("เลขไมล์จบ", min_value=last_odom_val, value=None, placeholder="เลขไมล์ปัจจุบัน", label_visibility="collapsed")
            with c_end_2:
                if st.button("🌙 ยืนยันจบกะ", type="primary", use_container_width=True):
                    if end_odom and end_odom >= last_odom_val:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': '🌙 เลิกงาน', 'ช่องทางรับเงิน': '-',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                            'เลขไมล์': end_odom, 'หมายเหตุ': f"ระยะทาง {end_odom - last_odom_val:.0f} กม."
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()
                    else: st.toast("⚠️ เลขไมล์ต้องเพิ่มขึ้น")
        else:
            c_start_1, c_start_2 = st.columns([2, 1])
            with c_start_1:
                start_odom = st.number_input("เลขไมล์เริ่ม", min_value=0.0, value=last_odom_val, step=1.0, label_visibility="collapsed")
            with c_start_2:
                if st.button("🚀 ยืนยันเริ่ม", type="primary", use_container_width=True):
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': '☀️ เริ่มงาน', 'ช่องทางรับเงิน': '-',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                        'เลขไมล์': start_odom, 'หมายเหตุ': 'เริ่มกะใหม่'
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    # --- ส่วนที่ 3: แบบฟอร์มบันทึก ---
    st.markdown("### 📝 บันทึกรายการ")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🚗 รับงาน", "⛽ เติมของ", "💳 เติมแอป", "🛠️ จ่ายอื่น"])
    
    # 1. รับงาน
    with sub_tab1:
        with st.form(key="form_income", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: platform = st.selectbox("แอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"], label_visibility="collapsed")
            with c2: pay_method = st.selectbox("การรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"], label_visibility="collapsed")

            c3, c4 = st.columns(2)
            with c3: app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, value=None, placeholder="0")
            with c4: real_receive = st.number_input("รับจริง (รวมทิป)", min_value=0.0, value=None, placeholder="0")
            
            note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
            
            if st.form_submit_button("✅ บันทึกรายได้", type="primary", use_container_width=True):
                price_val = app_price if app_price is not None else 0.0
                real_val = real_receive if real_receive is not None else 0.0
                
                if price_val > 0 or real_val > 0:
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
                    st.toast(f"บันทึก +{real_val:.0f} บาท")
                    st.rerun()
                else: st.warning("ระบุยอดเงินด้วยครับ")

    # 2. เติมพลังงาน (แก้ไขกลับเป็นแบบมาตรฐาน)
    with sub_tab2:
        with st.form(key="form_energy", clear_on_submit=True):
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            default_val = float(ev_home_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
            cost = st.number_input("จำนวนเงิน", min_value=0.0, value=default_val, placeholder="0")
            note = st.text_input("สถานที่ / หมายเหตุ")
            
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    # 🟢 แก้ไขกลับ: รายการ = 'ค่าน้ำมัน/ไฟ' (เหมือนเดิม)
                    # ส่วนรายละเอียด (e_type) ย้ายไปรวมกับหมายเหตุ
                    full_note = f"{e_type} - {note}" if note else e_type
                    
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 
                        'รายการ': 'ค่าน้ำมัน/ไฟ', # กลับมาใช้คำมาตรฐาน
                        'ช่องทางรับเงิน': 'จ่ายสด', 
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 
                        'หมายเหตุ': full_note # รายละเอียดมาอยู่ที่นี่แทน
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    # 3. เติมเครดิต
    with sub_tab3:
        with st.form(key="form_topup", clear_on_submit=True):
            sub_cat = st.selectbox("แอป", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
            cost = st.number_input("จำนวนเงิน", min_value=0.0, value=None, placeholder="0")
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    # 4. จ่ายอื่น
    with sub_tab4:
        with st.form(key="form_other", clear_on_submit=True):
            sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
            cost = st.number_input("จำนวนเงิน", min_value=0.0, value=None, placeholder="0")
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

# ==========================================
# TAB 2: สรุปผล (Final Complete: กู้คืนข้อมูลครบ + กราฟละเอียด)
# ==========================================
import calendar
import plotly.express as px

with tab2:
    with st.sidebar:
        st.divider()
        st.markdown("### 📊 ตัวเลือกแสดงผล (Tab 2)")
        time_filter = st.selectbox("📅 ช่วงเวลา:", ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง"], key="sb_time_filter")
        
        custom_start, custom_end = None, None
        if time_filter == "กำหนดเอง":
            dr = st.date_input("เลือกวันที่:", value=(get_thai_date(), get_thai_date()), key="sb_date_picker")
            if len(dr) == 2: custom_start, custom_end = dr

    st.markdown(f"### 📊 แดชบอร์ด: {time_filter}")
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        f_df = df.copy()
        
        # --- Filter Logic ---
        days_count = 1 
        if time_filter == "วันนี้": 
            f_df = df[df['วันที่'] == today]
        elif time_filter == "เมื่อวาน": 
            f_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
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
            inc_df = f_df[f_df['หมวดหมู่'] == 'รายรับ']
            exp_df = f_df[f_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            total_exp = exp_df['หัก/จ่าย'].sum()
            net = total_inc - total_exp
            cash = f_df['เงินสดเข้าตัว'].sum()
            
            # --- Metrics Calculation ---
            odom_df = f_df[f_df['เลขไมล์'] > 0]
            dist = 0
            if not odom_df.empty:
                d_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                dist = (d_odom['max'] - d_odom['min']).sum()
            
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
            
            if 'target_income' not in locals(): target_income = 2000
            total_target = target_income * days_count
            
            # --- Display Targets ---
            st.markdown(f"**🎯 เป้าหมาย: {total_inc:,.0f} / {total_target:,.0f} บาท**")
            progress = min(total_inc / total_target, 1.0) if total_target > 0 else 0
            st.progress(progress, text=f"ทำได้แล้ว {progress*100:.1f}%")

            # --- Display Metrics (2 Rows) ---
            st.markdown("#### 💎 ประสิทธิภาพ & การเงิน")
            
            baht_per_km = net / dist if dist > 0 else 0
            baht_per_hr = net / hours if hours > 0 else 0
            
            # แถวที่ 1: ประสิทธิภาพหลัก
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f} บ.", help="รายรับ - รายจ่าย")
            m2.metric("🛣️ ระยะทาง", f"{dist:,.0f} กม.")
            m3.metric("⚡ บาท / กม.", f"{baht_per_km:.2f} บ.")
            m4.metric("⏱️ บาท / ชม.", f"{baht_per_hr:.0f} บ.")
            
            # 🟢 แถวที่ 2: รายละเอียด (กู้คืนกลับมาแล้ว!)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 เงินสดเข้าตัว", f"{cash:,.0f} บ.", help="เงินสดที่เก็บไว้กับตัว")
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
                    st.plotly_chart(px.area(daily, x='วันที่', y='คงเหลือ/สุทธิ', title="📈 เส้นทางรายได้", markers=True, color_discrete_sequence=['#2E86C1']), use_container_width=True)
                else: st.info("รอข้อมูลรายได้...")

            with col_g2:
                if not inc_df.empty:
                    fig = px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', title="🍩 สัดส่วนแอป", hole=0.4, color='แอป', color_discrete_map=APP_COLORS)
                    fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)

            col_g3, col_g4 = st.columns(2)
            with col_g3:
                if not inc_df.empty:
                    temp = inc_df.copy()
                    temp['Hour'] = pd.to_datetime(temp['เวลา'], format='%H:%M').dt.hour
                    hm = temp.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                    if not hm.empty:
                        fig_hm = px.imshow(hm, title="🔥 ช่วงเวลาทำเงิน", aspect="auto", color_continuous_scale="Greens")
                        st.plotly_chart(fig_hm, use_container_width=True)
            
            with col_g4:
                # 🟢 Logic: เจาะลึกรายจ่ายทุกเม็ด (เหมือนเดิม)
                if not exp_df.empty:
                    def detailed_expense_name(row):
                        item = row['รายการ']
                        app_name = row['แอป']
                        note = str(row['หมายเหตุ']).strip()
                        
                        if 'เติมเครดิต' in item: return f"💳 เติม {app_name}"
                        if 'น้ำมัน' in item or 'ไฟ' in item:
                            if 'ชาร์จ' in item or 'ชาร์จ' in note: return "⚡ ชาร์จไฟ"
                            if 'น้ำมัน' in item or 'น้ำมัน' in note: return "⛽ น้ำมัน"
                            return "⛽ พลังงาน"
                        if 'ทั่วไป' in item:
                            if note and note.lower() != 'nan' and note != '': return f"🛠️ {note}"
                            return "🛠️ จ่ายทั่วไป"
                        return item

                    exp_df_plot = exp_df.copy()
                    exp_df_plot['ชื่อรายการกราฟ'] = exp_df_plot.apply(detailed_expense_name, axis=1)
                    exp_sum = exp_df_plot.groupby('ชื่อรายการกราฟ')['หัก/จ่าย'].sum().reset_index()
                    exp_sum = exp_sum.sort_values(by='หัก/จ่าย', ascending=True)

                    fig_exp = px.bar(
                        exp_sum, 
                        x='หัก/จ่าย', 
                        y='ชื่อรายการกราฟ', 
                        title="💸 รายจ่าย (เจาะลึก)", 
                        color='ชื่อรายการกราฟ', 
                        text_auto=True,
                        orientation='h'
                    )
                    st.plotly_chart(fig_exp, use_container_width=True)
                else:
                    st.info("ยังไม่มีรายจ่าย")

        else: st.warning(f"🔍 ไม่พบข้อมูล ({time_filter})")
    else: st.info("เริ่มบันทึกงานแรกได้เลย")

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

