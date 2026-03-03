import streamlit as st
import pandas as pd
import requests
import hmac
import hashlib
import time
import base64
import datetime
import re
from bs4 import BeautifulSoup

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

# --- [수정] 진짜 상품명만 골라내는 초정밀 크롤링 엔진 (v31) ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_realtime_shopping_v31(category_id):
    url = f"https://search.shopping.naver.com/best/category/click?categoryCategoryId=ALL&categoryChildCategoryId=ALL&categoryDemo=ALL&categoryRootCategoryId={category_id}&period=P1D"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        res = requests.get(url, headers=headers, timeout=12)
        res.encoding = 'utf-8' 
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [핵심] 상품 리스트 구역을 먼저 찾고 그 안에서 제목만 추출
        raw_items = soup.select('div[class*="imageProduct_title"] > a') or \
                    soup.select('div[class*="category_product_title"] > a') or \
                    soup.select('a[class*="product_link"]')
        
        # 엉뚱한 내비게이션 문구 필터링
        blacklist = ["본문 바로가기", "고객센터", "이전 페이지", "네이버 쇼핑", "NAVER"]
        clean_results = []
        for item in raw_items:
            text = item.get_text(strip=True)
            if text and not any(word in text for word in blacklist):
                clean_results.append(text)
        
        return clean_results[:10] if clean_results else ["데이터 갱신 중..."]
    except:
        return ["연결 지연 중..."]

# --- 메인 데이터 수집 (v31) ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_v31(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    try:
        res = requests.get("https://api.naver.com" + uri, params=params, headers=headers).json()
        if 'keywordList' not in res: return []
        results = []
        auth_h = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        for item in res['keywordList'][:15]:
            kw = item['relKeyword']
            def cl(v): return 10 if isinstance(v, str) and '<' in v else int(v)
            p, m = cl(item['monthlyPcQcCnt']), cl(item['monthlyMobileQcCnt'])
            t, b_res = p + m, requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100", headers=auth_h).json()
            b_v = b_res.get('total', 0)
            r_v = sum(1 for post in b_res.get('items', []) if post.get('postdate', '00000000') >= (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d'))
            c_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_h).json().get('total', 0)
            results.append({"v31_kw": kw, "v31_p": p, "v31_m": m, "v31_t": t, "v31_b": b_v, "v31_c": c_v, "v31_d": b_v + c_v, "v31_r": r_v, "v31_idx": round((b_v + c_v) / t, 2) if t > 0 else 0})
        return results
    except: return []

# --- [UI 디자인 정밀 고정] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    div[data-testid="stFormSubmitButton"] button { background-color: #F4B742 !important; color: white !important; border-radius: 12px !important; font-weight: bold !important; height: 4em !important; width: 100% !important; border: none !important; }
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    .metric-val { font-size: 3.2em; font-weight: 800; color: #333; }
    .sub-metric-val { font-size: 1.8em; font-weight: 800; color: #222; display: block; margin: 2px 0; }
    .sub-metric-label { font-size: 0.85em; font-weight: bold; color: #666; }
    .sub-pct { font-size: 0.8em; color: #777; font-weight: bold; }
    .status-badge { display: inline-block; padding: 6px 18px; border-radius: 50px; color: white; font-weight: 800; font-size: 0.85em; margin-left: 10px; vertical-align: middle; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    div[data-testid="stDataFrame"] thead tr th { text-align: center !important; font-weight: bold !important; }
    div[data-testid="stDataFrame"] td { text-align: center !important; }
    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 및 메뉴 구성 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 카테고리별 인기 키워드", use_container_width=True): st.session_state.page = "KEYWORD"
    if st.button("🔥 실시간 쇼핑 트렌드", use_container_width=True): st.session_state.page = "TREND"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555; font-size:0.85em;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 페이지 로직 ---

if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
    if submit and input_kw:
        st.session_state.kw_results = fetch_keyword_data_v31(input_kw)
        st.session_state.kw_target = input_kw
        st.rerun()
    if st.session_state.get('kw_results'):
        res = st.session_state.kw_results
        tgt = st.session_state.kw_target
        try:
            info = next((i for i in res if i['v31_kw'].replace(" ", "") == tgt.replace(" ", "")), res[0])
            c1, c2 = st.columns(2); c3, c4 = st.columns(2)
            with c1:
                t = info['v31_t']
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>💻 PC</span><span class='sub-metric-val'>{info['v31_p']:,}</span><span class='sub-pct'>{(info['v31_p']/t*100 if t>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>📱 모바일</span><span class='sub-metric-val'>{info['v31_m']:,}</span><span class='sub-pct'>{(info['v31_m']/t*100 if t>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>➕ 총합</span><span class='sub-metric-val'>{t:,}</span><span class='sub-pct'>100%</span></div>
                </div></div>""", unsafe_allow_html=True)
            with c2:
                s, col = ("매우 낮음", "#2ecc71") if info['v31_idx'] < 0.5 else ("낮음", "#3498db") if info['v31_idx'] < 1.0 else ("보통", "#f39c12") if info['v31_idx'] < 5.0 else ("높음", "#e67e22") if info['v31_idx'] < 10.0 else ("매우 높음", "#e74c3c")
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div style='text-align:center;'><span class='metric-val'>{info['v31_idx']}</span><span class='status-badge' style='background-color:{col};'>{s}</span></div></div>""", unsafe_allow_html=True)
            with c3:
                d = info['v31_d']
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>✍️ 블로그</span><span class='sub-metric-val'>{info['v31_b']:,}</span><span class='sub-pct'>{(info['v31_b']/d*100 if d>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>👥 카페</span><span class='sub-metric-val'>{info['v31_c']:,}</span><span class='sub-pct'>{(info['v31_c']/d*100 if d>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>➕ 총합</span><span class='sub-metric-val'>{d:,}</span><span class='sub-pct'>100%</span></div>
                </div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div style='text-align:center;'><span class='metric-val'>{info['v31_r']}</span><span class='sub-metric-label' style='font-size:1.5em; display:inline;'>건</span></div></div>""", unsafe_allow_html=True)
            st.divider()
            df = pd.DataFrame(res)
            m_cols = [("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"), ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"), ("최근 한 달\n발행량", " "), ("경쟁강도", " ")]
            df_display = df[["v31_kw", "v31_p", "v31_m", "v31_t", "v31_b", "v31_c", "v31_d", "v31_r", "v31_idx"]]
            df_display.columns = pd.MultiIndex.from_tuples(m_cols)
            st.dataframe(df_display.style.set_properties(**{'text-align': 'center'}).background_gradient(cmap='YlOrRd', subset=[("경쟁강도", " ")]), use_container_width=True, hide_index=True, height=650)
        except: st.warning("⚠️ 캐시 갱신이 필요합니다. 'C' 키를 한 번 눌러주세요!")

elif st.session_state.page == "KEYWORD":
    st.title("🛍️ 카테고리별 인기 키워드")
    cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "⚽ 레저": "운동", "🏠 생활": "생활용품", "💻 가전": "전자제품", "🛋️ 소품": "인테리어"}
    items = list(cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            n, q = items[i+j]
            t = requests.get(f"https://ac.search.naver.com/nx/ac?q={q}&con=0&ans=2&r_format=json&st=100").json()['items'][0]
            h = "".join([f"<div style='margin-bottom:8px; text-align:left;'><span style='color:#F4B742; font-weight:bold;'>{idx+1}</span> {v[0]}</div>" for idx, v in enumerate(t[:10])])
            cols[j].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:350px;'><h4>{n}</h4><br>{h}</div>", unsafe_allow_html=True)

elif st.session_state.page == "TREND":
    st.title("🔥 실시간 쇼핑 트렌드 (BEST 100)")
    best_cats = {"💄 뷰티": "50000002", "👗 패션": "50000000", "👜 잡화": "50000001", "🍎 식품": "50000006", "⚽ 레저": "50000009", "🏠 생활": "50000008", "💻 가전": "50000003", "🛋️ 소품": "50000004"}
    items = list(best_cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            n, cid = items[i+j]
            trends = fetch_realtime_shopping_v31(cid)
            h = "".join([f"<div style='margin-bottom:8px; text-align:left; font-size:0.9em;'><span style='color:#F4B742; font-weight:bold;'>{idx+1}</span> {v}</div>" for idx, v in enumerate(trends)])
            cols[j].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:450px;'><h4>{n}</h4><br>{h}</div>", unsafe_allow_html=True)

elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    news_cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (n, q) in enumerate(news_cats.items()):
        url = f"https://openapi.naver.com/v1/search/news.json?query={q}&display=7"
        news = requests.get(url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}).json().get('items', [])
        h = "".join([f"<div style='margin-bottom:10px; font-size:0.85em; text-align:left;'>🔗 <a href='{x['link']}' target='_blank' style='color:#555; text-decoration:none;'>{x['title'][:25].replace('<b>','').replace('</b>','') + '...'}</a></div>" for x in news])
        cols[i].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:420px;'><h4>{n}</h4><br>{h}</div>", unsafe_allow_html=True)