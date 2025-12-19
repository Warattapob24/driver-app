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
        
        # เพิ่มคอลัมน์ถ้ายังไม่มี (เพื่อให้ระบบเดิมทำงานต่อได้โดยไม่พัง)
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
# TAB 1: บันทึกงาน (กลับมาใช้รูปแบบเดิมเป๊ะๆ แต่เพิ่มช่องรับเงิน)
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
                # แถว 1: แอป + ช่องทางรับเงิน (ตามที่คุณขอ)
                c_app, c_pay = st.columns(2)
                with c_app:
                    platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                with c_pay:
                    # ✅ เพิ่มกลับมาให้แล้วครับ
                    pay_method = st.selectbox("ช่องทางรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])

                # แถว 2: ราคา
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
                        
                        # คำนวณเงินสดเข้าตัว (เพื่อเอาไปสรุป)
                        cash_in_hand = real_val if pay_method == "💵 เงินสด/โอน" else 0.0
                        
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 
                            'ช่องทางรับเงิน': pay_method, # ✅ บันทึกลงคอลัมน์นี้ตรงๆ ไม่อ้อม
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': 0, 'ทิป': tip, 
                            'คงเหลือ/สุทธิ': total_income, 
                            'เงินสดเข้าตัว': cash_in_hand, 
                            'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        
                        st.toast(f"บันทึกรายได้ {total_income:.0f} บาท ({pay_method})")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกยอดเงิน")

        # --- 2. เติมเครดิต (รายจ่าย) ---
        elif entry_type == "💳 เติมเครดิตแอป":
            st.markdown("#### 💳 เติมเงินเข้าแอป")
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
                            'เงินสดเข้าตัว': -cost_val, # เงินสดลดลง
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
# TAB 2: สรุปผล (ปรับกราฟตามที่ขอ + เพิ่มสรุปเงินสด)
# ==========================================
with tab2:
    st.markdown("### 📊 แดชบอร์ดสรุปผลละเอียด")
    
    # --- Filter ---
    with st.container(border=True):
        c_filter, c_date = st.columns([1, 2])
        with c_filter:
            time_filter = st.selectbox("📅 เลือกช่วงเวลา:", ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "ปีนี้", "กำหนดเอง"])
        with c_date:
            custom_start, custom_end = None, None
            if time_filter == "กำหนดเอง":
                dr = st.date_input("เลือกวันที่", value=(get_thai_date(), get_thai_date()))
                if len(dr) == 2: custom_start, custom_end = dr

    # --- Data Prep ---
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        filter_df = df.copy()
        
        # Filter Logic
        if time_filter == "วันนี้": filter_df = df[df['วันที่'] == today]
        elif time_filter == "เมื่อวาน": filter_df = df[df['วันที่'] == today - datetime.timedelta(days=1)]
        elif time_filter == "สัปดาห์นี้":
            start_week = today - datetime.timedelta(days=today.weekday())
            filter_df = df[df['วันที่'] >= start_week]
        elif time_filter == "เดือนนี้": filter_df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        elif time_filter == "ปีนี้": filter_df = df[pd.to_datetime(df['วันที่']).dt.year == today.year]
        elif time_filter == "กำหนดเอง" and custom_start: filter_df = df[(df['วันที่'] >= custom_start) & (df['วันที่'] <= custom_end)]
        
        if filter_df.empty:
            st.warning("ไม่พบข้อมูลในช่วงเวลานี้")
        else:
            # คำนวณยอด
            inc_df = filter_df[filter_df['หมวดหมู่'] == 'รายรับ']
            exp_df = filter_df[filter_df['หมวดหมู่'] == 'รายจ่าย']
            
            total_rev = inc_df['คงเหลือ/สุทธิ'].sum()
            total_exp = exp_df['หัก/จ่าย'].sum()
            net_profit = total_rev - total_exp
            
            # ยอดเงินสดในมือ (สำคัญมากสำหรับคนขับ)
            cash_in_hand = filter_df['เงินสดเข้าตัว'].sum()

            # แสดง Metric แบบใหม่
            st.markdown("#### 🏆 สถานะการเงิน")
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric("💰 กำไรสุทธิ", f"{net_profit:,.0f} บ.", delta=f"รายรับ {total_rev:,.0f}")
            with k2: st.metric("💵 เงินสดติดตัว", f"{cash_in_hand:,.0f} บ.", help="เงินสดรับ - จ่ายออก (ไม่รวมเงินในแอป)")
            with k3: st.metric("💸 รายจ่ายรวม", f"{total_exp:,.0f} บ.")
            
            # คำนวณระยะทาง & เวลา
            total_km = 0
            odom_df = filter_df[filter_df['เลขไมล์'] > 0]
            if not odom_df.empty:
                daily = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
                total_km = (daily['max'] - daily['min']).sum()
            else: total_km = filter_df['ระยะทาง(กม.)'].sum()
            
            with k4: st.metric("🛣️ วิ่งงาน", f"{total_km:,.0f} กม.")

            st.divider()

            # --- กราฟ 1: แท่งเปรียบเทียบ รายรับ vs รายจ่าย (แบบไม่มุดดิน) ---
            st.subheader("📈 เปรียบเทียบ: รายรับ (เขียว) vs รายจ่าย (แดง)")
            if not inc_df.empty or not exp_df.empty:
                d_inc = inc_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
                d_exp = exp_df.groupby('วันที่')['หัก/จ่าย'].sum().reset_index()
                d_chart = pd.merge(d_inc, d_exp, on='วันที่', how='outer').fillna(0)
                d_chart.columns = ['Date', 'Income', 'Expense']
                
                # กราฟแท่งคู่ (Grouped Bar)
                fig_bar = px.bar(d_chart, x='Date', y=['Income', 'Expense'], barmode='group',
                                 color_discrete_map={'Income': '#2ECC71', 'Expense': '#E74C3C'},
                                 labels={'value': 'บาท', 'variable': 'ประเภท'})
                # เปลี่ยนชื่อ Legend
                new_names = {'Income': 'รายรับรวม', 'Expense': 'รายจ่ายรวม'}
                fig_bar.for_each_trace(lambda t: t.update(name = new_names[t.name]))
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- กราฟ 2: Heatmap (ช่วงเวลาทำเงิน) ---
            st.subheader("🔥 ช่วงเวลาทำเงิน (Heatmap)")
            if not inc_df.empty:
                hm = inc_df.copy()
                hm['Day'] = pd.to_datetime(hm['วันที่']).dt.day_name()
                hm['Hour'] = pd.to_datetime(hm['เวลา'], format='%H:%M').dt.hour
                day_map = {'Monday': '1.จันทร์', 'Tuesday': '2.อังคาร', 'Wednesday': '3.พุธ', 'Thursday': '4.พฤหัส', 'Friday': '5.ศุกร์', 'Saturday': '6.เสาร์', 'Sunday': '7.อาทิตย์'}
                hm['DayThai'] = hm['Day'].map(day_map)
                
                piv = hm.pivot_table(index='DayThai', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum').fillna(0)
                if not piv.empty:
                    fig_hm = px.imshow(piv, color_continuous_scale='RdBu_r', aspect="auto", labels=dict(x="ชั่วโมง", y="วัน", color="บาท"))
                    st.plotly_chart(fig_hm, use_container_width=True)
                else: st.info("ข้อมูลไม่พอสร้าง Heatmap")

            # --- กราฟ 3: วงกลม (สัดส่วน) ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🎨 รายได้แยกแอป")
                if not inc_df.empty:
                    st.plotly_chart(px.pie(inc_df, values='คงเหลือ/สุทธิ', names='แอป', hole=0.4), use_container_width=True)
            with c2:
                st.subheader("💸 รายจ่ายแยกประเภท")
                if not exp_df.empty:
                    st.plotly_chart(px.pie(exp_df, values='หัก/จ่าย', names='รายการ', hole=0.4), use_container_width=True)

    else:
        st.info("ยังไม่มีข้อมูลในระบบ")

# ==========================================
# TAB 3: ฐานข้อมูล (เหมือนเดิม)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    view_df = st.session_state.data.copy()
    if not view_df.empty:
        # แสดงคอลัมน์สำคัญรวมถึงช่องทางรับเงิน
        cols = ['วันที่', 'เวลา', 'แอป', 'รายการ', 'ช่องทางรับเงิน', 'ยอดเต็ม/หน้าแอป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'หมายเหตุ']
        # กรองเอาเฉพาะคอลัมน์ที่มีอยู่จริง
        valid_cols = [c for c in cols if c in view_df.columns]
        
        edited = st.data_editor(view_df[valid_cols].sort_values(by=["วันที่", "เวลา"], ascending=False), num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกการแก้ไข", type="primary"):
            st.session_state.data.update(edited)
            save_data(st.session_state.data)
            st.success("บันทึกแล้ว")
            st.rerun()
    else:
        st.info("ไม่มีข้อมูล")
