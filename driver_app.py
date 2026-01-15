import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกรายได้คนขับ (Speed+)", page_icon="🚗", layout="wide")
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

# --- 3. DATA LOADING (เพิ่มระบบ Caching เพื่อความเร็ว) ---
# @st.cache_data(ttl=300) # เก็บข้อมูลไว้ในความจำ 5 นาที ไม่ต้องโหลดใหม่บ่อยๆ
def load_and_clean_data(refresh=False):
    # ถ้ามีการบังคับ Refresh หรือไม่มีข้อมูลใน Cache ให้โหลดใหม่
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # อ่านข้อมูล (ttl=0 คือโหลดสด)
        df = conn.read(ttl=0)
        
        required_cols = [
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ]
        
        if df.empty or len(df.columns) < len(required_cols):
             df = pd.DataFrame(columns=required_cols)
        
        # Clean Data
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
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)
        
        # เติมค่าว่าง
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
        
    except Exception as e:
        # st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}") # ปิด Error ชั่วคราวเพื่อให้ UI ไม่รก
        return pd.DataFrame(columns=[
            'วันที่', 'เวลา', 'แอป', 'หมวดหมู่', 'รายการ', 'ช่องทางรับเงิน',
            'ยอดเต็ม/หน้าแอป', 'หัก/จ่าย', 'ทิป', 'คงเหลือ/สุทธิ', 
            'เงินสดเข้าตัว', 'เลขไมล์', 'หมายเหตุ'
        ])

# --- ฟังก์ชันบันทึก ---
def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_save = df.copy()
        if 'วันที่' in df_save.columns:
            df_save['วันที่'] = df_save['วันที่'].astype(str)
        conn.update(worksheet="Drivers", data=df_save)
        # st.cache_data.clear() # เคลียร์ Cache ทันทีหลังบันทึก เพื่อให้เห็นข้อมูลใหม่
    except Exception as e:
        st.error(f"บันทึกไม่สำเร็จ: {e}")

# โหลดข้อมูลเข้า Session
if 'data' not in st.session_state:
    st.session_state.data = load_and_clean_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า & เมนู")
    st.caption(f"เวลา: {get_thai_time().strftime('%H:%M')}")
    
    # ปุ่ม Refresh แบบ Manual (ช่วยให้แอปไม่โหลดเองมั่วซั่ว)
    if st.button("🔄 รีเฟรชข้อมูล (กดเมื่อเน็ตดี)", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.data = load_and_clean_data(refresh=True)
        st.rerun()
    
    current_settings = load_settings()
    new_ev_rate = st.number_input("ค่าไฟชาร์จบ้าน (เหมา)", value=float(current_settings.get("ev_rate", 40.0)), step=5.0)
    
    if new_ev_rate != current_settings.get("ev_rate"):
        save_settings({"ev_rate": new_ev_rate})
        st.toast("บันทึกค่าไฟแล้ว!")
    
    ev_home_rate = new_ev_rate
    
    st.divider()
    if st.button("⚠️ ล้างข้อมูลทั้งหมด"):
        st.warning("ฟังก์ชันนี้ถูกปิดชั่วคราวเพื่อความปลอดภัย")

# --- 5. MAIN APP ---
st.title("🚗 ระบบบันทึกรายได้ (Pro)")
tab1, tab2, tab3, tab4 = st.tabs(["📝 บันทึกงาน", "📊 วิเคราะห์ความคุ้มค่า", "📈 ประวัติกราฟ", "🗂️ ฐานข้อมูล"])

# ==========================================
# TAB 1: บันทึกงาน (เหมือนเดิม)
# ==========================================
with tab1:
    col_type, col_form = st.columns([1, 2])
    with col_type:
        st.subheader("ทำรายการ")
        entry_type = st.radio(
            "ประเภทรายการ",
            ["🚗 รับงานขับรถ", "⛽ เติมน้ำมัน/ชาร์จไฟ", "💳 เติมเครดิตแอป", "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)", "🛠️ จ่ายอื่นๆ"],
        )

    with col_form:
        st.container(border=True)
        
        # 1. รับงาน
        if entry_type == "🚗 รับงานขับรถ":
            st.markdown("#### 📝 บันทึกรายได้")
            with st.form(key="form_income", clear_on_submit=True):
                c_app, c_pay = st.columns(2)
                with c_app:
                    platform = st.selectbox("เลือกแอป", ["Grab", "Bolt", "Line Man", "Maxim", "Robinhood", "Win", "งานนอก"])
                with c_pay:
                    pay_method = st.selectbox("ช่องทางรับเงิน", ["💵 เงินสด/โอน", "💳 ตัดบัตร/แอป"])

                c1, c2 = st.columns(2)
                with c1: app_price = st.number_input("ราคาหน้าแอป (ยอดเต็ม)", min_value=0.0, step=10.0, value=None)
                with c2: real_receive = st.number_input("เงินที่รับจริง (สุทธิเข้ากระเป๋า)", min_value=0.0, step=10.0, value=None)
                
                note = st.text_input("หมายเหตุ", placeholder="เช่น ลูกค้าทิป, งานไกล")
                submitted = st.form_submit_button("บันทึกรายได้ ✅", type="primary", use_container_width=True)
                
                if submitted:
                    price_val = app_price if app_price is not None else 0.0
                    real_val = real_receive if real_receive is not None else 0.0
                    
                    if price_val > 0 or real_val > 0:
                        if real_val == 0: real_val = price_val # ถ้าไม่กรอกรับจริง ให้เท่ากับหน้าแอป
                        
                        # คำนวณส่วนต่าง (ค่าธรรมเนียม หรือ ทิป)
                        diff = real_val - price_val
                        tip = diff if diff > 0 else 0
                        deduction = abs(diff) if diff < 0 else 0 # ถ้าได้น้อยกว่าหน้าแอป คือโดนหัก
                        
                        cash_in_hand = real_val if pay_method == "💵 เงินสด/โอน" else 0.0
                        
                        new_row = {
                            'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                            'แอป': platform, 'หมวดหมู่': 'รายรับ', 'รายการ': 'ค่าโดยสาร', 'ช่องทางรับเงิน': pay_method,
                            'ยอดเต็ม/หน้าแอป': price_val, 'หัก/จ่าย': deduction, 'ทิป': tip, 
                            'คงเหลือ/สุทธิ': real_val, 'เงินสดเข้าตัว': cash_in_hand, 
                            'เลขไมล์': 0, 'หมายเหตุ': note
                        }
                        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(st.session_state.data)
                        st.toast(f"บันทึกรายได้ {real_val:.0f} บาท")
                        st.rerun()
                    else: st.warning("กรุณากรอกยอดเงิน")

        # 2. เติมเครดิต
        elif entry_type == "💳 เติมเครดิตแอป":
            st.markdown("#### 💳 เติมเงินเข้าแอป")
            with st.form(key="form_topup", clear_on_submit=True):
                sub_cat = st.selectbox("แอปไหน", ["Grab Wallet", "Bolt", "Maxim", "Line Man", "Robinhood"])
                cost = st.number_input("จำนวนเงินที่เติม", min_value=0.0)
                submitted = st.form_submit_button("บันทึกรายจ่าย 💾", type="primary", use_container_width=True)
                
                if submitted and cost > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': sub_cat, 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'เติมเครดิต', 'ช่องทางรับเงิน': 'จ่ายสด',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 
                        'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': 'Top-up'
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.toast("บันทึกเติมเครดิตแล้ว")
                    st.rerun()

        # 3. พลังงาน
        elif entry_type == "⛽ เติมน้ำมัน/ชาร์จไฟ":
            st.markdown("#### ⚡ ต้นทุนพลังงาน")
            with st.form(key="form_energy", clear_on_submit=True):
                e_type = st.radio("ประเภท", ["⛽ น้ำมัน", "⚡ ชาร์จบ้าน (เหมา)", "🔌 ชาร์จสถานี"], horizontal=True)
                default_val = float(ev_home_rate) if e_type == "⚡ ชาร์จบ้าน (เหมา)" else None
                cost = st.number_input("จำนวนเงิน", min_value=0.0, value=default_val)
                note = st.text_input("สถานที่")
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                if submitted and cost > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ค่าน้ำมัน/ไฟ', 'ช่องทางรับเงิน': 'จ่ายสด',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 
                        'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': f"{e_type} - {note}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

        # 4. ไมล์
        elif entry_type == "🕒 เริ่มงาน/เลิกงาน (เลขไมล์)":
            st.markdown("#### 🕒 บันทึกเลขไมล์")
            with st.form(key="form_odom", clear_on_submit=True):
                shift_type = st.radio("สถานะ", ["☀️ เริ่มงาน", "🌙 เลิกงาน"], horizontal=True)
                odometer = st.number_input("เลขไมล์หน้าปัด", min_value=0.0)
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                if submitted and odometer > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ระบบ', 'หมวดหมู่': 'กะงาน', 'รายการ': shift_type, 'ช่องทางรับเงิน': '-',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': 0, 'ทิป': 0, 'คงเหลือ/สุทธิ': 0, 'เงินสดเข้าตัว': 0,
                        'เลขไมล์': odometer, 'หมายเหตุ': f"เลขไมล์ {shift_type}"
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()

        # 5. จ่ายอื่น
        elif entry_type == "🛠️ จ่ายอื่นๆ":
            st.markdown(f"#### 🛠️ จ่ายทั่วไป")
            with st.form(key="form_other", clear_on_submit=True):
                sub_cat = st.text_input("รายการ (เช่น ข้าว, ปะยาง)")
                cost = st.number_input("จำนวนเงิน", min_value=0.0)
                submitted = st.form_submit_button("บันทึก 💾", type="primary", use_container_width=True)
                if submitted and cost > 0:
                    new_row = {
                        'วันที่': get_thai_date(), 'เวลา': get_thai_time().strftime("%H:%M"),
                        'แอป': 'ค่าใช้จ่าย', 'หมวดหมู่': 'รายจ่าย', 'รายการ': 'ทั่วไป', 'ช่องทางรับเงิน': 'จ่ายสด',
                        'ยอดเต็ม/หน้าแอป': 0, 'หัก/จ่าย': cost, 'ทิป': 0, 
                        'คงเหลือ/สุทธิ': -cost, 'เงินสดเข้าตัว': -cost, 'เลขไมล์': 0, 'หมายเหตุ': sub_cat
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.rerun()
    st.markdown("<br>" * 5, unsafe_allow_html=True)

# ==========================================
# TAB 2: วิเคราะห์ความคุ้มค่า (NEW FEATURE)
# ==========================================
with tab2:
    st.subheader("📊 วิเคราะห์ความคุ้มค่า (GP Analysis)")
    
    df = st.session_state.data
    if not df.empty:
        # Filter เฉพาะงานขับรถที่มีรายได้
        rides = df[(df['หมวดหมู่'] == 'รายรับ') & (df['ยอดเต็ม/หน้าแอป'] > 0)].copy()
        
        if not rides.empty:
            # คำนวณ % การหัก (GP)
            # สูตร: (ราคาหน้าแอป - เงินที่ได้จริง) / ราคาหน้าแอป * 100
            rides['ส่วนต่าง'] = rides['ยอดเต็ม/หน้าแอป'] - rides['คงเหลือ/สุทธิ']
            rides['GP_Percent'] = (rides['ส่วนต่าง'] / rides['ยอดเต็ม/หน้าแอป']) * 100
            
            # --- 1. สรุปแยกรายแอป ---
            st.markdown("##### 🏆 จัดอันดับแอปน่าขับ (เฉลี่ย)")
            
            # Group by App
            app_stats = rides.groupby('แอป').agg({
                'GP_Percent': 'mean',
                'คงเหลือ/สุทธิ': 'mean',
                'ยอดเต็ม/หน้าแอป': 'count'
            }).reset_index()
            
            app_stats.rename(columns={
                'GP_Percent': 'โดนหักเฉลี่ย (%)', 
                'คงเหลือ/สุทธิ': 'รายได้เฉลี่ย/งาน',
                'ยอดเต็ม/หน้าแอป': 'จำนวนงาน'
            }, inplace=True)
            
            # จัดรูปแบบตัวเลข
            app_stats['โดนหักเฉลี่ย (%)'] = app_stats['โดนหักเฉลี่ย (%)'].map('{:.1f}%'.format)
            app_stats['รายได้เฉลี่ย/งาน'] = app_stats['รายได้เฉลี่ย/งาน'].map('{:,.0f}'.format)
            
            st.dataframe(
                app_stats.sort_values(by='จำนวนงาน', ascending=False), 
                use_container_width=True,
                hide_index=True
            )
            
            st.info("💡 **ทริค:** แอปไหนโดนหัก % น้อยกว่า และรายได้เฉลี่ยต่องานสูงกว่า คือแอปที่คุ้มค่าเหนื่อยที่สุด")

            st.divider()
            
            # --- 2. Scatter Plot: รายได้ vs การโดนหัก ---
            st.markdown("##### 🔍 กระจายตัวของงาน (รายได้ vs GP)")
            fig_scatter = px.scatter(
                rides, 
                x="ยอดเต็ม/หน้าแอป", 
                y="คงเหลือ/สุทธิ", 
                color="แอป",
                hover_data=["GP_Percent"],
                title="จุดยิ่งอยู่สูงเส้นทะแยงมุม ยิ่งคุ้ม (โดนหักน้อย)"
            )
            # เส้นอ้างอิง 100% (ไม่โดนหักเลย)
            fig_scatter.add_shape(type="line", line=dict(dash="dash", width=1, color="gray"),
                x0=0, x1=rides['ยอดเต็ม/หน้าแอป'].max(), y0=0, y1=rides['ยอดเต็ม/หน้าแอป'].max()
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        else:
            st.warning("ยังไม่มีข้อมูลงานขับรถเพื่อคำนวณ GP")
    else:
        st.info("ยังไม่มีข้อมูล")

# ==========================================
# TAB 3: ประวัติกราฟสถิติ (NEW FEATURE)
# ==========================================
with tab3:
    st.subheader("📈 ประวัติสถิติและแนวโน้ม")
    
    df = st.session_state.data
    if not df.empty:
        # แปลงวันที่ให้ชัวร์
        df['วันที่'] = pd.to_datetime(df['วันที่'])
        
        # เลือกดูรายเดือน หรือ รายวัน
        view_mode = st.radio("มุมมอง", ["รายวัน (30 วันล่าสุด)", "รายเดือน (ทั้งปี)"], horizontal=True)
        
        stats_df = df.copy()
        
        if view_mode == "รายวัน (30 วันล่าสุด)":
            last_30 = pd.Timestamp.now() - pd.Timedelta(days=30)
            stats_df = stats_df[stats_df['วันที่'] >= last_30]
            group_col = 'วันที่'
            x_format = "%d %b"
        else:
            stats_df['เดือน'] = stats_df['วันที่'].dt.to_period('M').astype(str)
            group_col = 'เดือน'
            x_format = "%b %Y"

        # เตรียมข้อมูลกราฟ
        daily_stats = stats_df.groupby(group_col).agg({
            'คงเหลือ/สุทธิ': 'sum',
            'ยอดเต็ม/หน้าแอป': 'sum',
            'เลขไมล์': lambda x: x.max() - x.min() if len(x) > 0 else 0
        }).reset_index()
        
        # กราฟ 1: รายได้สุทธิ
        st.markdown("##### 💰 แนวโน้มรายได้สุทธิ")
        fig_line = px.line(
            daily_stats, x=group_col, y='คงเหลือ/สุทธิ', 
            markers=True, title="รายได้เข้ากระเป๋าจริง",
            line_shape="spline"
        )
        fig_line.update_traces(line_color='#00B14F', line_width=3)
        st.plotly_chart(fig_line, use_container_width=True)
        
        # กราฟ 2: เปรียบเทียบ ยอดหน้าแอป vs รับจริง
        st.markdown("##### ⚖️ เทียบยอดหน้าแอป vs รับจริง (ส่วนต่างคือ GP/ค่าใช้จ่าย)")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=daily_stats[group_col], y=daily_stats['ยอดเต็ม/หน้าแอป'], name='หน้าแอป (Gross)', marker_color='#95A5A6'))
        fig_bar.add_trace(go.Bar(x=daily_stats[group_col], y=daily_stats['คงเหลือ/สุทธิ'], name='รับจริง (Net)', marker_color='#2ECC71'))
        fig_bar.update_layout(barmode='group', title="ถ้ารับจริงใกล้เคียงหน้าแอป แสดงว่าคุ้ม")
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("ไม่มีข้อมูลแสดงผล")

# ==========================================
# TAB 4: ฐานข้อมูล (เหมือนเดิม)
# ==========================================
with tab4:
    st.subheader("🗂️ ฐานข้อมูล")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        f_app = c1.multiselect("แอป", st.session_state.data['แอป'].unique())
        f_cat = c2.multiselect("หมวดหมู่", st.session_state.data['หมวดหมู่'].unique())
        f_date = c3.selectbox("วันที่", ["ทั้งหมด", "วันนี้", "เดือนนี้"])

    df_show = st.session_state.data.copy()
    if f_app: df_show = df_show[df_show['แอป'].isin(f_app)]
    if f_cat: df_show = df_show[df_show['หมวดหมู่'].isin(f_cat)]
    if f_date == "วันนี้": df_show = df_show[df_show['วันที่'] == get_thai_date()]
    elif f_date == "เดือนนี้": 
        t = get_thai_date()
        df_show = df_show[(pd.to_datetime(df_show['วันที่']).dt.month == t.month) & (pd.to_datetime(df_show['วันที่']).dt.year == t.year)]

    if not df_show.empty:
        # Sort ข้อมูลใหม่สุดขึ้นก่อน
        df_show = df_show.sort_values(by=["วันที่", "เวลา"], ascending=False)
        edited = st.data_editor(df_show, num_rows="dynamic", use_container_width=True, key="editor")
        
        if st.button("💾 บันทึกการเปลี่ยนแปลง", type="primary"):
            try:
                # Logic การลบและแก้ไข
                orig_idx = set(df_show.index)
                curr_idx = set(edited.index)
                deleted = orig_idx - curr_idx
                
                if deleted: st.session_state.data = st.session_state.data.drop(list(deleted))
                st.session_state.data.update(edited)
                save_data(st.session_state.data)
                
                st.success("บันทึกสำเร็จ!")
                # Force Reload เพื่อให้เห็นผลทันที
                st.cache_data.clear()
                st.session_state.data = load_and_clean_data(refresh=True)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
