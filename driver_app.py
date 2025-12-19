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

# --- 2. SETTINGS MANAGEMENT ---
def load_settings():
    default_settings = {"maxim_rate": 15, "ev_rate": 40.0}
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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"เวลา: {get_thai_time().strftime('%H:%M')}")
    
    current_settings = load_settings()
    new_maxim_rate = st.slider("Maxim หักคอม (%)", 0, 30, current_settings.get("maxim_rate", 15))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=float(current_settings.get("ev_rate", 40.0)), step=5.0)
    
    if new_maxim_rate != current_settings.get("maxim_rate") or new_ev_rate != current_settings.get("ev_rate"):
        updated_settings = {"maxim_rate": new_maxim_rate, "ev_rate": new_ev_rate}
        save_settings(updated_settings)
        st.toast("บันทึกการตั้งค่าแล้ว!")
    
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
                    real_receive = st.number_input("เงินที่รับจริงจากลูกค้า (รวมทิป)", min_value=0.0, step=10.0, value=None, placeholder="เท่าหน้าแอป")
                
                note = st.text_input("หมายเหตุ", placeholder="บันทึกช่วยจำ")
                submitted = st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True)
                
                if submitted:
                    price_val = app_price if app_price is not None else 0.0
                    real_val = real_receive if real_receive is not None else 0.0
                    
                    if price_val > 0 or real_val > 0:
                        # ถ้าไม่กรอกเงินรับจริง ให้ถือว่าเท่ากับหน้าแอป
                        if real_val == 0: real_val = price_val 
                        
                        deduction = 0
                        # คำนวณทิป = เงินรับจริง - ราคาหน้าแอป
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

        # --- 4. เติมเครดิต/อื่นๆ ---
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

# ==========================================
# TAB 2: DASHBOARD PRO (ปรับโฉมใหม่)
# ==========================================
with tab2:
    st.markdown("### 🚀 Dashboard วิเคราะห์รายได้")
    
    # --- Filter Section (Design ใหม่) ---
    with st.container(border=True):
        c_filter, c_date = st.columns([1, 2])
        with c_filter:
            time_filter = st.selectbox(
                "📅 เลือกช่วงเวลา:",
                ["สัปดาห์นี้", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "ทั้งหมด", "กำหนดเอง"]
            )
        with c_date:
            custom_start, custom_end = None, None
            if time_filter == "กำหนดเอง":
                dr = st.date_input("ระบุวันที่", value=(get_thai_date(), get_thai_date()))
                if len(dr) == 2: custom_start, custom_end = dr
            else:
                st.info(f"กำลังแสดงข้อมูล: {time_filter}")

    # --- Data Preparation ---
    df = st.session_state.data
    if not df.empty:
        # Filter Logic
        today = get_thai_date()
        filter_df = df.copy()
        
        if time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday())
            filter_df = df[df['วันที่'] >= start_week]
        elif time_filter == "เดือนนี้":
            filter_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "เดือนที่แล้ว":
            first = today.replace(day=1); last_prev = first - datetime.timedelta(days=1); start_prev = last_prev.replace(day=1)
            filter_df = df[(df['วันที่'] >= start_prev) & (df['วันที่'] <= last_prev)]
        elif time_filter == "ปีนี้":
            filter_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
        elif time_filter == "กำหนดเอง" and custom_start:
            filter_df = df[(df['วันที่'] >= custom_start) & (df['วันที่'] <= custom_end)]
        
        if filter_df.empty:
            st.warning("ไม่มีข้อมูลในช่วงเวลานี้")
        else:
            # --- CALCULATIONS ---
            # 1. Financials
            income_df = filter_df[filter_df['หมวดหมู่'] == 'รายรับ']
            expense_df = filter_df[filter_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_rev = income_df['คงเหลือ/สุทธิ'].sum()
            total_exp = expense_df['หัก/จ่าย'].sum()
            net_profit = total_rev - total_exp
            
            # 2. Distance & Fuel
            odom_rows = filter_df[filter_df['เลขไมล์'] > 0]
            total_km = 0
            if not odom_rows.empty:
                 # Group by date to find daily range
                daily_odom = odom_rows.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                total_km = (daily_odom['max'] - daily_odom['min']).sum()
            
            # Fallback if no odometer recorded but manual distance exists (optional logic)
            if total_km == 0: total_km = filter_df['ระยะทาง(กม.)'].sum()

            fuel_cost = expense_df[expense_df['รายการ'] == 'ค่าน้ำมัน/ไฟ']['หัก/จ่าย'].sum()
            cost_per_km = fuel_cost / total_km if total_km > 0 else 0

            # 3. Time (Approx)
            # Simple logic: Count distinct days * avg hours per day (or exact calculation if possible)
            # Using precise calculation from previous version
            shift_df = filter_df[filter_df['หมวดหมู่'] == 'กะงาน']
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
            
            hourly_rate = total_rev / total_hours if total_hours > 0 else 0

            # --- TOP METRICS (KPIs) ---
            st.markdown("#### 🏆 ภาพรวมผลประกอบการ")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            with kpi1:
                st.metric("💰 กำไรสุทธิ", f"{net_profit:,.0f} บ.", delta=f"รายรับ {total_rev:,.0f}")
            with kpi2:
                st.metric("💸 ค่าใช้จ่ายรวม", f"{total_exp:,.0f} บ.", delta=f"-{fuel_cost:,.0f} (เชื้อเพลิง)", delta_color="inverse")
            with kpi3:
                st.metric("🛣️ ต้นทุนต่อ กม.", f"{cost_per_km:.2f} บ./กม.", help="คำนวณจาก ค่าน้ำมันหารด้วยระยะทางรวม")
            with kpi4:
                st.metric("⏱️ รายได้ต่อ ชม.", f"{hourly_rate:.0f} บ./ชม.", help="รายรับหารด้วยชั่วโมงทำงานรวม")

            st.divider()

            # --- ROW 1: TREND & COMPOSITION ---
            r1c1, r1c2 = st.columns([2, 1])
            with r1c1:
                st.subheader("📈 แนวโน้มรายได้ (Daily Trend)")
                if not income_df.empty:
                    daily_inc = income_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
                    daily_exp = expense_df.groupby('วันที่')['หัก/จ่าย'].sum().reset_index()
                    
                    # Merge for chart
                    daily_chart = pd.merge(daily_inc, daily_exp, on='วันที่', how='outer').fillna(0)
                    daily_chart.columns = ['Date', 'Income', 'Expense']
                    daily_chart['Profit'] = daily_chart['Income'] - daily_chart['Expense']
                    
                    # Area Chart showing Net Profit vs Expense
                    fig_trend = px.bar(
                        daily_chart, x='Date', y=['Profit', 'Expense'], 
                        title="รายได้สุทธิ vs ค่าใช้จ่าย (รายวัน)",
                        color_discrete_map={'Profit': '#00CC96', 'Expense': '#EF553B'},
                        labels={'value': 'บาท', 'variable': 'ประเภท'}
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("ยังไม่มีข้อมูลรายรับรายวัน")

            with r1c2:
                st.subheader("🍰 ส่วนแบ่งแอป (Top Apps)")
                if not income_df.empty:
                    app_sum = income_df.groupby('แอป')['คงเหลือ/สุทธิ'].sum().reset_index()
                    fig_pie = px.donut(
                        app_sum, values='คงเหลือ/สุทธิ', names='แอป', 
                        hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    fig_pie.update_layout(showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.caption("ไม่มีข้อมูล")

            # --- ROW 2: STRATEGY (HEATMAP) ---
            st.subheader("🔥 Strategic Heatmap: ขับช่วงไหนดีที่สุด?")
            if not income_df.empty:
                # Prepare Heatmap Data
                hm_df = income_df.copy()
                hm_df['Day'] = pd.to_datetime(hm_df['วันที่']).dt.day_name()
                hm_df['Hour'] = pd.to_datetime(hm_df['เวลา'], format='%H:%M').dt.hour
                
                # Map English days to Thai for display
                day_map = {
                    'Monday': '1.จันทร์', 'Tuesday': '2.อังคาร', 'Wednesday': '3.พุธ',
                    'Thursday': '4.พฤหัส', 'Friday': '5.ศุกร์', 'Saturday': '6.เสาร์', 'Sunday': '7.อาทิตย์'
                }
                hm_df['DayThai'] = hm_df['Day'].map(day_map)
                
                # Pivot Table
                pivot_hm = hm_df.pivot_table(index='DayThai', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum').fillna(0)
                
                # Heatmap Chart
                fig_hm = px.imshow(
                    pivot_hm, 
                    labels=dict(x="ชั่วโมง", y="วัน", color="รายได้"),
                    x=pivot_hm.columns, y=pivot_hm.index,
                    color_continuous_scale='RdBu_r', aspect="auto"
                )
                st.plotly_chart(fig_hm, use_container_width=True)
                st.caption("💡 **สีน้ำเงินเข้ม** = ช่วงเวลาที่ทำเงินได้สูงสุด | **สีแดง** = รายได้น้อย")
            else:
                st.info("ต้องการข้อมูลรายรับมากกว่านี้เพื่อสร้าง Heatmap")

    else:
        st.info("📝 ยังไม่มีข้อมูลในระบบ กรุณาบันทึกงานแรกที่ Tab 1")

# ==========================================
# TAB 3: ฐานข้อมูล (เพิ่มตัวกรองกลับมาให้ตามที่เคยขอ)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    
    # เพิ่มตัวกรอง (Filters) ไว้ด้านบน
    with st.container(border=True):
        st.write("🔍 **ตัวกรองค้นหา**")
        fc1, fc2 = st.columns(2)
        with fc1: 
            f_app = st.multiselect("เลือกแอป:", options=st.session_state.data['แอป'].unique(), default=[])
        with fc2:
             f_month = st.checkbox("ดูเฉพาะเดือนนี้", value=False)

    view_df = st.session_state.data.copy()
    if f_app: view_df = view_df[view_df['แอป'].isin(f_app)]
    if f_month: 
        today = get_thai_date()
        view_df = view_df[(pd.to_datetime(view_df['วันที่']).dt.month == today.month) & (pd.to_datetime(view_df['วันที่']).dt.year == today.year)]

    st.caption(f"พบข้อมูล: {len(view_df)} รายการ")
    if not view_df.empty:
        edited = st.data_editor(view_df.sort_values(by=["วันที่", "เวลา"], ascending=False), num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกการแก้ไข", type="primary"):
            # Update กลับไปที่ Main DF (Logic ง่ายๆ: ทับของเก่าด้วย Index)
            st.session_state.data.update(edited)
            save_data(st.session_state.data)
            st.success("บันทึกแล้ว")
            st.rerun()
    else:
        st.info("ไม่พบข้อมูลตามเงื่อนไข")

