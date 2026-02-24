import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import random

# --- [보안] Streamlit Secrets 적용 ---
# 사용자님이 이미 발급받아 등록해두신 Client ID와 Secret을 사용합니다.
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

# --- [진짜 실시간] 실시간 검색 제안어 수집 함수 ---
# 고정 데이터 대신 네이버의 실시간 자동완성 데이터를 낚아채오는 핵심 함수입니다.
def fetch_realtime_data(query):
    if not query: return []
    # 네이버 실시간 검색 제안 API 호출
    url = f"https://ac.search.naver.com/nx/ac?q={query}&con=0&ans=2&r_format=json&r_enc=UTF-8&st=100"
    try:
        res = requests.get(url)
        items = res.json()['items'][0]
        return [item[0] for item in items][:10]
    except:
        return ["데이터를 가져올 수 없습니다."]

# --- 데이터 수집 함수 (기존 로직 유지) ---
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
        border-radius: 12px; font-weight: bold; margin-bottom: 12px; height: 3.5em; width: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .stMetric {{ background-color: #FBEECC; padding: 20px; border-radius: 15px; border-left: 8px solid #F4B742; margin-bottom: 10px; }}
    .trend-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 420px; }}
    .trend-header {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F4B742; font-size: 0.9em; }}
    .trend-header-news {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F1A18E; }}
    .trend-list {{ padding: 15px; }}
    .trend-item {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 0.85em; border-bottom: 1px solid #f9f9f9; padding-bottom: 5px; }}
    .trend-rank {{ color: #F4B742; font-weight: bold; width: 25px; margin-right: 8px; }}
    @media (max-width: 768px) {{ [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; }} }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

def set_page(name): st.session_state.page = name

# --- 사이드바 ---
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    st.button("🏠 메인 키워드 분석", on_click=set_page, args=("HOME",), use_container_width=True)
    st.button("🛍️ 쇼핑 인기 트렌드", on_click=set_page, args=("SHOP",), use_container_width=True)
    st.button("📰 오늘의 뉴스 이슈", on_click=set_page, args=("NEWS",), use_container_width=True)
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 페이지 로직 ---
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석 리포트")
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 다이소 화장품")
    if st.button("실시간 통합 분석 시작", use_container_width=True):
        if input_kw:
            with st.spinner('🐹 데이터를 분석 중...'):
                st.session_state.kw_results = fetch_keyword_data(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()
    if st.session_state.get('kw_results'):
        df = pd.DataFrame(st.session_state.kw_results)
        seed_data = df.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("월간 검색량", f"{seed_data['월간 검색량']:,}회")
        col2.metric("총 문서 수", f"{seed_data['총 문서 수']:,}건")
        col3.metric("경쟁 강도", f"{seed_data['경쟁 강도']}")
        st.divider()
        st.subheader("📊 연관 키워드 상세 분석 (스크롤 없음)")
        st.dataframe(df.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']), use_container_width=True, hide_index=True, height=560)

elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드 뱅크")
    st.info("💡 카테고리명을 수정하면 네이버의 진짜 실시간 트렌드 키워드를 물어옵니다!")
    # 사용자 취향 반영 8개 카테고리
    default_cats = ["다이소 화장품", "여성 의류", "캐스퍼 용품", "밀키트 추천", "캠핑 장비", "영양제", "자취 가전", "인테리어 소품"]
    
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            with cols[j]:
                cat_name = st.text_input(f"카테고리 {i+j+1}", value=default_cats[i+j], key=f"cat_{i+j}")
                real_kws = fetch_realtime_data(cat_name)
                html = "".join([f"<div class='trend-item'><span class='trend-rank'>{idx+1}</span>{val}</div>" for idx, val in enumerate(real_kws)])
                st.markdown(f"<div class='trend-card'><div class='trend-header'>🔍 {cat_name}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)

elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    st.info("💡 분야별 실시간 핵심 뉴스입니다.")
    news_cats = {"🗞️ 주요 종합": "종합", "💰 경제 소식": "경제", "💻 IT 이슈": "IT", "🌿 생활 문화": "생활"}
    cols = st.columns(4)
    for i, (name, query) in enumerate(news_cats.items()):
        with cols[i]:
            url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            news_items = requests.get(url, headers=headers).json().get('items', [])
            html = "".join([f"<div class='trend-item'>🔗 <a href='{n['link']}' target='_blank' style='color:#555; text-decoration:none;'>{n['title'][:30].replace('<b>','').replace('</b>','') + '...'}</a></div>" for n in news_items])
            st.markdown(f"<div class='trend-card'><div class='trend-header-news'>{name}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)