import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import datetime

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
        "X-Timestamp": timestamp, "X-API-KEY": api_key, "X-Customer": str(customer_id),
        "X-Signature": base64.b64encode(signature).decode()
    }

# --- [데이터 수집] v19 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_v19(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    try:
        res = requests.get("https://api.naver.com" + uri, params=params, headers=headers).json()
        if 'keywordList' not in res: return []
        results = []
        auth_h = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        thirty_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        for item in res['keywordList'][:15]:
            kw = item['relKeyword']
            def cl(v): return 10 if isinstance(v, str) and '<' in v else int(v)
            p, m = cl(item['monthlyPcQcCnt']), cl(item['monthlyMobileQcCnt'])
            t = p + m
            b_res = requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100", headers=auth_h).json()
            b_v = b_res.get('total', 0)
            r_v = sum(1 for post in b_res.get('items', []) if post.get('postdate', '00000000') >= thirty_ago)
            c_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_h).json().get('total', 0)
            results.append({
                "v19_kw": kw, "v19_p": p, "v19_m": m, "v19_t": t, 
                "v19_b": b_v, "v19_c": c_v, "v19_d": b_v + c_v, 
                "v19_r": r_v, "v19_idx": round((b_v + c_v) / t, 2) if t > 0 else 0
            })
        return results
    except: return []

def get_naver_trends(q):
    try:
        res = requests.get(f"https://ac.search.naver.com/nx/ac?q={q}&con=0&ans=2&r_format=json&st=100").json()
        return [item[0] for item in res['items'][0]][:10]
    except: return ["데이터 로드 중..."]

# --- [UI 디자인 및 반응형 설정] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    /* 분석 시작 버튼 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; font-weight: bold !important;
        height: 4em !important; width: 100% !important;
    }

    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 200px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    
    /* 숫자 크기 확대 */
    .metric-val { font-size: 3.2em; font-weight: 800; color: #333; }
    .sub-metric-val { font-size: 1.6em; font-weight: 800; color: #222; display: block; margin: 5px 0; }
    .sub-metric-label { font-size: 0.8em; font-weight: bold; color: #666; }

    @media (max-width: 768px) {
        .metric-val { font-size: 2.2em !important; }
        .sub-metric-val { font-size: 1.2em !important; }
        .quad-box { padding: 15px !important; min-height: 150px !important; }
    }

    .status-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.75em; margin-left: 5px; vertical-align: middle; }
    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 메뉴 복구 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    # 메뉴 버튼들 복구
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    st.write("---")
    # 시그니처 문구 복구
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555; font-size:0.85em;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 페이지 로직 ---

# 1. HOME: 메인 키워드 분석
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
        
    if submit and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_keyword_data_v19(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        res = st.session_state.kw_results
        tgt = st.session_state.kw_target
        
        try:
            # v19 이름표 검증 로직
            if res and 'v19_kw' not in res[0]:
                st.session_state.kw_results = None
                st.rerun()
                
            info = next((i for i in res if i['v19_kw'].replace(" ", "") == tgt.replace(" ", "")), res[0])
            c1, c2 = st.columns(2); c3, c4 = st.columns(2)
            
            with c1:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>💻PC</span><span class='sub-metric-val'>{info['v19_p']:,}</span></div>
                    <div><span class='sub-metric-label'>📱MO</span><span class='sub-metric-val'>{info['v19_m']:,}</span></div>
                    <div><span class='sub-metric-label'>➕TOT</span><span class='sub-metric-val'>{info['v19_t']:,}</span></div>
                </div></div>""", unsafe_allow_html=True)
            with c2:
                s, col = ("매우 낮음", "#2ecc71") if info['v19_idx'] < 0.5 else ("낮음", "#3498db") if info['v19_idx'] < 1.0 else ("보통", "#f39c12") if info['v19_idx'] < 5.0 else ("높음", "#e67e22") if info['v19_idx'] < 10.0 else ("매우 높음", "#e74c3c")
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div style='text-align:center;'><span class='metric-val'>{info['v19_idx']}</span><span class='status-badge' style='background-color:{col};'>{s}</span></div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>✍️BLOG</span><span class='sub-metric-val'>{info['v19_b']:,}</span></div>
                    <div><span class='sub-metric-label'>👥CAFE</span><span class='sub-metric-val'>{info['v19_c']:,}</span></div>
                    <div><span class='sub-metric-label'>➕TOT</span><span class='sub-metric-val'>{info['v19_d']:,}</span></div>
                </div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div style='text-align:center;'><span class='metric-val'>{info['v19_r']}</span><span class='sub-metric-label' style='font-size:1.5em; display:inline;'>건</span></div></div>""", unsafe_allow_html=True)
            
            st.divider()
            df = pd.DataFrame(res)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except: st.warning("⚠️ 캐시 갱신이 필요합니다. 'C' 키를 한 번만 눌러주세요!")

# 2. SHOP: 쇼핑 트렌드 복구
elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드")
    cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "🏠 생활": "생활용품", "🛋️ 소품": "인테리어"}
    items = list(cats.items())
    for i in range(0, 6, 3):
        cols = st.columns(3)
        for j in range(3):
            n, q = items[i+j]
            trends = get_naver_trends(q)
            html = "".join([f"<div style='margin-bottom:8px; text-align:left;'><span style='color:#F4B742; font-weight:bold;'>{idx+1}</span> {v}</div>" for idx, v in enumerate(trends)])
            cols[j].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:350px;'><h4>{n}</h4><br>{html}</div>", unsafe_allow_html=True)

# 3. NEWS: 뉴스 이슈 복구
elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    news_cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (n, q) in enumerate(news_cats.items()):
        url = f"https://openapi.naver.com/v1/search/news.json?query={q}&display=7"
        news = requests.get(url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}).json().get('items', [])
        html = "".join([f"<div style='margin-bottom:10px; font-size:0.85em; text-align:left;'>🔗 <a href='{x['link']}' target='_blank' style='color:#555; text-decoration:none;'>{x['title'][:25].replace('<b>','').replace('</b>','') + '...'}</a></div>" for x in news])
        cols[i].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:420px;'><h4>{n}</h4><br>{html}</div>", unsafe_allow_html=True)