import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import json
import os
from streamlit_gsheets import GSheetsConnection
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ", page_icon="🚗", layout="wide")
SETTINGS_FILE = "settings.json"
SHEET_NAME = "Drivers"

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
        # พยายามโหลด Settings จาก Cloud ถ้ามี
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
        df = conn.read(worksheet=SHEET_NAME, ttl=0)
        
        required_cols = [
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ]
        
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
        # กรณี Error ให้คืน DataFrame เปล่า เพื่อให้แอปไม่พัง
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_save = df.copy()
        if 'วันที่' in df_save.columns:
            df_save['วันที่'] = df_save['วันที่'].astype(str)
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
    
    current_settings = load_settings()
    
    # Settings: EV Rate
    saved_rate = float(current_settings.get("ev_rate", 50.0))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=saved_rate, step=5.0)
    
    # Settings: Target Income
    st.divider()
    st.markdown("### 🎯 เป้าหมายรายวัน")
    saved_target = float(current_settings.get("target_income", 2000.0))
    new_target = st.number_input("ตั้งเป้ารายได้ (บาท)", value=saved_target, step=100.0)
    
    # Auto Save Settings
    if new_ev_rate != saved_rate or new_target != saved_target:
        current_settings["ev_rate"] = new_ev_rate
        current_settings["target_income"] = new_target
        save_settings(current_settings)
        st.toast("บันทึกการตั้งค่าแล้ว!")
        import time
        time.sleep(0.5)
        st.rerun()

    ev_home_rate = new_ev_rate
    target_income = new_target

    # Zone ล้างข้อมูล
    st.divider()
    with st.expander("⚠️ ล้างข้อมูล"):
        if st.checkbox("ยืนยันลบทั้งหมด"):
            if st.button("ล้างข้อมูล 🗑️", type="primary"):
                st.session_state.data = st.session_state.data.iloc[0:0]
                save_data(st.session_state.data)
                st.success("ล้างข้อมูลแล้ว")
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
            return float(max_odom) if max_odom > 0 else 0.0
        return 0.0

    def get_work_status():
        df = st.session_state.data
        if not df.empty:
            shift_df = df[df['หมวดหมู่'] == 'กะงาน']
            if not shift_df.empty:
                return shift_df.iloc[-1]['รายการ']
        return "🌙 เลิกงาน"

    # Progress Bar
    today = get_thai_date()
    df = st.session_state.data
    today_income = 0.0
    if not df.empty:
        today_df = df[(df['วันที่'] == today) & (df['หมวดหมู่'] == 'รายรับ')]
        today_income = today_df['คงเหลือ/สุทธิ'].sum()
    
    progress = min(today_income / target_income, 1.0) if target_income > 0 else 0
    st.progress(progress, text=f"🎯 เป้าหมาย: {progress*100:.0f}% ({today_income:,.0f} / {target_income:,.0f})")
    st.divider()

    # Expander กะงาน
    current_status = get_work_status()
    last_odom_val = get_last_odom()
    expander_label = f"สถานะ: {current_status} (ไมล์ล่าสุด {last_odom_val:,.0f})"
    
    with st.expander(expander_label, expanded=False):
        if "เริ่ม" in current_status:
            c1, c2 = st.columns([2, 1])
            with c1: end_odom = st.number_input("เลขไมล์จบ", min_value=last_odom_val, value=None)
            with c2: 
                if st.button("🌙 จบกะ", type="primary", use_container_width=True):
                    if end_odom and end_odom >= last_odom_val:
                        new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': '🌙 เลิกงาน', 'ช่องทางรับเงิน': '-', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0, 'เลขไมล์': end_odom, 'หมายเหตุ': f"ระยะทาง {end_odom - last_odom_val:.0f} กม."}
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.rerun()
        else:
            c1, c2 = st.columns([2, 1])
            with c1: start_odom = st.number_input("เลขไมล์เริ่ม", min_value=0.0, value=last_odom_val)
            with c2:
                if st.button("🚀 เริ่มกะ", type="primary", use_container_width=True):
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': '☀️ เริ่มงาน', 'ช่องทางรับเงิน': '-', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0, 'เลขไมล์': start_odom, 'หมายเหตุ': 'เริ่มกะใหม่'}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    # Forms บันทึก
    st.markdown("### 📝 บันทึกรายการ")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🚗 รับงาน", "⛽ เติมของ", "💳 เติมแอป", "🛠️ จ่ายอื่น"])
    
    with sub_tab1: # รับงาน
        with st.form("form_income", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: platform = st.selectbox("แอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
            with c2: pay_method = st.selectbox("การรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])
            c3, c4 = st.columns(2)
            with c3: app_price = st.number_input("ราคาหน้าแอป", min_value=0.0)
            with c4: real_receive = st.number_input("รับจริง (รวมทิป)", min_value=0.0)
            note = st.text_input("หมายเหตุ")
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                pv = app_price if app_price else 0.0
                rv = real_receive if real_receive else 0.0
                if pv > 0 or rv > 0:
                    if rv == 0 and pv > 0: rv = pv
                    tip = max(0, rv - pv)
                    cash = rv if pay_method == "💵 เงินสด/โอน" else 0.0
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method, 'ยอดเต็ม/หน้าแอป': pv, 'หัก/จ่าย': 0, 'ทิป': tip, 'คงเหลือ/สุทธิ': rv, 'เงินสดเข้าตัว': cash, 'เลขไมล์': 0, 'หมายเหตุ': note}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast(f"บันทึก +{rv:.0f} บาท")
                    st.rerun()

    with sub_tab2: # เติมของ
        with st.form("form_energy", clear_on_submit=True):
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            d_val = float(ev_home_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
            cost = st.number_input("จำนวนเงิน", min_value=0.0, value=d_val)
            note = st.text_input("สถานที่/หมายเหตุ")
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    full_note = f"{e_type} - {note}" if note else e_type
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': full_note}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    with sub_tab3: # เติมแอป
        with st.form("form_topup", clear_on_submit=True):
            sub_cat = st.selectbox("แอป", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
            cost = st.number_input("จำนวนเงิน", min_value=0.0)
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

    with sub_tab4: # จ่ายอื่น
        with st.form("form_other", clear_on_submit=True):
            sub_cat = st.text_input("รายการ")
            cost = st.number_input("จำนวนเงิน", min_value=0.0)
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    new_row = {'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"), 'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด', 'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat}
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

# ==========================================
# TAB 2: สรุปผล (แก้ไข Error วันที่)
# ==========================================
with tab2:
    with st.sidebar:
        st.divider()
        time_filter = st.selectbox("📅 ช่วงเวลา (สรุปผล):", ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง"])
        custom_s, custom_e = None, None
        if time_filter == "กำหนดเอง":
            dr = st.date_input("เลือกวันที่", value=(get_thai_date(), get_thai_date()))
            if len(dr) == 2: custom_s, custom_e = dr

    st.markdown(f"### 📊 แดชบอร์ด: {time_filter}")
    
    # 🟢 1. เตรียมข้อมูลและแปลงวันที่ให้ชัวร์ก่อนกรอง
    df = st.session_state.data.copy()
    if not df.empty:
        # แปลงคอลัมน์ 'วันที่' ให้เป็น datetime ของ pandas จริงๆ เพื่อแก้ปัญหา TypeError
        df['วันที่_filter'] = pd.to_datetime(df['วันที่'], errors='coerce')
        
        # เตรียมตัวแปรวันที่ปัจจุบันแบบ pandas timestamp
        today = pd.to_datetime(get_thai_date())
        f_df = df.copy()
        
        # --- Filter Logic (ใช้ 'วันที่_filter' ในการกรอง) ---
        days_count = 1
        
        if time_filter == "วันนี้": 
            f_df = df[df['วันที่_filter'].dt.date == today.date()]
            
        elif time_filter == "เมื่อวาน": 
            target_date = today - pd.Timedelta(days=1)
            f_df = df[df['วันที่_filter'].dt.date == target_date.date()]
            
        elif time_filter == "สัปดาห์นี้":
            start = today - pd.Timedelta(days=today.weekday())
            end = start + pd.Timedelta(days=6)
            f_df = df[(df['วันที่_filter'] >= start) & (df['วันที่_filter'] <= end)]
            days_count = 7
            
        elif time_filter == "เดือนนี้":
            f_df = df[(df['วันที่_filter'].dt.month == today.month) & (df['วันที่_filter'].dt.year == today.year)]
            days_count = calendar.monthrange(today.year, today.month)[1]
            
        elif time_filter == "เดือนที่แล้ว":
            # หาวันแรกของเดือนนี้ แล้วถอยไป 1 วันจะได้วันสิ้นเดือนที่แล้ว
            first_of_month = today.replace(day=1)
            last_prev = first_of_month - pd.Timedelta(days=1)
            start_prev = last_prev.replace(day=1)
            f_df = df[(df['วันที่_filter'] >= start_prev) & (df['วันที่_filter'] <= last_prev)]
            days_count = calendar.monthrange(start_prev.year, start_prev.month)[1]
            
        elif time_filter == "ปีนี้":
            f_df = df[df['วันที่_filter'].dt.year == today.year]
            days_count = 365
            
        elif time_filter == "กำหนดเอง" and custom_s and custom_e:
            # แปลง custom_s/e ให้เป็น timestamp เพื่อเปรียบเทียบ
            ts_start = pd.to_datetime(custom_s)
            ts_end = pd.to_datetime(custom_e)
            f_df = df[(df['วันที่_filter'] >= ts_start) & (df['วันที่_filter'] <= ts_end)]
            days_count = (custom_e - custom_s).days + 1

        if not f_df.empty:
            inc_df = f_df[f_df['หมวดหมู่'] == 'รายรับ']
            exp_df = f_df[f_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            total_exp = exp_df['หัก/จ่าย'].sum()
            net = total_inc - total_exp
            cash = f_df['เงินสดเข้าตัว'].sum()
            
            # Distance & Hours
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

            total_target = target_income * days_count
            st.markdown(f"**🎯 เป้าหมาย: {total_inc:,.0f} / {total_target:,.0f} บาท**")
            prog = min(total_inc / total_target, 1.0) if total_target > 0 else 0
            st.progress(prog, text=f"ทำได้แล้ว {prog*100:.1f}%")

            # Metrics
            st.markdown("#### 💎 ประสิทธิภาพ & การเงิน")
            baht_km = net / dist if dist > 0 else 0
            baht_hr = net / hours if hours > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f} บ.")
            m2.metric("🛣️ ระยะทาง", f"{dist:,.0f} กม.")
            m3.metric("⚡ บาท/กม.", f"{baht_km:.2f} บ.")
            m4.metric("⏱️ บาท/ชม.", f"{baht_hr:.0f} บ.")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 เงินสดเข้าตัว", f"{cash:,.0f} บ.")
            c2.metric("💸 รายจ่ายรวม", f"{total_exp:,.0f} บ.")
            c3.metric("⏳ ชั่วโมงขับ", f"{hours:.1f} ชม.")
            c4.metric("📝 จำนวนงาน", f"{len(inc_df)} งาน")
            st.divider()

            # Graphs
            APP_COLORS = { "Grab": "#00B14F", "Line Man": "#06C755", "Bolt": "#34D186", "Maxim": "#FFD600", "Robinhood": "#9D2398", "Win": "#FF6B00", "งานนอก": "#7F8C8D", "ระบบ": "#95A5A6" }
            
            g1, g2 = st.columns([2, 1])
            with g1:
                if not inc_df.empty:
                    daily = inc_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
                    st.plotly_chart(px.area(daily, x='วันที่', y='คงเหลือ/สุทธิ', title="📈 เส้นทางรายได้", markers=True, color_discrete_sequence=['#2E86C1']), use_container_width=True)
            with g2:
                if not inc_df.empty:
                    fig = px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', title="🍩 สัดส่วนแอป", hole=0.4, color='แอป', color_discrete_map=APP_COLORS)
                    fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
            
            g3, g4 = st.columns(2)
            with g3:
                 if not inc_df.empty:
                    t_df = inc_df.copy()
                    t_df['Hour'] = pd.to_datetime(t_df['เวลา'], format='%H:%M').dt.hour
                    hm = t_df.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                    if not hm.empty: st.plotly_chart(px.imshow(hm, title="🔥 ช่วงเวลาทำเงิน", aspect="auto", color_continuous_scale="Greens"), use_container_width=True)
            with g4:
                if not exp_df.empty:
                    e_sum = exp_df.groupby('รายการ')['หัก/จ่าย'].sum().reset_index().sort_values('หัก/จ่าย')
                    st.plotly_chart(px.bar(e_sum, x='หัก/จ่าย', y='รายการ', title="💸 รายจ่าย", text_auto=True, orientation='h'), use_container_width=True)
        else: st.warning(f"🔍 ไม่พบข้อมูล ({time_filter})")
    else: st.info("เริ่มบันทึกงานแรกได้เลย")

# ==========================================
# TAB 3: ฐานข้อมูล (แก้ไขเฉพาะจุดนี้ให้เสถียรขึ้น)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    
    # Filter
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        # เช็คข้อมูลก่อนสร้าง widget
        all_apps = st.session_state.data['แอป'].unique() if not st.session_state.data.empty else []
        all_cats = st.session_state.data['หมวดหมู่'].unique() if not st.session_state.data.empty else []
        
        f_app = c1.multiselect("แอป", all_apps)
        f_cat = c2.multiselect("หมวดหมู่", all_cats)
        f_date = c3.selectbox("วันที่", ["ทั้งหมด", "วันนี้", "เดือนนี้"])

    df_show = st.session_state.data.copy()
    if not df_show.empty:
        # Apply Filter
        if f_app: df_show = df_show[df_show['แอป'].isin(f_app)]
        if f_cat: df_show = df_show[df_show['หมวดหมู่'].isin(f_cat)]
        
        t = get_thai_date()
        if f_date == "วันนี้": df_show = df_show[df_show['วันที่'] == t]
        elif f_date == "เดือนนี้": df_show = df_show[(pd.to_datetime(df_show['วันที่']).dt.month == t.month) & (pd.to_datetime(df_show['วันที่']).dt.year == t.year)]

        # --- จุดแก้ไขสำคัญ: Data Editor ---
        # ใช้ st.data_editor เพื่อแสดงและแก้ไขข้อมูล
        edited_df = st.data_editor(
            df_show, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="db_editor",
            column_config={
                "คงเหลือ/สุทธิ": st.column_config.NumberColumn(format="%.0f ฿"),
                "ยอดเต็ม/หน้าแอป": st.column_config.NumberColumn(format="%.0f ฿"),
                "วันที่": st.column_config.DateColumn(format="YYYY-MM-DD")
            }
        )
        
        # ปุ่มบันทึก (Logic ปรับปรุงใหม่)
        if st.button("💾 บันทึกการเปลี่ยนแปลง", type="primary"):
            try:
                # 1. กรณีไม่ได้กรองข้อมูล (แสดงทั้งหมด) -> แทนที่ข้อมูลได้เลย
                if len(df_show) == len(st.session_state.data):
                    st.session_state.data = edited_df
                
                # 2. กรณีมีการกรองข้อมูล (แสดงบางส่วน) -> ต้อง Update เฉพาะส่วนที่แก้
                else:
                    # แปลง Index ให้ตรงกันเพื่อ Update
                    # (หมายเหตุ: ในที่นี้เราใช้ Index เดิมจาก st.session_state.data)
                    st.session_state.data.update(edited_df)
                    
                    # ตรวจสอบการลบแถว (ยากกว่าเมื่อมีการกรอง แต่โค้ดนี้จะเน้นการแก้ไขค่าเป็นหลัก)
                    # หากต้องการลบ แนะนำให้ลบตอนเลือก "ทั้งหมด"
                    if len(edited_df) < len(df_show):
                         st.warning("⚠️ การลบแถวขณะกรองข้อมูลอาจไม่สมบูรณ์ แนะนำให้เลือกวันที่ 'ทั้งหมด' ก่อนลบ")

                save_data(st.session_state.data)
                st.success("บันทึกเรียบร้อย!")
                st.rerun()
                
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.info("ไม่มีข้อมูล")

