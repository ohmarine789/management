import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- 1. 데이터베이스 및 CSV 관리 함수 ---
def get_connection():
    return sqlite3.connect('store_crm.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, phone TEXT, birth TEXT, address TEXT, 
                  size TEXT, notes TEXT, join_date TEXT, points INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  customer_id INTEGER, type TEXT, location TEXT, 
                  sale_date TEXT, item_name TEXT, item_code TEXT, spec TEXT, unit TEXT,
                  unit_price INTEGER, quantity INTEGER, supply_value INTEGER, tax INTEGER,
                  sale_amount INTEGER, add_amount INTEGER, discount_amount INTEGER, total_amount INTEGER,
                  remarks TEXT)''')
    conn.commit()
    conn.close()
    sync_to_csv()

def sync_to_csv():
    conn = get_connection()
    try:
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
        customers_df.to_csv('customers_backup.csv', index=False, encoding='utf-8-sig')
        query = '''
            SELECT s.*, c.name AS customer_name, c.phone 
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
        '''
        sales_df = pd.read_sql(query, conn)
        sales_df.to_csv('sales_backup.csv', index=False, encoding='utf-8-sig')
    finally:
        conn.close()

# --- 2. 비즈니스 로직 함수 ---
def manage_customer(action, c_id=None, data=None):
    conn = get_connection()
    c = conn.cursor()
    if action == "add":
        c.execute('''INSERT INTO customers (name, phone, birth, address, size, notes, join_date, points) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, 0)''', 
                  (data['name'], data['phone'], data['birth'], data['address'], data['size'], data['notes'], data['join_date']))
    elif action == "update":
        c.execute('''UPDATE customers SET name=?, phone=?, birth=?, address=?, size=?, notes=? WHERE id=?''', 
                  (data['name'], data['phone'], data['birth'], data['address'], data['size'], data['notes'], c_id))
    elif action == "delete":
        c.execute("DELETE FROM customers WHERE id=?", (c_id,))
        c.execute("DELETE FROM sales WHERE customer_id=?", (c_id,))
    conn.commit()
    conn.close()
    sync_to_csv()

def add_transaction(c_id, t_data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO sales 
                 (customer_id, type, location, sale_date, item_name, item_code, spec, unit,
                  unit_price, quantity, supply_value, tax, sale_amount, add_amount, 
                  discount_amount, total_amount, remarks) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (c_id, t_data['type'], t_data['location'], t_data['sale_date'], t_data['item_name'], 
               t_data['item_code'], t_data['spec'], t_data['unit'], t_data['unit_price'], 
               t_data['quantity'], t_data['supply_value'], t_data['tax'], t_data['sale_amount'], 
               t_data['add_amount'], t_data['discount_amount'], t_data['total_amount'], t_data['remarks']))
    adj = 0.05 if t_data['type'] == "판매" else -0.05
    c.execute("UPDATE customers SET points = points + ? WHERE id = ?", (int(t_data['total_amount'] * adj), c_id))
    conn.commit()
    conn.close()
    sync_to_csv()

# --- 3. UI 렌더링 ---
def render_integrated_management():
    st.title("👕 통합 고객 및 매출 관리")

    # 1단계: 상단바 (검색 및 신규 등록)
    col_search, col_add = st.columns([3, 1])
    with col_search:
        search_q = st.text_input("🔍 고객 검색 (이름 또는 연락처)", placeholder="검색어를 입력하면 리스트가 필터링됩니다.")
    with col_add:
        st.write(" ") # 정렬용
        if st.button("➕ 신규 회원 등록", use_container_width=True):
            st.session_state['show_add_form'] = not st.session_state.get('show_add_form', False)

    if st.session_state.get('show_add_form', False):
        with st.container(border=True):
            with st.form("new_customer_form", clear_on_submit=True):
                st.write("### 🆕 신규 회원 정보 입력")
                c1, c2, c3 = st.columns(3)
                n_name = c1.text_input("고객명*")
                n_phone = c2.text_input("연락처*")
                n_size = c3.text_input("사이즈")
                c4, c5 = st.columns(2)
                n_birth = c4.date_input("생년월일", value=datetime(1990, 1, 1))
                n_join = c5.date_input("가입일", value=datetime.now())
                n_addr = st.text_input("주소")
                n_notes = st.text_area("비고")
                if st.form_submit_button("저장하기"):
                    if n_name and n_phone:
                        manage_customer("add", data={'name': n_name, 'phone': n_phone, 'birth': str(n_birth), 'address': n_addr, 'size': n_size, 'notes': n_notes, 'join_date': str(n_join)})
                        st.success("등록 완료!")
                        st.session_state['show_add_form'] = False
                        st.rerun()

    st.divider()

    # 2단계: 회원 리스트 (전체 보기 + 검색 필터링)
    conn = get_connection()
    if search_q:
        query = f"SELECT * FROM customers WHERE name LIKE '%{search_q}%' OR phone LIKE '%{search_q}%' ORDER BY name ASC"
    else:
        query = "SELECT * FROM customers ORDER BY id DESC"
    
    all_customers = pd.read_sql(query, conn)
    conn.close()

    if not all_customers.empty:
        # 페이지네이션
        page_size = 10
        total_pages = max((len(all_customers) // page_size) + (1 if len(all_customers) % page_size > 0 else 0), 1)
        p_col1, p_col2 = st.columns([1, 5])
        current_page = p_col1.selectbox("페이지", range(1, total_pages + 1))
        
        start_idx = (current_page - 1) * page_size
        page_df = all_customers.iloc[start_idx : start_idx + page_size]

        st.write(f"📢 총 **{len(all_customers)}명**의 회원이 있습니다.")
        
        # 헤더
        h = st.columns([1, 1.5, 2, 1.5, 1.5, 1])
        h[0].markdown("**ID**")
        h[1].markdown("**고객명**")
        h[2].markdown("**연락처**")
        h[3].markdown("**사이즈**")
        h[4].markdown("**포인트**")
        h[5].markdown("**작업**")

        # 회원 리스트 출력 구간
        for _, row in page_df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 2, 1.5, 1.5, 1])
                c1.text(row['id'])
                c2.text(row['name'])
                c3.text(row['phone'])
                c4.text(row['size'] if row['size'] else "-")
                c5.text(f"{row['points']:,} P")
                
                # 버튼을 클릭하면 세션 상태를 토글하여 상세 정보를 보여줌
                if c6.button("조회/관리", key=f"btn_{row['id']}"):
                    st.session_state[f"detail_{row['id']}"] = not st.session_state.get(f"detail_{row['id']}", False)

                # 상세 정보 창이 활성화되었을 때
                if st.session_state.get(f"detail_{row['id']}", False):
                    with st.container(border=True):
                        # 상단에 회원 핵심 정보 요약 표시
                        st.markdown(f"### 📋 {row['name']} 고객 상세 프로필")
                        inf1, inf2, inf3 = st.columns(3)
                        inf1.write(f"**생년월일:** {row['birth']}")
                        inf2.write(f"**가입일:** {row['join_date']}")
                        inf3.write(f"**주소:** {row['address'] if row['address'] else '미등록'}")
                        if row['notes']:
                            st.info(f"**고객 특이사항:** {row['notes']}")

                        st.divider()

                        # 작업 탭 구성
                        t1, t2, t3 = st.tabs(["🛒 신규 판매 등록", "📜 전체 판매 내역", "⚙️ 정보 수정/삭제"])
                        
                        with t1: # 신규 거래 등록 (세분화된 양식)
                            with st.form(f"sale_form_{row['id']}"):
                                s1, s2, s3 = st.columns(3)
                                t_date = s1.date_input("구매일", value=datetime.now())
                                t_type = s2.radio("거래구분", ["판매", "반품"], horizontal=True)
                                t_loc = s3.radio("장소", ["매장", "행사매장"], horizontal=True)
                                
                                s4, s5, s6 = st.columns([2, 1, 1])
                                t_item = s4.text_input("품목명*")
                                t_code = s5.text_input("품목번호")
                                t_spec = s6.text_input("규격(사이즈/색상)")
                                
                                s7, s8, s9, s10 = st.columns(4)
                                t_u_price = s7.number_input("단가", min_value=0, step=100)
                                t_qty = s8.number_input("수량", min_value=1, step=1)
                                t_add = s9.number_input("추가금액", value=0)
                                t_disc = s10.number_input("할인금액", value=0)
                                
                                t_total = (t_u_price * t_qty) + t_add - t_disc
                                st.markdown(f"#### 💰 최종 합계 금액: {t_total:,}원")
                                
                                if st.form_submit_button("거래 내역 저장"):
                                    if t_item:
                                        add_transaction(row['id'], {
                                            'type': t_type, 'location': t_loc, 'sale_date': str(t_date),
                                            'item_name': t_item, 'item_code': t_code, 'spec': t_spec, 'unit': 'pcs',
                                            'unit_price': t_u_price, 'quantity': t_qty, 'supply_value': int(t_total/1.1),
                                            'tax': t_total - int(t_total/1.1), 'sale_amount': t_u_price*t_qty,
                                            'add_amount': t_add, 'discount_amount': t_disc, 'total_amount': t_total, 'remarks': ''
                                        })
                                        st.success("거래가 등록되었습니다.")
                                        st.rerun()

                        with t2: # 전체 판매 내역 (상세 필드 표시)
                            conn = get_connection()
                            h_df = pd.read_sql(f"SELECT sale_date, type, item_name, item_code, spec, unit_price, quantity, total_amount, location FROM sales WHERE customer_id = {row['id']} ORDER BY sale_date DESC", conn)
                            conn.close()
                            
                            if not h_df.empty:
                                st.dataframe(h_df, use_container_width=True)
                            else:
                                st.write("구매 내역이 없습니다.")

                        with t3: # 정보 수정 및 삭제
                            with st.form(f"edit_form_{row['id']}"):
                                e1, e2 = st.columns(2)
                                en = e1.text_input("이름", value=row['name'])
                                ep = e2.text_input("연락처", value=row['phone'])
                                eb = e1.date_input("생년월일", value=datetime.strptime(row['birth'], '%Y-%m-%d') if row['birth'] else datetime(1990, 1, 1))
                                es = e2.text_input("사이즈", value=row['size'])
                                ea = st.text_input("주소", value=row['address'])
                                et = st.text_area("메모", value=row['notes'])
                                
                                b1, b2 = st.columns(2)
                                if b1.form_submit_button("회원 정보 수정"):
                                    manage_customer("update", c_id=row['id'], data={'name': en, 'phone': ep, 'birth': str(eb), 'address': ea, 'size': es, 'notes': et})
                                    st.success("수정 완료!")
                                    st.rerun()
                                if b2.form_submit_button("🚨 회원 삭제"):
                                    manage_customer("delete", c_id=row['id'])
                                    st.rerun()
                st.divider()
    else:
        st.info("데이터가 없습니다. 회원을 먼저 등록해 주세요.")

def render_stats():
    st.header("📊 통계 및 데이터 관리")
    if os.path.exists('sales_backup.csv'):
        df = pd.read_csv('sales_backup.csv')
        st.metric("총 실매출액", f"{int(df[df['type']=='판매']['total_amount'].sum() - df[df['type']=='반품']['total_amount'].sum()):,}원")
        st.dataframe(df, use_container_width=True)
        st.download_button("엑셀용 CSV 다운로드", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sales_data.csv")

def main():
    st.set_page_config(page_title="통합 매장 관리", layout="wide")
    init_db()
    menu = st.sidebar.radio("메뉴 이동", ["통합 관리 화면", "매출 통계"])
    if menu == "통합 관리 화면": render_integrated_management()
    else: render_stats()

if __name__ == "__main__": main()