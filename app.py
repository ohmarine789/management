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
                  name TEXT, phone TEXT, points INTEGER, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  customer_id INTEGER, item_name TEXT, price INTEGER, date TEXT)''')
    conn.commit()
    conn.close()
    sync_to_csv()

def sync_to_csv():
    """DB 내용을 CSV 파일로 내보낼 때, 판매 기록에 고객 이름을 포함시킵니다."""
    conn = get_connection()
    try:
        customers_df = pd.read_sql("SELECT * FROM customers", conn)
        customers_df.to_csv('customers_backup.csv', index=False, encoding='utf-8-sig')
        
        # JOIN을 사용하여 고객 이름이 포함된 판매 리스트 생성
        query = '''
            SELECT s.id, c.name AS customer_name, c.phone, s.item_name, s.price, s.date 
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
        '''
        sales_df = pd.read_sql(query, conn)
        sales_df.to_csv('sales_backup.csv', index=False, encoding='utf-8-sig')
    finally:
        conn.close()

# --- 2. 비즈니스 로직 함수 ---
def register_customer(name, phone, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, phone, points, notes) VALUES (?, ?, ?, ?)", 
              (name, phone, 0, notes))
    conn.commit()
    conn.close()
    sync_to_csv()

def add_sale_record(c_id, item, price, current_points):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO sales (customer_id, item_name, price, date) VALUES (?, ?, ?, ?)",
              (c_id, item, price, now))
    new_points = current_points + int(price * 0.05)
    c.execute("UPDATE customers SET points = ? WHERE id = ?", (new_points, c_id))
    conn.commit()
    conn.close()
    sync_to_csv()
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
                st.success(f"✅ {name} 고객 등록 완료")
            else:
                st.warning("필수 정보를 입력하세요.")

def render_customer_management():
    st.header("🔍 고객 관리 및 판매")
    search_name = st.text_input("고객 이름 검색")
    
    if search_name:
        conn = get_connection()
        # 검색 결과 리스트로 보여주기
        customer_df = pd.read_sql(f"SELECT * FROM customers WHERE name LIKE '%{search_name}%'", conn)
        conn.close()

        if not customer_df.empty:
            # 여러 명일 경우 선택할 수 있게 처리
            customer_list = [f"{row['name']} ({row['phone']})" for _, row in customer_df.iterrows()]
            selected_customer = st.selectbox("고객 선택", customer_list)
            
            # 선택된 고객 정보 추출
            idx = customer_list.index(selected_customer)
            c_info = customer_df.iloc[idx]
            c_id, c_name, c_phone, c_points, c_notes = c_info['id'], c_info['name'], c_info['phone'], c_info['points'], c_info['notes']
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("고객 상세 정보")
                st.write(f"**이름:** {c_name}")
                st.write(f"**연락처:** {c_phone}")
                st.metric("현재 포인트", f"{c_points}P")
                st.info(f"📝 메모: {c_notes}")

            with col2:
                st.subheader("🛒 구매 등록")
                item = st.text_input("상품명")
                price = st.number_input("가격", min_value=0, step=1000)
                if st.button("구매 확정"):
                    add_sale_record(c_id, item, price, c_points)
                    st.success("구매 완료!")
                    st.rerun()

            st.divider()
            st.subheader(f"📅 {c_name} 고객님의 구매 이력")
            conn = get_connection()
            hist = pd.read_sql(f"SELECT item_name, price, date FROM sales WHERE customer_id = {c_id} ORDER BY date DESC", conn)
            conn.close()
            st.dataframe(hist, use_container_width=True)
        else:
            st.error("검색된 고객이 없습니다.")

def render_dashboard():
    st.header("📊 매장 전체 현황")
    if os.path.exists('sales_backup.csv'):
        # CSV 파일로부터 데이터 로드
        sales_df = pd.read_csv('sales_backup.csv')
        
        m1, m2 = st.columns(2)
        m1.metric("총 매출액", f"{int(sales_df['price'].sum()):,}원")
        m2.metric("총 판매 건수", f"{len(sales_df)}건")
        
        st.subheader("📝 전체 판매 이력 (구매자 포함)")
        # 표 형식 보기 좋게 정리
        display_df = sales_df.rename(columns={
            'customer_name': '구매자',
            'phone': '연락처',
            'item_name': '상품명',
            'price': '가격',
            'date': '구매일시'
        })
        st.dataframe(display_df[['구매자', '연락처', '상품명', '가격', '구매일시']], use_container_width=True)
        
        st.download_button(
            label="전체 판매 기록 CSV 다운로드",
            data=sales_df.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"all_sales_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )
    else:
        st.info("판매 데이터가 아직 없습니다.")

def main():
    st.set_page_config(page_title="의류 매장 CRM", layout="wide")
    init_db()

    st.sidebar.title("🧥 CRM 시스템")
    choice = st.sidebar.radio("메뉴", ["고객 조회/판매", "신규 고객 등록", "대시보드"])

    if choice == "고객 조회/판매":
        render_customer_management()
    elif choice == "신규 고객 등록":
        render_registration()
    elif choice == "대시보드":
        render_dashboard()

if __name__ == "__main__":
    main()