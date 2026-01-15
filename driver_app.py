import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ", page_icon="🚗", layout="wide")
SHEET_NAME = "Drivers"

# --- SMART NUMBER FORMATTER (ตามคำขอที่ 3) ---
def fmt_num(val):
    """
    จัดรูปแบบตัวเลข:
    - ใส่ลูกน้ำ (,)
    - ถ้าเป็นจำนวนเต็ม ให้ตัด .00 ทิ้ง
    - ถ้ามีทศนิยม ให้แสดงตามจริง (สูงสุด 2 ตำแหน่ง)
    """
    if val is None: return "0"
    if isinstance(val, (int, float)):
        # จัดรูปแบบเป็นทศนิยม 2 ตำแหน่งก่อน
        s = "{:,.2f}".format(val)
        # ลบเลข 0 ต่อท้าย และลบจุดถ้าไม่มีทศนิยมเหลือ
        return s.rstrip('0').rstrip('.') if '.' in s else s
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
        
        col_map = {
            'Date': 'วันที่', 'Time': 'เวลา', 'Platform': 'แอป',
            'Category': 'หมวดหมู่', 'SubCategory': 'รายการ',
            'Amount_Gross': 'ยอดเต็ม/หน้าแอป', 'Deduction': 'หัก/จ่าย',
            'Tip': 'ทิป', 'Net_Income': 'คงเหลือ/สุทธิ',
            'Distance_Km': 'ระยะทาง(กม.)', 'Note': 'หมายเหตุ',
            'Odometer': 'เลขไมล์', 'Payment_Method': 'ช่องทางรับเงิน',
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
        st.error(f"⚠️ ไม่พบชีทชื่อ '{SHEET_NAME}' หรือเชื่อมต่อไม่ได้: {e}")
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
    saved_rate = float(current_settings.get("ev_rate", 50.0))
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=saved_rate, step=5.0)
    
    st.divider()
    st.markdown("### 🎯 เป้าหมายรายวัน")
    saved_target = float(current_settings.get("target_income", 2000.0))
    new_target = st.number_input("ตั้งเป้ารายได้ (บาท)", value=saved_target, step=100.0)
    
    if new_ev_rate != saved_rate or new_target != saved_target:
        current_settings["ev_rate"] = new_ev_rate
        current_settings["target_income"] = new_target
        save_settings(current_settings)
        st.toast(f"บันทึกการตั้งค่าลง Cloud แล้ว! ☁️")
        st.rerun()

    st.divider()
    with st.expander("⚠️ พื้นที่อันตราย"):
        if st.checkbox("ยืนยันลบข้อมูล"):
            if st.button("ล้างข้อมูลทั้งหมด 🗑️", type="primary"):
                st.session_state.data = st.session_state.data.iloc[0:0] 
                save_data(st.session_state.data)
                st.success("ล้างข้อมูลเรียบร้อย")
                st.rerun()

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📊 วิเคราะห์ & ประวัติ", "🗂️ ฐานข้อมูล"])

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

    today = get_thai_date()
    df = st.session_state.data
    
    today_income = 0.0
    if not df.empty:
        today_df = df[(df['วันที่'] == today) & (df['หมวดหมู่'] == 'รายรับ')]
        today_income = today_df['คงเหลือ/สุทธิ'].sum()
    
    target = new_target
    progress = min(today_income / target, 1.0) if target > 0 else 0
    
    c_prog_1, c_prog_2 = st.columns([3, 1])
    with c_prog_1:
        st.progress(progress, text=f"🎯 เป้าหมาย: {fmt_num(progress*100)}%")
    with c_prog_2:
        st.caption(f"💰 {fmt_num(today_income)} / {fmt_num(target)}")

    st.divider()

    current_status = get_work_status()
    last_odom_val = get_last_odom()

    if "เริ่ม" in current_status:
        expander_label = f"🟢 สถานะ: วิ่งงานอยู่ (เริ่ม {fmt_num(last_odom_val)} กม.)"
        expander_icon = "🚕"
    else:
        expander_label = f"🔴 สถานะ: พักผ่อน (ล่าสุด {fmt_num(last_odom_val)} กม.)"
        expander_icon = "🏠"

    with st.expander(expander_label, expanded=False, icon=expander_icon):
        if "เริ่ม" in current_status:
            c_end_1, c_end_2 = st.columns([2, 1]) 
            with c_end_1:
                end_odom = st.number_input("เลขไมล์จบ", min_value=last_odom_val, value=None, placeholder="เลขไมล์ปัจจุบัน")
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
                start_odom = st.number_input("เลขไมล์เริ่ม", min_value=0.0, value=last_odom_val, step=1.0)
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

    st.markdown("### 📝 บันทึกรายการ")
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🚗 รับงาน", "⛽ เติมของ", "💳 เติมแอป", "🛠️ จ่ายอื่น"])
    
    with sub_tab1:
        with st.form(key="form_income", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: platform = st.selectbox("แอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
            with c2: pay_method = st.selectbox("การรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])

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
                    st.toast(f"บันทึก +{fmt_num(real_val)} บาท")
                    st.rerun()
                else: st.warning("ระบุยอดเงินด้วยครับ")

    with sub_tab2:
        with st.form(key="form_energy", clear_on_submit=True):
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            default_val = float(new_ev_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
            cost = st.number_input("จำนวนเงิน", min_value=0.0, value=default_val, placeholder="0")
            note = st.text_input("สถานที่ / หมายเหตุ")
            
            if st.form_submit_button("บันทึก", type="primary", use_container_width=True):
                if cost:
                    full_note = f"{e_type} - {note}" if note else e_type
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 
                        'รายการ': 'ค่าน้ำมัน/ไฟ', 
                        'ช่องทางรับเงิน': 'จ่ายสด', 
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 
                        'หมายเหตุ': full_note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

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
# TAB 2: วิเคราะห์ (เพิ่มกราฟประวัติ + ตารางความคุ้มค่า)
# ==========================================
with tab2:
    st.markdown("### 📊 วิเคราะห์ผลประกอบการ")
    
    # --- 1. Filter Section ---
    with st.expander("🔎 ตัวกรองข้อมูล", expanded=False):
        time_filter = st.selectbox("📅 ช่วงเวลา:", ["วันนี้", "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้", "ปีนี้", "ทั้งหมด"], key="sb_time_filter")
    
    df = st.session_state.data
    if not df.empty:
        today = get_thai_date()
        f_df = df.copy()
        f_df['วันที่_dt'] = pd.to_datetime(f_df['วันที่'])
        
        # Filter Logic
        if time_filter == "วันนี้": 
            f_df = f_df[f_df['วันที่'] == today]
        elif time_filter == "เมื่อวาน": 
            f_df = f_df[f_df['วันที่'] == today - datetime.timedelta(days=1)]
        elif time_filter == "สัปดาห์นี้":
            start = today - datetime.timedelta(days=today.weekday())
            f_df = f_df[(f_df['วันที่'] >= start)]
        elif time_filter == "เดือนนี้": 
            f_df = f_df[(f_df['วันที่_dt'].dt.month == today.month) & (f_df['วันที่_dt'].dt.year == today.year)]
        elif time_filter == "ปีนี้": 
            f_df = f_df[f_df['วันที่_dt'].dt.year == today.year]
        
        # --- CALCULATION ---
        inc_df = f_df[f_df['หมวดหมู่'] == 'รายรับ']
        exp_df = f_df[f_df['หมวดหมู่'] == 'รายจ่าย']
        
        total_inc = inc_df['คงเหลือ/สุทธิ'].sum()
        total_exp = exp_df['หัก/จ่าย'].sum()
        net_profit = total_inc - total_exp
        
        # Distance Logic
        dist = 0
        odom_df = f_df[f_df['เลขไมล์'] > 0]
        if not odom_df.empty:
            d_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
            dist = (d_odom['max'] - d_odom['min']).sum()

        # --- ส่วนที่ 1: ภาพรวมตัวเลข (Metrics) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 กำไรสุทธิ", f"{fmt_num(net_profit)} บ.")
        m2.metric("💸 รายรับรวม", f"{fmt_num(total_inc)} บ.")
        m3.metric("📉 รายจ่ายรวม", f"{fmt_num(total_exp)} บ.")
        m4.metric("🛣️ ระยะทาง", f"{fmt_num(dist)} กม.")
        
        st.divider()

        # --- ส่วนที่ 2 (ใหม่): ตารางความคุ้มค่าแอป (App Worthiness) ---
        st.subheader("🏆 ความคุ้มค่าแต่ละแอป (คำนวณ GP)")
        if not inc_df.empty:
            # Group by App
            app_stats = inc_df.groupby('แอป').agg({
                'ยอดเต็ม/หน้าแอป': 'sum',
                'คงเหลือ/สุทธิ': 'sum',
                'ทิป': 'sum',
                'วันที่': 'count'
            }).reset_index()
            app_stats.rename(columns={'วันที่': 'จำนวนงาน', 'ยอดเต็ม/หน้าแอป': 'ยอดหน้าแอป', 'คงเหลือ/สุทธิ': 'รายรับจริง'}, inplace=True)
            
            # Calculate GP
            # สูตร: รายรับจริง (Net) = ยอดหน้าแอป - GP + ทิป
            # ดังนั้น GP (บาท) = ยอดหน้าแอป - (รายรับจริง - ทิป)
            app_stats['GP_amount'] = app_stats['ยอดหน้าแอป'] - (app_stats['รายรับจริง'] - app_stats['ทิป'])
            
            # ป้องกันการหารด้วยศูนย์
            app_stats['GP_percent'] = app_stats.apply(
                lambda x: (x['GP_amount'] / x['ยอดหน้าแอป'] * 100) if x['ยอดหน้าแอป'] > 0 else 0, axis=1
            )
            
            # Format Data for Display
            app_stats_show = app_stats.copy()
            app_stats_show['% GP/หัก'] = app_stats_show['GP_percent'].apply(lambda x: f"{fmt_num(x)}%")
            app_stats_show['ยอดหน้าแอป'] = app_stats_show['ยอดหน้าแอป'].apply(fmt_num)
            app_stats_show['รายรับจริง'] = app_stats_show['รายรับจริง'].apply(fmt_num)
            app_stats_show['GP (บาท)'] = app_stats_show['GP_amount'].apply(fmt_num)
            
            # Show Table
            st.dataframe(
                app_stats_show[['แอป', 'จำนวนงาน', 'ยอดหน้าแอป', 'รายรับจริง', 'GP (บาท)', '% GP/หัก']],
                use_container_width=True,
                hide_index=True
            )
            st.caption("* สูตรคำนวณ: GP = ยอดหน้าแอป - (รายรับจริง - ทิป) | หากรับงานนอกหรือรับเงินสดเต็มจำนวน GP จะเป็น 0%")
        else:
            st.info("ยังไม่มีข้อมูลรายรับ")

        st.divider()

        # --- ส่วนที่ 3 (ใหม่): กราฟประวัติ (Historical Trends) ---
        st.subheader("📈 กราฟประวัติ (แนวโน้ม)")
        
        # Prepare Data for Graph
        if not f_df.empty:
            daily_inc = inc_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum()
            daily_exp = exp_df.groupby('วันที่')['หัก/จ่าย'].sum()
            
            # Merge Income & Expense
            daily_stats = pd.DataFrame({'รายรับ': daily_inc, 'รายจ่าย': daily_exp}).fillna(0)
            daily_stats['กำไร'] = daily_stats['รายรับ'] - daily_stats['รายจ่าย']
            daily_stats = daily_stats.reset_index()
            
            # Plot
            fig_hist = px.line(daily_stats, x='วันที่', y=['รายรับ', 'รายจ่าย', 'กำไร'], 
                               title="เส้นทางรายรับ-รายจ่าย", markers=True,
                               color_discrete_map={'รายรับ': '#00B14F', 'รายจ่าย': '#E74C3C', 'กำไร': '#2E86C1'})
            fig_hist.update_layout(hovermode="x unified")
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Additional Graph: Income by App over time
            if not inc_df.empty:
                daily_app = inc_df.groupby(['วันที่', 'แอป'])['คงเหลือ/สุทธิ'].sum().reset_index()
                fig_app_trend = px.bar(daily_app, x='วันที่', y='คงเหลือ/สุทธิ', color='แอป', 
                                       title="สัดส่วนรายได้แยกตามแอป (รายวัน)")
                st.plotly_chart(fig_app_trend, use_container_width=True)

        else:
            st.info("ไม่มีข้อมูลในช่วงเวลานี้")
            
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")

# ==========================================
# TAB 3: ฐานข้อมูล
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        apps = st.session_state.data['แอป'].unique() if not st.session_state.data.empty else []
        f_app = c1.multiselect("แอป", apps)
        f_date = c3.selectbox("วันที่", ["ทั้งหมด", "วันนี้", "เดือนนี้"])

    df_show = st.session_state.data.copy()
    if not df_show.empty:
        if f_app: df_show = df_show[df_show['แอป'].isin(f_app)]
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
                "คงเหลือ/สุทธิ": st.column_config.NumberColumn(format="%.0f"), # พยายามลดทศนิยมใน Table
                "ยอดเต็ม/หน้าแอป": st.column_config.NumberColumn(format="%.0f"),
            }
        )
        
        if st.button("💾 บันทึกการเปลี่ยนแปลง", type="primary"):
            try:
                if len(df_show) != len(st.session_state.data):
                     st.warning("⚠️ กำลังกรองข้อมูลอยู่ ระบบบันทึกเฉพาะที่เห็นเท่านั้น")
                     st.session_state.data.update(edited_df)
                else:
                     st.session_state.data = edited_df
                
                save_data(st.session_state.data)
                st.success("บันทึกสำเร็จ!")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    else:
        st.info("ไม่มีข้อมูล")
