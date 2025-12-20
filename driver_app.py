import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ (Pro)", page_icon="🚗", layout="wide")

# --- TIMEZONE ---
def get_thai_time():
    tz_thai = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz_thai)

def get_thai_date():
    return get_thai_time().date()

# --- 2. GOOGLE SHEETS CONNECTION ---
# ฟังก์ชันโหลดและบันทึกข้อมูลผ่าน Google Sheets
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # อ่านข้อมูล (ttl=0 คือไม่แคช อ่านใหม่ทุกครั้งที่โหลด)
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        # คลีนข้อมูลให้ถูกต้อง
        required_cols = [
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ]
        
        # ถ้าไฟล์ว่าง ให้สร้าง Header
        if df.empty or len(df.columns) < len(required_cols):
            return pd.DataFrame(columns=required_cols)
        
        # แปลงข้อมูลตัวเลขและวันที่
        num_cols = ['ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 'เงินสดเข้าตัว', 'เลขไมล์']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        df['วันที่'] = pd.to_datetime(df['วันที่']).dt.date
        return df
        
    except Exception as e:
        st.error(f"เชื่อมต่อ Google Sheets ไม่สำเร็จ: {e}")
        # กรณีฉุกเฉิน สร้าง Dataframe เปล่า
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

def save_to_gsheets(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # แปลงวันที่กลับเป็น String ก่อนบันทึก เพื่อป้องกัน Error ใน Sheets
        df_save = df.copy()
        df_save['วันที่'] = df_save['วันที่'].astype(str)
        conn.update(worksheet="Sheet1", data=df_save)
    except Exception as e:
        st.error(f"บันทึกไม่สำเร็จ: {e}")

# โหลดข้อมูลเข้า Session
if 'data' not in st.session_state:
    st.session_state.data = get_data()

# --- 3. SETTINGS (เก็บ Local เหมือนเดิม หรือจะเก็บใน Sheets อีกหน้าก็ได้) ---
# เพื่อความง่าย ส่วนนี้เก็บใน Session ชั่วคราว หรือใช้ไฟล์ JSON เดิมได้
if 'ev_rate' not in st.session_state: st.session_state.ev_rate = 40.0

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.caption(f"Update ล่าสุด: {get_thai_time().strftime('%H:%M:%S')}")
    
    # ปุ่มรีเฟรชข้อมูลจาก Sheets
    if st.button("🔄 ดึงข้อมูลล่าสุดจาก Cloud"):
        st.session_state.data = get_data()
        st.rerun()

    st.divider()
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=st.session_state.ev_rate, step=5.0)
    st.session_state.ev_rate = new_ev_rate
    
    st.info("💡 ข้อมูลจะถูกบันทึกลง Google Sheets อัตโนมัติ")

# --- 5. MAIN APP ---
st.title("🚗 Driver Income Pro 🚀")
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน", "📈 วิเคราะห์ผล (Pro)", "🗂️ ฐานข้อมูล"])

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
        # (Logic ส่วนบันทึกเหมือนเดิมทุกประการ แต่เรียก save_to_gsheets แทน)
        
        # ... [CODE ส่วนฟอร์มรับงาน เหมือนเดิมเป๊ะ ตัดมาใส่ได้เลย] ...
        # เพื่อไม่ให้โค้ดยาวเกินไป ผมจะใส่ Logic หลักให้ดูว่าเปลี่ยนตรง save ครับ
        
        # ตัวอย่าง 1: รับงาน
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            with st.form(key="form_income", clear_on_submit=True):
                c_app, c_pay = st.columns(2)
                with c_app: platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                with c_pay: pay_method = st.selectbox("ช่องทางรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])
                c1, c2 = st.columns(2)
                with c1: app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0, value=None)
                with c2: real_receive = st.number_input("เงินที่รับจริง (รวมทิป)", min_value=0.0, step=10.0, value=None)
                note = st.text_input("หมายเหตุ")
                if st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True):
                    price_val = app_price if app_price else 0.0
                    real_val = real_receive if real_receive else 0.0
                    if price_val > 0 or real_val > 0:
                        if real_val == 0: real_val = price_val
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method,
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': 0, 'ทิป': max(0, real_val - price_val), 
                            'คงเหลือ/สุทธิ': real_val, 'เงินสดเข้าตัว': real_val if pay_method == "💵 เงินสด/โอน" else 0.0, 
                            'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_to_gsheets(st.session_state.data) # <--- เปลี่ยนตรงนี้
                        st.toast("บันทึกเรียบร้อย!"); st.rerun()

        # ตัวอย่าง 2: เติมน้ำมัน/ไฟ
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            with st.form(key="form_energy", clear_on_submit=True):
                e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
                default_val = st.session_state.ev_rate if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
                cost = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, value=default_val)
                note = st.text_input("สถานที่")
                if st.form_submit_button("บันทึกค่าใช้จ่าย 💾", type="primary", use_container_width=True):
                    if cost and cost > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost,
                            'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_to_gsheets(st.session_state.data) # <--- เปลี่ยนตรงนี้
                        st.toast("บันทึกเรียบร้อย!"); st.rerun()

        # ... (สำหรับปุ่มอื่นๆ ก็ทำเหมือนกันคือเปลี่ยน save_data เป็น save_to_gsheets) ...
        # เพื่อประหยัดพื้นที่ ผมละไว้ในฐานที่เข้าใจนะครับ (Logic เติมเครดิต, ไมล์, จ่ายอื่นๆ เหมือนเดิมครับ)
        elif entry_type == "💳 เติมเครดิตแอป":
             st.markdown("#### 💳 เติมเงินเข้าแอป")
             with st.form(key="form_topup", clear_on_submit=True):
                sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
                cost = st.number_input("จำนวนเงิน", min_value=0.0)
                if st.form_submit_button("บันทึกรายจ่าย 💾", type="primary", use_container_width=True):
                    if cost and cost > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost,
                            'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_to_gsheets(st.session_state.data); st.rerun()

        elif entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            with st.form(key="form_odom", clear_on_submit=True):
                shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
                odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0, step=1.0)
                if st.form_submit_button("บันทึกเลขไมล์ 💾", type="primary", use_container_width=True):
                    if odometer and odometer > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': shift_type, 'ช่องทางรับเงิน': '-',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                            'เลขไมล์': odometer, 'หมายเหตุ': f"เลขไมล์ {shift_type}"
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_to_gsheets(st.session_state.data); st.rerun()

        elif entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### 🛠️ จ่ายทั่วไป")
            with st.form(key="form_other", clear_on_submit=True):
                sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
                cost = st.number_input("จำนวนเงิน", min_value=0.0)
                if st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True):
                    if cost and cost > 0:
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด',
                            'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost,
                            'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_to_gsheets(st.session_state.data); st.rerun()

# ==========================================
# TAB 2: กราฟขั้นเทพ (New & Improved)
# ==========================================
with tab2:
    st.markdown("### 📈 Dashboard วิเคราะห์ผลงาน")
    
    # --- Filter ---
    period = st.selectbox("📅 เลือกมุมมอง", ["7 วันล่าสุด", "เดือนนี้", "เดือนที่แล้ว", "ปีนี้", "ทั้งหมด"])
    df = st.session_state.data.copy()
    
    if not df.empty:
        today = get_thai_date()
        df['วันที่'] = pd.to_datetime(df['วันที่']).dt.date # Ensure date type
        
        if period == "7 วันล่าสุด":
            start_date = today - datetime.timedelta(days=7)
            df = df[df['วันที่'] >= start_date]
        elif period == "เดือนนี้":
            df = df[(pd.to_datetime(df['วันที่']).dt.month == today.month) & (pd.to_datetime(df['วันที่']).dt.year == today.year)]
        # ... (Logic filter อื่นๆ ละไว้เพื่อให้โค้ดกระชับ ใช้แบบเดิมได้เลย) ...

        # --- PREPARE DATA ---
        income_df = df[df['หมวดหมู่'] == 'รายรับ']
        expense_df = df[df['หมวดหมู่'] == 'รายจ่าย']
        
        total_income = income_df['คงเหลือ/สุทธิ'].sum()
        total_expense = expense_df['หัก/จ่าย'].sum()
        net_profit = total_income - total_expense
        
        # คำนวณระยะทางรวม (Logic เดิม)
        odom_df = df[df['เลขไมล์'] > 0]
        total_km = 0
        if not odom_df.empty:
             daily_odom = odom_df.groupby('วันที่')['เลขไมล์'].agg(['min', 'max'])
             total_km = (daily_odom['max'] - daily_odom['min']).sum()

        # --- 1. Top Metrics (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 กำไรสุทธิ", f"{net_profit:,.0f} บ.", delta=f"รายรับ {total_income:,.0f}")
        col2.metric("💸 รายจ่ายรวม", f"{total_expense:,.0f} บ.")
        col3.metric("🛣️ ระยะทางวิ่ง", f"{total_km:,.0f} กม.")
        if total_km > 0:
            col4.metric("⚡ กำไร/กม.", f"{net_profit/total_km:.2f} บ./กม.", help="ยิ่งเยอะยิ่งคุ้มค่าเหนื่อย")
        else:
            col4.metric("⚡ กำไร/กม.", "0.00")

        st.divider()

        # --- 2. Advanced Graphs ---
        
        # COLOR PALETTE
        APP_COLORS = {
            "Grab": "#00B14F", "Line Man": "#06C755", "Bolt": "#34D186", 
            "Maxim": "#FFD600", "Robinhood": "#9D2398", "Win": "#FF6B00", 
            "งานนอก": "#7F8C8D", "ระบบ": "#95A5A6"
        }

        # ROW 1: Trend & Composition
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("##### 📅 แนวโน้มรายได้ (Daily Trend)")
            daily_inc = income_df.groupby('วันที่')['คงเหลือ/สุทธิ'].sum().reset_index()
            if not daily_inc.empty:
                fig_trend = px.area(
                    daily_inc, x='วันที่', y='คงเหลือ/สุทธิ', 
                    title="รายได้รายวัน (Area Chart)", markers=True,
                    color_discrete_sequence=['#4CAF50']
                )
                # เพิ่มเส้นค่าเฉลี่ย
                avg_inc = daily_inc['คงเหลือ/สุทธิ'].mean()
                fig_trend.add_hline(y=avg_inc, line_dash="dot", annotation_text=f"เฉลี่ย {avg_inc:.0f}", annotation_position="top left")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายรับในช่วงนี้")

        with g2:
            st.markdown("##### 🍩 สัดส่วนรายได้ (Donut Chart)")
            if not income_df.empty:
                fig_donut = px.pie(
                    income_df, values='คงเหลือ/สุทธิ', names='แอป', 
                    color='แอป', color_discrete_map=APP_COLORS,
                    hole=0.4
                )
                fig_donut.update_layout(showlegend=False)
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True)

        # ROW 2: Deep Dive (Sunburst & Heatmap)
        g3, g4 = st.columns(2)
        
        with g3:
            st.markdown("##### ☀️ เจาะลึกแหล่งรายได้ (Sunburst)")
            # กราฟนี้เจ๋งมาก: ดูว่า แอปไหน -> จ่ายแบบไหน -> ได้เงินเท่าไหร่
            if not income_df.empty:
                fig_sun = px.sunburst(
                    income_df, path=['แอป', 'ช่องทางรับเงิน'], values='คงเหลือ/สุทธิ',
                    color='แอป', color_discrete_map=APP_COLORS
                )
                st.plotly_chart(fig_sun, use_container_width=True)

        with g4:
            st.markdown("##### ⏱️ ช่วงเวลาทำเงิน (Heatmap)")
            # วิเคราะห์ว่าชั่วโมงไหนงานเข้าเยอะสุด
            if not income_df.empty:
                income_df['Hour'] = pd.to_datetime(income_df['เวลา'], format='%H:%M').dt.hour
                # สร้างตาราง Pivot: แกน X=ชั่วโมง, แกน Y=แอป, ค่า=จำนวนเงิน
                heatmap_data = income_df.pivot_table(index='แอป', columns='Hour', values='คงเหลือ/สุทธิ', aggfunc='sum', fill_value=0)
                
                fig_heat = px.imshow(
                    heatmap_data, 
                    labels=dict(x="นาฬิกา (ชม.)", y="แอป", color="บาท"),
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    aspect="auto", color_continuous_scale="Greens"
                )
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("ต้องมีข้อมูลเวลาเพื่อแสดงกราฟนี้")
                
    else:
        st.info("📭 ยังไม่มีข้อมูลในระบบ เริ่มบันทึกงานแรกได้เลย!")

# ==========================================
# TAB 3: ฐานข้อมูล (อัปเดตให้รองรับ Sheets)
# ==========================================
with tab3:
    st.subheader("🗂️ ฐานข้อมูล (Google Sheets Connected 🟢)")
    # (Logic การ Filter เหมือนเดิม)
    # ...
    
    # ส่วนแสดงผลและแก้ไข
    if 'data' in st.session_state and not st.session_state.data.empty:
        edited_df = st.data_editor(
            st.session_state.data,
            num_rows="dynamic",
            use_container_width=True,
            key="gsheets_editor"
        )
        
        if st.button("💾 บันทึกการเปลี่ยนแปลงลง Cloud", type="primary"):
            save_to_gsheets(edited_df)
            st.session_state.data = edited_df
            st.success("✅ อัปเดต Google Sheets เรียบร้อย!")
            st.rerun()
