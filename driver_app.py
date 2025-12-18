import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="Pro Driver Analytics", page_icon="🚖", layout="wide")

# ไฟล์เก็บข้อมูล
DATA_FILE = "driver_data.csv"

# โหลดข้อมูล
def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        # แปลงคอลัมน์ Date เป็น datetime เพื่อการคำนวณที่ถูกต้อง
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            'Date', 'Time', 'Platform', 'Category', 'SubCategory', 
            'Amount_Gross', 'Deduction', 'Tip', 'Net_Income', 'Distance_Km', 'Note'
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# โหลดเข้า Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 2. SIDEBAR (ตั้งค่า) ---
with st.sidebar:
    st.title("⚙️ ตั้งค่าระบบ")
    maxim_comm_rate = st.slider("Maxim หักคอมมิชชั่น (%)", 0, 30, 15) / 100
    ev_home_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมาจ่าย/ครั้ง)", value=40, step=5)
    
    st.info("💡 ทิป: ไปที่เมนู 'ฐานข้อมูล' เพื่อแก้ไขข้อมูลเก่า")

# --- 3. MAIN APP ---
st.title("🚖 Driver Revenue Pro (ระบบบริหารงานขับรถ)")

# สร้าง Tabs ใหม่ 3 หน้า
tab1, tab2, tab3 = st.tabs(["📝 บันทึกงาน (Entry)", "📊 วิเคราะห์ผล (Analytics)", "🗂️ ฐานข้อมูล (Database)"])

# ==========================================
# TAB 1: บันทึกข้อมูล (Entry Form)
# ==========================================
with tab1:
    col_type, col_form = st.columns([1, 2])
    
    with col_type:
        st.subheader("เลือกรายการ")
        entry_type = st.radio(
            "ประเภทรายการ",
            ["🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "💳 เติมเครดิตแอป", "🛠️ จ่ายอื่นๆ"],
            captions=["รายได้จากการขับ", "ต้นทุนพลังงาน", "Top-up Wallet", "ซ่อมบำรุง/อาหาร"]
        )

    with col_form:
        st.container(border=True)
        # --- FORM 1: รับงาน ---
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            platform = st.selectbox("แพลตฟอร์ม", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
            
            c1, c2 = st.columns(2)
            with c1: 
                app_price = st.number_input("ราคาหน้าแอป (บาท)", min_value=0.0, step=10.0)
            with c2: 
                real_receive = st.number_input("เงินรับจริง (รวมทิป)", min_value=0.0, value=app_price, step=10.0)
            
            distance = st.number_input("ระยะทางงานนี้ (Km) - เพื่อคำนวณความคุ้มค่า", min_value=0.0, step=1.0)
            note = st.text_input("หมายเหตุ")
            
            if st.button("บันทึกรายได้ ✅", type="primary", use_container_width=True):
                if app_price > 0:
                    deduction = 0
                    tip = max(0, real_receive - app_price)
                    
                    # Logic คำนวณรายได้สุทธิ
                    if platform in ["Maxim", "งานนอก"]:
                        deduction = app_price * maxim_comm_rate
                        net_income = app_price - deduction + tip
                    else:
                        net_income = app_price + tip 

                    new_row = {
                        'Date': datetime.date.today(),
                        'Time': datetime.datetime.now().strftime("%H:%M"),
                        'Platform': platform,
                        'Category': 'Income',
                        'SubCategory': 'Fare',
                        'Amount_Gross': app_price,
                        'Deduction': deduction,
                        'Tip': tip,
                        'Net_Income': net_income,
                        'Distance_Km': distance,
                        'Note': note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast(f"บันทึกสำเร็จ! ได้กำไร {net_income:.0f} บาท")

        # --- FORM 2: พลังงาน ---
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ บันทึกต้นทุนพลังงาน")
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            
            c1, c2 = st.columns(2)
            with c1:
                cost = st.number_input("ค่าใช้จ่าย (บาท)", value=(ev_home_rate if "บ้าน" in e_type else 0.0))
            with c2:
                # ถ้าเติมน้ำมัน ให้กรอก Odometer ได้เพื่อคำนวณอัตราสิ้นเปลืองในอนาคต (ถ้าต้องการ)
                pass 

            note = st.text_input("สถานที่ / ปั๊ม")
            
            if st.button("บันทึกค่าพลังงาน 💸", type="primary", use_container_width=True):
                if cost > 0:
                    new_row = {
                        'Date': datetime.date.today(),
                        'Time': datetime.datetime.now().strftime("%H:%M"),
                        'Platform': 'Expense',
                        'Category': 'Expense',
                        'SubCategory': 'Fuel/Energy',
                        'Amount_Gross': 0,
                        'Deduction': cost,
                        'Tip': 0,
                        'Net_Income': -cost,
                        'Distance_Km': 0,
                        'Note': f"{e_type} - {note}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast("บันทึกเรียบร้อย")

        # --- FORM 3: เติมเครดิต ---
        elif entry_type == "💳 เติมเครดิตแอป":
            st.markdown("#### 💳 เติมเงินเข้ากระเป๋าแอป")
            platform = st.selectbox("แอปไหน?", ["Grab Wallet", "Bolt Balance", "Maxim", "Line Man Credit"])
            amount = st.number_input("จำนวนเงิน", min_value=0.0, step=100.0)
            
            if st.button("บันทึกการเติมเงิน", type="primary", use_container_width=True):
                new_row = {
                    'Date': datetime.date.today(),
                    'Time': datetime.datetime.now().strftime("%H:%M"),
                    'Platform': platform,
                    'Category': 'Expense',
                    'SubCategory': 'Top-up',
                    'Amount_Gross': 0,
                    'Deduction': amount,
                    'Tip': 0,
                    'Net_Income': -amount,
                    'Distance_Km': 0,
                    'Note': "Top-up"
                }
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.data)
                st.toast("บันทึกเรียบร้อย")

        # --- FORM 4: อื่นๆ ---
        elif entry_type == "🛠️ จ่ายอื่นๆ":
             st.markdown("#### 🛠️ ค่าใช้จ่ายทั่วไป")
             cost = st.number_input("จำนวนเงิน", min_value=0.0)
             note = st.text_input("รายการ (เช่น ปะยาง, ข้าว, กาแฟ)")
             if st.button("บันทึก", type="primary", use_container_width=True):
                 new_row = {
                        'Date': datetime.date.today(),
                        'Time': datetime.datetime.now().strftime("%H:%M"),
                        'Platform': 'Expense',
                        'Category': 'Expense',
                        'SubCategory': 'General',
                        'Amount_Gross': 0,
                        'Deduction': cost,
                        'Tip': 0,
                        'Net_Income': -cost,
                        'Distance_Km': 0,
                        'Note': note
                    }
                 st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                 save_data(st.session_state.data)
                 st.toast("บันทึกเรียบร้อย")

# ==========================================
# TAB 2: วิเคราะห์ผล (Dashboard)
# ==========================================
with tab2:
    df = st.session_state.data
    
    if not df.empty:
        # --- 1. คำนวณตัวเลขสำคัญ (KPIs) ---
        income_df = df[df['Category'] == 'Income']
        expense_df = df[df['Category'] == 'Expense']
        
        total_income = income_df['Net_Income'].sum()
        total_tips = income_df['Tip'].sum()
        
        # แยกค่าใช้จ่าย: ไม่รวม Top-up เพราะมันเป็นเงินค้างในแอป ยังไม่หายไปไหน (ในทางบัญชี)
        # แต่ถ้านับกระแสเงินสด คือจ่ายไปแล้ว. ในที่นี้ขอแสดงแบบแยกให้เห็นชัดๆ
        fuel_cost = expense_df[expense_df['SubCategory'] == 'Fuel/Energy']['Deduction'].sum()
        topup_cost = expense_df[expense_df['SubCategory'] == 'Top-up']['Deduction'].sum()
        other_cost = expense_df[expense_df['SubCategory'] == 'General']['Deduction'].sum()
        
        total_km = income_df['Distance_Km'].sum()
        
        # คำนวณกำไรเข้ากระเป๋าจริง (รายรับงาน - ค่าน้ำมัน - ค่าซ่อม) *ไม่หักเติมเครดิตเพราะมันหมุนเวียน*
        net_profit_pocket = total_income - fuel_cost - other_cost
        
        # Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 กำไรเข้ากระเป๋า (สุทธิ)", f"{net_profit_pocket:,.0f} บ.", delta="หักน้ำมันแล้ว")
        m2.metric("⛽ ต้นทุนพลังงาน", f"{fuel_cost:,.0f} บ.")
        m3.metric("🛣️ วิ่งงานไปแล้ว", f"{total_km:,.0f} กม.")
        
        # Cost per KM calculation
        if total_km > 0:
            cost_per_km = fuel_cost / total_km
            income_per_km = total_income / total_km
            m4.metric("📊 รายได้เฉลี่ย/กม.", f"{income_per_km:.2f} บ.", f"ต้นทุน {cost_per_km:.2f} บ./กม.")
        else:
            m4.metric("📊 รายได้เฉลี่ย/กม.", "0.00", "รอข้อมูลระยะทาง")

        st.markdown("---")

        # --- 2. Charts (กราฟ) ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🏆 แอปไหนทำเงินสูงสุด?")
            if not income_df.empty:
                # Group by Platform
                plat_sum = income_df.groupby('Platform')['Net_Income'].sum().reset_index()
                fig_bar = px.bar(plat_sum, x='Platform', y='Net_Income', color='Platform', text_auto=True, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายได้")
                
        with c2:
            st.subheader("💸 เงินรั่วไหลไปกับอะไร?")
            if not expense_df.empty:
                # Group by SubCategory
                exp_sum = expense_df.groupby('SubCategory')['Deduction'].sum().reset_index()
                fig_pie = px.pie(exp_sum, values='Deduction', names='SubCategory', hole=0.4, title="สัดส่วนค่าใช้จ่าย")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลค่าใช้จ่าย")

        # --- 3. Heatmap ช่วงเวลาทำเงิน (New Feature!) ---
        st.subheader("🔥 ช่วงเวลาทอง (ขับตอนไหนรวยสุด)")
        if not income_df.empty:
            # แปลงเวลาเป็น Hour
            income_df['Hour'] = pd.to_datetime(income_df['Time'], format='%H:%M').dt.hour
            # สร้างกราฟ Histogram ดูช่วงเวลา
            fig_hist = px.histogram(income_df, x='Hour', y='Net_Income', nbins=24, title="รายได้รวม แยกตามช่วงเวลาของวัน (0-23 น.)", color_discrete_sequence=['#FFD700'])
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
        
    else:
        st.info("👋 ยินดีต้อนรับ! เริ่มบันทึกข้อมูลหน้าแรกได้เลยครับ")

# ==========================================
# TAB 3: ฐานข้อมูล (Database Editor) - แก้ปัญหาข้อ 1
# ==========================================
with tab3:
    st.subheader("🗂️ จัดการฐานข้อมูล (แก้ไข/ลบ)")
    st.info("📝 คุณสามารถแก้ไขข้อมูลในตารางนี้ได้เลย ระบบจะบันทึกอัตโนมัติ")
    
    if not st.session_state.data.empty:
        # Data Editor: พระเอกของเราที่ช่วยให้แก้ไขข้อมูลได้เหมือน Excel
        edited_df = st.data_editor(
            st.session_state.data,
            num_rows="dynamic", # อนุญาตให้เพิ่มแถว/ลบแถวได้
            use_container_width=True,
            key="editor"
        )
        
        # ปุ่มกดบันทึก (จริงๆ data_editor มันแก้ session state แต่เราต้อง save ลงไฟล์ด้วย)
        if st.button("💾 บันทึกการแก้ไขลงไฟล์", type="primary"):
            st.session_state.data = edited_df
            save_data(edited_df)
            st.success("บันทึกข้อมูลล่าสุดเรียบร้อยแล้ว!")
    else:
        st.write("ไม่มีข้อมูลให้แก้ไข")
