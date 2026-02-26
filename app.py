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

# --- [데이터] 네이버 키워드 상세 분석 (4분할 & 최근 발행량 포함) ---
@st.cache_data(ttl=600)
def fetch_keyword_data_final(target_kw):
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

        # 최근 30일 기준일 계산
        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        for item in all_keywords:
            kw = item['relKeyword']
            def clean_count(val):
                if isinstance(val, str) and '<' in val: return 10
                return int(val)
            
            pc_vol = clean_count(item['monthlyPcQcCnt'])
            mo_vol = clean_count(item['monthlyMobileQcCnt'])
            total_vol = pc_vol + mo_vol
            
            # 1. 블로그 데이터 (누적 및 최근 100개 분석)
            blog_url = f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=100&sort=sim"
            blog_res = requests.get(blog_url, headers=auth_headers).json()
            blog_total = blog_res.get('total', 0)
            
            recent_month_cnt = 0
            for post in blog_res.get('items', []):
                if post.get('postdate', '00000000') >= thirty_days_ago:
                    recent_month_cnt += 1
            
            # 2. 카페 데이터 (누적)
            cafe_url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={kw}&display=1"
            cafe_total = requests.get(cafe_url, headers=auth_headers).json().get('total', 0)
            
            total_doc = blog_total + cafe_total
            
            results.append({
                "키워드": kw,
                "PC 검색량": pc_vol,
                "모바일 검색량": mo_vol,
                "총 검색량": total_vol,
                "블로그 누적": blog_total,
                "카페 누적": cafe_total,
                "총 누적문서": total_doc,
                "최근 한 달 발행량": recent_month_cnt,
                "경쟁 강도": round(total_doc / total_vol, 2) if total_vol > 0 else 0
            })
        return results
    except Exception as e:
        return []

# --- UI 설정 (햄둥이 테마) ---
st.set_page_config(page_title="햄스터 브레인", layout="wide", page_icon="🐹")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #FBEECC; border-right: 2px solid #F4B742; }
    .quadrant-box {
        background-color: #FBEECC; padding: 20px; border-radius: 20px;
        border-left: 10px solid #F4B742; margin-bottom: 20px; min-height: 160px;
    }
    .quad-title { font-weight: bold; color: #555; font-size: 1.1em; margin-bottom: 10px; display: flex; align-items: center; }
    .quad-val { font-size: 1.8em; font-weight: 800; color: #333; margin-bottom: 5px; }
    .quad-sub { font-size: 0.85em; color: #777; }
    </style>
""", unsafe_allow_html=True)

# --- 세션 관리 ---
if 'page' not in st.session_state: st.session_state.page = "HOME"
if 'kw_results' not in st.session_state: st.session_state.kw_results = None

# --- 사이드바 ---
with st.sidebar:
    st.markdown("<div style='text-align:center; font-size:60px;'>🐹</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>햄둥이 메뉴</h3>", unsafe_allow_html=True)
    if st.button("🏠 메인 키워드 분석", use_container_width=True): st.session_state.page = "HOME"

# --- 메인 로직 ---
if st.session_state.page == "HOME":
    st.title("📊 키워드 4분할 정밀 분석 리포트")
    input_kw = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 킬리안")
    
    if st.button("실시간 통합 분석 시작", use_container_width=True):
        if input_kw:
            with st.spinner('🐹 햄둥이가 데이터를 분류하고 있어요...'):
                st.session_state.kw_results = fetch_keyword_data_final(input_kw)
                st.session_state.kw_target = input_kw
                st.rerun()

    if st.session_state.get('kw_results'):
        df = pd.DataFrame(st.session_state.kw_results)
        
        # [방어 로직] 필수 컬럼이 없으면 경고 후 중단
        required_cols = ['PC 검색량', '총 누적문서', '최근 한 달 발행량']
        if not all(col in df.columns for col in required_cols):
            st.error("⚠️ 데이터 구조가 업데이트되었습니다. 'C'를 눌러 캐시를 지우고 다시 검색해주세요!")
            st.stop()
            
        target = st.session_state.kw_target
        seed_data = df[df['키워드'].str.replace(" ", "") == target.replace(" ", "")]
        info = seed_data.iloc[0] if not seed_data.empty else df.iloc[0]

        # --- 4분할 레이아웃 배치 ---
        col_top_left, col_top_right = st.columns(2)
        col_bot_left, col_bot_right = st.columns(2)

        with col_top_left:
            st.markdown(f"""<div class='quadrant-box'><div class='quad-title'>🔍 월간 검색량</div>
                <div class='quad-val'>{info['총 검색량']:,}회</div>
                <div class='quad-sub'>💻 PC {info['PC 검색량']:,} | 📱 모바일 {info['모바일 검색량']:,}</div></div>""", unsafe_allow_html=True)

        with col_top_right:
            comp = info['경쟁 강도']
            status = "낮음" if comp < 1 else "보통" if comp < 5 else "높음"
            st.markdown(f"""<div class='quadrant-box'><div class='quad-title'>📈 분석 지표</div>
                <div class='quad-val'>{comp}</div>
                <div class='quad-sub'>경쟁 강도 수준: <b>{status}</b></div></div>""", unsafe_allow_html=True)

        with col_bot_left:
            st.markdown(f"""<div class='quadrant-box'><div class='quad-title'>📚 콘텐츠 발행량 (누적)</div>
                <div class='quad-val'>{info['총 누적문서']:,}건</div>
                <div class='quad-sub'>블로그 {info['블로그 누적']:,} | 카페 {info['카페 누적']:,}</div></div>""", unsafe_allow_html=True)

        with col_bot_right:
            recent = info['최근 한 달 발행량']
            activity = "🔥 매우 활발" if recent > 50 else "✅ 보통" if recent > 10 else "💤 정체"
            st.markdown(f"""<div class='quadrant-box'><div class='quad-title'>📅 최근 한 달 발행량 (추산)</div>
                <div class='quad-val'>{recent}건 / 100건</div>
                <div class='quad-sub'>최신 글 100개 중 한 달 내 작성 비중: <b>{activity}</b></div></div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 연관 키워드 상세 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)