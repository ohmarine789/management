import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- 1. 데이터베이스 및 CSV 관리 함수 ---
def get_connection():
    return sqlite3.connect('./sqlite_db/store_crm.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 고객 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, phone TEXT, birth TEXT, address TEXT, 
                  size TEXT, notes TEXT, join_date TEXT, points INTEGER)''')
    # 판매 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, type TEXT, location TEXT, 
                  sale_date TEXT, item_name TEXT, item_code TEXT, spec TEXT, unit TEXT,
                  unit_price INTEGER, quantity INTEGER, supply_value INTEGER, tax INTEGER,
                  sale_amount INTEGER, add_amount INTEGER, discount_amount INTEGER, total_amount INTEGER,
                  payment_method TEXT, remarks TEXT)''')
    # 수선 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, 
                  reg_date TEXT, item_code TEXT, item_name TEXT, color TEXT, phone TEXT, 
                  repair_notes TEXT, service_type TEXT, cost INTEGER, payment_method TEXT, other_notes TEXT)''')
    conn.commit()
    conn.close()
    sync_to_csv()

def sync_to_csv():
    conn = get_connection()
    try:
        pd.read_sql("SELECT * FROM customers", conn).to_csv('customers_backup.csv', index=False, encoding='utf-8-sig')
        pd.read_sql("SELECT * FROM sales", conn).to_csv('sales_backup.csv', index=False, encoding='utf-8-sig')
        pd.read_sql("SELECT * FROM repairs", conn).to_csv('repairs_backup.csv', index=False, encoding='utf-8-sig')
    finally:
        conn.close()

# --- 2. 비즈니스 로직 함수 ---
def add_transaction(c_id, t_data):
    conn = get_connection(); c = conn.cursor()
    c.execute('''INSERT INTO sales (customer_id, type, location, sale_date, item_name, item_code, spec, unit, unit_price, quantity, supply_value, tax, sale_amount, add_amount, discount_amount, total_amount, payment_method, remarks) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (c_id, t_data['type'], t_data['location'], t_data['sale_date'], t_data['item_name'], t_data['item_code'], t_data['spec'], t_data['unit'], t_data['unit_price'], t_data['quantity'], t_data['supply_value'], t_data['tax'], t_data['sale_amount'], t_data['add_amount'], t_data['discount_amount'], t_data['total_amount'], t_data['payment_method'], t_data['remarks']))
    adj = 0.05 if t_data['type'] == "판매" else -0.05
    c.execute("UPDATE customers SET points = points + ? WHERE id = ?", (int(t_data['total_amount'] * adj), c_id))
    conn.commit(); conn.close(); sync_to_csv()

def delete_transaction(sale_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT customer_id, total_amount, type FROM sales WHERE id = ?", (sale_id,))
    sale = c.fetchone()
    if sale:
        c_id, amount, t_type = sale; adj = -0.05 if t_type == "판매" else 0.05
        c.execute("UPDATE customers SET points = points + ? WHERE id = ?", (int(amount * adj), c_id))
        c.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    conn.commit(); conn.close(); sync_to_csv()

def add_repair(c_id, r_data):
    conn = get_connection(); c = conn.cursor()
    c.execute('''INSERT INTO repairs (customer_id, reg_date, item_code, item_name, color, phone, repair_notes, service_type, cost, payment_method, other_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (c_id, r_data['reg_date'], r_data['item_code'], r_data['item_name'], r_data['color'], r_data['phone'], r_data['repair_notes'], r_data['service_type'], r_data['cost'], r_data['payment_method'], r_data['other_notes']))
    conn.commit(); conn.close(); sync_to_csv()

def delete_repair(r_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM repairs WHERE id = ?", (r_id,))
    conn.commit(); conn.close(); sync_to_csv()

def manage_customer(action, c_id=None, data=None):
    conn = get_connection(); c = conn.cursor()
    if action == "add":
        c.execute('''INSERT INTO customers (name, phone, birth, address, size, notes, join_date, points) VALUES (?, ?, ?, ?, ?, ?, ?, 0)''', (data['name'], data['phone'], data['birth'], data['address'], data['size'], data['notes'], data['join_date']))
    elif action == "update":
        c.execute('''UPDATE customers SET name=?, phone=?, birth=?, address=?, size=?, notes=? WHERE id=?''', (data['name'], data['phone'], data['birth'], data['address'], data['size'], data['notes'], c_id))
    elif action == "delete":
        c.execute("DELETE FROM customers WHERE id=?", (c_id,)); c.execute("DELETE FROM sales WHERE customer_id=?", (c_id,)); c.execute("DELETE FROM repairs WHERE customer_id=?", (c_id,))
    conn.commit(); conn.close(); sync_to_csv()

# --- 3. UI 렌더링 ---
def render_integrated_management():
    st.markdown("""<style>html, body, [class*="st-"] { font-size: 14px; } [data-testid="stVerticalBlock"] > div { padding-top: 0.05rem !important; padding-bottom: 0.05rem !important; margin-bottom: 0rem !important; } hr { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; } .stButton > button { height: 26px !important; padding-top: 0px !important; padding-bottom: 0px !important; line-height: 1 !important; }</style>""", unsafe_allow_html=True)
    st.title("👕 통합 매장 관리 시스템")

    col_search, col_add = st.columns([3, 1])
    with col_search: search_q = st.text_input("🔍 고객 검색", placeholder="이름 또는 번호 입력")
    with col_add: 
        st.write(" ")
        if st.button("➕ 신규 회원 등록", use_container_width=True): st.session_state['show_add'] = not st.session_state.get('show_add', False)

    if st.session_state.get('show_add', False):
        with st.container(border=True):
            with st.form("new_customer"):
                c1, c2, c3 = st.columns(3); n_name = c1.text_input("고객명*"); n_phone = c2.text_input("연락처*"); n_size = c3.text_input("사이즈")
                c4, c5 = st.columns(2); n_birth = c4.date_input("생일", value=datetime(1990,1,1)); n_join = c5.date_input("가입일")
                n_addr = st.text_input("주소"); n_notes = st.text_area("비고")
                if st.form_submit_button("등록 완료"):
                    if n_name and n_phone:
                        manage_customer("add", data={'name':n_name, 'phone':n_phone, 'birth':str(n_birth), 'address':n_addr, 'size':n_size, 'notes':n_notes, 'join_date':str(n_join)})
                        st.session_state['show_add'] = False
                        st.rerun()

    st.divider()
    conn = get_connection()
    query = f"SELECT * FROM customers WHERE name LIKE '%{search_q}%' OR phone LIKE '%{search_q}%' ORDER BY id DESC" if search_q else "SELECT * FROM customers ORDER BY id DESC"
    all_customers = pd.read_sql(query, conn); conn.close()

    if not all_customers.empty:
        h = st.columns([0.5, 1.5, 2, 1, 1.5, 1])
        for col, text in zip(h, ["ID", "이름", "연락처", "사이즈", "포인트", "관리"]): col.markdown(f"**{text}**")
        st.markdown("---")

        for _, row in all_customers.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 1.5, 2, 1, 1.5, 1])
            c1.text(row['id']); c2.text(row['name']); c3.text(row['phone']); c4.text(row['size'] if row['size'] else "-"); c5.text(f"{row['points']:,} P")
            if c6.button("조회", key=f"v_{row['id']}", use_container_width=True): st.session_state[f"open_{row['id']}"] = not st.session_state.get(f"open_{row['id']}", False)

            if st.session_state.get(f"open_{row['id']}", False):
                with st.container(border=True):
                    t1, t2, t3, t4 = st.tabs(["🛒 판매 등록", "🧵 수선 접수", "📜 히스토리", "⚙️ 정보수정"])
                    
                    with t1: # 판매 등록
                        with st.form(f"s_form_{row['id']}"):
                            # [요청사항 반영] 구분, 장소, 결제수단을 한 줄에 같은 폼(Selectbox)으로 배치
                            row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
                            s_date = row1_col1.date_input("날짜")
                            s_type = row1_col2.selectbox("거래구분", ["판매", "반품"])
                            s_loc = row1_col3.selectbox("판매장소", ["매장", "행사매장"])
                            s_pay = row1_col4.selectbox("결제수단", ["카드", "현금", "기타"])

                            row2_col1, row2_col2, row2_col3 = st.columns([2, 1, 1])
                            s_item = row2_col1.text_input("품목명*")
                            s_code = row2_col2.text_input("품목코드")
                            s_spec = row2_col3.text_input("사이즈/규격")

                            row3_col1, row3_col2, row3_col3, row3_col4 = st.columns(4)
                            s_up = row3_col1.number_input("단가", min_value=0, step=100)
                            s_qty = row3_col2.number_input("수량", min_value=1, step=1)
                            s_add = row3_col3.number_input("추가금액", value=0)
                            s_disc = row3_col4.number_input("할인금액", value=0)
                            
                            total = (s_up * s_qty) + s_add - s_disc
                            st.markdown(f"### 💰 최종 결제 금액: {total:,}원")
                            
                            if st.form_submit_button("판매 내역 저장"):
                                if s_item:
                                    add_transaction(row['id'], {'type':s_type, 'location':s_loc, 'sale_date':str(s_date), 'item_name':s_item, 'item_code':s_code, 'spec':s_spec, 'unit':'', 'unit_price':s_up, 'quantity':s_qty, 'supply_value':int(total/1.1), 'tax':total-int(total/1.1), 'sale_amount':s_up*s_qty, 'add_amount':s_add, 'discount_amount':s_disc, 'total_amount':total, 'payment_method':s_pay, 'remarks':''})
                                    st.rerun()

                    with t2: # 수선 접수
                        with st.form(f"r_form_{row['id']}"):
                            r1, r2, r3 = st.columns(3); r_date = r1.date_input("접수일자"); r_code = r2.text_input("품번"); r_item = r3.text_input("품명")
                            r4, r5, r6 = st.columns(3); r_color = r4.text_input("색상"); r_phone = r5.text_input("연락처", value=row['phone']); r_type = r6.selectbox("유료/무료", ["무료", "유료"])
                            r_notes = st.text_input("수선내용 (예: 밑단 줄임)")
                            r7, r8, r9 = st.columns(3); r_cost = r7.number_input("수선비용", min_value=0); r_pay = r8.selectbox("수선비 결제", ["미결제", "현금", "카드"]); r_etc = r9.text_input("기타 메모")
                            if st.form_submit_button("수선 내역 저장"):
                                add_repair(row['id'], {'reg_date':str(r_date), 'item_code':r_code, 'item_name':r_item, 'color':r_color, 'phone':r_phone, 'repair_notes':r_notes, 'service_type':r_type, 'cost':r_cost, 'payment_method':r_pay, 'other_notes':r_etc})
                                st.rerun()

                    with t3: # 히스토리
                        st.subheader("🛒 판매 및 🧵 수선 내역")
                        conn = get_connection()
                        s_hist = pd.read_sql(f"SELECT id, sale_date, item_name, total_amount, payment_method, location FROM sales WHERE customer_id = {row['id']} ORDER BY sale_date DESC", conn)
                        r_hist = pd.read_sql(f"SELECT id, reg_date, item_name, repair_notes, cost, payment_method FROM repairs WHERE customer_id = {row['id']} ORDER BY reg_date DESC", conn)
                        conn.close()
                        
                        if not s_hist.empty:
                            st.write("**[판매 기록]**")
                            for _, sr in s_hist.iterrows():
                                sc1, sc2, sc3, sc4, sc5 = st.columns([2, 3, 2, 1.5, 1])
                                sc1.text(sr['sale_date']); sc2.text(sr['item_name']); sc3.text(f"{sr['total_amount']:,}원"); sc4.text(f"{sr['location']}/{sr['payment_method']}")
                                if sc5.button("삭제", key=f"ds_{sr['id']}"): delete_transaction(sr['id']); st.rerun()
                        
                        if not r_hist.empty:
                            st.write("**[수선 기록]**")
                            for _, rr in r_hist.iterrows():
                                rc1, rc2, rc3, rc4, rc5 = st.columns([2, 2, 3, 1.5, 1])
                                rc1.text(rr['reg_date']); rc2.text(rr['item_name']); rc3.text(rr['repair_notes']); rc4.text(f"{rr['cost']:,}원({rr['payment_method']})")
                                if rc5.button("삭제", key=f"dr_{rr['id']}"): delete_repair(rr['id']); st.rerun()

                    with t4: # 정보 수정
                        with st.form(f"e_form_{row['id']}"):
                            en = st.text_input("이름", value=row['name']); ep = st.text_input("연락처", value=row['phone']); ea = st.text_input("주소", value=row['address']); es = st.text_input("사이즈", value=row['size']); et = st.text_area("메모", value=row['notes'])
                            if st.form_submit_button("정보 수정 저장"): manage_customer("update", c_id=row['id'], data={'name':en, 'phone':ep, 'birth':row['birth'], 'address':ea, 'size':es, 'notes':et}); st.rerun()
            st.markdown("---")
    else: st.info("고객 데이터가 없습니다.")

def render_dashboard():
    st.header("📊 매출 및 수선 통계")
    if os.path.exists('sales_backup.csv'):
        df = pd.read_csv('sales_backup.csv')
        c1, c2, c3 = st.columns(3)
        c1.metric("총 판매액", f"{int(df[df['type']=='판매']['total_amount'].sum()):,}원")
        c2.metric("카드 결제 건수", f"{len(df[df['payment_method']=='카드'])}건")
        c3.metric("현금 결제 건수", f"{len(df[df['payment_method']=='현금'])}건")
        st.dataframe(df, use_container_width=True)

def main():
    st.set_page_config(page_title="의류 매장 CRM", layout="wide")
    init_db()
    menu = st.sidebar.radio("메뉴", ["통합 관리", "대시보드"])
    if menu == "통합 관리": render_integrated_management()
    else: render_dashboard()

if __name__ == "__main__": main()