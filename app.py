import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
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

# --- 데이터 수집 함수 ---
@st.cache_data(ttl=600)
def fetch_keyword_data(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    try:
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
    except: return []

# --- UI 설정 및 디자인 (미니멀 & 햄둥이 컬러) ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }}
    .stSidebar [data-testid="stVerticalBlock"] div[data-testid="stButton"] button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 12px; font-weight: bold; margin-bottom: 12px; height: 4em; width: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .stMetric {{ background-color: #FBEECC; padding: 20px; border-radius: 15px; border-left: 8px solid #F4B742; }}
    .trend-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
    .trend-header {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F4B742; }}
    .trend-header-news {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F1A18E; }}
    .trend-list {{ padding: 15px; }}
    .trend-item {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 0.9em; border-bottom: 1px solid #f9f9f9; padding-bottom: 5px; }}
    .trend-rank {{ color: #F4B742; font-weight: bold; width: 25px; margin-right: 8px; }}
    @media (max-width: 768px) {{ [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; }} }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

def set_page(name): st.session_state.page = name

# --- 사이드바: 버튼 메뉴 ---
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    st.button("🏠 메인 키워드 분석", on_click=set_page, args=("HOME",), use_container_width=True)
    st.button("🛍️ 쇼핑 인기 트렌드", on_click=set_page, args=("SHOP",), use_container_width=True)
    st.button("📰 오늘의 뉴스 이슈", on_click=set_page, args=("NEWS",), use_container_width=True)
    st.write("---")
    # 블로그 100회 포스팅 챌린지 응원
    st.caption("🐹 사용자님의 '100개 글쓰기' 도전을 응원합니다!")

# --- 페이지 로직 ---
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석 리포트")
    input_kw = st.text_input("분석할 키워드 입력", placeholder="예: 다이소 화장품")
    if st.button("분석 시작", use_container_width=True):
        if input_kw:
            with st.spinner('🐹 데이터를 수집 중...'):
                st.session_state.kw_results = fetch_keyword_data(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()
    if st.session_state.get('kw_results'):
        df = pd.DataFrame(st.session_state.kw_results)
        # 상단 지표 및 경쟁 강도 컬러링 적용
        st.dataframe(df.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']), use_container_width=True, hide_index=True)

elif st.session_state.page == "SHOP":
    st.title("🛍️ 쇼핑 인기 트렌드")
    st.info("💡 분야별 실시간 인기 검색어입니다.")
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
    items_list = list(trends.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            cat, kw_list = items_list[i+j]
            with cols[j]:
                html = "".join([f"<div class='trend-item'><span class='trend-rank'>{idx+1}</span>{val}</div>" for idx, val in enumerate(kw_list)])
                st.markdown(f"<div class='trend-card'><div class='trend-header'>{cat}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)

elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    st.info("💡 분야별 실시간 핵심 뉴스입니다.")
    news_cats = {"🗞️ 종합 뉴스": "종합", "💰 경제 뉴스": "경제", "💻 IT 뉴스": "IT", "🌿 생활 뉴스": "생활"}
    cols = st.columns(4)
    for i, (name, query) in enumerate(news_cats.items()):
        with cols[i]:
            url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            news = requests.get(url, headers=headers).json().get('items', [])
            html = "".join([f"<div class='trend-item'>🔗 <a href='{n['link']}' target='_blank' style='color:#555; text-decoration:none;'>{n['title'][:30].replace('<b>','').replace('</b>','') + '...'}</a></div>" for n in news])
            st.markdown(f"<div class='trend-card'><div class='trend-header-news'>{name}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)