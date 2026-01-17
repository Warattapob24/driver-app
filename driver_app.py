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
SHEET_NAME = "Drivers" 

# --- FORMATTING HELPER ---
def fmt_num(val):
    if val is None: return "0"
    try:
        f_val = float(val)
        if f_val.is_integer():
            return f"{int(f_val):,}"
        else:
            return f"{f_val:,.2f}".rstrip('0').rstrip('.')
    except:
        return str(val)

# --- TIMEZONE ---
def get_thai_time():
    tz_thai = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz_thai)

def get_thai_date():
    return get_thai_time().date()

# --- 2. SETTINGS ---
def load_settings():
    conn = st.connection("gsheets", type=GSheetsConnection)
    default_settings = {"ev_rate": 50.0, "target_income": 2000.0} 
    try:
        df = conn.read(worksheet="Settings", ttl=3600)
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
        st.cache_data.clear()
    except Exception as e:
        st.error(f"บันทึกค่าตั้งต้นไม่สำเร็จ: {e}")
        
# --- 3. DATA LOADING (Smart Cache) ---
@st.cache_data(ttl=600) 
def load_and_clean_data_cached():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet=SHEET_NAME, ttl=600)
        
        required_cols = [
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ]
        
        if df.empty or len(df.columns) < len(required_cols):
             return pd.DataFrame(columns=required_cols)
        
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
        
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0 if col in ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์'] else ""
        
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        if 'วันที่' in df.columns:
            df['วันที่'] = pd.to_datetime(df['วันที่'], errors='coerce').dt.date
            
        return df[required_cols]
        
    except Exception as e:
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

def load_and_clean_data():
    return load_and_clean_data_cached()

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_save = df.copy()
        if 'วันที่' in df_save.columns:
            df_save['วันที่'] = df_save['วันที่'].astype(str)
        conn.update(worksheet=SHEET_NAME, data=df_save)
        st.cache_data.clear()
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
    
    current_settings = load_settings()
    
    saved_rate = int(float(current_settings.get("ev_rate", 50.0)))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=saved_rate, step=5, format="%d")
    
    st.divider()
    st.markdown("### 🎯 เป้าหมายรายวัน")
    
    saved_target = int(float(current_settings.get("target_income", 2000.0)))
    new_target = st.number_input("ตั้งเป้ารายได้ (บาท)", value=saved_target, step=100, format="%d")
    
    target_income = new_target
    ev_home_rate = new_ev_rate

    if new_ev_rate != saved_rate or new_target != saved_target:
        current_settings["ev_rate"] = new_ev_rate
        current_settings["target_income"] = new_target
        save_settings(current_settings)
        st.toast(f"บันทึกการตั้งค่าลง Cloud แล้ว! ☁️")
        import time
        time.sleep(1)
        st.rerun()
    
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
# TAB 1: บันทึกงาน
# ==========================================
with tab1:
    def get_last_odom():
        df = st.session_state.data
        if not df.empty:
            max_odom = df['เลขไมล์'].max()
            return int(max_odom) if max_odom > 0 else 0
        return 0

    def get_work_status():
        df = st.session_state.data
        if not df.empty:
            shift_df = df[df['หมวดหมู่'] == 'กะงาน']
            if not shift_df.empty:
                return shift_df.iloc[-1]['รายการ']
        return "🌙 เลิกงาน"

    # --- แถบพลัง ---
    today = get_thai_date()
    df = st.session_state.data
    
    today_income = 0.0
    if not df.empty:
        today_df = df[(df['วันที่'] == today) & (df['หมวดหมู่'] == 'รายรับ')]
        today_income = today_df['คงเหลือ/สุทธิ'].sum()
    
    progress = min(today_income / target_income, 1.0) if target_income > 0 else 0
    
    c_prog_1, c_prog_2 = st.columns([3, 1])
    with c_prog_1:
        st.progress(progress, text=f"🎯 เป้าหมาย: {progress*100:.0f}%")
    with c_prog_2:
        st.caption(f"💰 {fmt_num(today_income)} / {fmt_num(target_income)}")

    st.divider()

    # --- จัดการกะงาน ---
    current_status = get_work_status()
    last_odom_val = get_last_odom()

    if "เริ่ม" in current_status:
        expander_label = f"🟢 สถานะ: วิ่งงานอยู่ (เริ่มที่ {fmt_num(last_odom_val)} กม.) - คลิกเพื่อจบกะ 🔽"
        expander_icon = "🚕"
    else:
        expander_label = f"🔴 สถานะ: พักผ่อน (ล่าสุด {fmt_num(last_odom_val)} กม.) - คลิกเพื่อเริ่มงาน 🔽"
        expander_icon = "🏠"

    with st.expander(expander_label, expanded=False, icon=expander_icon):
        if "เริ่ม" in current_status:
            c_end_1, c_end_2 = st.columns([2, 1]) 
            with c_end_1:
                end_odom = st.number_input("เลขไมล์จบ", min_value=last_odom_val, value=None, placeholder="เลขไมล์ปัจจุบัน", step=1, format="%d", label_visibility="collapsed")
            with c_end_2:
                if st.button("🌙 ยืนยันจบกะ", type="primary", use_container_width=True):
                    if end_odom and end_odom >= last_odom_val:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': '🌙 เลิกงาน', 'ช่องทางรับเงิน': '-',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                            'เลขไมล์': end_odom, 'หมายเหตุ': f"ระยะทาง {end_odom - last_odom_val} กม."
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()
                    else: st.toast("⚠️ เลขไมล์ต้องเพิ่มขึ้น")
        else:
            c_start_1, c_start_2 = st.columns([2, 1])
            with c_start_1:
                start_odom = st.number_input("เลขไมล์เริ่ม", min_value=0, value=last_odom_val, step=1, format="%d", label_visibility="collapsed")
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

    # --- แบบฟอร์มบันทึก ---
    st.markdown("### 📝 บันทึกรายการ")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🚗 รับงาน", "⛽ เติมของ", "💳 เติมแอป", "🛠️ จ่ายอื่น"])
    
    # 1. รับงาน
    with sub_tab1:
        with st.form(key="form_income", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: platform = st.selectbox("แอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"], label_visibility="collapsed")
            with c2: pay_method = st.selectbox("การรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"], label_visibility="collapsed")

            c3, c4 = st.columns(2)
            with c3: 
                app_price = st.number_input("ราคาหน้าแอป", min_value=0, value=None, placeholder="0", step=1, format="%d")
            with c4: 
                real_receive = st.number_input("รับจริง (รวมทิป)", min_value=0, value=None, placeholder="0", step=1, format="%d")
            
            note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
            
            if st.form_submit_button("✅ บันทึกรายได้", type="primary", use_container_width=True):
                price_val = float(app_price) if app_price is not None else 0.0
                real_val = float(real_receive) if real_receive is not None else 0.0
                
                deduction = 0.0
                if price_val > 0 or real_val > 0:
                    if real_val == 0 and price_val > 0: real_val = price_val 
                    tip = max(0, real_val - price_val)
                    
                    # 🟢 LOGIC สำคัญ: คำนวณยอดหัก (Deduction) สำหรับงานตัดบัตร
                    deducted = 0
                    if pay_method == "💳 ตัดบัตร/แอป":
                        # ถ้าราคาหน้าแอปมากกว่ารับจริง แสดงว่าโดนหัก
                        if price_val > real_val:
                            deducted = price_val - real_val
                            tip = 0 # ถ้ายอดรับจริงน้อยกว่าหน้าแอป แสดงว่าไม่มีทิป (หรือทิปรวมอยู่ในนั้นแล้วแต่ยังโดนหักอยู่ดี)
                    
                    cash_in_hand = real_val if "เงินสด" in pay_method else 0.0

                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method,
                        'ยอดเต็ม/หน้าแอป': price_val, 
                        'หัก/จ่าย': deducted, # บันทึกยอดที่โดนหักตรงนี้
                        'ทิป': tip, 
                        'คงเหลือ/สุทธิ': real_val, 'เงินสดเข้าตัว': cash_in_hand, 
                        'เลขไมล์': 0, 'หมายเหตุ': note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast(f"บันทึก +{fmt_num(real_val)} บาท")
                    st.rerun()
                else: st.warning("ระบุยอดเงินด้วยครับ")

    # 2. เติมพลังงาน
    with sub_tab2:
        with st.form(key="form_energy", clear_on_submit=True):
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            default_val = int(ev_home_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
            cost = st.number_input("จำนวนเงิน", min_value=0, value=default_val, placeholder="0", step=1, format="%d")
            note = st.text_input("สถานที่ / หมายเหตุ")
            
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    full_note = f"{e_type} - {note}" if note else e_type
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด', 
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': full_note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    # 3. เติมเครดิต
    with sub_tab3:
        st.info("💡 การเติมเครดิตที่นี่ จะถูกนำไปคำนวณเป็น 'ต้นทุนค่าคอมมิชชั่น' ของแต่ละแอป")
        with st.form(key="form_topup", clear_on_submit=True):
            sub_cat = st.selectbox("แอป", ["Grab", "Bolt", "Maxim", "Line Man", "Robinhood", "Win", "งานนอก"])
            cost = st.number_input("จำนวนเงินที่เติม/โดนหัก", min_value=0, value=None, placeholder="0", step=1, format="%d")
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
            cost = st.number_input("จำนวนเงิน", min_value=0, value=None, placeholder="0", step=1, format="%d")
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

# ==========================================
# TAB 2: สรุปผล (GP Fix: Force Calculate Deduction)
# ==========================================
import calendar

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
            
            # --- 1. เตรียมข้อมูลรายวัน ---
            daily_income = f_df[f_df['หมวดหมู่']=='รายรับ'].groupby('วันที่')['คงเหลือ/สุทธิ'].sum()
            daily_expense = f_df[f_df['หมวดหมู่']=='รายจ่าย'].groupby('วันที่')['หัก/จ่าย'].sum()
            daily_cash = f_df.groupby('วันที่')['เงินสดเข้าตัว'].sum()
            daily_dist = f_df[f_df['เลขไมล์'] > 0].groupby('วันที่')['เลขไมล์'].agg(lambda x: x.max() - x.min())
            
            # คำนวณชั่วโมง
            daily_hours = {}
            shift_df = f_df[f_df['หมวดหมู่'] == 'กะงาน']
            for d in f_df['วันที่'].unique():
                ds = shift_df[shift_df['วันที่'] == d]
                s = ds[ds['รายการ'].str.contains("เริ่ม")]['เวลา']
                e = ds[ds['รายการ'].str.contains("เลิก")]['เวลา']
                h_val = 0
                if not s.empty and not e.empty:
                    try:
                        ts = pd.to_datetime(s.min(), format='%H:%M')
                        te = pd.to_datetime(e.max(), format='%H:%M')
                        h = (te - ts).total_seconds()/3600
                        if h < 0: h += 24
                        h_val = h
                    except: pass
                daily_hours[d] = h_val
            daily_hours_series = pd.Series(daily_hours)

            daily_master = pd.DataFrame(index=f_df['วันที่'].unique()).sort_index()
            daily_master['กำไรสุทธิ'] = daily_income.sub(daily_expense, fill_value=0)
            daily_master['รายรับรวม'] = daily_income
            daily_master['รายจ่ายรวม'] = daily_expense
            daily_master['เงินสดเข้าตัว'] = daily_cash
            daily_master['ระยะทาง'] = daily_dist
            daily_master['ชั่วโมงขับ'] = daily_hours_series
            daily_master = daily_master.fillna(0).reset_index().rename(columns={'index':'วันที่'})

            # --- 2. Metrics รวม ---
            net = daily_master['กำไรสุทธิ'].sum()
            dist = daily_master['ระยะทาง'].sum()
            cash = daily_master['เงินสดเข้าตัว'].sum()
            total_exp = daily_master['รายจ่ายรวม'].sum()
            hours = daily_master['ชั่วโมงขับ'].sum()
            baht_per_km = net / dist if dist > 0 else 0
            baht_per_hr = net / hours if hours > 0 else 0
            
            total_target = target_income * days_count
            total_income_only = daily_master['รายรับรวม'].sum() 
            
            # --- Display Targets ---
            st.markdown(f"**🎯 เป้าหมาย (รายรับ): {fmt_num(total_income_only)} / {fmt_num(total_target)} บาท**")
            progress = min(total_income_only / total_target, 1.0) if total_target > 0 else 0
            st.progress(progress, text=f"ทำได้แล้ว {progress*100:.1f}%")

            # --- Display Metrics ---
            st.markdown("#### 💎 ประสิทธิภาพ & การเงิน")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{fmt_num(net)} บ.", help="รายรับ - รายจ่าย")
            m2.metric("🛣️ ระยะทาง", f"{fmt_num(dist)} กม.")
            m3.metric("⚡ บาท / กม.", f"{fmt_num(baht_per_km)} บ.")
            m4.metric("⏱️ บาท / ชม.", f"{fmt_num(baht_per_hr)} บ.")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 เงินสดเข้าตัว", f"{fmt_num(cash)} บ.")
            c2.metric("💸 รายจ่ายรวม", f"{fmt_num(total_exp)} บ.")
            c3.metric("⏳ ชั่วโมงขับ", f"{fmt_num(hours)} ชม.")
            c4.metric("📝 จำนวนงาน", f"{len(inc_df)} งาน")
            
            st.divider()

            # --- 🟢 ส่วนกราฟ Drill Down ---
            st.markdown("### 📈 เจาะลึกประวัติสถิติ (คลิกเลือกหัวข้อ)")
            chart_mode = st.radio(
                "เลือกข้อมูลที่ต้องการดูกราฟ:",
                ["💰 กำไรสุทธิ", "🛣️ ระยะทาง", "💵 เงินสดเข้าตัว", "💸 รายจ่ายรวม", "⏳ ชั่วโมงขับ"],
                horizontal=True,
                label_visibility="collapsed"
            )

            col_map = {
                "💰 กำไรสุทธิ": ("กำไรสุทธิ", "#2E86C1"),
                "🛣️ ระยะทาง": ("ระยะทาง", "#F39C12"),
                "💵 เงินสดเข้าตัว": ("เงินสดเข้าตัว", "#27AE60"),
                "💸 รายจ่ายรวม": ("รายจ่ายรวม", "#C0392B"),
                "⏳ ชั่วโมงขับ": ("ชั่วโมงขับ", "#8E44AD")
            }
            selected_col, color_code = col_map[chart_mode]

            if not daily_master.empty:
                fig_trend = px.area(daily_master, x='วันที่', y=selected_col, title=f"แนวโน้ม: {chart_mode}", markers=True, color_discrete_sequence=[color_code])
                fig_trend.update_traces(hovertemplate='%{y:,.2f}')
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.info("ไม่มีข้อมูลสำหรับสร้างกราฟ")

            st.divider()

            # --- 🟢 วิเคราะห์ความคุ้มค่า (GP: Logic ใหม่ Force Calculate) ---
            with st.expander("💸 วิเคราะห์ความคุ้มค่า (GP & ค่าคอม)", expanded=True):
                # 1. ข้อมูลฝั่งจ่าย (เติมเครดิต)
                app_expenses = exp_df[~exp_df['แอป'].isin(['ค่าใช้จ่าย', 'ระบบ'])].copy()
                app_expenses['แอป'] = app_expenses['แอป'].replace({'Grab Wallet': 'Grab'}) 
                
                # 2. ข้อมูลฝั่งรับ
                app_incomes = inc_df.copy()
                
                if not app_incomes.empty:
                    gp_data = []
                    all_apps = set(app_incomes['แอป'].unique()) | set(app_expenses['แอป'].unique())
                    
                    for app in all_apps:
                        # กรองข้อมูลเฉพาะแอปนั้นๆ
                        this_app_inc = app_incomes[app_incomes['แอป'] == app]
                        this_app_exp = app_expenses[app_expenses['แอป'] == app]
                        
                        # ยอดงานทั้งหมด (Gross)
                        gross_income = this_app_inc['ยอดเต็ม/หน้าแอป'].sum()
                        
                        # A: หักจากการเติมเครดิต (ดูจากรายจ่าย - Top up)
                        deduct_from_topup = this_app_exp['หัก/จ่าย'].sum()
                        
                        # B: หักหน้างาน (ตัดบัตร/แอป) -> 🟢 คำนวณใหม่ตรงนี้เลย ไม่เชื่อ Database เก่า
                        # Logic: เฉพาะงาน 'ตัดบัตร' ให้เอา (หน้าแอป - รับจริง) มาเป็นยอดหักทันที
                        credit_jobs = this_app_inc[this_app_inc['ช่องทางรับเงิน'].str.contains('ตัดบัตร', na=False)]
                        deduct_from_job = 0
                        if not credit_jobs.empty:
                            # คำนวณส่วนต่าง (หน้าแอป - สุทธิ) = ค่าคอมที่โดนหัก
                            deduct_from_job = (credit_jobs['ยอดเต็ม/หน้าแอป'] - credit_jobs['คงเหลือ/สุทธิ']).sum()
                        
                        # รวมยอดหักทั้งหมด
                        total_deduction = deduct_from_topup + deduct_from_job

                        if gross_income > 0:
                            gp_pct = (total_deduction / gross_income) * 100
                            gp_data.append({
                                "แอป": app, 
                                "GP (%)": gp_pct, 
                                "รวมค่าคอม (บ.)": total_deduction, 
                                "ยอดหน้าแอป (บ.)": gross_income,
                                "จากเติมเครดิต": deduct_from_topup,
                                "จากหักตัดบัตร": deduct_from_job
                            })
                    
                    if gp_data:
                        gp_df = pd.DataFrame(gp_data).sort_values(by="GP (%)", ascending=True)
                        
                        c_gp1, c_gp2 = st.columns([1, 2])
                        with c_gp1: 
                            st.dataframe(
                                gp_df, 
                                column_config={
                                    "GP (%)": st.column_config.NumberColumn(format="%.1f %%"),
                                    "รวมค่าคอม (บ.)": st.column_config.NumberColumn(format="%.0f"),
                                    "ยอดหน้าแอป (บ.)": st.column_config.NumberColumn(format="%.0f"),
                                    "จากเติมเครดิต": st.column_config.NumberColumn(format="%.0f", help="มาจากเมนู 'เติมเครดิต'"),
                                    "จากหักตัดบัตร": st.column_config.NumberColumn(format="%.0f", help="คำนวณจากส่วนต่าง (หน้าแอป - รับจริง) ของงานตัดบัตร")
                                },
                                hide_index=True, 
                                use_container_width=True
                            )
                        with c_gp2: 
                            st.plotly_chart(px.bar(gp_df, x='GP (%)', y='แอป', orientation='h', title="📉 Total Deduction vs Gross", text_auto='.1f', color='GP (%)', color_continuous_scale='Reds'), use_container_width=True)
                    else: st.info("ข้อมูลไม่เพียงพอ")
                else: st.info("ไม่มีข้อมูลรายรับ")

            st.divider()

            # --- กราฟวงกลม & Heatmap ---
            APP_COLORS = { "Grab": "#00B14F", "Line Man": "#06C755", "Bolt": "#34D186", "Maxim": "#FFD600", "Robinhood": "#9D2398", "Win": "#FF6B00", "งานนอก": "#7F8C8D", "ระบบ": "#95A5A6" }
            c_pie, c_heat = st.columns(2)
            with c_pie:
                if not inc_df.empty:
                    st.plotly_chart(px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', title="🍩 สัดส่วนรายได้", hole=0.4, color='แอป', color_discrete_map=APP_COLORS), use_container_width=True)
            with c_heat:
                if not inc_df.empty:
                    temp = inc_df.copy()
                    temp['Hour'] = pd.to_datetime(temp['เวลา'], format='%H:%M').dt.hour
                    hm = temp.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                    if not hm.empty:
                        st.plotly_chart(px.imshow(hm, title="🔥 ช่วงเวลาทำเงิน", aspect="auto", color_continuous_scale="Greens"), use_container_width=True)

            # --- กราฟรายจ่ายเจาะลึก ---
            st.markdown("### 💸 รายจ่าย (เจาะลึก)")
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
                exp_sum = exp_df_plot.groupby('ชื่อรายการกราฟ')['หัก/จ่าย'].sum().reset_index().sort_values(by='หัก/จ่าย', ascending=True)

                fig_exp = px.bar(
                    exp_sum, 
                    x='หัก/จ่าย', 
                    y='ชื่อรายการกราฟ', 
                    color='ชื่อรายการกราฟ', 
                    text_auto='.0f',
                    orientation='h'
                )
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายจ่าย")

        else: st.warning(f"🔍 ไม่พบข้อมูล ({time_filter})")
    else: st.info("เริ่มบันทึกงานแรกได้เลย")
                                    
# ==========================================
# TAB 3: ฐานข้อมูล (Performance)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        apps = st.session_state.data['แอป'].unique() if not st.session_state.data.empty else []
        cats = st.session_state.data['หมวดหมู่'].unique() if not st.session_state.data.empty else []
        
        f_app = c1.multiselect("แอป", apps)
        f_cat = c2.multiselect("หมวดหมู่", cats)
        f_date = c3.selectbox("วันที่", ["เดือนนี้", "วันนี้", "ทั้งหมด"])

    df_show = st.session_state.data.copy()
    if not df_show.empty:
        if f_app: df_show = df_show[df_show['แอป'].isin(f_app)]
        if f_cat: df_show = df_show[df_show['หมวดหมู่'].isin(f_cat)]
        if f_date == "วันนี้": df_show = df_show[df_show['วันที่'] == get_thai_date()]
        elif f_date == "เดือนนี้": 
            t = get_thai_date()
            df_show = df_show[(pd.to_datetime(df_show['วันที่']).dt.month == t.month) & (pd.to_datetime(df_show['วันที่']).dt.year == t.year)]

        edited_df = st.data_editor(
            df_show, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="editor",
            column_config={
                "คงเหลือ/สุทธิ": st.column_config.NumberColumn(format="%.2f ฿"),
                "ยอดเต็ม/หน้าแอป": st.column_config.NumberColumn(format="%.2f ฿"),
                "วันที่": st.column_config.DateColumn(format="YYYY-MM-DD")
            }
        )
        
        if st.button("💾 บันทึกการเปลี่ยนแปลง", type="primary"):
            try:
                if len(df_show) != len(st.session_state.data):
                      st.warning("⚠️ คุณกำลังกรองข้อมูลอยู่ ระบบจะบันทึกเฉพาะข้อมูลที่เห็นเท่านั้น")
                      st.session_state.data.update(edited_df)
                else:
                      st.session_state.data = edited_df
                
                save_data(st.session_state.data)
                st.success("บันทึกสำเร็จ!")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    else:
        st.info("ไม่มีข้อมูลให้แสดง")


