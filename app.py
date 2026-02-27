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

# --- [데이터 수집] 캐시 리셋을 위해 v8로 업그레이드 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_hamster_data_v8(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    try:
        res = requests.get("https://api.naver.com" + uri, params=params, headers=headers).json()
        if 'keywordList' not in res: return []
        
        all_keywords = res['keywordList'][:15]
        results = []
        auth_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        for item in all_keywords:
            kw = item['relKeyword']
            def clean_count(val):
                if isinstance(val, str) and '<' in val: return 10
                return int(val)
            
            p, m = clean_count(item['monthlyPcQcCnt']), clean_count(item['monthlyMobileQcCnt'])
            t = p + m
            b_res = requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100&sort=sim", headers=auth_headers).json()
            b_v = b_res.get('total', 0)
            r_v = sum(1 for post in b_res.get('items', []) if post.get('postdate', '00000000') >= thirty_days_ago)
            c_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_headers).json().get('total', 0)
            
            results.append({
                "key": kw, "p": p, "m": m, "t": t, "blog": b_v, "cafe": c_v, "doc": b_v + c_v, "rec": r_v, "idx": round((b_v + c_v) / t, 2) if t > 0 else 0
            })
        return results
    except: return []

# --- [UI 디자인 강제 주입] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    /* 1. 분석 시작 버튼 디자인 고정 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; font-weight: bold !important;
        height: 3.8em !important; width: 100% !important; border: none !important;
    }

    /* 2. 대시보드 박스 헤더 왼쪽 정렬 */
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    
    .center-content { text-align: center; margin-top: 10px; }
    .metric-val { font-size: 2.8em; font-weight: 800; color: #333; display: inline-block; }
    .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8em; margin-left: 5px; vertical-align: middle; }

    /* 3. [최후의 수단] 표 전체 영역 강제 가운데 정렬/볼드체 주입 */
    [data-testid="stDataFrame"] thead th {
        text-align: center !important; vertical-align: middle !important;
        font-weight: bold !important; color: #333 !important; background-color: #f8f9fa !important;
    }
    [data-testid="stDataFrame"] td { text-align: center !important; }

    /* 시스템 알림 제거 */
    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 복구 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    if st.button("🌐 구글 실시간 트렌드", use_container_width=True): st.session_state.page = "GOOGLE"
    st.write("---")

# --- 페이지 로직 ---

if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
        
    if submit and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_hamster_data_v8(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        res = st.session_state.kw_results
        tgt = st.session_state.kw_target
        info = next((i for i in res if i['key'].replace(" ", "") == tgt.replace(" ", "")), res[0])

        c1, c2 = st.columns(2); c3, c4 = st.columns(2)
        with c1:
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>💻<br><small><b>PC</b></small><br><b>{info['p']:,}</b><br><small>{(info['p']/info['t']*100 if info['t']>0 else 0):.1f}%</small></div>
                <div>📱<br><small><b>모바일</b></small><br><b>{info['m']:,}</b><br><small>{(info['m']/info['t']*100 if info['t']>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{info['t']:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)
        with c2:
            s, col = ("매우 낮음", "#2ecc71") if info['idx'] < 0.5 else ("낮음", "#3498db") if info['idx'] < 1.0 else ("보통", "#f39c12") if info['idx'] < 5.0 else ("높음", "#e67e22") if info['idx'] < 10.0 else ("매우 높음", "#e74c3c")
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div class='center-content'><div class='metric-val'>{info['idx']}</div><span class='status-badge' style='background-color:{col};'>{s}</span><br><small>검색량 대비 문서 발행 비율</small></div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>✍️<br><small><b>블로그</b></small><br><b>{info['b']:,}</b><br><small>{(info['b']/info['doc']*100 if info['doc']>0 else 0):.1f}%</small></div>
                <div>👥<br><small><b>카페</b></small><br><b>{info['c']:,}</b><br><small>{(info['c']/info['doc']*100 if info['doc']>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{info['doc']:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div class='center-content'><div class='metric-val'>{info['rec']}건</div><br><small>최근 30일 이내 등록된 글</small></div></div>""", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📋 연관 키워드 상세 리스트")
        df = pd.DataFrame(res)
        m_cols = [("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"), ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"), ("최근 한 달\n발행량", " "), ("경쟁강도", " ")]
        df = df[["key", "p", "m", "t", "b", "c", "doc", "rec", "idx"]]
        df.columns = pd.MultiIndex.from_tuples(m_cols)
        
        # 가운데 정렬 스타일 적용 출력
        st.dataframe(df.style.set_properties(**{'text-align': 'center'}).background_gradient(cmap='YlOrRd', subset=[("경쟁강도", " ")]), use_container_width=True, hide_index=True, height=580)

# 쇼핑, 뉴스, 구글 트렌드 로직 복구
elif st.session_state.page == "SHOP": st.title("🛍️ 쇼핑 인기 트렌드")
elif st.session_state.page == "NEWS": st.title("📰 오늘의 뉴스 이슈")
elif st.session_state.page == "GOOGLE": st.title("🌐 구글 실시간 트렌드")