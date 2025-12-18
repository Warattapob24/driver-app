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

# --- 2. SETTINGS MANAGEMENT (ระบบจำค่าการตั้งค่า) ---
def load_settings():
    # ค่าเริ่มต้นถ้ายังไม่มีไฟล์
    default_settings = {"maxim_rate": 15, "ev_rate": 40.0}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return default_settings
    return default_settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

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
            'Odometer': 'เลขไมล์'
        }
        df.rename(columns=col_map, inplace=True)
        
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'ระยะทาง(กม.)', 'เลขไมล์']
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            else: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        if 'วันที่' in df.columns:
            df['วันที่'] = pd.to_datetime(df['วันที่']).dt.date
            
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'ระยะทาง(กม.)', 'เลขไมล์', 'หมายเหตุ'
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_and_clean_data()
    save_data(st.session_state.data)

# --- 4. SIDEBAR (ปรับปรุงให้จำค่าได้) ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"เวลา: {get_thai_time().strftime('%H:%M')}")
    
    # โหลดค่าเดิมมาแสดง
    current_settings = load_settings()
    
    # Widget ปรับค่า
    new_maxim_rate = st.slider("Maxim หักคอม (%)", 0, 30, current_settings.get("maxim_rate", 15))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=float(current_settings.get("ev_rate", 40.0)), step=5.0)
    
    # ตรวจสอบว่ามีการเปลี่ยนแปลงไหม? ถ้ามีให้บันทึกทันที
    if new_maxim_rate != current_settings.get("maxim_rate") or new_ev_rate != current_settings.get("ev_rate"):
        updated_settings = {"maxim_rate": new_maxim_rate, "ev_rate": new_ev_rate}
        save_settings(updated_settings)
        # ไม่ต้อง rerun ก็ได้ เพราะค่าเปลี่ยนแล้ว แต่เพื่อให้แน่ใจว่าหน้าอื่นใช้ค่าใหม่
        st.toast("บันทึกการตั้งค่าแล้ว!")
    
    # ตัวแปรสำหรับนำไปคำนวณในหน้าหลัก
    maxim_comm_rate = new_maxim_rate / 100
    ev_home_rate = new_ev_rate
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูล", type="primary"):
        st.session_state.data = pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'ระยะทาง(กม.)', 'เลขไมล์', 'หมายเหตุ'
        ])
        save_data(st.session_state.data)
        st.rerun()

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 สรุปผลละเอียด", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน
# ==========================================
with tab1:
    col_type, col_form = st.columns([1, 2])
    with col_type:
        st.subheader("เลือกรายการ")
        entry_type = st.radio(
            "ประเภทรายการ",
            ["🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)", "💳 เติมเครดิตแอป", "🛠️ จ่ายอื่นๆ"],
        )

    with col_form:
        st.container(border=True)
        # --- 1. รับงาน ---
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            with st.form(key="form_income", clear_on_submit=True):
                platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                c1, c2 = st.columns(2)
                with c1: 
                    app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0, value=None, placeholder="0.00")
                with c2: 
                    real_receive = st.number_input("เงินรับจริง (รวมทิป)", min_value=0.0, step=10.0, value=None, placeholder="เท่าหน้าแอป")
                
                note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
                submitted = st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True)
                
                if submitted:
                    price_val = app_price if app_price is not None else 0.0
                    real_val = real_receive if real_receive is not None else 0.0
                    
                    if price_val > 0 or real_val > 0:
                        if real_val == 0: real_val = price_val 
                        
                        deduction = 0
                        tip = max(0, real_val - price_val)
                        
                        if platform == "Maxim":
                            deduction = price_val * maxim_comm_rate
                            net_income = price_val - deduction + tip
                        else:
                            net_income = price_val + tip 
                        
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร',
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': deduction, 'ทิป': tip, 
                            'คงเหลือ/สุทธิ': net_income, 'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast(f"บันทึกสำเร็จ! เข้ากระเป๋า {net_income:.0f} บาท")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกยอดเงิน")

        # --- 2. น้ำมัน/ไฟ ---
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            with st.form(key="form_energy", clear_on_submit=True):
                e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
                
                # ใช้ค่าที่โหลดมาจาก Settings
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
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost_val,
                            'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast("บันทึกเรียบร้อย")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกจำนวนเงิน")

        # --- 3. เลขไมล์ ---
        elif entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            with st.form(key="form_odom", clear_on_submit=True):
                shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
                last_odom = 0.0
                if not st.session_state.data.empty: last_odom = st.session_state.data['เลขไมล์'].max()
                st.caption(f"เลขไมล์ล่าสุดในระบบ: {last_odom:,.0f}")
                odometer = st.number_input("เลขไมล์หน้าปัดปัจจุบัน", min_value=0.0, step=1.0, value=None, placeholder="กรอกเลขไมล์")
                submitted = st.form_submit_button("บันทึกเลขไมล์ 💾", type="primary", use_container_width=True)
                if submitted:
                    odom_val = odometer if odometer is not None else 0.0
                    if odom_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': shift_type,
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0,
                            'ระยะทาง(กม.)': 0, 'เลขไมล์': odom_val, 'หมายเหตุ': f"เลขไมล์ {shift_type}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast(f"บันทึก {shift_type} แล้ว")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกเลขไมล์")

        # --- 4. อื่นๆ ---
        elif entry_type == "💳 เติมเครดิตแอป" or entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### {entry_type}")
            with st.form(key="form_other", clear_on_submit=True):
                if "เครดิต" in entry_type:
                    item_name = "เติมเครดิต"
                    sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man"])
                else:
                    item_name = "ทั่วไป"
                    sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
                cost = st.number_input("จำนวนเงิน", min_value=0.0, value=None, placeholder="0.00")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                if submitted:
                    cost_val = cost if cost is not None else 0.0
                    if cost_val > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': sub_cat if "เครดิต" in entry_type else 'ค่าใช้จ่าย',
                            'หมวดหมู่': 'รายจ่าย', 'รายการ': item_name,
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost_val,
                            'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast("บันทึกเรียบร้อย")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกจำนวนเงิน")
    st.markdown("<br>" * 10, unsafe_allow_html=True)

# ==========================================
# TAB 2: สรุปผล
# ==========================================
with tab2:
    st.markdown("### 📊 แดชบอร์ดสรุปผลละเอียด")
    time_filter = st.selectbox(
        "📅 เลือกช่วงเวลาที่ต้องการดู:",
        ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "กำหนดเอง (เลือกวันที่)"]
    )
    
    custom_start_date = None
    custom_end_date = None
    if time_filter == "กำหนดเอง (เลือกวันที่)":
        st.info("👇 จิ้มที่ช่องวันที่ เพื่อเลือกช่วงเวลาเริ่มต้น-สิ้นสุด")
        date_range = st.date_input("ระบุช่วงวันที่:", value=(get_thai_date(), get_thai_date()), max_value=get_thai_date())
        if len(date_range) == 2: custom_start_date, custom_end_date = date_range
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        filtered_df = df.copy()
        
        if time_filter == "วันนี้": filtered_df = df[df['วันที่'] == today]
        elif time_filter == "เมื่อวาน": filtered_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
        elif time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday())
            end_week = start_week + datetime.timedelta(days=6)
            filtered_df = df[(df['วันที่'] >= start_week) & (df['วันที่'] <= end_week)]
        elif time_filter == "เดือนนี้": filtered_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "เดือนที่แล้ว":
            first_day = today.replace(day=1)
            last_day_prev = first_day - datetime.timedelta(days=1)
            start_prev = last_day_prev.replace(day=1)
            filtered_df = df[(df['วันที่'] >= start_prev) & (df['วันที่'] <= last_day_prev)]
        elif time_filter == "ปีนี้": filtered_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
        elif time_filter == "กำหนดเอง (เลือกวันที่)" and custom_start_date:
            filtered_df = df[(df['วันที่'] >= custom_start_date) & (df['วันที่'] <= custom_end_date)]
        elif time_filter == "กำหนดเอง (เลือกวันที่)": filtered_df = pd.DataFrame()

        if not filtered_df.empty:
            odom_df = filtered_df[filtered_df['เลขไมล์'] > 0]
            daily_dist = 0
            if not odom_df.empty:
                daily_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                daily_dist = (daily_odom['max'] - daily_odom['min']).sum()
            total_km = daily_dist if daily_dist > 0 else filtered_df['ระยะทาง(กม.)'].sum()

            inc_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายรับ']
            exp_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            fuel = exp_df[exp_df['รายการ'] == 'ค่าน้ำมัน/ไฟ']['หัก/จ่าย'].sum()
            other = exp_df[exp_df['รายการ'] == 'ทั่วไป']['หัก/จ่าย'].sum()
            net = total_inc - fuel - other

            st.caption(f"สรุปยอด: {time_filter}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net:,.0f}")
            m2.metric("⛽ น้ำมัน/ไฟ", f"{fuel:,.0f}")
            m3.metric("🛣️ วิ่ง(กม.)", f"{total_km:,.0f}")
            if total_km > 0: m4.metric("📊 บาท/กม.", f"{total_inc/total_km:.1f}")
            else: m4.metric("📊 บาท/กม.", "-")

            st.divider()
            if time_filter in ["วันนี้", "เมื่อวาน"]:
                with st.expander("ดูรายการย่อย"):
                    st.dataframe(inc_df[['เวลา', 'แอป', 'คงเหลือ/สุทธิ', 'หมายเหตุ']], use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if not inc_df.empty:
                    fig = px.bar(inc_df.groupby('แอป')['คงเหลือ/สุทธิ'].sum().reset_index(), x='แอป', y='คงเหลือ/สุทธิ', color='แอป', text_auto=True, title=f"รายได้แยกแอป")
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if not inc_df.empty:
                    inc_df['Hour'] = pd.to_datetime(inc_df['เวลา'], format='%H:%M').dt.hour
                    fig = px.histogram(inc_df, x='Hour', y='คงเหลือ/สุทธิ', nbins=24, title=f"ช่วงเวลาทำเงิน", color_discrete_sequence=['#FF4B4B'])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"ไม่พบข้อมูลในช่วง: {time_filter}")
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")

with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    if not st.session_state.data.empty:
        edited = st.data_editor(st.session_state.data, num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกแก้ไข", type="primary"):
            st.session_state.data = edited
            save_data(edited)
            st.success("บันทึกแล้ว")
