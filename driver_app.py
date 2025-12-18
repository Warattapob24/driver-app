import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="Driver Revenue Pro", page_icon="🚗", layout="wide")

# ไฟล์สำหรับเก็บข้อมูล (บนคอมพิวเตอร์)
DATA_FILE = "driver_data.csv"

# ฟังก์ชันโหลดข้อมูล
def load_data():
    try:
        # ลองอ่านไฟล์ CSV ถ้ามี
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        # ถ้าไม่มีไฟล์ ให้สร้างตารางเปล่า
        return pd.DataFrame(columns=[
            'Date', 'Time', 'Platform', 'Category', 'SubCategory', 
            'Amount_Gross', 'Deduction', 'Tip', 'Net_Income', 'Note'
        ])

# ฟังก์ชันบันทึกข้อมูล
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# โหลดข้อมูลเข้าสู่ Session
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 2. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ ตั้งค่า (Settings)")
    maxim_comm_rate = st.slider("Maxim หักคอมมิชชั่น (%)", 0, 30, 15) / 100
    ev_home_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมาจ่าย/ครั้ง)", value=40, step=5)
    
    st.divider()
    # ปุ่มดาวน์โหลดไฟล์ CSV (เผื่อเอาไปใช้ที่อื่น)
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(st.session_state.data)
    st.download_button(
        label="📥 ดาวน์โหลดข้อมูลเป็น CSV",
        data=csv,
        file_name='driver_data_export.csv',
        mime='text/csv',
    )

# --- 3. MAIN UI ---
st.title("🚗 Driver Revenue Tracker")
tab1, tab2 = st.tabs(["📝 บันทึกงาน/ค่าใช้จ่าย", "📊 สรุปผลกำไร"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("เลือกรายการ")
        entry_type = st.radio(
            "ทำรายการประเภทไหน?",
            ["🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "💳 เติมเครดิตเข้าแอป (Top-up)", "🛠️ จ่ายอื่นๆ"],
        )

    with col2:
        # === FORM 1: รับงาน (Income) ===
        if entry_type == "🚗 รับงานขับรถ":
            st.info("💡 กรอกยอดหน้าแอป vs ยอดรับจริง ระบบจะคิดทิปให้")
            platform = st.selectbox("แพลตฟอร์ม", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
            
            c1, c2 = st.columns(2)
            with c1: app_price = st.number_input("ราคาหน้าแอป", min_value=0.0, step=10.0)
            with c2: real_receive = st.number_input("เงินที่รับจริง (รวมทิป)", min_value=0.0, value=app_price, step=10.0)
            
            note = st.text_input("หมายเหตุ")
            
            if st.button("บันทึกรายได้ ✅", type="primary", use_container_width=True):
                if app_price > 0:
                    deduction = 0
                    tip = max(0, real_receive - app_price)
                    
                    # Logic หักคอมมิชชั่น (เฉพาะแอปที่โชว์ราคาก่อนหัก)
                    if platform in ["Maxim", "งานนอก"]:
                        deduction = app_price * maxim_comm_rate
                        net_income = app_price - deduction + tip
                    else:
                        # Grab/Bolt ถือว่าหักแล้ว (Net)
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
                        'Note': note
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data) # บันทึกลงไฟล์
                    st.success(f"บันทึกรายได้ {net_income:.2f} บาท เรียบร้อย!")

        # === FORM 2: เติมเครดิต (Wallet Top-up) ===
        elif entry_type == "💳 เติมเครดิตเข้าแอป (Top-up)":
            st.warning("💸 การเติมเครดิตถือเป็นค่าใช้จ่ายล่วงหน้า")
            platform = st.selectbox("เติมเข้าแอปไหน?", ["Grab Wallet", "Bolt Balance", "Maxim", "Line Man Credit", "Robinhood"])
            amount = st.number_input("จำนวนเงินที่เติม", min_value=0.0, step=100.0)
            
            if st.button("บันทึกการเติมเงิน 💾", type="primary", use_container_width=True):
                if amount > 0:
                    new_row = {
                        'Date': datetime.date.today(),
                        'Time': datetime.datetime.now().strftime("%H:%M"),
                        'Platform': platform,
                        'Category': 'Expense',
                        'SubCategory': 'Top-up/Commission',
                        'Amount_Gross': 0,
                        'Deduction': amount,
                        'Tip': 0,
                        'Net_Income': -amount, # เป็นค่าลบ (รายจ่าย)
                        'Note': "เติมเครดิตงาน"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.success(f"บันทึกเติมเงิน {platform} {amount} บาท เรียบร้อย!")

        # === FORM 3: พลังงาน (Energy) ===
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
            cost = st.number_input("ค่าใช้จ่าย", value=(ev_home_rate if "บ้าน" in e_type else 0.0))
            note = st.text_input("สถานที่/ปั๊ม")
            
            if st.button("บันทึกค่าพลังงาน ⚡", type="primary", use_container_width=True):
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
                        'Note': f"{e_type} - {note}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.success("บันทึกเรียบร้อย!")
        
        # === FORM 4: อื่นๆ ===
        elif entry_type == "🛠️ จ่ายอื่นๆ":
             cost = st.number_input("จำนวนเงิน", min_value=0.0)
             note = st.text_input("รายการ (เช่น ปะยาง, ข้าว)")
             if st.button("บันทึก", type="primary"):
                 new_row = {
                        'Date': datetime.date.today(),
                        'Time': datetime.datetime.now().strftime("%H:%M"),
                        'Platform': 'Expense',
                        'Category': 'Expense',
                        'SubCategory': 'Maintenance/Other',
                        'Amount_Gross': 0,
                        'Deduction': cost,
                        'Tip': 0,
                        'Net_Income': -cost,
                        'Note': note
                    }
                 st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                 save_data(st.session_state.data)
                 st.success("บันทึกเรียบร้อย!")

# --- 4. DASHBOARD ---
with tab2:
    df = st.session_state.data
    if not df.empty:
        # Metrics
        income_only = df[df['Net_Income'] > 0]['Net_Income'].sum()
        expense_only = df[df['Net_Income'] < 0]['Net_Income'].abs().sum()
        topup_only = df[df['SubCategory'] == 'Top-up/Commission']['Deduction'].sum()
        
        # แยกค่าเติมเครดิตออกจากค่าใช้จ่ายทั่วไปเพื่อให้เห็นภาพชัดขึ้น
        real_expense = expense_only - topup_only 
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 เงินเข้ากระเป๋าสุทธิ", f"{income_only - real_expense - topup_only:,.0f} บ.")
        m2.metric("💳 เติมเงินเข้าแอปไปแล้ว", f"{topup_only:,.0f} บ.")
        m3.metric("⛽ ค่าน้ำมัน/ซ่อม", f"{real_expense:,.0f} บ.")

        st.divider()
        st.subheader("ประวัติรายการล่าสุด")
        st.dataframe(df.sort_values(by="Time", ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูล")