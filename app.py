import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. 데이터베이스 관련 함수 ---
def get_connection():
    """DB 연결을 생성하고 커서를 반환합니다."""
    conn = sqlite3.connect('store_crm.db', check_same_thread=False)
    return conn

def init_db():
    """데이터베이스 테이블을 초기화합니다."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, phone TEXT, points INTEGER, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  customer_id INTEGER, item_name TEXT, price INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

# --- 2. 비즈니스 로직 함수 ---
def register_customer(name, phone, notes):
    """신규 고객을 등록합니다."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, phone, points, notes) VALUES (?, ?, ?, ?)", 
              (name, phone, 0, notes))
    conn.commit()
    conn.close()

def add_sale_record(c_id, item, price, current_points):
    """판매 기록을 추가하고 포인트를 업데이트합니다."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 판매 기록 추가
    c.execute("INSERT INTO sales (customer_id, item_name, price, date) VALUES (?, ?, ?, ?)",
              (c_id, item, price, now))
    
    # 포인트 적립 (5%)
    new_points = current_points + int(price * 0.05)
    c.execute("UPDATE customers SET points = ? WHERE id = ?", (new_points, c_id))
    
    conn.commit()
    conn.close()
    return new_points

# --- 3. UI 렌더링 함수 ---
def render_registration():
    st.header("👤 신규 고객 등록")
    with st.form("customer_form", clear_on_submit=True):
        name = st.text_input("고객 이름")
        phone = st.text_input("전화번호")
        notes = st.text_area("특이사항")
        if st.form_submit_button("등록하기"):
            if name and phone:
                register_customer(name, phone, notes)
                st.success(f"✅ {name} 고객님이 등록되었습니다.")
            else:
                st.warning("이름과 전화번호를 입력해주세요.")

def render_customer_management():
    st.header("🔍 고객 관리 및 판매")
    search_name = st.text_input("고객 이름 검색")
    
    if search_name:
        conn = get_connection()
        customer = pd.read_sql(f"SELECT * FROM customers WHERE name LIKE '%{search_name}%'", conn)
        conn.close()

        if not customer.empty:
            # 첫 번째 검색 결과 사용
            c_id, c_name, c_phone, c_points, c_notes = customer.iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("고객 정보")
                st.write(f"**이름:** {c_name} | **연락처:** {c_phone}")
                st.metric("현재 포인트", f"{c_points}P")
                st.info(f"📝 메모: {c_notes}")

            with col2:
                st.subheader("🛒 구매 등록")
                item = st.text_input("상품명")
                price = st.number_input("가격", min_value=0, step=1000)
                if st.button("구매 확정"):
                    new_pts = add_sale_record(c_id, item, price, c_points)
                    st.success(f"구매 완료! (새 포인트: {new_pts}P)")
                    st.rerun() # 화면 갱신

            st.divider()
            st.subheader("📅 이 고객의 구매 이력")
            conn = get_connection()
            hist = pd.read_sql(f"SELECT item_name, price, date FROM sales WHERE customer_id = {c_id} ORDER BY date DESC", conn)
            conn.close()
            st.dataframe(hist, use_container_width=True)
        else:
            st.error("검색된 고객이 없습니다.")

def render_dashboard():
    st.header("📊 매장 현황")
    conn = get_connection()
    sales_df = pd.read_sql("SELECT * FROM sales", conn)
    customers_df = pd.read_sql("SELECT * FROM customers", conn)
    conn.close()

    m1, m2 = st.columns(2)
    m1.metric("총 매출액", f"{sales_df['price'].sum():,}원")
    m2.metric("등록 고객 수", f"{len(customers_df)}명")
    
    st.subheader("전체 판매 로그")
    st.dataframe(sales_df, use_container_width=True)

# --- 4. 메인 컨트롤러 ---
def main():
    st.set_page_config(page_title="의류 매장 CRM", layout="wide")
    init_db() # 프로그램 시작 시 DB 초기화 확인

    st.sidebar.title("🧥 매장 관리 시스템")
    menu = ["고객 조회/판매", "신규 고객 등록", "대시보드"]
    choice = st.sidebar.radio("메뉴 이동", menu)

    if choice == "고객 조회/판매":
        render_customer_management()
    elif choice == "신규 고객 등록":
        render_registration()
    elif choice == "대시보드":
        render_dashboard()

if __name__ == "__main__":
    main()