import streamlit as st
import pandas as pd
import time
import hashlib
import hmac
import base64
import requests
import random

# --- [보안] Streamlit Secrets 적용 ---
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

# --- 데이터 수집 및 제목 생성 함수들 (기존과 동일) ---
def fetch_keyword_data(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    method = "GET"
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    headers = get_header(method, uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    ad_res = requests.get("https://api.naver.com" + uri, params=params, headers=headers)
    res_json = ad_res.json()
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
        search_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        search_res = requests.get(search_url, headers=search_headers)
        doc_count = search_res.json().get('total', 0)
        comp_idx = round(doc_count / search_vol, 2) if search_vol > 0 else 0
        results.append({"키워드": kw, "월간 검색량": search_vol, "총 문서 수": doc_count, "경쟁 강도": comp_idx})
    return results

def fetch_trend_data(query, category="news"):
    url = f"https://openapi.naver.com/v1/search/{category}.json?query={query}&display=10&sort=sim"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    res = requests.get(url, headers=headers)
    return res.json().get('items', [])

def generate_titles(keyword):
    styles = {
        "감성형": [f"✨ [공감] {keyword} 고민인 당신에게", f"🌿 {keyword} 속 작은 행복"],
        "정보형": [f"📝 햄둥이의 {keyword} 핵심 가이드", f"🔍 {keyword} 완벽 정리"],
        "궁금증형": [f"😮 {keyword} 설마 아직도 모르세요?", f"⚠️ {keyword} 전 필수 체크!"],
        "일상형": [f"🐹 햄둥지둥 일상: {keyword}", f"🐾 {keyword} 탐방기"],
        "후기형": [f"💡 {keyword} 실패 없는 선택!", f"🌟 {keyword} 내돈내산 찐후기"]
    }
    return [random.choice(v) for k, v in styles.items()]

# --- UI 설정 및 디자인 ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")

# 햄둥이 테마 컬러 적용: 몸통(#F4B742), 배(#FBEECC), 볼터치(#F1A18E)
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; padding-top: 20px; }}
    
    /* 사이드바 메뉴 버튼 스타일 */
    .stSidebar [data-testid="stVerticalBlock"] > div > button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 10px; font-weight: bold; margin-bottom: 5px; height: 3.5em; transition: 0.3s;
    }}
    .stSidebar [data-testid="stVerticalBlock"] > div > button:hover {{
        background-color: #F4B742; color: white;
    }}
    
    /* 메인 버튼 및 스타일 */
    .stButton>button {{ background-color: #F4B742; color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3.5em; }}
    .stMetric {{ background-color: #FBEECC; padding: 25px; border-radius: 15px; border-left: 8px solid #F4B742; }}
    .title-box {{ background-color: #ffffff; padding: 15px; border-radius: 10px; border: 2px dashed #F1A18E; margin-bottom: 10px; }}
    .trend-card {{ background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #FBEECC; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 상태 초기화 (메뉴 및 결과 저장용) ---
if 'menu' not in st.session_state:
    st.session_state.menu = "🏠 메인 키워드 분석"
if 'kw_results' not in st.session_state:
    st.session_state.kw_results = None

# --- 사이드바: 햄둥이 메뉴 (버튼식) ---
with st.sidebar:
    # 🐹 이미지 깨짐 방지: 이모지와 텍스트로 깔끔하게 구성하거나 신뢰할 수 있는 URL 사용
    st.markdown("<h1 style='text-align: center;'>🐹</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #333;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    
    # 버튼식 메뉴 구현
    if st.button("🏠 메인 키워드 분석", use_container_width=True):
        st.session_state.menu = "🏠 메인 키워드 분석"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True):
        st.session_state.menu = "🛍️ 쇼핑 인기 트렌드"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True):
        st.session_state.menu = "📰 오늘의 뉴스 이슈"
        
    st.write("---")
    st.caption("'햄둥이의 햄둥지둥 일상보고서'의 성장을 응원합니다! 💖")

# --- 선택된 메뉴에 따른 페이지 표시 ---
menu = st.session_state.menu

if menu == "🏠 메인 키워드 분석":
    st.title("📊 메인 키워드 분석기")
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 다이소 화장품")
    
    if st.button("실시간 통합 분석 시작!"):
        if input_kw:
            with st.spinner('🐹 햄둥이가 데이터를 물어오는 중...'):
                results = fetch_keyword_data(input_kw)
                st.session_state.kw_results = results
                st.session_state.kw_target = input_kw
                st.balloons()
        else: st.warning("키워드를 입력해 주세요.")

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
        st.subheader("📊 연관 키워드 상세 분석 리포트")
        df_related = df[df['키워드'].str.replace(" ", "") != target.replace(" ", "")].sort_values(by="경쟁 강도")
        st.dataframe(df_related.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']), use_container_width=True, hide_index=True)
        
        if not df_related.empty:
            st.success(f"🐹 햄둥이의 추천: 현재 **[{df_related.iloc[0]['키워드']}]** 키워드가 공략하기 가장 좋습니다!")

        st.divider()
        st.subheader("✍️ 햄둥이의 감성 제목 추천")
        selected_kw = st.selectbox("제목을 지을 키워드 선택", df['키워드'].tolist())
        if selected_kw:
            for title in generate_titles(selected_kw):
                st.markdown(f"<div class='title-box'>{title}</div>", unsafe_allow_html=True)

elif menu == "🛍️ 쇼핑 인기 트렌드":
    st.title("🛍️ 쇼핑 인기 트렌드")
    st.info("💡 '화장품'과 '미용' 분야의 최신 트렌드 아이템입니다.")
    search_query = st.text_input("트렌드를 알고 싶은 카테고리/상품명", value="무스탕")
    if st.button("트렌드 확인"):
        items = fetch_trend_data(search_query, category="shop")
        for item in items:
            st.markdown(f"""
            <div class='trend-card'>
                <h4 style='color:#F4B742;'>🛒 {item['title'].replace('<b>','').replace('</b>','')}</h4>
                <p>최저가: {item['lprice']}원 | 판매처: {item['mallName']}</p>
                <a href='{item['link']}' target='_blank'>상품 상세 보기</a>
            </div>
            """, unsafe_allow_html=True)

elif menu == "📰 오늘의 뉴스 이슈":
    st.title("📰 오늘의 뉴스 이슈")
    st.info("💡 블로그 포스팅 소재로 활용하기 좋은 최신 이슈들입니다.")
    news_query = st.text_input("뉴스 키워드 검색", value="2026 트렌드")
    if st.button("뉴스 키워드 수집"):
        news_items = fetch_trend_data(news_query, category="news")
        for news in news_items:
            st.markdown(f"""
            <div class='trend-card'>
                <h4 style='color:#F1A18E;'>📢 {news['title'].replace('<b>','').replace('</b>','')}</h4>
                <p>{news['description'].replace('<b>','').replace('</b>','')[:100]}...</p>
                <a href='{news['link']}' target='_blank'>기사 원문 보기</a>
            </div>
            """, unsafe_allow_html=True)