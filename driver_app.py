import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Driver Pro Mobile", page_icon="🚗", layout="wide")
DATA_FILE = "driver_data.csv"

# --- TIMEZONE ---
def get_thai_time():
    tz_thai = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz_thai)

def get_thai_date():
    return get_thai_time().date()

# --- 2. DATA LOADING ---
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
        
        # Ensure numeric columns
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"Time: {get_thai_time().strftime('%H:%M')}")
    maxim_comm_rate = st.slider("Maxim หักคอม (%)", 0, 30, 15) / 100
    ev_home_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=40, step=5)
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูล", type="primary"):
        st.session_state.data = pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'ระยะทาง(กม.)', 'เลขไมล์', 'หมายเหตุ'
        ])
        save_data(st.session_state.data)
        st.rerun()

# --- 4. MAIN APP ---
st.title("🚗 Driver Pro")
tab1, tab2, tab3 = st.tabs(["📝 บันทึก", "📊 สรุป", "🗂️ ข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (MOBILE OPTIMIZED)
# ==========================================
with tab1:
    # ใช้ radio แนวนอนเพื่อประหยัดพื้นที่แนวตั้ง (ลดโอกาสคีย์บอร์ดบัง)
    entry_type = st.radio(
        "", # ซ่อน label เพื่อประหยัดที่
        ["รับงาน", "น้ำมัน/ไฟ", "ไมล์(เริ่ม/จบ)", "อื่นๆ"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.write(f"**เมนู:** {entry_type}") # แสดงหัวข้อให้เห็นชัดๆ แทน

    # --- 1. รับงาน ---
    if entry_type == "รับงาน":
        with st.form(key="form_income", clear_on_submit=True):
            # เรียงแนวนอน ลดความสูง
            c_app, c_note = st.columns([1, 1])
            with c_app:
                platform = st.selectbox("แอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"], label_visibility="collapsed")
            with c_note:
                note = st.text_input("หมายเหตุ", placeholder="โน้ตสั้นๆ", label_visibility="collapsed")

            c1, c2 = st.columns(2)
            with c1: 
                # value=None คือหัวใจสำคัญ! ทำให้ช่องว่าง ไม่ต้องลบเลข 0
                app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0, value=None, placeholder="0")
            with c2: 
                real_receive = st.number_input("รับจริง (ถ้ามีทิป)", min_value=0.0, step=10.0, value=None, placeholder="เท่าหน้าแอป")
            
            # ปุ่มใหญ่กดง่าย
            submitted = st.form_submit_button("✅ บันทึกรายได้", type="primary", use_container_width=True)
            
            if submitted:
                # แปลง None เป็น 0 เพื่อคำนวณ
                price_val = app_price if app_price is not None else 0.0
                real_val = real_receive if real_receive is not None else 0.0
                
                if price_val > 0 or real_val > 0:
                    if real_val == 0: real_val = price_val # ถ้าไม่กรอกรับจริง ให้เท่าหน้าแอป
                    
                    deduction = 0
                    tip = max(0, real_val - price_val)
                    
                    if platform in ["Maxim", "งานนอก"]:
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
                    st.toast(f"รับ {net_income:.0f} บ. (ทิป {tip:.0f})")
                    st.rerun()
                else:
                    st.warning("ใส่ราคาด้วยครับ")

    # --- 2. ไมล์ ---
    elif entry_type == "ไมล์(เริ่ม/จบ)":
        with st.form(key="form_odom", clear_on_submit=True):
            shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
            
            last_odom = 0.0
            if not st.session_state.data.empty: last_odom = st.session_state.data['เลขไมล์'].max()
            st.caption(f"ล่าสุด: {last_odom:,.0f}")
            
            # value=None ไม่ต้องลบเลขเก่า
            odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0, step=1.0, value=None, placeholder="กรอกเลขไมล์")
            
            submitted = st.form_submit_button("💾 บันทึกไมล์", type="primary", use_container_width=True)
            
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
                    st.error("ใส่เลขไมล์ด้วยครับ")

    # --- 3. น้ำมัน/ไฟ ---
    elif entry_type == "น้ำมัน/ไฟ":
        with st.form(key="form_energy", clear_on_submit=True):
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน", "🔌 ชาร์จสถานี"], horizontal=True)
            
            # ชาร์จบ้านมีค่า Default แต่ถ้าเลือกอื่นให้เป็นว่าง
            default_val = ev_home_rate if e_type == "⚡ ชาร์จบ้าน" else None
            
            c1, c2 = st.columns(2)
            with c1:
                cost = st.number_input("บาท", min_value=0.0, value=default_val, placeholder="0")
            with c2:
                note = st.text_input("สถานที่", placeholder="ปั๊ม/จุดชาร์จ")

            submitted = st.form_submit_button("💸 บันทึกจ่าย", type="primary", use_container_width=True)
            
            if submitted:
                cost_val = cost if cost is not None else 0.0
                if cost_val > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost_val,
                        'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} {note}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast("บันทึกแล้ว")
                    st.rerun()
                else:
                    st.warning("ใส่ราคาด้วยครับ")

    # --- 4. อื่นๆ ---
    elif entry_type == "อื่นๆ":
        with st.form(key="form_other", clear_on_submit=True):
            type_other = st.selectbox("ประเภท", ["เติมเครดิตงาน", "ค่ากิน/ซ่อม/อื่นๆ"])
            
            sub_cat = ""
            if type_other == "เติมเครดิตงาน":
                 sub_cat = st.selectbox("แอป", ["Grab Wallet", "Bolt", "Maxim", "Line Man"])
            else:
                 sub_cat = st.text_input("รายการ", placeholder="เช่น ข้าว, ปะยาง")
            
            cost = st.number_input("บาท", min_value=0.0, value=None, placeholder="0")
            
            submitted = st.form_submit_button("💾 บันทึก", type="primary", use_container_width=True)
            
            if submitted:
                cost_val = cost if cost is not None else 0.0
                if cost_val > 0:
                    item_name = "เติมเครดิต" if "เครดิต" in type_other else "ทั่วไป"
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': sub_cat if "เครดิต" in type_other else 'ค่าใช้จ่าย',
                        'หมวดหมู่': 'รายจ่าย', 'รายการ': item_name,
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost_val, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost_val,
                        'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast("บันทึกแล้ว")
                    st.rerun()

    # เพิ่มพื้นที่ว่างด้านล่างเพื่อให้ Scroll หลบแป้นพิมพ์ได้ง่ายขึ้น
    st.write("<br><br><br>", unsafe_allow_html=True)

# ==========================================
# TAB 2 & 3: เหมือนเดิม
# ==========================================
with tab2:
    st.markdown("### 📊 สรุปผล")
    filter_col1, _ = st.columns([2, 1])
    with filter_col1:
        time_filter = st.selectbox("ช่วงเวลา", ["วันนี้", "สัปดาห์นี้", "เดือนนี้", "ปีนี้", "ทั้งหมด"])
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        filtered_df = df.copy()
        
        if time_filter == "วันนี้": filtered_df = df[df['วันที่'] == today]
        elif time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday())
            end_week = start_week + datetime.timedelta(days=6)
            filtered_df = df[(df['วันที่'] >= start_week) & (df['วันที่'] <= end_week)]
        elif time_filter == "เดือนนี้": filtered_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "ปีนี้": filtered_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]

        if not filtered_df.empty:
            odom_df = filtered_df[filtered_df['เลขไมล์'] > 0]
            daily_dist = 0
            if not odom_df.empty:
                daily_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                daily_odom['run_dist'] = daily_odom['max'] - daily_odom['min']
                daily_dist = daily_odom['run_dist'].sum()
            total_km = daily_dist if daily_dist > 0 else filtered_df['ระยะทาง(กม.)'].sum()

            inc_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายรับ']
            exp_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายจ่าย']
            total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
            fuel = exp_df[exp_df['รายการ'] == 'ค่าน้ำมัน/ไฟ']['หัก/จ่าย'].sum()
            other = exp_df[exp_df['รายการ'] == 'ทั่วไป']['หัก/จ่าย'].sum()
            net = total_inc - fuel - other

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไร", f"{net:,.0f}")
            m2.metric("⛽ น้ำมัน/ไฟ", f"{fuel:,.0f}")
            m3.metric("🛣️ วิ่ง(กม.)", f"{total_km:,.0f}")
            if total_km > 0: m4.metric("📊 บาท/กม.", f"{total_inc/total_km:.1f}")
            else: m4.metric("📊 บาท/กม.", "-")

            st.divider()
            if not inc_df.empty:
                fig = px.bar(inc_df.groupby('แอป')['คงเหลือ/สุทธิ'].sum().reset_index(), x='แอป', y='คงเหลือ/สุทธิ', color='แอป', text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลช่วงนี้")

with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    if not st.session_state.data.empty:
        edited = st.data_editor(st.session_state.data, num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกแก้ไข", type="primary"):
            st.session_state.data = edited
            save_data(edited)
            st.success("บันทึกแล้ว")
