import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ", page_icon="🚗", layout="wide")
DATA_FILE = "driver_data.csv"

# --- 🎯 ฟังก์ชันจัดการเวลาประเทศไทย (UTC+7) ---
def get_thai_time():
    tz_thai = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz_thai)

def get_thai_date():
    return get_thai_time().date()

# --- 2. DATA LOADING & CLEANING ---
def load_and_clean_data():
    try:
        df = pd.read_csv(DATA_FILE)
        
        # 1. แปลงหัวตาราง
        col_map = {
            'Date': 'วันที่', 'Time': 'เวลา', 'Platform': 'แอป',
            'Category': 'หมวดหมู่', 'SubCategory': 'รายการ',
            'Amount_Gross': 'ยอดเต็ม/หน้าแอป', 'Deduction': 'หัก/จ่าย',
            'Tip': 'ทิป', 'Net_Income': 'คงเหลือ/สุทธิ',
            'Distance_Km': 'ระยะทาง(กม.)', 'Note': 'หมายเหตุ',
            'Odometer': 'เลขไมล์'
        }
        df.rename(columns=col_map, inplace=True)

        # 2. แปลงคำภาษาอังกฤษ
        val_map = {
            'Income': 'รายรับ', 'Expense': 'รายจ่าย',
            'Fare': 'ค่าโดยสาร', 'Fuel/Energy': 'ค่าน้ำมัน/ไฟ',
            'Top-up': 'เติมเครดิต', 'General': 'ทั่วไป',
            'Top-up/Commission': 'เติมเครดิต', 'Maintenance/Other': 'ทั่วไป'
        }
        df.replace(val_map, inplace=True)

        # 3. แปลงตัวเลข
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'ระยะทาง(กม.)', 'เลขไมล์']
        for col in num_cols:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 4. แปลงวันที่ให้เป็น Date Object จริงๆ เพื่อใช้กรอง
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
    current_time = get_thai_time().strftime("%H:%M")
    st.info(f"🕒 เวลาไทย: {current_time}")
    
    maxim_comm_rate = st.slider("Maxim หักคอมมิชชั่น (%)", 0, 30, 15) / 100
    ev_home_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมาจ่าย/ครั้ง)", value=40, step=5)
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูลทั้งหมด", type="primary"):
        st.session_state.data = pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'ระยะทาง(กม.)', 'เลขไมล์', 'หมายเหตุ'
        ])
        save_data(st.session_state.data)
        st.rerun()

# --- 4. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้ (Driver Pro)")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 สรุปผลกำไร", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (เหมือนเดิม)
# ==========================================
with tab1:
    col_type, col_form = st.columns([1, 2])
    with col_type:
        st.subheader("เลือกรายการ")
        entry_type = st.radio(
            "ประเภทรายการ",
            ["🕒 เริ่มงาน/เลิกงาน (เลขไมล์)", "🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "💳 เติมเครดิตแอป", "🛠️ จ่ายอื่นๆ"],
        )

    with col_form:
        st.container(border=True)
        
        if entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
            last_odom = 0.0
            if not st.session_state.data.empty: last_odom = st.session_state.data['เลขไมล์'].max()
            odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0, value=float(last_odom), step=1.0)
            if st.button("บันทึกเลขไมล์ 💾", type="primary", use_container_width=True):
                if odometer > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': shift_type,
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0,
                        'ระยะทาง(กม.)': 0, 'เลขไมล์': odometer, 'หมายเหตุ': f"เลขไมล์ {shift_type}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast(f"บันทึก {shift_type} เรียบร้อย!")

        elif entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
            c1, c2 = st.columns(2)
            with c1: app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0)
            with c2: real_receive = st.number_input("เงินรับจริง (รวมทิป)", min_value=0.0, value=app_price, step=10.0)
            with st.expander("ใส่ระยะทาง (ไม่บังคับ)"): distance = st.number_input("ระยะทางงานนี้ (กม.)", min_value=0.0, step=1.0)
            note = st.text_input("หมายเหตุ")
            if st.button("บันทึกรายได้ ✅", type="primary", use_container_width=True):
                if app_price > 0:
                    deduction = 0
                    tip = max(0, real_receive - app_price)
                    if platform in ["Maxim", "งานนอก"]:
                        deduction = app_price * maxim_comm_rate
                        net_income = app_price - deduction + tip
                    else:
                        net_income = app_price + tip 
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร',
                        'ยอดเต็ม/หน้าแอป': app_price, 'หัก/จ่าย': deduction, 'ทิป': tip, 
                        'คงเหลือ/สุทธิ': net_income, 'ระยะทาง(กม.)': distance, 'เลขไมล์': 0, 'หมายเหตุ': note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast(f"บันทึกสำเร็จ! เข้ากระเป๋า {net_income:.0f} บาท")

        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            cost = st.number_input("บาท", value=(ev_home_rate if "บ้าน" in e_type else 0.0))
            note = st.text_input("สถานที่")
            if st.button("บันทึก", type="primary", use_container_width=True):
                new_row = {
                    'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                    'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ',
                    'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost,
                    'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                }
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.data)
                st.toast("บันทึกเรียบร้อย")

        elif entry_type == "💳 เติมเครดิตแอป" or entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### {entry_type}")
            if "เครดิต" in entry_type:
                item_name = "เติมเครดิต"
                sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man"])
            else:
                item_name = "ทั่วไป"
                sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
            cost = st.number_input("จำนวนเงิน", min_value=0.0)
            if st.button("บันทึก", type="primary", use_container_width=True):
                 new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': sub_cat if "เครดิต" in entry_type else 'ค่าใช้จ่าย',
                        'หมวดหมู่': 'รายจ่าย', 'รายการ': item_name,
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost,
                        'ระยะทาง(กม.)': 0, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                    }
                 st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                 save_data(st.session_state.data)
                 st.toast("บันทึกเรียบร้อย")

# ==========================================
# TAB 2: สรุปผล (อัปเกรดใหม่! เพิ่มตัวกรอง)
# ==========================================
with tab2:
    st.markdown("### 📊 แดชบอร์ดสรุปผล")
    
    # --- 🕒 TIME FILTER (ตัวกรองช่วงเวลา) ---
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        time_filter = st.radio(
            "เลือกช่วงเวลาที่ต้องการดู:",
            ["วันนี้", "สัปดาห์นี้", "เดือนนี้", "ปีนี้", "ทั้งหมด"],
            horizontal=True,
            index=0
        )
    
    df = st.session_state.data
    
    if not df.empty:
        # --- LOGIC กรองข้อมูลตามเวลา ---
        today = get_thai_date()
        filtered_df = df.copy()
        
        if time_filter == "วันนี้":
            filtered_df = df[df['วันที่'] == today]
        elif time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday()) # วันจันทร์
            end_week = start_week + datetime.timedelta(days=6) # วันอาทิตย์
            filtered_df = df[(df['วันที่'] >= start_week) & (df['วันที่'] <= end_week)]
        elif time_filter == "เดือนนี้":
            filtered_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "ปีนี้":
            filtered_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
        else:
            pass # ทั้งหมด
            
        # --- แสดงข้อมูลหลังกรอง ---
        if not filtered_df.empty:
            st.caption(f"กำลังแสดงข้อมูล: {time_filter} ({len(filtered_df)} รายการ)")
            
            # คำนวณระยะทาง (Logic เดิม)
            odom_df = filtered_df[filtered_df['เลขไมล์'] > 0]
            daily_dist = 0
            if not odom_df.empty:
                daily_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                daily_odom['run_dist'] = daily_odom['max'] - daily_odom['min']
                daily_dist = daily_odom['run_dist'].sum()
            manual_dist = filtered_df['ระยะทาง(กม.)'].sum()
            total_km = daily_dist if daily_dist > 0 else manual_dist

            # คำนวณเงิน
            income_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายรับ']
            expense_df = filtered_df[filtered_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_income = income_df['คงเหลือ/สุทธิ'].sum()
            fuel_cost = expense_df[expense_df['รายการ'] == 'ค่าน้ำมัน/ไฟ']['หัก/จ่าย'].sum()
            other_cost = expense_df[expense_df['รายการ'] == 'ทั่วไป']['หัก/จ่าย'].sum()
            net_profit = total_income - fuel_cost - other_cost

            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 กำไรสุทธิ", f"{net_profit:,.0f} บ.")
            m2.metric("⛽ ค่าน้ำมัน/ไฟ", f"{fuel_cost:,.0f} บ.")
            m3.metric("🛣️ วิ่งไป (กม.)", f"{total_km:,.0f} กม.")
            
            if total_km > 0:
                income_km = total_income / total_km
                cost_km = fuel_cost / total_km
                m4.metric("📊 รายได้/กม.", f"{income_km:.1f} บ.", f"ต้นทุน {cost_km:.1f} บ.")
            else:
                m4.metric("📊 รายได้/กม.", "0.0", "ไม่มีระยะทาง")

            st.divider()
            
            # กราฟ
            c1, c2 = st.columns(2)
            with c1:
                if not income_df.empty:
                    plat_sum = income_df.groupby('แอป')['คงเหลือ/สุทธิ'].sum().reset_index()
                    fig = px.bar(plat_sum, x='แอป', y='คงเหลือ/สุทธิ', color='แอป', text_auto=True, title=f"รายได้แยกตามแอป ({time_filter})")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"ไม่พบรายได้ในช่วง: {time_filter}")

            with c2:
                if not income_df.empty:
                    income_df['Hour'] = pd.to_datetime(income_df['เวลา'], format='%H:%M').dt.hour
                    fig = px.histogram(income_df, x='Hour', y='คงเหลือ/สุทธิ', nbins=24, title=f"ช่วงเวลาทำเงิน ({time_filter})", color_discrete_sequence=['#FF4B4B'])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("ไม่พบข้อมูลช่วงเวลา")
        else:
            st.warning(f"ยังไม่มีข้อมูลสำหรับ: {time_filter}")
            
    else:
        st.info("ยังไม่มีข้อมูลในระบบ เริ่มบันทึกงานแรกได้เลย!")

# ==========================================
# TAB 3: ฐานข้อมูล
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    if not st.session_state.data.empty:
        edited_df = st.data_editor(st.session_state.data, num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกการแก้ไข", type="primary"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.success("บันทึกแล้ว")
