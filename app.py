import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import random

# --- [보안] Streamlit Secrets ---
NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
AD_ACCESS_KEY = st.secrets["AD_ACCESS_KEY"]
AD_SECRET_KEY = st.secrets["AD_SECRET_KEY"]
AD_CUSTOMER_ID = st.secrets["AD_CUSTOMER_ID"]

# --- 공통 함수: 네이버 인증 ---
def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    signature = hmac.new(secret_key.encode(), (timestamp + "." + method + "." + uri).encode(), hashlib.sha256).digest()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": base64.b64encode(signature).decode()
    }

# --- 데이터 수집 함수 ---
def fetch_keyword_data(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    res = requests.get("https://api.naver.com" + uri, params=params, headers=headers)
    res_json = res.json()
    if 'keywordList' not in res_json: return []
    all_keywords = res_json['keywordList'][:15]
    results = []
    for item in all_keywords:
        kw = item['relKeyword']
        def clean_count(val):
            if isinstance(val, str) and '<' in val: return 10
            return int(val)
        search_vol = clean_count(item['monthlyPcQcCnt']) + clean_count(item['monthlyMobileQcCnt'])
        search_url = f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=1"
        search_res = requests.get(search_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET})
        doc_count = search_res.json().get('total', 0)
        results.append({"키워드": kw, "월간 검색량": search_vol, "총 문서 수": doc_count, "경쟁 강도": round(doc_count / search_vol, 2) if search_vol > 0 else 0})
    return results

# --- UI 설정 및 디자인 (모바일 최적화 CSS 포함) ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }}
    
    /* 사이드바 메뉴 버튼 */
    .stSidebar [data-testid="stVerticalBlock"] div[data-testid="stButton"] button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 12px; font-weight: bold; margin-bottom: 10px; height: 4em; width: 100%;
    }}
    
    /* 지표 및 카드 스타일 */
    .stMetric {{ background-color: #FBEECC; padding: 25px; border-radius: 15px; border-left: 8px solid #F4B742; }}
    .trend-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
    .trend-header {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F4B742; }}
    .trend-header-news {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F1A18E; }}
    
    @media (max-width: 768px) {{
        [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 상태 ---
if 'menu' not in st.session_state: st.session_state.menu = "🏠 메인 키워드 분석"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

def change_menu(target): st.session_state.menu = target

# --- 사이드바 ---
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    st.button("🏠 메인 키워드 분석", on_click=change_menu, args=("🏠 메인 키워드 분석",), use_container_width=True)
    st.button("🛍️ 쇼핑 인기 트렌드", on_click=change_menu, args=("🛍️ 쇼핑 인기 트렌드",), use_container_width=True)
    st.button("📰 오늘의 뉴스 이슈", on_click=change_menu, args=("📰 오늘의 뉴스 이슈",), use_container_width=True)
    st.write("---")
    st.caption("🐹 햄둥이와 함께 블로그 100개 글쓰기 정복!")

# --- 페이지 로직 ---
menu = st.session_state.menu

if menu == "🏠 메인 키워드 분석":
    st.title("📊 키워드 분석 리포트")
    input_kw = st.text_input("분석할 키워드 입력", placeholder="예: 다이소 화장품")
    if st.button("실시간 통합 분석 시작"):
        if input_kw:
            with st.spinner('🐹 데이터를 수집 중...'):
                st.session_state.kw_results = fetch_keyword_data(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()
    
    if st.session_state.kw_results:
        df = pd.DataFrame(st.session_state.kw_results)
        target = st.session_state.kw_target
        
        # 상단 요약 지표
        seed_data = df[df['키워드'].str.replace(" ", "") == target.replace(" ", "")]
        if seed_data.empty: seed_data = df.iloc[[0]]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("월간 검색량", f"{seed_data.iloc[0]['월간 검색량']:,}회")
        col2.metric("총 문서 수", f"{seed_data.iloc[0]['총 문서 수']:,}건")
        col3.metric("경쟁 강도", f"{seed_data.iloc[0]['경쟁 강도']}")

        st.divider()
        st.subheader("📊 연관 키워드 분석 (경쟁 강도 컬러링)")
        
        # [부활] 경쟁 강도 컬럼에 컬러 그라데이션 적용
        df_display = df[df['키워드'].str.replace(" ", "") != target.replace(" ", "")].sort_values(by="경쟁 강도")
        st.dataframe(
            df_display.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']),
            use_container_width=True, hide_index=True
        )
        
        if not df_display.empty:
            st.success(f"🐹 햄둥이의 추천: 현재 **[{df_display.iloc[0]['키워드']}]** 키워드가 가장 공략하기 좋습니다!")

# (쇼핑 트렌드 및 뉴스 이슈 로직은 이전과 동일하게 유지됩니다.)
elif menu == "🛍️ 쇼핑 인기 트렌드":
    st.title("🛍️ 분야별 트렌드 TOP 10")
    # ... (생략)