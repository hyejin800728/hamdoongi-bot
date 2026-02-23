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

# --- 데이터 수집 함수 (네이버 검색광고 & 뉴스 검색) ---
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

# --- UI 설정 및 디자인 (햄둥이 테마 컬러 적용) ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; }}
    
    /* 버튼 및 카드 스타일 */
    .stSidebar [data-testid="stVerticalBlock"] > div > button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 10px; font-weight: bold; margin-bottom: 8px; height: 3.5em; transition: 0.3s;
    }}
    .stSidebar [data-testid="stVerticalBlock"] > div > button:hover {{ background-color: #F4B742; color: white; }}
    
    .trend-card {{
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 0px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 400px;
    }}
    .trend-header-news {{
        background-color: #f8f9fa; border-bottom: 1px solid #e0e0e0;
        padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; color: #333;
        border-top: 5px solid #F1A18E; /* 햄둥이 볼터치 컬러 포인트 */
    }}
    .trend-list {{ padding: 12px; }}
    .news-item {{ border-bottom: 1px solid #f9f9f9; padding: 8px 0; font-size: 0.85em; }}
    .news-item a {{ color: #555; text-decoration: none; font-weight: 500; }}
    .news-item a:hover {{ color: #F1A18E; }}
    
    .stMetric {{ background-color: #FBEECC; padding: 25px; border-radius: 15px; border-left: 8px solid #F4B742; }}
    </style>
    """, unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 ---
if 'menu' not in st.session_state: st.session_state.menu = "🏠 메인 키워드 분석"

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.menu = "🏠 메인 키워드 분석"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.menu = "🛍️ 쇼핑 인기 트렌드"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.menu = "📰 오늘의 뉴스 이슈"
    st.write("---")
    st.caption("'햄둥이의 햄둥지둥 일상보고서' 100회 포스팅을 향해! 🚀")

# --- 페이지 로직 ---
menu = st.session_state.menu

if menu == "🏠 메인 키워드 분석":
    st.title("📊 메인 키워드 분석기")
    # (기존 키워드 분석 로직 코드 생략 - 이전 버전과 동일)
    st.info("💡 분석하고 싶은 키워드를 입력해 보세요.")

elif menu == "🛍️ 쇼핑 인기 트렌드":
    st.title("🛍️ 분야별 인기 검색어 TOP 10")
    # (기존 8개 분야 쇼핑 트렌드 로직 코드 생략 - 이전 버전과 동일)

elif menu == "📰 오늘의 뉴스 이슈":
    st.title("📰 언론사 및 분야별 뉴스 토픽")
    st.info("💡 블로그 글감으로 활용하기 좋은 분야별 실시간 핵심 이슈입니다.")

    #의 카드 레이아웃을 뉴스에 적용
    news_categories = {
        "🗞️ 주요 종합지": ["연합뉴스", "뉴시스", "뉴스1", "한국일보", "동아일보"],
        "💰 경제/경영": ["매일경제", "한국경제", "서울경제", "머니투데이", "파이낸셜뉴스"],
        "💻 IT/과학": ["전자신문", "디지털데일리", "지디넷코리아", "테크월드", "아이뉴스24"],
        "🌿 생활/문화": ["스포츠경향", "매경헬스", "여성신문", "문화일보", "주간조선"]
    }

    cols = st.columns(4)
    for i, (category, press_list) in enumerate(news_categories.items()):
        with cols[i]:
            # 실제 API 호출 시에는 각 분야의 키워드를 넣어 검색 결과를 가져옵니다.
            dummy_query = category.split()[-1] 
            url = f"https://openapi.naver.com/v1/search/news.json?query={dummy_query}&display=5&sort=sim"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            news_items = requests.get(url, headers=headers).json().get('items', [])
            
            items_html = ""
            for item in news_items:
                title = item['title'].replace('<b>','').replace('</b>','')[:35] + "..."
                items_html += f"<div class='news-item'><a href='{item['link']}' target='_blank'>🔗 {title}</a></div>"
            
            st.markdown(f"""
            <div class='trend-card'>
                <div class='trend-header-news'>{category}</div>
                <div class='trend-list'>{items_html}</div>
            </div>
            """, unsafe_allow_html=True)