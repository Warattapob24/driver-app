import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import json
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ", page_icon="🚗", layout="wide")
DATA_FILE = "driver_data.csv"
SETTINGS_FILE = "settings.json"

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
    try:
        df = pd.read_csv(DATA_FILE)
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
        df.rename(columns=col_map, inplace=True)
        
        # เพิ่มคอลัมน์ถ้ายังไม่มี
        if 'ช่องทางรับเงิน' not in df.columns: df['ช่องทางรับเงิน'] = 'ไม่ระบุ'
        if 'เงินสดเข้าตัว' not in df.columns: df['เงินสดเข้าตัว'] = 0.0

        # แปลงตัวเลข
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์']
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            else: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        if 'วันที่' in df.columns:
            df['วันที่'] = pd.to_datetime(df['วันที่']).dt.date
            
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_and_clean_data()
    save_data(st.session_state.data)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"เวลา: {get_thai_time().strftime('%H:%M')}")
    
    current_settings = load_settings()
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=float(current_settings.get("ev_rate", 40.0)), step=5.0)
    
    if new_ev_rate != current_settings.get("ev_rate"):
        save_settings({"ev_rate": new_ev_rate})
        st.toast("บันทึกค่าไฟแล้ว!")
    
    ev_home_rate = new_ev_rate
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูลทั้งหมด", type="primary"):
        st.session_state.data = pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])
        save_data(st.session_state.data)
        st.rerun()

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 สรุปผลละเอียด", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (เหมือนเดิม 100%)
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
        
        # --- 1. รับงาน ---
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            with st.form(key="form_income", clear_on_submit=True):
                # แถว 1
                c_app, c_pay = st.columns(2)
                with c_app:
                    platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                with c_pay:
                    pay_method = st.selectbox("ช่องทางรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])

                # แถว 2
                c1, c2 = st.columns(2)
                with c1: 
                    app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0, value=None, placeholder="0.00")
                with c2: 
                    real_receive = st.number_input("เงินที่รับจริง (รวมทิป)", min_value=0.0, step=10.0, value=None, placeholder="เท่าหน้าแอป")
                
                note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
                submitted = st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True)
                
                if submitted:
                    price_val = app_price if app_price is not None else 0.0
                    real_val = real_receive if real_receive is not None else 0.0
                    
                    if price_val > 0 or real_val > 0:
                        if real_val == 0: real_val = price_val 
                        
                        tip = max(0, real_val - price_val)
                        total_income = real_val 
                        
                        # คำนวณเงินสดเข้าตัว
                        cash_in_hand = 0.0
                        if pay_method == "💵 เงินสด/โอน":
                            cash_in_hand = real_val
                        else:
                            cash_in_hand = 0.0 
                        
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method,
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': 0, 'ทิป': tip, 
                            'คงเหลือ/สุทธิ': total_income, 
                            'เงินสดเข้าตัว': cash_in_hand, 
                            'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        
                        msg = f"บันทึกรายได้ {total_income:.0f} บาท"
                        if tip > 0: msg += f" (ทิป {tip:.0f})"
                        st.toast(msg)
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกยอดเงิน")

        # --- 2. เติมเครดิต (รายจ่าย) ---
        elif entry_type == "💳 เติมเครดิตแอป":
            st.markdown("#### 💳 เติมเงินเข้าแอป (นับเป็นค่าใช้จ่าย)")
            with st.form(key="form_topup", clear_on_submit=True):
                sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
                cost = st.number_input("จำนวนเงินที่เติม", min_value=0.0, value=None, placeholder="0.00")
                submitted = st.form_submit_button("บันทึกรายจ่าย 💾", type="primary", use_container_width=True)
                
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 
                            'เงินสดเข้าตัว': -cost_val,
                            'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast(f"บันทึกเติมเงิน {cost_val} บาทแล้ว")
                        st.rerun()
                    else: st.warning("กรุณากรอกจำนวนเงิน")

        # --- 3. น้ำมัน/ไฟ ---
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            with st.form(key="form_energy", clear_on_submit=True):
                e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
                default_val = None
                if e_type == "⚡ ชาร์จบ้าน (เหมา)": default_val = float(ev_home_rate)
                cost = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, value=default_val, placeholder="0.00")
                note = st.text_input("สถานที่")
                submitted = st.form_submit_button("บันทึกค่าใช้จ่าย 💾", type="primary", use_container_width=True)
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 
                            'เงินสดเข้าตัว': -cost_val,
                            'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast("บันทึกเรียบร้อย")
                        st.rerun()
                    else: st.warning("กรุณากรอกจำนวนเงิน")

        # --- 4. ไมล์ ---
        elif entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            with st.form(key="form_odom", clear_on_submit=True):
                shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
                last_odom = 0.0
                if not st.session_state.data.empty: last_odom = st.session_state.data['เลขไมล์'].max()
                st.caption(f"เลขไมล์ล่าสุด: {last_odom:,.0f}")
                odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0, step=1.0, value=None, placeholder="กรอกเลขไมล์")
                submitted = st.form_submit_button("บันทึกเลขไมล์ 💾", type="primary", use_container_width=True)
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
                        st.toast(f"บันทึก {shift_type} แล้ว")
                        st.rerun()
                    else: st.error("กรุณากรอกเลขไมล์")

        # --- 5. จ่ายอื่นๆ ---
        elif entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### 🛠️ จ่ายทั่วไป")
            with st.form(key="form_other", clear_on_submit=True):
                item_name = "ทั่วไป"
                sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
                cost = st.number_input("จำนวนเงิน", min_value=0.0, value=None, placeholder="0.00")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': item_name, 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 
                            'คงเหลือ/สุทธิ': -cost_val, 
                            'เงินสดเข้าตัว': -cost_val,
                            'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast("บันทึกเรียบร้อย")
                        st.rerun()
                    else: st.warning("กรุณากรอกจำนวนเงิน")
    st.markdown("<br>" * 5, unsafe_allow_html=True)

# ==========================================
# TAB 2: สรุปผล (โครงสร้างเดิม + สีถูกต้อง)
# ==========================================
with tab2:
    st.markdown("### 📊 แดชบอร์ดสรุปผลละเอียด")
    time_filter = st.selectbox(
        "📅 เลือกช่วงเวลา:",
        ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง (เลือกวันที่)"]
    )
    
    custom_start = None
    custom_end = None
    if time_filter == "กำหนดเอง (เลือกวันที่)":
        st.info("👇 จิ้มปฏิทินเลือกช่วงเวลา")
        date_range = st.date_input("ช่วงวันที่:", value=(get_thai_date(), get_thai_date()))
        if len(date_range) == 2: custom_start, custom_end = date_range
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        filtered_df = df.copy()
        
        # --- Date Filtering ---
        if time_filter == "วันนี้": filtered_df = df[df['วันที่'] == today]
        elif time_filter == "เมื่อวาน": filtered_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
        elif time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday())
            filtered_df = df[(df['วันที่'] >= start_week) & (df['วันที่'] <= start_week + datetime.timedelta(days=6))]
        elif time_filter == "เดือนนี้": filtered_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "เดือนที่แล้ว":
            first = today.replace(day=1); last_prev = first - datetime.timedelta(days=1); start_prev = last_prev.replace(day=1)
            filtered_df = df[(df['วันที่'] >= start_prev) & (df['วันที่'] <= last_prev)]
        elif time_filter == "ปีนี้": filtered_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
        elif time_filter == "กำหนดเอง (เลือกวันที่)" and custom_start:
            filtered_df = df[(df['วันที่'] >= custom_start) & (df['วันที่'] <= custom_end)]
        elif time_filter == "กำหนดเอง (เลือกวันที่)": filtered_df = pd.DataFrame()

        if not filtered_df.empty:
            # 1. ระยะทาง & เวลา
            odom_df = filtered_df[filtered_df['เลขไมล์'] > 0]
            daily_dist = 0
            if not odom_df.empty:
                daily_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                daily_dist = (daily_odom['max'] - daily_odom['min']).sum()
            total_km = daily_dist if daily_dist > 0 else filtered_df['ระยะทาง(กม.)'].sum()

            shift_df = filtered_df[filtered_df['หมวดหมู่'] == 'กะงาน']
            total_hours = 0
            if not shift_df.empty:
                for d in shift_df['วันที่'].unique():
                    day_shifts = shift_df[shift_df['วันที่'] == d]
                    starts = day_shifts[day_shifts['รายการ'].str.contains("เริ่ม")]['เวลา']
                    ends = day_shifts[day_shifts['รายการ'].str.contains("เลิก")]['เวลา']
                    if not starts.empty and not ends.empty:
                        try:
                            t_s = pd.to_datetime(starts.min(), format='%H:%M')
                            t_e = pd.to_datetime(ends.max(), format='%H:%M')
                            h = (t_e - t_s).total_seconds() / 3600
                            if h < 0: h += 24
                            total_hours += h
                        except: pass

            # 2. การเงิน
            inc_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายรับ']
            exp_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            fuel = exp_df[exp_df['รายการ'] == 'ค่าน้ำมัน/ไฟ']['หัก/จ่าย'].sum()
            # รายจ่ายรวม (น้ำมัน + เติมเครดิต + อื่นๆ)
            total_expense = exp_df['หัก/จ่าย'].sum()
            
            net = total_inc - total_expense
            
            # เงินสดในมือ (Cash Flow)
            cash_in_hand = filtered_df['เงินสดเข้าตัว'].sum()

            st.caption(f"สรุปยอด: {time_filter}")
            
            # กล่องเงินสด
            st.container(border=True).markdown(f"### 💵 เงินสดที่จับต้องได้จริง: {cash_in_hand:,.0f} บาท")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f}", help="รายได้งาน - (น้ำมัน + เติมเครดิต + อื่นๆ)")
            m2.metric("💸 รายจ่ายรวม", f"{total_expense:,.0f}")
            m3.metric("🛣️ วิ่ง(กม.)", f"{total_km:,.0f}")
            m4.metric("⏱️ เวลางาน", f"{total_hours:.1f} ชม.")
            
            st.divider()
            
            # สถิติ
            s1, s2 = st.columns(2)
            if total_km > 0: s1.metric("📊 รายได้/กม.", f"{total_inc/total_km:.1f} บ.")
            if total_hours > 0: s2.metric("💵 รายได้/ชม.", f"{total_inc/total_hours:.0f} บ.")
            
            # รายการย่อย
            if time_filter in ["วันนี้", "เมื่อวาน"]:
                with st.expander("ดูรายการงานที่วิ่ง"):
                    cols = ['เวลา', 'แอป', 'ยอดเต็ม/หน้าแอป', 'ทิป', 'คงเหลือ/สุทธิ', 'ช่องทางรับเงิน']
                    st.dataframe(inc_df[cols], use_container_width=True)

            st.divider()
            
            # --- กราฟ (ที่แก้ไขสีให้แล้ว) ---
            
            # 🟢 1. กำหนดชุดสีที่ถูกต้อง (Brand Colors)
            APP_COLORS = {
                "Grab": "#00B14F",      # เขียว Grab
                "Line Man": "#06C755",  # เขียว Line Man
                "Bolt": "#34D186",      # เขียว Bolt (Mint)
                "Maxim": "#FFD600",     # เหลือง Maxim
                "Robinhood": "#9D2398", # ม่วง Robinhood
                "Win": "#FF6B00",       # ส้ม วิน
                "งานนอก": "#7F8C8D",    # เทา
                "ระบบ": "#95A5A6"       # เทาอ่อน
            }
            
            c1, c2 = st.columns(2)
            with c1:
                # รายได้แยกแอป (ใส่สีให้แล้ว)
                if not inc_df.empty: 
                    st.plotly_chart(px.bar(
                        inc_df.groupby('แอป')['คงเหลือ/สุทธิ'].sum().reset_index(), 
                        x='แอป', y='คงเหลือ/สุทธิ', 
                        color='แอป', text_auto=True, title="รายได้แยกแอป",
                        color_discrete_map=APP_COLORS  # ✅ ใส่สีตรงนี้ครับ
                    ), use_container_width=True)
            with c2:
                # รายจ่ายแยกประเภท
                if not exp_df.empty: 
                    st.plotly_chart(px.pie(
                        exp_df, values='หัก/จ่าย', names='รายการ', 
                        title="สัดส่วนรายจ่าย (น้ำมัน vs เติมแอป)", hole=0.4
                    ), use_container_width=True)

        else: st.warning(f"ไม่พบข้อมูล: {time_filter}")
    else: st.info("ยังไม่มีข้อมูล")

# ==========================================
# TAB 3: ฐานข้อมูล (เหมือนเดิม)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล (ค้นหาและแก้ไข)")
    with st.container(border=True):
        st.write("🔍 **ตัวกรองค้นหา**")
        fc1, fc2, fc3 = st.columns(3)
        with fc1: f_app = st.multiselect("เลือกแอป:", options=st.session_state.data['แอป'].unique(), default=[], key="db_app_filter")
        with fc2: f_cat = st.multiselect("หมวดหมู่:", options=st.session_state.data['หมวดหมู่'].unique(), default=[], key="db_cat_filter")
        with fc3: f_date_mode = st.selectbox("ช่วงวันที่:", ["ทั้งหมด", "วันนี้", "เดือนนี้", "กำหนดเอง"], key="db_date_mode")
    
    view_df = st.session_state.data.copy()
    if f_app: view_df = view_df[view_df['แอป'].isin(f_app)]
    if f_cat: view_df = view_df[view_df['หมวดหมู่'].isin(f_cat)]
    
    today = get_thai_date()
    if f_date_mode == "วันนี้": view_df = view_df[view_df['วันที่'] == today]
    elif f_date_mode == "เดือนนี้": view_df = view_df[(pd.to_datetime(view_df['วันที่']).dt.month == today.month) & (pd.to_datetime(view_df['วันที่']).dt.year == today.year)]
    elif f_date_mode == "กำหนดเอง":
        d_range = st.date_input("เลือกช่วง:", value=(today, today), key="db_custom_date")
        if len(d_range) == 2: view_df = view_df[(view_df['วันที่'] >= d_range[0]) & (view_df['วันที่'] <= d_range[1])]

    st.caption(f"พบข้อมูล: {len(view_df)} รายการ")
    if not view_df.empty:
        # แสดงคอลัมน์สำคัญ
        cols_to_show = [c for c in view_df.columns if c in ['วันที่', 'เวลา', 'แอป', 'รายการ', 'ช่องทางรับเงิน', 'ยอดเต็ม/หน้าแอป', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'หมายเหตุ']]
        edited_view = st.data_editor(view_df[cols_to_show].sort_values(by=["วันที่", "เวลา"], ascending=False), num_rows="dynamic", use_container_width=True, key="data_editor_view")
        
        if st.button("💾 บันทึกการแก้ไข (ในตารางที่กรอง)", type="primary"):
            st.session_state.data.update(edited_view)
            save_data(st.session_state.data)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.rerun()
    else: st.info("ไม่พบข้อมูลตามเงื่อนไข")
