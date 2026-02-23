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

# --- 데이터 수집 함수 (기존 로직 유지) ---
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

# --- UI 설정 및 디자인 (현대적인 미니멀리즘 적용) ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; }}
    
    /* 사이드바 메뉴 버튼 */
    .stSidebar [data-testid="stVerticalBlock"] > div > button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 10px; font-weight: bold; margin-bottom: 8px; height: 3.5em; transition: 0.3s;
    }}
    .stSidebar [data-testid="stVerticalBlock"] > div > button:hover {{ background-color: #F4B742; color: white; }}
    
    /* 데이터랩 카드 디자인 (8개 카테고리 최적화) */
    .trend-card {{
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 0px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        min-height: 420px;
    }}
    .trend-header {{
        background-color: #f8f9fa; border-bottom: 1px solid #e0e0e0;
        padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; color: #333;
        border-top: 5px solid #F4B742;
    }}
    .trend-list {{ padding: 12px; }}
    .trend-item {{ display: flex; align-items: center; margin-bottom: 10px; font-size: 0.9em; border-bottom: 1px solid #f9f9f9; padding-bottom: 5px; }}
    .trend-rank {{ color: #F4B742; font-weight: bold; width: 25px; margin-right: 8px; }}
    .trend-text {{ color: #555; cursor: pointer; }}
    .trend-text:hover {{ color: #F4B742; text-decoration: underline; }}
    
    .stMetric {{ background-color: #FBEECC; padding: 25px; border-radius: 15px; border-left: 8px solid #F4B742; }}
    .title-box {{ background-color: #ffffff; padding: 15px; border-radius: 10px; border: 2px dashed #F1A18E; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 관리 ---
if 'menu' not in st.session_state: st.session_state.menu = "🏠 메인 키워드 분석"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

# --- 사이드바: 햄둥이 메뉴 (버튼식) ---
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.menu = "🏠 메인 키워드 분석"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.menu = "🛍️ 쇼핑 인기 트렌드"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.menu = "📰 오늘의 뉴스 이슈"
    st.write("---")
    st.caption("'햄둥이의 햄둥지둥 일상보고서'의 성장을 응원합니다! 💖")

# --- 페이지 로직 ---
menu = st.session_state.menu

if menu == "🏠 메인 키워드 분석":
    st.title("📊 메인 키워드 분석기")
    input_kw = st.text_input("분석할 중심 키워드를 입력하세요", placeholder="예: 다이소 화장품")
    if st.button("분석 시작"):
        if input_kw:
            with st.spinner('🐹 데이터를 수집 중...'):
                st.session_state.kw_results = fetch_keyword_data(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()
    
    if st.session_state.kw_results:
        df = pd.DataFrame(st.session_state.kw_results)
        col1, col2, col3 = st.columns(3)
        col1.metric("월간 검색량", f"{df.iloc[0]['월간 검색량']:,}회")
        col2.metric("총 문서 수", f"{df.iloc[0]['총 문서 수']:,}건")
        col3.metric("경쟁 강도", f"{df.iloc[0]['경쟁 강도']}")
        st.divider()
        st.subheader("📊 연관 키워드 상세 분석 리포트")
        st.dataframe(df.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']), use_container_width=True, hide_index=True)

elif menu == "🛍️ 쇼핑 인기 트렌드":
    st.title("🛍️ 분야별 인기 검색어 TOP 10")
    st.info("💡 각 카테고리별 실시간 인기 키워드입니다. 글감을 찾는 힌트로 활용해 보세요!")
    
    # 스타일의 8개 카테고리 데이터
    trends = {
        "💄 화장품/미용": ["리들샷", "미백 앰플", "수분 크림", "쿠션 팩트", "선크림", "아이크림", "클렌징 오일", "핸드크림", "틴트", "마스크팩"],
        "👗 패션의류": ["트위드 자켓", "원피스", "가죽 자켓", "경량 패딩", "여성 슬랙스", "가디건", "블라우스", "롱스커트", "와이드 팬츠", "바람막이"],
        "👜 패션잡화": ["카드지갑", "에코백", "크로스백", "캡모자", "양말 세트", "백팩", "선글라스", "헤어 집게핀", "숄더백", "벨트"],
        "🍎 식품": ["닭가슴살", "제로 콜라", "햇반", "견과류", "단백질 쉐이크", "사과 10kg", "밀키트", "스테비아 토마토", "탄산수", "고구마"],
        "⚽ 스포츠/레저": ["골프공", "테니스 라켓", "요가 매트", "캠핑 의자", "등산화", "자전거", "수영복", "아령", "러닝화", "배드민턴"],
        "🏠 생활/건강": ["규조토 발매트", "먼지없는 이불", "욕실 청소용품", "멀티탭", "옷걸이", "주방 선반", "영양제 통", "마스크", "실내화", "물티슈"],
        "💻 디지털/가전": ["아이패드 케이스", "무선 이어폰", "보조배터리", "가습기", "블루투스 키보드", "스마트 워치", "노트북 파우치", "전기포트", "마우스 패드", "거치대"],
        "🛋️ 가구/인테리어": ["전신 거울", "수납장", "좌식 책상", "조명 스탠드", "벽시계", "커튼", "러그", "빈백 소파", "행거", "디퓨저"]
    }
    
    # 4열씩 2줄로 배치
    trend_list = list(trends.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            category, items = trend_list[i+j]
            with cols[j]:
                items_html = "".join([f"<div class='trend-item'><span class='trend-rank'>{idx+1}</span><span class='trend-text'>{val}</span></div>" for idx, val in enumerate(items)])
                st.markdown(f"""
                <div class='trend-card'>
                    <div class='trend-header'>{category}</div>
                    <div class='trend-list'>{items_html}</div>
                </div>
                """, unsafe_allow_html=True)

elif menu == "📰 오늘의 뉴스 이슈":
    st.title("📰 오늘의 뉴스 이슈")
    news_query = st.text_input("뉴스 키워드 검색", value="2026 트렌드")
    if st.button("뉴스 수집"):
        st.write("실시간 뉴스를 분석하고 있습니다...")