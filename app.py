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

# --- [데이터 수집] v20 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_v20(target_kw):
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
                "v20_kw": kw, "v20_p": p, "v20_m": m, "v20_t": t, 
                "v20_b": b_v, "v20_c": c_v, "v20_d": b_v + c_v, 
                "v20_r": r_v, "v20_idx": round((b_v + c_v) / t, 2) if t > 0 else 0
            })
        return results
    except: return []

# --- [UI 디자인 및 반응형 설정] ---
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

    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    
    /* 숫자 크기 확대 */
    .metric-val { font-size: 3.2em; font-weight: 800; color: #333; }
    .sub-metric-val { font-size: 1.8em; font-weight: 800; color: #222; display: block; margin: 2px 0; }
    .sub-metric-label { font-size: 0.85em; font-weight: bold; color: #666; }
    .sub-pct { font-size: 0.8em; color: #777; font-weight: bold; }

    @media (max-width: 768px) {
        .metric-val { font-size: 2.2em !important; }
        .sub-metric-val { font-size: 1.3em !important; }
        .quad-box { padding: 15px !important; min-height: 150px !important; }
    }

    /* 표 가운데 정렬 강제 시도 */
    div[data-testid="stDataFrame"] thead tr th { text-align: center !important; font-weight: bold !important; }
    div[data-testid="stDataFrame"] td { text-align: center !important; }

    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555; font-size:0.85em;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 페이지 로직 ---
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
        
    if submit and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_keyword_data_v20(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        res = st.session_state.kw_results
        tgt = st.session_state.kw_target
        
        try:
            # v20 이름표 검증
            if res and 'v20_kw' not in res[0]:
                st.session_state.kw_results = None
                st.rerun()
                
            info = next((i for i in res if i['v20_kw'].replace(" ", "") == tgt.replace(" ", "")), res[0])
            c1, c2 = st.columns(2); c3, c4 = st.columns(2)
            
            # 1. 월간 검색량 (숫자 확대 + 퍼센트 복구)
            with c1:
                t = info['v20_t']
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>💻 PC</span><span class='sub-metric-val'>{info['v20_p']:,}</span><span class='sub-pct'>{(info['v20_p']/t*100 if t>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>📱 모바일</span><span class='sub-metric-val'>{info['v20_m']:,}</span><span class='sub-pct'>{(info['v20_m']/t*100 if t>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>➕ 총합</span><span class='sub-metric-val'>{t:,}</span><span class='sub-pct'>100%</span></div>
                </div></div>""", unsafe_allow_html=True)
            
            with c2:
                s, col = ("매우 낮음", "#2ecc71") if info['v20_idx'] < 0.5 else ("낮음", "#3498db") if info['v20_idx'] < 1.0 else ("보통", "#f39c12") if info['v20_idx'] < 5.0 else ("높음", "#e67e22") if info['v20_idx'] < 10.0 else ("매우 높음", "#e74c3c")
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div style='text-align:center;'><span class='metric-val'>{info['v20_idx']}</span><span class='status-badge' style='background-color:{col};'>{s}</span></div></div>""", unsafe_allow_html=True)
            
            # 3. 콘텐츠 누적 발행 (숫자 확대 + 퍼센트 복구)
            with c3:
                d = info['v20_d']
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div><span class='sub-metric-label'>✍️ 블로그</span><span class='sub-metric-val'>{info['v20_b']:,}</span><span class='sub-pct'>{(info['v20_b']/d*100 if d>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>👥 카페</span><span class='sub-metric-val'>{info['v20_c']:,}</span><span class='sub-pct'>{(info['v20_c']/d*100 if d>0 else 0):.1f}%</span></div>
                    <div><span class='sub-metric-label'>➕ 총합</span><span class='sub-metric-val'>{d:,}</span><span class='sub-pct'>100%</span></div>
                </div></div>""", unsafe_allow_html=True)
            
            with c4:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div style='text-align:center;'><span class='metric-val'>{info['v20_r']}</span><span class='sub-metric-label' style='font-size:1.5em; display:inline;'>건</span></div></div>""", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📋 연관 키워드 상세 리스트")
            
            # 표 헤더 깨짐 해결: 내부 이름표를 예쁜 MultiIndex로 매핑
            df = pd.DataFrame(res)
            m_cols = [
                ("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"),
                ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"),
                ("최근 한 달\n발행량", " "), ("경쟁강도", " ")
            ]
            df_display = df[["v20_kw", "v20_p", "v20_m", "v20_t", "v20_b", "v20_c", "v20_d", "v20_r", "v20_idx"]]
            df_display.columns = pd.MultiIndex.from_tuples(m_cols)
            
            st.dataframe(df_display.style.set_properties(**{'text-align': 'center'}), use_container_width=True, hide_index=True, height=580)
        except: st.warning("⚠️ 캐시 갱신이 필요합니다. 'C' 키를 한 번만 눌러주세요!")