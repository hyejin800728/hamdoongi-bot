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
    return ["현재 구글 서버 연결이 원활하지 않습니다."]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_v5(target_kw):
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
            
            pc_v, mo_v = clean_count(item['monthlyPcQcCnt']), clean_count(item['monthlyMobileQcCnt'])
            tot_s = pc_v + mo_v
            blog_res = requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100&sort=sim", headers=auth_headers).json()
            blog_v = blog_res.get('total', 0)
            rec_v = sum(1 for post in blog_res.get('items', []) if post.get('postdate', '00000000') >= thirty_days_ago)
            cafe_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_headers).json().get('total', 0)
            
            results.append({
                "kw_key": kw, "pc": pc_v, "mo": mo_v, "tot_s": tot_s,
                "blog": blog_v, "cafe": cafe_v, "tot_d": blog_v + cafe_v,
                "rec": rec_v, "comp": round((blog_v + cafe_v) / tot_s, 2) if tot_s > 0 else 0
            })
        return results
    except: return []

# --- [UI 디자인 강제 주입] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    /* 1. 분석 시작 버튼 크기 및 컬러 고정 */
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; border: none !important;
        font-weight: bold !important; height: 3.8em !important; width: 100% !important;
    }

    /* 2. 대시보드 박스 헤더: 왼쪽 정렬 */
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    .center-content { text-align: center; margin-top: 10px; }
    .metric-val { font-size: 2.8em; font-weight: 800; color: #333; display: inline-block; }
    .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8em; margin-left: 5px; vertical-align: middle; }

    /* 3. [핵심] 표 헤더 디자인 강제 주입: 가운데 정렬 및 볼드 */
    div[data-testid="stDataFrame"] thead tr th {
        text-align: center !important; vertical-align: middle !important;
        font-weight: bold !important; color: #333 !important; background-color: #f8f9fa !important;
    }
    div[data-testid="stDataFrame"] td { text-align: center !important; }

    /* 4. 시스템 알림 숨기기 */
    [data-testid="stStatusWidget"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    if st.button("🌐 구글 실시간 트렌드", use_container_width=True): st.session_state.page = "GOOGLE"
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555;'>햄둥이의 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- [페이지 로직] ---

# 1. 메인 키워드 분석 (HOME)
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit_button = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
        
    if submit_button and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_keyword_data_v5(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        results = st.session_state.kw_results
        target = st.session_state.kw_target
        info = next((i for i in results if i['kw_key'].replace(" ", "") == target.replace(" ", "")), results[0])

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        with c1:
            tot = info['tot_s']
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>💻<br><small><b>PC</b></small><br><b>{info['pc']:,}</b><br><small>{(info['pc']/tot*100 if tot>0 else 0):.1f}%</small></div>
                <div>📱<br><small><b>모바일</b></small><br><b>{info['mo']:,}</b><br><small>{(info['mo']/tot*100 if tot>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{tot:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)

        with c2:
            comp_v = info['comp']
            status, color = ("매우 낮음", "#2ecc71") if comp_v < 0.5 else ("낮음", "#3498db") if comp_v < 1.0 else ("보통", "#f39c12") if comp_v < 5.0 else ("높음", "#e67e22") if comp_v < 10.0 else ("매우 높음", "#e74c3c")
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div class='center-content'>
                <div class='metric-val'>{comp_v}</div><span class='status-badge' style='background-color:{color};'>{status}</span>
                <div style='color:#777; font-size:0.9em; margin-top:10px; font-weight:bold; text-align:center;'>검색량 대비 문서 발행 비율</div></div></div>""", unsafe_allow_html=True)

        with c3:
            doc_tot = info['tot_d']
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>✍️<br><small><b>블로그</b></small><br><b>{info['blog']:,}</b><br><small>{(info['blog']/doc_tot*100 if doc_tot>0 else 0):.1f}%</small></div>
                <div>👥<br><small><b>카페</b></small><br><b>{info['cafe']:,}</b><br><small>{(info['cafe']/doc_tot*100 if doc_tot>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{doc_tot:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)

        with c4:
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div class='center-content'>
                <div class='metric-val'>{info['rec']}건</div><div style='color:#777; font-size:0.9em; margin-top:10px; font-weight:bold; text-align:center;'>최근 30일 이내 등록된 글</div></div></div>""", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📋 연관 키워드 상세 리스트")
        df_final = pd.DataFrame(results)
        multi_cols = [
            ("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"),
            ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"),
            ("최근 한 달\n발행량", " "), ("경쟁강도", " ")
        ]
        df_final = df_final[["kw_key", "pc", "mo", "tot_s", "blog", "cafe", "tot_d", "rec", "comp"]]
        df_final.columns = pd.MultiIndex.from_tuples(multi_cols)
        st.dataframe(df_final.style.set_properties(**{'text-align': 'center'}).background_gradient(cmap='YlOrRd', subset=[("경쟁강도", " ")]), use_container_width=True, hide_index=True, height=580)

# 2. 쇼핑 인기 트렌드 (SHOP)
elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드")
    shop_cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "⚽ 레저": "운동", "🏠 생활": "생활용품", "💻 가전": "전자제품", "🛋️ 소품": "인테리어"}
    items = list(shop_cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            cat_name, query = items[i+j]
            trends = get_real_trends(query)
            html = "".join([f"<div style='margin-bottom:8px; font-size:0.9em;'><span style='color:#F4B742; font-weight:bold; margin-right:8px;'>{idx+1}</span>{val}</div>" for idx, val in enumerate(trends)])
            cols[j].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:380px; text-align:left;'><h4 style='text-align:center;'>{cat_name}</h4><br>{html}</div>", unsafe_allow_html=True)

# 3. 오늘의 뉴스 이슈 (NEWS)
elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    news_cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (name, query) in enumerate(news_cats.items()):
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=7"
        news_items = requests.get(url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}).json().get('items', [])
        html = "".join([f"<div style='margin-bottom:12px; font-size:0.85em; text-align:left;'>🔗 <a href='{n['link']}' target='_blank' style='color:#555; text-decoration:none;'>{n['title'][:30].replace('<b>','').replace('</b>','') + '...'}</a></div>" for n in news_items])
        cols[i].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:450px;'><h4 style='text-align:center;'>{name}</h4><br>{html}</div>", unsafe_allow_html=True)

# 4. 구글 실시간 트렌드 (GOOGLE)
elif st.session_state.page == "GOOGLE":
    st.title("🌐 구글 실시간 급상승 트렌드")
    with st.spinner('🐹 구글의 트렌드를 읽어오는 중...'):
        g_trends = get_google_trends()
        cl, cr = st.columns(2)
        for idx, val in enumerate(g_trends):
            col = cl if idx < 5 else cr
            col.markdown(f"<div style='background-color:#ffffff; padding:18px; border-radius:12px; border:1px solid #eee; margin-bottom:12px; border-left: 6px solid #4285F4; text-align:left;'><span style='color:#4285F4; font-weight:bold; margin-right:12px;'>{idx+1}</span> {val}</div>", unsafe_allow_html=True)