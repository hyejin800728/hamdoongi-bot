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

# --- [데이터 수집] 에러 방지를 위해 고유 영문 키 사용 ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_keyword_data_safe(target_kw):
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
            
            # [핵심] 내부 데이터 키는 절대 변하지 않는 영문으로 고정하여 KeyError 방지
            results.append({
                "kw": kw, "pc_v": pc_v, "mo_v": mo_v, "tot_s": tot_s,
                "blog_v": blog_v, "cafe_v": cafe_v, "tot_d": blog_v + cafe_v,
                "rec_v": rec_v, "comp_i": round((blog_v + cafe_v) / tot_s, 2) if tot_s > 0 else 0
            })
        return results
    except: return []

# --- [UI 디자인 정밀 설정] ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; min-width: 250px !important; }
    
    /* 1. 분석 시작 버튼 황금색 강제 적용 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #F4B742 !important; color: white !important;
        border-radius: 12px !important; border: none !important;
        font-weight: bold !important; height: 3.5em !important; width: 100% !important;
    }

    /* 2. 대시보드 박스 헤더: 왼쪽 정렬 */
    .quad-box { background-color: #FBEECC; padding: 25px; border-radius: 20px; border-left: 10px solid #F4B742; margin-bottom: 15px; min-height: 220px; }
    .quad-title { font-weight: bold !important; color: #555; font-size: 1.1em; margin-bottom: 15px; text-align: left !important; }
    
    .center-content { text-align: center; margin-top: 10px; }
    .metric-val { font-size: 2.8em; font-weight: 800; color: #333; display: inline-block; }
    .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8em; margin-left: 5px; vertical-align: middle; }

    /* 3. 표 헤더 디자인 강제 주입: 가운데 정렬 및 볼드 */
    div[data-testid="stDataFrame"] thead tr th {
        text-align: center !important;
        vertical-align: middle !important;
        font-weight: bold !important;
        color: #333 !important;
        background-color: #f8f9fa !important;
    }
    div[data-testid="stDataFrame"] td { text-align: center !important; }

    /* 4. 시스템 Running 메시지 숨기기 */
    [data-testid="stStatusWidget"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 및 사이드바 복구 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>햄스터 브레인</h2>", unsafe_allow_html=True)
    st.write("---")
    # 메뉴 버튼들 복구
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"
    if st.button("🛍️ 쇼핑 인기 트렌드", use_container_width=True): st.session_state.page = "SHOP"
    if st.button("📰 오늘의 뉴스 이슈", use_container_width=True): st.session_state.page = "NEWS"
    if st.button("🌐 구글 실시간 트렌드", use_container_width=True): st.session_state.page = "GOOGLE"
    st.write("---")
    st.markdown("<p style='text-align:center; font-weight:bold; color:#555;'>햄둥이의 햄둥지둥 일상보고서🐹💭</p>", unsafe_allow_html=True)

# --- 메인 페이지 로직 ---
if st.session_state.page == "HOME":
    st.title("📊 메인 키워드 분석")
    with st.form("search_form", clear_on_submit=False):
        input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 조말론")
        submit_button = st.form_submit_button("실시간 통합 분석 시작")
        
    if submit_button and input_kw:
        with st.spinner('🐹 데이터를 정밀 분석 중...'):
            st.session_state.kw_results = fetch_keyword_data_safe(input_kw)
            st.session_state.kw_target = input_kw
            st.rerun()

    if st.session_state.get('kw_results'):
        results = st.session_state.kw_results
        target = st.session_state.kw_target
        # [안전] 내부 영문 키 'kw'를 사용하여 데이터 추출
        info = next((i for i in results if i['kw'].replace(" ", "") == target.replace(" ", "")), results[0])

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        # 1. 월간 검색량 (타이틀 왼쪽)
        with c1:
            tot = info['tot_s']
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>🔍 월간 검색량</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>💻<br><small><b>PC</b></small><br><b>{info['pc_v']:,}</b><br><small>{(info['pc_v']/tot*100 if tot>0 else 0):.1f}%</small></div>
                <div>📱<br><small><b>모바일</b></small><br><b>{info['mo_v']:,}</b><br><small>{(info['mo_v']/tot*100 if tot>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{tot:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)

        # 2. 경쟁강도 (가운데 정렬)
        with c2:
            comp = info['comp_i']
            status, color = ("매우 낮음", "#2ecc71") if comp < 0.5 else ("낮음", "#3498db") if comp < 1.0 else ("보통", "#f39c12") if comp < 5.0 else ("높음", "#e67e22") if comp < 10.0 else ("매우 높음", "#e74c3c")
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📈 경쟁강도</div><div class='center-content'>
                <div class='metric-val'>{comp}</div><span class='status-badge' style='background-color:{color};'>{status}</span>
                <div style='color:#777; font-size:0.9em; margin-top:10px; font-weight:bold; text-align:center;'>검색량 대비 문서 발행 비율</div></div></div>""", unsafe_allow_html=True)

        # 3. 콘텐츠 누적 발행 (타이틀 왼쪽)
        with c3:
            doc_tot = info['tot_d']
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📚 콘텐츠 누적 발행</div><div style='display:flex; justify-content:space-around; text-align:center;'>
                <div>✍️<br><small><b>블로그</b></small><br><b>{info['blog_v']:,}</b><br><small>{(info['blog_v']/doc_tot*100 if doc_tot>0 else 0):.1f}%</small></div>
                <div>👥<br><small><b>카페</b></small><br><b>{info['cafe_v']:,}</b><br><small>{(info['cafe_v']/doc_tot*100 if doc_tot>0 else 0):.1f}%</small></div>
                <div>➕<br><small><b>전체</b></small><br><b>{doc_tot:,}</b><br><small>100%</small></div>
            </div></div>""", unsafe_allow_html=True)

        # 4. 최근 한 달 발행 (가운데 정렬)
        with c4:
            st.markdown(f"""<div class='quad-box'><div class='quad-title'>📅 최근 한 달 발행</div><div class='center-content'>
                <div class='metric-val'>{info['rec_v']}건</div><div style='color:#777; font-size:0.9em; margin-top:10px; font-weight:bold; text-align:center;'>최신 데이터 100건 중 30일 이내 등록된 글</div></div></div>""", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📋 연관 키워드 상세 리스트")

        # [디자인 완성] 표 계층 구조 생성 (MultiIndex)
        df = pd.DataFrame(results)
        multi_cols = [
            ("키워드", " "), ("월간 검색량", "PC"), ("월간 검색량", "모바일"), ("월간 검색량", "총합"),
            ("콘텐츠 누적발행", "블로그"), ("콘텐츠 누적발행", "카페"), ("콘텐츠 누적발행", "총합"),
            ("최근 한 달\n발행량", " "), ("경쟁강도", " ")
        ]
        # 내부 영문 데이터를 표 구조에 맞춰 매핑
        df = df[["kw", "pc_v", "mo_v", "tot_s", "blog_v", "cafe_v", "tot_d", "rec_v", "comp_i"]]
        df.columns = pd.MultiIndex.from_tuples(multi_cols)
        
        # 스타일 주입 및 출력
        st.dataframe(
            df.style.set_properties(**{'text-align': 'center'})
                    .background_gradient(cmap='YlOrRd', subset=[("경쟁강도", " ")]),
            use_container_width=True, hide_index=True, height=580
        )

# 나머지 페이지들 (SHOP, NEWS, GOOGLE) 생략 가능하나 로직 복구용
elif st.session_state.page == "SHOP": st.title("🛍️ 쇼핑 인기 트렌드")
elif st.session_state.page == "NEWS": st.title("📰 오늘의 뉴스 이슈")
elif st.session_state.page == "GOOGLE": st.title("🌐 구글 실시간 트렌드")