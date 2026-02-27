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
        "X-Timestamp": timestamp, "X-API-KEY": api_key, "X-Customer": str(customer_id),
        "X-Signature": base64.b64encode(signature).decode()
    }

# --- [데이터 수집] 캐시 리셋을 위해 완전히 새로운 함수명 사용 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_ultimate(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    headers = get_header("GET", uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    try:
        res = requests.get("https://api.naver.com" + uri, params=params, headers=headers).json()
        if 'keywordList' not in res: return []
        all_keywords = res['keywordList'][:15]
        results = []
        auth_h = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        thirty_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        for item in all_keywords:
            kw = item['relKeyword']
            def cl(v): return 10 if isinstance(v, str) and '<' in v else int(v)
            p, m = cl(item['monthlyPcQcCnt']), cl(item['monthlyMobileQcCnt'])
            t = p + m
            b_res = requests.get(f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100", headers=auth_h).json()
            b_v = b_res.get('total', 0)
            r_v = sum(1 for post in b_res.get('items', []) if post.get('postdate', '00000000') >= thirty_ago)
            c_v = requests.get(f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1", headers=auth_h).json().get('total', 0)
            # [에러 방지] 영문 키값으로 완벽 고정
            results.append({
                "kw": kw, "p": p, "m": m, "tot_s": t, "blog": b_v, "cafe": c_v, "tot_d": b_v + c_v, "rec": r_v, "idx": round((b_v + c_v) / t, 2) if t > 0 else 0
            })
        return results
    except: return []

# --- 기타 수집 보조 함수 ---
def get_naver_trends(q):
    try:
        res = requests.get(f"https://ac.search.naver.com/nx/ac?q={q}&con=0&ans=2&r_format=json&st=100").json()
        return [item[0] for item in res['items'][0]][:10]
    except: return ["데이터 로드 중..."]

# --- [UI 디자인 강제 주입] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    /* 1. 분석 버튼: 황금색 + 가로 꽉 차게 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; font-weight: bold !important;
        height: 4em !important; width: 100% !important; border: none !important;
    }

    /* 2. 대시보드 박스: 타이틀 왼쪽, 본문 가운데 */
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    .metric-val { font-size: 2.8em; font-weight: 800; color: #333; display: inline-block; }
    .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8em; margin-left: 5px; vertical-align: middle; }

    /* 3. [핵심] 시스템 CSS 강제 주입: 표 헤더 가운데 정렬 */
    [data-testid="stDataFrame"] thead tr th { text-align: center !important; font-weight: bold !important; color: #333 !important; }
    [data-testid="stDataFrame"] td { text-align: center !important; }

    /* 시스템 알림 제거 */
    [data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div><h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    if st.button("🌐 구글 실시간 트렌드", use_container_width=True): st.session_state.page = "GOOGLE"

# --- 페이지별 로직 ---

if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form"):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit = st.form_submit_button("실시간 통합 분석 시작", use_container_width=True)
        
    if submit and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_keyword_data_ultimate(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        res = st.session_state.kw_results
        tgt = st.session_state.kw_target
        # [에러 방지] 영문 키를 사용하여 KeyError 원천 차단
        try:
            info = next((i for i in res if i['kw'].replace(" ", "") == tgt.replace(" ", "")), res[0])
            c1, c2 = st.columns(2); c3, c4 = st.columns(2)
            with c1:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div>💻<br><small><b>PC</b></small><br><b>{info['p']:,}</b><br><small>{(info['p']/info['tot_s']*100 if info['tot_s']>0 else 0):.1f}%</small></div>
                    <div>📱<br><small><b>모바일</b></small><br><b>{info['m']:,}</b><br><small>{(info['m']/info['tot_s']*100 if info['tot_s']>0 else 0):.1f}%</small></div>
                    <div>➕<br><small><b>전체</b></small><br><b>{info['tot_s']:,}</b><br><small>100%</small></div>
                </div></div>""", unsafe_allow_html=True)
            with c2:
                s, col = ("매우 낮음", "#2ecc71") if info['idx'] < 0.5 else ("낮음", "#3498db") if info['idx'] < 1.0 else ("보통", "#f39c12") if info['idx'] < 5.0 else ("높음", "#e67e22") if info['idx'] < 10.0 else ("매우 높음", "#e74c3c")
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div style='text-align:center;'><div class='metric-val'>{info['idx']}</div><span class='status-badge' style='background-color:{col};'>{s}</span><br><small>검색량 대비 문서 발행 비율</small></div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                    <div>✍️<br><small><b>블로그</b></small><br><b>{info['blog']:,}</b><br><small>{(info['blog']/info['tot_d']*100 if info['tot_d']>0 else 0):.1f}%</small></div>
                    <div>👥<br><small><b>카페</b></small><br><b>{info['cafe']:,}</b><br><small>{(info['cafe']/info['tot_d']*100 if info['tot_d']>0 else 0):.1f}%</small></div>
                    <div>➕<br><small><b>전체</b></small><br><b>{info['tot_d']:,}</b><br><small>100%</small></div>
                </div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div style='text-align:center;'><div class='metric-val'>{info['rec']}건</div><br><small>최근 30일 이내 등록된 글</small></div></div>""", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📋 연관 키워드 상세 리스트")
            df = pd.DataFrame(res)
            # 계층형 표 헤더 구성
            m_cols = [("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"), ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"), ("최근 한 달\n발행량", " "), ("경쟁강도", " ")]
            df = df[["kw", "p", "m", "tot_s", "blog", "cafe", "tot_d", "rec", "idx"]]
            df.columns = pd.MultiIndex.from_tuples(m_cols)
            
            # [최종] 스타일 엔진을 통해 가운데 정렬 강제 적용
            st.dataframe(df.style.set_properties(**{'text-align': 'center'}).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center'), ('font-weight', 'bold')]}]).background_gradient(cmap='YlOrRd', subset=[("경쟁강도", " ")]), use_container_width=True, hide_index=True, height=580)
        except Exception as e: st.warning("⚠️ 캐시 데이터를 갱신 중입니다. 잠시 후 다시 시도해 주세요.")

elif st.session_state.page == "SHOP":
    st.title("🛍️ 실시간 쇼핑 트렌드")
    cats = {"💄 뷰티": "화장품", "👗 패션": "의류", "👜 잡화": "가방", "🍎 식품": "간식", "⚽ 레저": "운동", "🏠 생활": "생활용품", "💻 가전": "전자제품", "🛋️ 소품": "인테리어"}
    items = list(cats.items())
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            n, q = items[i+j]
            trends = get_naver_trends(q)
            html = "".join([f"<div style='margin-bottom:8px; text-align:left;'><span style='color:#F4B742; font-weight:bold;'>{idx+1}</span> {v}</div>" for idx, v in enumerate(trends)])
            cols[j].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:350px;'><h4>{n}</h4><br>{html}</div>", unsafe_allow_html=True)

elif st.session_state.page == "NEWS":
    st.title("📰 오늘의 뉴스 이슈")
    cats = {"🗞️ 종합": "종합", "💰 경제": "경제", "💻 IT": "IT", "🌿 생활": "생활"}
    cols = st.columns(4)
    for i, (n, q) in enumerate(cats.items()):
        url = f"https://openapi.naver.com/v1/search/news.json?query={q}&display=7"
        news = requests.get(url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}).json().get('items', [])
        html = "".join([f"<div style='margin-bottom:10px; font-size:0.85em; text-align:left;'>🔗 <a href='{x['link']}' target='_blank' style='color:#555; text-decoration:none;'>{x['title'][:25].replace('<b>','').replace('</b>','') + '...'}</a></div>" for x in news])
        cols[i].markdown(f"<div style='border:1px solid #eee; border-radius:12px; padding:15px; min-height:420px;'><h4>{n}</h4><br>{html}</div>", unsafe_allow_html=True)

elif st.session_state.page == "GOOGLE":
    st.title("🌐 구글 실시간 급상승 트렌드")
    try:
        pytrends = TrendReq(hl='ko', tz=540); df = pytrends.trending_searches(pn='south_korea'); g_trends = df[0].tolist()[:10]
        cl, cr = st.columns(2)
        for idx, v in enumerate(g_trends):
            col = cl if idx < 5 else cr
            col.markdown(f"<div style='background-color:#ffffff; padding:15px; border-radius:10px; border:1px solid #eee; margin-bottom:10px; border-left: 5px solid #4285F4; text-align:left;'>{idx+1}. {v}</div>", unsafe_allow_html=True)
    except: st.error("현재 구글 서버와 연결이 원활하지 않습니다.")