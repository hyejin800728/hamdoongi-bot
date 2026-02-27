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

# --- [데이터 수집] v17 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_v17(target_kw):
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
            t, blog_res = p + m, requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100", headers=auth_h).json()
            b_v = blog_res.get('total', 0)
            r_v = sum(1 for post in blog_res.get('items', []) if post.get('postdate', '00000000') >= thirty_ago)
            c_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_h).json().get('total', 0)
            results.append({
                "v17_kw": kw, "v17_p": p, "v17_m": m, "v17_t": t, 
                "v17_b": b_v, "v17_c": c_v, "v17_d": b_v + c_v, 
                "v17_r": r_v, "v17_i": round((b_v + c_v) / t, 2) if t > 0 else 0
            })
        return results
    except: return []

# --- [UI 디자인 반응형 설정] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; font-weight: bold !important;
        height: 4em !important; width: 100% !important;
    }

    /* 반응형 대시보드 박스 */
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 200px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    
    /* 숫자 크기: 기본(PC)은 크게, 모바일은 미디어 쿼리로 조절 */
    .metric-val { font-size: 3.2em; font-weight: 800; color: #333; }
    .sub-metric-val { font-size: 1.6em; font-weight: 800; color: #222; display: block; margin: 5px 0; }
    .sub-metric-label { font-size: 0.8em; font-weight: bold; color: #666; }

    /* 모바일 환경(너비 768px 이하) 특화 스타일 */
    @media (max-width: 768px) {
        .metric-val { font-size: 2.2em !important; }
        .sub-metric-val { font-size: 1.2em !important; }
        .quad-box { padding: 15px !important; min-height: 150px !important; }
        .quad-title { font-size: 0.9em !important; }
    }

    .status-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.75em; margin-left: 5px; vertical-align: middle; }
    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555; font-size:0.85em;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 메인 로직 ---
st.title("📊 메인 키워드 분석")
with st.form("search_form"):
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 주름개선화장품")
    submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
    
if submit and input_kw:
    with st.spinner('🐹 데이터를 정밀 분석 중...'):
        st.session_state.kw_results = fetch_keyword_data_v17(input_kw)
        st.session_state.kw_target = input_kw
        st.rerun()

if st.session_state.get('kw_results'):
    res = st.session_state.kw_results
    tgt = st.session_state.kw_target
    info = next((i for i in res if i['v17_kw'].replace(" ", "") == tgt.replace(" ", "")), res[0])

    c1, c2 = st.columns(2); c3, c4 = st.columns(2)
    # 각 박스 내부
    with c1:
        st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
            <div><span class='sub-metric-label'>💻PC</span><span class='sub-metric-val'>{info['v17_p']:,}</span></div>
            <div><span class='sub-metric-label'>📱MO</span><span class='sub-metric-val'>{info['v17_m']:,}</span></div>
            <div><span class='sub-metric-label'>➕TOT</span><span class='sub-metric-val'>{info['v17_t']:,}</span></div>
        </div></div>""", unsafe_allow_html=True)
    with c2:
        s, col = ("매우 낮음", "#2ecc71") if info['v17_i'] < 0.5 else ("낮음", "#3498db") if info['v17_i'] < 1.0 else ("보통", "#f39c12") if info['v17_i'] < 5.0 else ("높음", "#e67e22") if info['v17_i'] < 10.0 else ("매우 높음", "#e74c3c")
        st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div style='text-align:center;'><span class='metric-val'>{info['v17_i']}</span><span class='status-badge' style='background-color:{col};'>{s}</span></div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
            <div><span class='sub-metric-label'>✍️BLOG</span><span class='sub-metric-val'>{info['v17_b']:,}</span></div>
            <div><span class='sub-metric-label'>👥CAFE</span><span class='sub-metric-val'>{info['v17_c']:,}</span></div>
            <div><span class='sub-metric-label'>➕TOT</span><span class='sub-metric-val'>{info['v17_d']:,}</span></div>
        </div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div style='text-align:center;'><span class='metric-val'>{info['v17_r']}</span><span class='sub-metric-label' style='font-size:1.5em;'>건</span></div></div>""", unsafe_allow_html=True)
    
    st.divider()
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)