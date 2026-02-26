import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import datetime
from pytrends.request import TrendReq

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

# --- [데이터 수집 함수들] ---

def get_real_trends(query):
    url = f"https://ac.search.naver.com/nx/ac?q={query}&con=0&ans=2&r_format=json&r_enc=UTF-8&st=100"
    try:
        res = requests.get(url).json()
        return [item[0] for item in res['items'][0]][:10]
    except: return ["데이터 로드 중..."]

def get_google_trends():
    for attempt in range(3):
        try:
            pytrends = TrendReq(hl='ko', tz=540, timeout=(10, 25))
            df = pytrends.trending_searches(pn='south_korea')
            if not df.empty: return df[0].tolist()[:10]
        except:
            if attempt < 2: time.sleep(2); continue
    return ["현재 구글 트렌드 데이터를 불러올 수 없습니다."]

@st.cache_data(ttl=600)
def fetch_keyword_data_v2(target_kw):
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
        auth_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        for item in all_keywords:
            kw = item['relKeyword']
            def clean_count(val):
                if isinstance(val, str) and '<' in val: return 10
                return int(val)
            
            pc_vol, mo_vol = clean_count(item['monthlyPcQcCnt']), clean_count(item['monthlyMobileQcCnt'])
            total_vol = pc_vol + mo_vol
            
            blog_res = requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100&sort=sim", headers=auth_headers).json()
            blog_total = blog_res.get('total', 0)
            recent_month_cnt = sum(1 for post in blog_res.get('items', []) if post.get('postdate', '00000000') >= thirty_days_ago)
            
            cafe_total = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_headers).json().get('total', 0)
            
            results.append({
                "키워드": kw, "PC 검색량": pc_vol, "모바일 검색량": mo_vol, "총 검색량": total_vol,
                "블로그 누적": blog_total, "카페 누적": cafe_total, "총 누적문서": blog_total + cafe_total,
                "최근 한 달 발행량": recent_month_cnt, "경쟁 강도": round((blog_total + cafe_total) / total_vol, 2) if total_vol > 0 else 0
            })
        return results
    except: return []

# --- [UI 설정] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    .stSidebar [data-testid="stVerticalBlock"] div[data-testid="stButton"] button {
        background-color: #ffffff; border: 2px solid #F4B742; color: #333;
        border-radius: 12px; font-weight: bold; margin-bottom: 12px; height: 3.5em; width: 100%;
    }
    .quadrant-box {
        background-color: #FBEECC; padding: 20px; border-radius: 20px;
        border-left: 10px solid #F4B742; margin-bottom: 20px; min-height: 160px;
    }
    .quad-title { font-weight: bold; color: #555; font-size: 1.1em; margin-bottom: 10px; }
    .quad-val { font-size: 1.8em; font-weight: 800; color: #333; margin-bottom: 5px; }
    .quad-sub { font-size: 0.85em; color: #777; }
    .trend-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; margin-bottom: 20px; min-height: 400px; }
    .trend-header { background-color: #f8f9fa; padding: 12px; border-radius: 12px 12px 0 0; font-weight: bold; text-align: center; border-top: 5px solid #F4B742; }
    .trend-item { display: flex; align-items: center; margin-bottom: 8px; font-size: 0.85em; padding: 0 15px; }
    .trend-rank { color: #F4B742; font-weight: bold; width: 25px; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    if st.button("🌐 구글 실시간 트렌드", use_container_width=True): st.session_state.page = "GOOGLE"
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- [페이지 로직] ---

# 1. 메인 키워드 분석 (HOME)
if st.session_state.page == "HOME":
    st.title("📊 키워드 4분할 정밀 분석")
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 킬리안")
    if st.button("실시간 통합 분석 시작", use_container_width=True):
        if input_kw:
            with st.spinner('🐹 데이터를 분석 중...'):
                st.session_state.kw_results = fetch_keyword_data_v2(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()

    if st.session_state.get('kw_results'):
        df = pd.DataFrame(st.session_state.kw_results)
        if 'PC 검색량' not in df.columns:
            st.warning("⚠️ 'C' 키를 눌러 캐시를 지워주세요!")
            st.stop()
        
        target = st.session_state.kw_target
        seed_data = df[df['키워드'].str.replace(" ", "") == target.replace(" ", "")]
        info = seed_data.iloc[0] if not seed_data.empty else df.iloc[0]

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        with c1: st.markdown(f"<div class='quadrant-box'><div class='quad-title'>🔍 월간 검색량</div><div class='quad-val'>{info['총 검색량']:,}회</div><div class='quad-sub'>PC {info['PC 검색량']:,} | 모바일 {info['모바일 검색량']:,}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='quadrant-box'><div class='quad-title'>📈 분석 지표</div><div class='quad-val'>{info['경쟁 강도']}</div><div class='quad-sub'>상태: <b>{'낮음' if info['경쟁 강도'] < 1 else '보통'}</b></div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='quadrant-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div class='quad-val'>{info['총 누적문서']:,}건</div><div class='quad-sub'>블로그 {info['블로그 누적']:,} | 카페 {info['카페 누적']:,}</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='quadrant-box'><div class='quad-title'>📅 최근 한 달 발행</div><div class='quad-val'>{info['최근 한 달 발행량']}건 / 100건</div><div class='quad-sub'>최신 100개 중 한 달 내 작성 비중</div></div>", unsafe_allow_html=True)
        
        st.divider()
        st.dataframe(df, use_container_width=True, hide_index=True)

# 2. 쇼핑 트렌드 (SHOP)
elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드")
    shop_cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "⚽ 레저": "운동", "🏠 생활": "생활용품", "💻 가전": "전자제품", "🛋️ 소품": "인테리어"}
    items = list(shop_cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            cat_name, search_query = items[i+j]
            trends = get_real_trends(search_query)
            html = "".join([f"<div class='trend-item'><span class='trend-rank'>{idx+1}</span>{val}</div>" for idx, val in enumerate(trends)])
            cols[j].markdown(f"<div class='trend-card'><div class='trend-header'>{cat_name}</div><br>{html}</div>", unsafe_allow_html=True)

# 3. 뉴스 이슈 (NEWS)
elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    news_cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (name, query) in enumerate(news_cats.items()):
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5"
        news_items = requests.get(url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}).json().get('items', [])
        html = "".join([f"<div class='trend-item'>🔗 <a href='{n['link']}' target='_blank' style='color:#555; text-decoration:none;'>{n['title'][:25].replace('<b>','').replace('</b>','') + '...'}</a></div>" for n in news_items])
        cols[i].markdown(f"<div class='trend-card'><div class='trend-header'>{name}</div><br>{html}</div>", unsafe_allow_html=True)

# 4. 구글 트렌드 (GOOGLE)
elif st.session_state.page == "GOOGLE":
    st.title("🌐 구글 실시간 급상승 트렌드")
    with st.spinner('🐹 데이터를 가져오는 중...'):
        g_trends = get_google_trends()
        cl, cr = st.columns(2)
        for idx, val in enumerate(g_trends):
            col = cl if idx < 5 else cr
            col.markdown(f"<div style='background-color:#ffffff; padding:15px; border-radius:10px; border:1px solid #eee; margin-bottom:10px; border-left: 5px solid #4285F4;'><span style='color:#4285F4; font-weight:bold; margin-right:10px;'>{idx+1}</span> {val}</div>", unsafe_allow_html=True)