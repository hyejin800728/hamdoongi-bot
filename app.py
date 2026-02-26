import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import random
import datetime
from pytrends.request import TrendReq # 구글 트렌드 연동 라이브러리

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

# --- [데이터] 네이버 실시간 트렌드 수집 (쇼핑) ---
def get_real_trends(query):
    url = f"https://ac.search.naver.com/nx/ac?q={query}&con=0&ans=2&r_format=json&r_enc=UTF-8&st=100"
    try:
        res = requests.get(url).json()
        return [item[0] for item in res['items'][0]][:10]
    except:
        return ["데이터 로드 중..."]

# --- [데이터] 구글 실시간 급상승어 가져오기 (재시도 로직) ---
def get_google_trends():
    for attempt in range(3):
        try:
            pytrends = TrendReq(hl='ko', tz=540, timeout=(10, 25))
            df = pytrends.trending_searches(pn='south_korea')
            if not df.empty:
                return df[0].tolist()[:10]
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            else:
                return ["현재 구글 트렌드 호출이 많아 잠시 제한되었습니다. (잠시 후 다시 시도)"]
    return ["데이터를 불러오는 데 실패했습니다."]

# --- [데이터] 네이버 키워드 데이터 상세 분석 (블랙키위 스타일) ---
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
        
        # 상위 15개 연관 키워드 추출
        all_keywords = res_json['keywordList'][:15]
        results = []
        
        # 검색 API 인증 헤더
        auth_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}

        for item in all_keywords:
            kw = item['relKeyword']
            
            def clean_count(val):
                if isinstance(val, str) and '<' in val: return 10
                return int(val)
            
            pc_vol = clean_count(item['monthlyPcQcCnt'])
            mo_vol = clean_count(item['monthlyMobileQcCnt'])
            total_vol = pc_vol + mo_vol
            
            # 블로그 및 카페 문서수 개별 수집
            blog_url = f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=1"
            blog_res = requests.get(blog_url, headers=auth_headers).json()
            blog_count = blog_res.get('total', 0)
            
            cafe_url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1"
            cafe_res = requests.get(cafe_url, headers=auth_headers).json()
            cafe_count = cafe_res.get('total', 0)
            
            total_doc = blog_count + cafe_count
            
            results.append({
                "키워드": kw,
                "PC 검색량": pc_vol,
                "모바일 검색량": mo_vol,
                "총 검색량": total_vol,
                "블로그 문서": blog_count,
                "카페 문서": cafe_count,
                "총 문서수": total_doc,
                "경쟁 강도": round(total_doc / total_vol, 2) if total_vol > 0 else 0
            })
        return results
    except: return []

# --- UI 설정 및 햄둥이 컬러 테마 ---
# 메인 몸통: #F4B742, 배: #FBEECC, 볼터치: #F1A18E
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }}
    
    /* 사이드바 버튼 스타일 */
    .stSidebar [data-testid="stVerticalBlock"] div[data-testid="stButton"] button {{
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 12px; font-weight: bold; margin-bottom: 12px; height: 3.5em; width: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    /* 지표 카드 스타일 */
    .stMetric {{ 
        background-color: #FBEECC; padding: 20px; border-radius: 15px; 
        border-left: 8px solid #F4B742; margin-bottom: 10px; 
    }}
    
    .trend-card {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 410px; }}
    .trend-header {{ background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F4B742; }}
    .trend-list {{ padding: 15px; }}
    .trend-item {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 0.85em; border-bottom: 1px solid #f9f9f9; padding-bottom: 4px; color: #555; }}
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
    st.button("🌐 구글 실시간 트렌드", on_click=set_page, args=("GOOGLE",), use_container_width=True)
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 페이지 로직 ---
# 1. 메인 키워드 분석 (블랙키위 스타일 강화)
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석 리포트")
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 킬리안")
    if st.button("실시간 통합 분석 시작", use_container_width=True):
        if input_kw:
            with st.spinner('🐹 데이터를 꼼꼼히 분석 중...'):
                st.session_state.kw_results = fetch_keyword_data(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()

    if st.session_state.get('kw_results'):
        df = pd.DataFrame(st.session_state.kw_results)
        target = st.session_state.kw_target
        # 검색어와 정확히 일치하는 데이터 찾기
        seed_data = df[df['키워드'].str.replace(" ", "") == target.replace(" ", "")]
        if seed_data.empty: seed_data = df.iloc[[0]]
        
        target_info = seed_data.iloc[0]
        
        # [섹션 1] 월간 검색량 상세
        st.subheader(f"🔍 '{target}' 월간 검색량")
        col1, col2, col3 = st.columns(3)
        col1.metric("PC 검색량", f"{target_info['PC 검색량']:,}회")
        col2.metric("모바일 검색량", f"{target_info['모바일 검색량']:,}회")
        col3.metric("총 검색량", f"{target_info['총 검색량']:,}회", delta="통합")

        # [섹션 2] 콘텐츠 발행량 상세
        st.subheader("📝 콘텐츠 발행량 (누적)")
        col4, col5, col6 = st.columns(3)
        col4.metric("블로그 문서", f"{target_info['블로그 문서']:,}건")
        col5.metric("카페 문서", f"{target_info['카페 문서']:,}건")
        col6.metric("총 문서 수", f"{target_info['총 문서수']:,}건")

        # [섹션 3] 경쟁 분석
        st.subheader("📈 시장 분석 지표")
        comp_val = target_info['경쟁 강도']
        # 블랙키위 스타일의 경쟁 강도 판단
        if comp_val < 1: status = "낮음 (블루오션)"
        elif comp_val < 5: status = "보통"
        else: status = "높음 (레드오션)"
        
        st.metric("콘텐츠 포화도 (경쟁 강도)", f"{comp_val}", delta=status, delta_color="inverse")

        st.divider()
        st.subheader("📊 연관 키워드 상세 리스트")
        st.dataframe(df.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']), use_container_width=True, hide_index=True, height=500)

# 2. 쇼핑 인기 트렌드
elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드 발견")
    shop_cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "⚽ 레저": "운동", "🏠 생활": "생활용품", "💻 가전": "전자제품", "🛋️ 소품": "인테리어"}
    items = list(shop_cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            cat_name, search_query = items[i+j]
            with cols[j]:
                trends = get_real_trends(search_query)
                html = "".join([f"<div class='trend-item'><span class='trend-rank'>{idx+1}</span>{val}</div>" for idx, val in enumerate(trends)])
                st.markdown(f"<div class='trend-card'><div class='trend-header'>{cat_name}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)

# 3. 뉴스 이슈
elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    news_cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (name, query) in enumerate(news_cats.items()):
        with cols[i]:
            url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            news_items = requests.get(url, headers=headers).json().get('items', [])
            html = "".join([f"<div class='trend-item'>🔗 <a href='{n['link']}' target='_blank' style='color:#555; text-decoration:none;'>{n['title'][:25].replace('<b>','').replace('</b>','') + '...'}</a></div>" for n in news_items])
            st.markdown(f"<div class='trend-card'><div class='trend-header'>{name}</div><div class='trend-list'>{html}</div></div>", unsafe_allow_html=True)

# 4. 구글 실시간 트렌드
elif st.session_state.page == "GOOGLE":
    st.title("🌐 구글 실시간 급상승 트렌드")
    with st.spinner('🐹 구글 트렌드 파도를 타는 중...'):
        g_trends = get_google_trends()
        col_l, col_r = st.columns(2)
        for idx, val in enumerate(g_trends):
            col = col_l if idx < 5 else col_r
            with col:
                st.markdown(f"""
                <div style='background-color:#ffffff; padding:15px; border-radius:10px; border:1px solid #eee; margin-bottom:10px; border-left: 5px solid #4285F4;'>
                    <span style='color:#4285F4; font-weight:bold; margin-right:10px;'>{idx+1}</span> {val}
                </div>
                """, unsafe_allow_html=True)